import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

# Database URL from env or fallback to local Docker default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://octet:password@127.0.0.1:5432/octet"
)

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Set to True for SQL logging
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency per FastAPI che fornisce una sessione DB asincrona."""
    async with AsyncSessionLocal() as session:
        yield session
