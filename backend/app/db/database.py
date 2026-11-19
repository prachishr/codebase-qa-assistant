
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings


# Convert PostgreSQL URL to asyncpg format
database_url = settings.DATABASE_URL

if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1
    )
elif database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1
    )


# Create asynchronous database engine
engine = create_async_engine(
    database_url,
    connect_args={"ssl": "require"},
    pool_pre_ping=True
)


# Create asynchronous database sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


# Base class for database models
class Base(DeclarativeBase):
    pass


# FastAPI database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
