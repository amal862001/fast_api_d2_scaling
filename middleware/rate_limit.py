import time
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from services.cache_service import get_redis

# Rate Limits
AUTHENTICATED_LIMIT   = 200   # req/min
UNAUTHENTICATED_LIMIT = 30    # req/min
WINDOW_SECONDS        = 60


# Paths that skip rate limiting
EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/redoc",
                "/metrics", "/health/live", "/health/ready"}


class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        # skip exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Identify client
        api_key    = request.headers.get("X-API-Key")
        forwarded  = request.headers.get("X-Forwarded-For")
        client_ip  = forwarded.split(",")[0].strip() if forwarded else request.client.host

        # authenticated if API key present or Authorization header present
        auth_header    = request.headers.get("Authorization")
        is_authed      = bool(api_key or auth_header)
        limit          = AUTHENTICATED_LIMIT if is_authed else UNAUTHENTICATED_LIMIT
        identifier     = api_key if api_key else client_ip
        redis_key      = f"rate_limit:{identifier}"

        # Sliding window via Redis sorted set
        redis      = await get_redis()
        now        = time.time()
        window_start = now - WINDOW_SECONDS

        pipe = redis.pipeline()
        # 1. add current request timestamp as score AND member
        pipe.zadd(redis_key, {str(now): now})
        # 2. remove all entries older than 60 seconds
        pipe.zremrangebyscore(redis_key, 0, window_start)
        # 3. count remaining entries = requests in last 60s
        pipe.zcard(redis_key)
        # 4. set key expiry so Redis auto-cleans idle clients
        pipe.expire(redis_key, WINDOW_SECONDS * 2)
        results    = await pipe.execute()

        request_count = results[2]   # zcard result
        remaining     = max(0, limit - request_count)

        # Over limit → 429 with Retry-After header
        if request_count > limit:
            retry_after = WINDOW_SECONDS
            return Response(
                content      = json.dumps({
                    "error"               : "rate_limit_exceeded",
                    "retry_after_seconds" : retry_after,
                    "limit"               : limit,
                    "window_seconds"      : WINDOW_SECONDS
                }),
                status_code  = 429,
                media_type   = "application/json",
                headers      = {
                    "Retry-After"          : str(retry_after),
                    "X-RateLimit-Limit"    : str(limit),
                    "X-RateLimit-Remaining": "0"
                }
            )

        # Under limit → pass through 
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response