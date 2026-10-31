"""Correlation ID and sanitized error response middleware (CA-11).

Complies with:
- NFR-SEC-10: Sensitive application errors shall not expose internal details
- SW Architecture §6.1, §6.2, §6.4: Correlation ID carried through all requests;
  internal 500 errors logged with correlation ID and returned generically.
- TC-F4-13: Error responses do not leak internal implementation details
"""

import logging
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("upskill.api")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or preserves X-Correlation-ID for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract existing correlation ID or generate a new UUIDv4
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state so route handlers and exception handlers can access it
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers that sanitize internal errors (NFR-SEC-10, TC-F4-13)."""

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

        # Log internal details server-side with correlation id for debugging
        logger.error(
            f"Unhandled server error [correlation_id={correlation_id}]: {exc}",
            exc_info=True,
        )

        # Return generic sanitized payload with correlation_id
        # No stack trace, token, or internal DB details leaked (NFR-SEC-10)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred",
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id},
        )
