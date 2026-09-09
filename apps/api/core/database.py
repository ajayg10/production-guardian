"""Database initialization and session management."""
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Async engine for application queries
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.app_debug,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def init_db() -> None:
    """Initialize database connection pool, create tables, and auto-seed if empty."""
    try:
        # Ensure models are registered on Base
        import models.database  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        logger.info("database.connected_and_tables_verified", url=_mask_db_url(settings.database_url))

        # Check if database has any production data; if not, seed automatically!
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            from models.database import Production
            result = await session.execute(select(Production).limit(1))
            prod = result.scalar_one_or_none()
            if not prod:
                logger.info("database.empty_auto_seeding")
                from database.seed.seed import seed
                await seed(session, count=10)
                logger.info("database.auto_seeding_complete")

    except Exception as e:
        logger.error("database.connection_failed", error=str(e))
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _mask_db_url(url: str) -> str:
    """Mask password in database URL for logging."""
    if "@" in url:
        prefix = url.split("@")[0]
        suffix = url.split("@")[1]
        if ":" in prefix:
            parts = prefix.rsplit(":", 1)
            return f"{parts[0]}:***@{suffix}"
    return url
