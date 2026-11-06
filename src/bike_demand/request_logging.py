"""Structured request logging for the bike-demand API (Week 3, Lab 5).

Every HTTP request writes exactly one JSON line to stdout, so ``docker logs``
shows what happened without seeing the request itself. Standard library only:
no new dependency in pyproject.toml.

Logged per request: request id, method, route path, status, outcome, duration,
model version and, for a rejected request, which fields were invalid and why
(e.g. "hr:less_than_equal"), never what was sent.

Never logged: request or response bodies, field values, headers, query
strings, client addresses, environment variables, exception messages.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import IO, Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

LOGGER_NAME = "bike_demand.api"
REQUEST_ID_HEADER = "X-Request-ID"

# An incoming request id is reused only if it is short and plain; anything else
# is replaced, so a client cannot inject arbitrary text into the logs.
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_MAX_FIELD_NAME = 64

logger = logging.getLogger(LOGGER_NAME)


class JsonFormatter(logging.Formatter):
    """Render a record as one JSON object: ts, level, event, then its fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    level: str | None = None, stream: IO[str] | None = None
) -> logging.Logger:
    """Send this service's log lines to stdout as JSON.

    The level comes from the argument, else the LOG_LEVEL environment variable,
    else INFO. An unknown level raises ValueError at start-up instead of
    silently logging nothing. Calling it again replaces the handler.
    """
    level_name = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers[:] = [handler]
    logger.setLevel(level_name)
    logger.propagate = False
    return logger


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Write one structured line, e.g. log_event("model_loaded", model_version=v)."""
    logger.log(level, event, extra={"fields": fields})


def _outcome(status: int) -> tuple[str, int]:
    if status < 400:
        return "served", logging.INFO
    if status == 503:
        return "unavailable", logging.WARNING
    if status < 500:
        return "rejected", logging.INFO
    return "failed", logging.ERROR


def _request_id(request: Request) -> str:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    if _SAFE_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex[:12]


def _describe_error(err: dict[str, Any]) -> str:
    """'field:reason' for one validation error, never the submitted value.

    {"loc": ("body", "hr"), "type": "less_than_equal"} -> "hr:less_than_equal"
    A body that is not valid JSON -> "body:json_invalid".
    """
    loc = list(err.get("loc", ()))
    reason = str(err.get("type", "invalid"))
    if reason == "json_invalid" or len(loc) < 2:
        field = "body"
    else:
        field = ".".join(str(p) for p in loc[1:])
    return f"{field[:_MAX_FIELD_NAME]}:{reason}"


def _error_location(exc: BaseException) -> str | None:
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return None
    last = frames[-1]
    return f"{os.path.basename(last.filename)}:{last.lineno}"


def install_request_logging(
    app: FastAPI, get_model_version: Callable[[], str | None]
) -> None:
    """Log one line per request on ``app``.

    ``get_model_version`` returns the version of the model currently loaded
    (None when there is none); it is read at the end of each request.

    Call this after your own exception handlers are registered: the handler
    for invalid input wraps the existing one, so responses stay unchanged.
    """
    previous_handler = app.exception_handlers.get(
        RequestValidationError, request_validation_exception_handler
    )

    async def remember_invalid_fields(request: Request, exc: Exception):
        errors = exc.errors() if isinstance(exc, RequestValidationError) else []
        request.state.invalid_fields = sorted({_describe_error(e) for e in errors})
        response = previous_handler(request, exc)
        if inspect.isawaitable(response):  # the team's handler may be sync or async
            response = await response
        return response

    app.add_exception_handler(RequestValidationError, remember_invalid_fields)

    @app.middleware("http")
    async def log_each_request(request: Request, call_next):
        request_id = _request_id(request)
        started = time.perf_counter()
        fields: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }
        try:
            response = await call_next(request)
        except Exception as exc:
            fields.update(
                status=500,
                ms=round((time.perf_counter() - started) * 1000, 1),
                model_version=get_model_version(),
                error=type(exc).__name__,
                error_at=_error_location(exc),
            )
            log_event("failed", logging.ERROR, **fields)
            raise

        event, level = _outcome(response.status_code)
        fields.update(
            status=response.status_code,
            ms=round((time.perf_counter() - started) * 1000, 1),
            model_version=get_model_version(),
        )
        invalid = getattr(request.state, "invalid_fields", None)
        if invalid:
            fields["invalid_fields"] = invalid
        log_event(event, level, **fields)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
