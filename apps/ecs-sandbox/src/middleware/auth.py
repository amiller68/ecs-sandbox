"""X-Sandbox-Secret authentication middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret: str):
        super().__init__(app)
        self.secret = secret

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check and web terminal (WS does its own token check)
        if request.url.path == "/health" or request.url.path.startswith("/web"):
            return await call_next(request)

        provided = request.headers.get("X-Sandbox-Secret")
        if not provided or provided != self.secret:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing X-Sandbox-Secret header"},
            )

        return await call_next(request)
