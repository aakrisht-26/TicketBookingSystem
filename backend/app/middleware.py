"""HTTP middleware.

Written against the raw ASGI interface rather than Starlette's
``BaseHTTPMiddleware``. See ``docs/adr/0004-pure-asgi-middleware.md``: the base
class buffers the response through an anyio memory stream, which breaks the
server-sent event stream added in step 10.
"""

import re
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.request_context import REQUEST_ID_HEADER, set_request_id

_logger = structlog.get_logger(__name__)

# A correlation ID is echoed into responses and into logs, so an inbound value
# is only trusted if it is short and unambiguously safe to render.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_UNHANDLED_STATUS_CODE = 500


class CorrelationIdMiddleware:
    """Give every request a correlation ID and attach it to logs and responses.

    Takes the client's ``X-Request-ID`` when it is well formed, so a trace
    started at a load balancer or a browser survives into this process, and
    generates one otherwise. The ID goes into a context variable before
    anything else runs, which is what lets the log processor stamp it onto
    every line and the error handlers put it in every error body. It is echoed
    on the response so a client can quote it.

    There is deliberately no unbinding step. Each request is handled in its own
    task with its own copy of the context, and the ID is set unconditionally at
    the top of every request, so one request cannot observe another's.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._resolve_request_id(Headers(scope=scope))
        set_request_id(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # Error handlers set the header themselves, because a failure
                # above this middleware never reaches this wrapper.
                if REQUEST_ID_HEADER not in headers:
                    headers.append(REQUEST_ID_HEADER, request_id)
            await send(message)

        await self.app(scope, receive, send_with_request_id)

    @staticmethod
    def _resolve_request_id(headers: Headers) -> str:
        incoming = headers.get(REQUEST_ID_HEADER)
        if incoming is not None and _SAFE_REQUEST_ID.fullmatch(incoming):
            return incoming
        return uuid.uuid4().hex


class AccessLogMiddleware:
    """Log one structured line per request.

    This is what makes the correlation ID useful: it is the line an operator
    greps for after a user quotes an ID from an error response. uvicorn's own
    access log is disabled in favour of it, because uvicorn cannot see the
    correlation context and reports the status of a response produced by an
    exception handler inconsistently.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 0

        async def send_capturing_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_capturing_status)
        except Exception:
            # The response has not been produced yet; the handler above this
            # middleware turns this into a 500. Log the request at the status
            # the client will actually see, then let it propagate.
            _logger.info(
                "request.completed",
                method=scope["method"],
                path=scope["path"],
                status_code=_UNHANDLED_STATUS_CODE,
            )
            raise

        _logger.info(
            "request.completed",
            method=scope["method"],
            path=scope["path"],
            status_code=status_code,
        )
