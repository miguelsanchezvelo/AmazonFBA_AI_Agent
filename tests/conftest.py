import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database.models import Base

TEST_DB_PATH = Path("tests/test_app.db")
# NOTE: File-based SQLite ensures all async connections share the same schema during tests.
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"


@pytest.fixture(scope="session")
def event_loop():
    """Create an isolated event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncEngine:
    """Async database engine bound to temporary SQLite database."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()


@pytest_asyncio.fixture()
async def async_session(test_engine: AsyncEngine) -> AsyncSession:
    """Provide a fresh async SQLAlchemy session per test."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()
