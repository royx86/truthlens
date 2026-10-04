"""
TruthLens – Database Engine, Session Factory, and Initialization.
Configured for PostgreSQL (via asyncpg) with graceful local fallback for development.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _resolve_db_url(url: str) -> str:
    """Normalize database URL for asyncpg / aiosqlite."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def _create_engine(url: str) -> AsyncEngine:
    """Create an async engine with appropriate kwargs for the target database."""
    kwargs: dict = {"echo": False}
    # pool_size / max_overflow / pool_pre_ping are not supported by SQLite
    if "sqlite" not in url:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return create_async_engine(url, **kwargs)


# Resolve configured URL (PostgreSQL by default from settings.database_url)
_target_url = _resolve_db_url(settings.database_url)

_active_engine: AsyncEngine = _create_engine(_target_url)

_active_session_maker = async_sessionmaker(
    bind=_active_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

engine = _active_engine


@asynccontextmanager
async def AsyncSessionLocal() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a session from the active sessionmaker."""
    async with _active_session_maker() as session:
        yield session


async def init_db() -> None:
    """
    Initialize database schema (create tables if they don't exist).
    If PostgreSQL is unreachable, falls back to local SQLite to ensure
    seamless local development without crashing the app.
    """
    global _active_engine, _active_session_maker

    try:
        async with _active_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            # Ensure model metadata is loaded before create_all
            import app.db.models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)

            # Auto-migrate any missing columns on PostgreSQL if table pre-existed
            target_str = str(_target_url)
            if "postgresql" in target_str or "postgres" in target_str:
                await conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            -- 1. Ensure auto-incrementing sequence for id
                            CREATE SEQUENCE IF NOT EXISTS users_id_seq;
                            ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');
                            ALTER SEQUENCE users_id_seq OWNED BY users.id;
                            PERFORM setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false);

                            -- 2. Ensure id is primary key
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conrelid = 'users'::regclass AND contype = 'p'
                            ) THEN
                                ALTER TABLE users ADD PRIMARY KEY (id);
                            END IF;

                            -- 3. Ensure hashed_password exists
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'hashed_password'
                            ) THEN
                                IF EXISTS (
                                    SELECT 1 FROM information_schema.columns 
                                    WHERE table_name = 'users' AND column_name = 'password'
                                ) THEN
                                    ALTER TABLE users RENAME COLUMN password TO hashed_password;
                                ELSIF EXISTS (
                                    SELECT 1 FROM information_schema.columns 
                                    WHERE table_name = 'users' AND column_name = 'password_hash'
                                ) THEN
                                    ALTER TABLE users RENAME COLUMN password_hash TO hashed_password;
                                ELSE
                                    ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) DEFAULT '' NOT NULL;
                                END IF;
                            END IF;

                            -- 4. Ensure name exists
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'name'
                            ) THEN
                                ALTER TABLE users ADD COLUMN name VARCHAR(120) DEFAULT '' NOT NULL;
                            END IF;

                            -- 5. Ensure email exists
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'email'
                            ) THEN
                                ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT '' NOT NULL;
                            END IF;

                            -- 6. Ensure created_at exists and has default
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'created_at'
                            ) THEN
                                ALTER TABLE users ADD COLUMN created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL;
                            ELSE
                                ALTER TABLE users ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
                            END IF;
                        END $$;
                        """
                    )
                )
        logger.info("Successfully connected to primary PostgreSQL database: %s", settings.database_url)
    except Exception as exc:
        logger.warning(
            "Primary database (%s) connection failed: %s. "
            "Falling back to local SQLite database (truthlens.db) for development.",
            settings.database_url,
            exc,
        )
        fallback_url = "sqlite+aiosqlite:///./truthlens.db"
        _active_engine = _create_engine(fallback_url)
        _active_session_maker = async_sessionmaker(
            bind=_active_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with _active_engine.begin() as conn:
            import app.db.models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Initialized fallback local SQLite database: %s", fallback_url)


_initialized = False


async def ensure_db() -> None:
    """Ensure database has been initialized once."""
    global _initialized
    if not _initialized:
        await init_db()
        _initialized = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields an async DB session."""
    await ensure_db()
    async with _active_session_maker() as session:
        yield session
