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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup - test database connection    ``
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        print("Database connected")

    # check Redis
    redis = await get_redis()
    await redis.ping()
    print("Redis connected")    

    # run stats once immediately on startup
    await refresh_live_stats()
    print("Live stats initialized")

    # start background loop — runs every 60s
    task = asyncio.create_task(stats_refresh_loop())

    yield

    # shutdown — cancel background task cleanly
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
     
       
    await engine.dispose()
    print("Shutdown complete")
    

app = FastAPI(
    title="NYC 311 API",
    description="Internal API for NYC agency staff to manage 311 complaints",
    version="1.0.0",
    lifespan=lifespan
)





# register exception handlers
register_exception_handlers(app)

# register routers
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(analytics_router)
app.include_router(attachments_router)
app.include_router(ws_router)


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "NYC 311 API is running"}


