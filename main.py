from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from database import engine
from config import settings
from routers.auth import router as auth_router
from routers.complaints import router as complaints_router
from routers.analytics import router as analytics_router
from exceptions import register_exception_handlers
from routers.attachments import router as attachments_router
from services.cache_service import get_redis
from routers.websocket import router as ws_router
import asyncio
from services.stats_service import stats_refresh_loop, refresh_live_stats
from middleware.rate_limit import RateLimitMiddleware
from routers.api_keys import router as api_keys_router
from routers.reports import router as reports_router
from routers.google_auth import router as google_auth_router
from starlette.middleware.sessions import SessionMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from services.logging_service import configure_logging, get_logger
from middleware.request_id import RequestIDMiddleware
from routers.health import router as health_router
from routers.reports import router as reports_router




@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM nyc_311_service_requests"))
        row_count = result.scalar()

    redis = await get_redis()
    await redis.ping()

    await refresh_live_stats()
    task = asyncio.create_task(stats_refresh_loop())

    logger.info(
    "startup",
    dataset_rows    = row_count,
    redis_connected = True,
    db_connected    = True,
    )

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await engine.dispose()
    logger.info("shutdown")

    

# configure structured logging before app starts
configure_logging()
logger = get_logger("main")



app = FastAPI(
    title="NYC 311 API",
    description="Internal API for NYC agency staff to manage 311 complaints",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


# Prometheues instrumentation
Instrumentator().instrument(app).expose(app)

# register exception handlers
register_exception_handlers(app)

# Routers
app.include_router(health_router)
app.include_router(reports_router)
app.include_router(google_auth_router)
app.include_router(api_keys_router)
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(analytics_router)
app.include_router(attachments_router)
app.include_router(ws_router)



@app.get("/", tags=["Health Check"])
def root():
    return {"message": "NYC 311 API is running"}


