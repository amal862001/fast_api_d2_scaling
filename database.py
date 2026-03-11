from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings

engine = create_async_engine(settings.DATABASE_URL,pool_size=20, max_overflow=40, echo=True, pool_timeout=30)  # Adjust pool settings as needed

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # expire_on_commit=False to prevent objects from being expired after commit


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()