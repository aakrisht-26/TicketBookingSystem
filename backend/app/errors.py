"""The error registry.

Every failure this API can return to a client is declared here, once. A code
is stable and machine-readable: the frontend switches on ``code`` and never on
``message``, so a message can be reworded without breaking a client.

The envelope is always::

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

No stack trace, no exception type and no SQL ever reaches a client. The
correlation ID does, so a user can quote it and the matching server logs can be
found.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.request_context import REQUEST_ID_HEADER, current_request_id

_logger = structlog.get_logger(__name__)


class ErrorCode(StrEnum):
    """Machine-readable error codes.

    A code is added here in the same change that adds the condition raising it,
    and is never removed while any client might still switch on it.
    """

    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    """The HTTP status and default wording for one error code."""

    status_code: int
    message: str


ERROR_REGISTRY: Final[dict[ErrorCode, ErrorSpec]] = {
    ErrorCode.DATABASE_UNAVAILABLE: ErrorSpec(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        message="The service is not ready. The database could not be reached.",
    ),
    ErrorCode.INTERNAL_ERROR: ErrorSpec(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred. Quote the request id when reporting it.",
    ),
    ErrorCode.METHOD_NOT_ALLOWED: ErrorSpec(
        status_code=HTTP_405_METHOD_NOT_ALLOWED,
        message="That method is not allowed on this resource.",
    ),
    ErrorCode.NOT_FOUND: ErrorSpec(
        status_code=HTTP_404_NOT_FOUND,
        message="The requested resource does not exist.",
    ),
    ErrorCode.VALIDATION_ERROR: ErrorSpec(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        message="The request body or parameters failed validation.",
    ),
}

# Starlette raises bare HTTPExceptions for routing failures. These are the only
# statuses it produces that are part of this API's contract; anything else
# reaching the handler is a programming error, not a client error, and is
# reported as INTERNAL_ERROR rather than leaked in an unregistered shape.
_ROUTING_STATUS_CODES: Final[dict[int, ErrorCode]] = {
    HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
}


class AppError(Exception):
    """An error this application raises deliberately.

    Carries a registered code. The status and default message come from the
    registry, so a raise site states what went wrong and never what HTTP status
    that happens to map to.
    """

    def __init__(self, code: ErrorCode, message: str | None = None) -> None:
        self.code = code
        self.spec = ERROR_REGISTRY[code]
        self.message = message or self.spec.message
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        """The HTTP status registered for this code."""
        return self.spec.status_code


class ErrorDetail(BaseModel):
    """The body of an error response."""

    code: ErrorCode = Field(description="Stable machine-readable code. Switch on this.")
    message: str = Field(description="Human-readable explanation. Do not switch on this.")
    request_id: str = Field(description="Correlation ID, matching the X-Request-ID header.")


class ErrorResponse(BaseModel):
    """The error envelope returned by every failing endpoint."""

    error: ErrorDetail

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource does not exist.",
                    "request_id": "0f9a1c2e4b6d48f0a1b2c3d4e5f60718",
                }
            }
        }
    }


def error_response(code: ErrorCode, message: str | None = None) -> JSONResponse:
    """Build the error envelope for a registered code.

    The correlation ID is set on the response header as well as in the body,
    because a 500 raised above the correlation middleware never reaches that
    middleware's response path and would otherwise lose the header.
    """
    spec = ERROR_REGISTRY[code]
    request_id = current_request_id()
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message or spec.message,
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=spec.status_code,
        content=body.model_dump(mode="json"),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    """Render a deliberately raised AppError."""
    # Starlette types every handler as taking a bare Exception, so the narrowing
    # is a cast rather than a check. Only this class is registered for it.
    error = cast("AppError", exc)
    _logger.info(
        "request.failed",
        code=error.code.value,
        status_code=error.status_code,
        path=request.url.path,
    )
    return error_response(error.code, error.message)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Render Starlette's routing failures through the registry."""
    error = cast("StarletteHTTPException", exc)
    code = _ROUTING_STATUS_CODES.get(error.status_code)
    if code is None:
        _logger.error(
            "http_exception.unregistered_status",
            status_code=error.status_code,
            path=request.url.path,
        )
        return error_response(ErrorCode.INTERNAL_ERROR)
    return error_response(code)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Summarise a request validation failure into the envelope's message.

    Pydantic's per-field detail is flattened into the message rather than added
    as a new field, because nothing consumes a structured detail list yet. The
    step that renders field-level form errors adds the field and its test.
    """
    error = cast("RequestValidationError", exc)
    problems = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )
    _logger.info("request.validation_failed", path=request.url.path, problems=problems)
    return error_response(ErrorCode.VALIDATION_ERROR, problems or None)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Last resort. Nothing about the exception reaches the client."""
    _logger.exception(
        "request.unhandled_exception",
        exc_type=type(exc).__name__,
        path=request.url.path,
    )
    return error_response(ErrorCode.INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    """Route every exception class through the registry."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
