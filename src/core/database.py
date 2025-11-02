"""
Database configuration and connection management.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection manager."""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    def _create_engine(self) -> AsyncEngine:
        """Create database engine."""
        engine_kwargs = {
            "echo": settings.is_development,
            "pool_pre_ping": True,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
        }

        # Add pooling configuration for production
        if not settings.is_development:
            engine_kwargs.update({
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            })
        else:
            # Use NullPool for development to avoid connection issues
            engine_kwargs["poolclass"] = NullPool

        engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

        logger.info(
            "Database engine created",
            extra={
                "database_url": settings.DATABASE_URL.split("@")[-1],  # Log without credentials
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            }
        )

        return engine

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        if settings.is_development:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.warning("Database tables dropped")
        else:
            raise RuntimeError("Cannot drop tables in production environment")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async for session in db_manager.get_session():
        yield session


async def init_db() -> None:
    """Initialize database."""
    await db_manager.create_tables()


async def close_db() -> None:
    """Close database connections."""
    await db_manager.close()