"""structlog configuration.

Everything the process logs goes through one handler, including the records
uvicorn and SQLAlchemy emit through the standard library. Without that,
production would interleave JSON application logs with unstructured framework
lines and half the output would be unparseable by a log aggregator.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import Processor

from app.request_context import current_request_id

# uvicorn installs its own handlers on import. Left in place they print a
# second, unstructured copy of every line next to the JSON one.
_REROUTED_LOGGERS = ("uvicorn", "uvicorn.error")

# uvicorn's access log is silenced rather than rerouted, because
# AccessLogMiddleware already emits one line per request with the method,
# path and status as separate fields instead of one preformatted string.
_SILENCED_LOGGERS = ("uvicorn.access",)

# Handlers are removed by name rather than by clearing the root logger, so
# reconfiguring never silently removes a handler somebody else installed.
_HANDLER_NAME = "tbs.console"


def _add_request_id(
    _logger: Any,  # structlog fixes this signature; the logger is not used here
    _method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Stamp the correlation ID onto every line emitted during a request.

    Applied as a processor rather than left to callers, so a log line cannot be
    written without it by forgetting to bind it. This is the only mechanism
    that puts the ID into a log line: structlog's ``merge_contextvars`` would
    be a second one, and with two, neither is load-bearing and removing either
    leaves every test still passing.
    """
    request_id = current_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging(*, json_logs: bool, level: str) -> None:
    """Configure structlog and the standard library root logger.

    Idempotent: calling it twice replaces this module's handler rather than
    adding a second one, so an application factory called once per test does
    not multiply output.
    """
    shared_processors: list[Processor] = [
        _add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    handler.set_name(_HANDLER_NAME)

    root = logging.getLogger()
    for installed in [h for h in root.handlers if h.get_name() == _HANDLER_NAME]:
        root.removeHandler(installed)
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in _REROUTED_LOGGERS:
        rerouted = logging.getLogger(name)
        rerouted.handlers.clear()
        rerouted.propagate = True

    for name in _SILENCED_LOGGERS:
        silenced = logging.getLogger(name)
        silenced.handlers.clear()
        silenced.propagate = False
