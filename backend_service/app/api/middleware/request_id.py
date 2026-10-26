import contextvars
from typing import Optional
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for correlating logs with the current request
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id_ctx", default=None
)


def get_current_request_id() -> str:
    """Retrieve the current request ID from context or return empty string."""
    return request_id_ctx.get() or "unknown"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every inbound request has an X-Request-ID header.
    Attaches the request ID to the request state and context variable,
    and returns it on the HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)
