"""Light rate limit + optional demo key for public Render deploy."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

# IP -> timestamps of recent mutating requests
_HITS: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    - GET/HEAD/OPTIONS: free
    - Mutating methods: limited per IP per minute (settings.rate_limit_per_minute)
    - X-Clearance-Key matching settings.demo_api_key bypasses limit
    - If settings.require_demo_key and demo_api_key set: writes need the key
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method.upper()
        if method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)

        path = request.url.path
        # always allow health under any method (defensive)
        if path.rstrip("/").endswith("/api/health"):
            return await call_next(request)

        key_header = request.headers.get("x-clearance-key") or request.headers.get(
            "X-Clearance-Key"
        )
        has_valid_key = bool(
            settings.demo_api_key and key_header and key_header == settings.demo_api_key
        )

        if settings.require_demo_key and settings.demo_api_key and not has_valid_key:
            return JSONResponse(
                {
                    "detail": "Demo write key required. Set X-Clearance-Key header.",
                    "hint": "Public reads are open; writes need DEMO_API_KEY when enforced.",
                },
                status_code=401,
            )

        if has_valid_key or settings.rate_limit_per_minute <= 0:
            return await call_next(request)

        ip = _client_ip(request)
        now = time.time()
        window = 60.0
        limit = settings.rate_limit_per_minute
        q = _HITS[ip]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return JSONResponse(
                {
                    "detail": f"Rate limit exceeded ({limit}/min). Retry shortly.",
                    "retry_after_seconds": int(window - (now - q[0])) if q else 60,
                },
                status_code=429,
                headers={"Retry-After": "60"},
            )
        q.append(now)
        return await call_next(request)


def reset_rate_limit_state() -> None:
    """Test helper."""
    _HITS.clear()
