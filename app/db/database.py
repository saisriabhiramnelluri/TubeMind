"""Async database connection management via Supabase PostgreSQL (asyncpg)."""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Engine and session factory (initialized lazily)
_engine = None
_async_session_factory = None


def _get_engine():
    """Get or create the async engine connected to Supabase PostgreSQL."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url

        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Please configure a Supabase PostgreSQL connection string in .env "
                "(format: postgresql+asyncpg://user:pass@host:port/dbname)"
            )

        # Normalize driver prefix — Supabase provides postgresql:// by default
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        if not url.startswith("postgresql+asyncpg://"):
            raise RuntimeError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(starting with postgresql:// or postgresql+asyncpg://). "
                "Received: %s..." % url[:30]
            )

        _engine = create_async_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        )
        logger.info("Database engine created  [driver=PostgreSQL/asyncpg, pool_size=5]")

    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency: yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables on startup."""
    engine = _get_engine()
    async with engine.begin() as conn:
        # Import models so they register with Base
        from app.db import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created or verified successfully")


async def close_db():
    """Close the database engine on shutdown."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection pool closed")
