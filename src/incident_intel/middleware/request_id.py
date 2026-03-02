"""Add a unique request_id to every HTTP request to trace it through logs."""

import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request_id to each request.

    The request_id is:
    - Bound to the logging context (appears in all logs)
    - Added to response headers as X-Request-ID

    Note: Uses BaseHTTPMiddleware for simplicity. This is appropriate for
    this use case (header-only modification). For production systems with
    large file uploads or streaming responses, consider pure ASGI middleware
    to avoid buffering issues.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process each request and add request_id.

        Args:
            request: The incoming HTTP request.
            call_next: Function to call the next middleware/handler.

        Returns:
            The HTTP response with X-Request-ID header.
        """
        # Generate unique request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to logging context (all logs will include this)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            # Process request
            response = await call_next(request)

            # Add to response headers for client debugging
            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            # Clean up context to prevent leaking
            structlog.contextvars.clear_contextvars()
