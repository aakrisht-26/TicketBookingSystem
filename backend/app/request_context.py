"""Per-request context, carried in a context variable.

The correlation ID has to be readable from places that never see a ``Request``:
log processors, exception handlers running above the router, and later the
event bus. A context variable set by the correlation middleware reaches all of
them without threading an argument through every call site.
"""

from contextvars import ContextVar

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")

REQUEST_ID_HEADER = "X-Request-ID"


def set_request_id(request_id: str) -> None:
    """Bind the correlation ID for the current request."""
    _REQUEST_ID.set(request_id)


def current_request_id() -> str:
    """Return the correlation ID for the current request.

    Empty only outside a request, or if a failure happened above the
    correlation middleware. Callers render it as-is rather than inventing a
    substitute, so a missing ID is visible rather than disguised.
    """
    return _REQUEST_ID.get()
