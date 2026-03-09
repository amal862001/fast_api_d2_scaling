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



@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup - test database connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        print("Database connected")
    yield
    # shutdown
    await engine.dispose()
    print("Database disconnected")

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


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "NYC 311 API is running"}


