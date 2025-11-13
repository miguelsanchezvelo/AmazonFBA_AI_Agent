#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Session Management for Async SQLAlchemy.

Maneja conexiones y sesiones async de SQLAlchemy con asyncpg para PostgreSQL.
Implementa connection pooling y manejo de errores graceful.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from backend.api.config import settings

logger = logging.getLogger(__name__)


def get_async_database_url() -> str:
    """
    Convert synchronous database URL to async URL.
    
    Converts postgresql:// to postgresql+asyncpg://
    
    Returns:
        Async database URL string
        
    Examples:
        >>> url = get_async_database_url()
        >>> assert url.startswith("postgresql+asyncpg://")
    """
    database_url = settings.database_url
    
    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        # If it's already correct or unknown format, return as is
        pass
    
    return database_url


# Create async database engine with connection pooling
async_engine: Optional[AsyncEngine] = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create async database engine.
    
    Returns:
        AsyncEngine instance with connection pooling configured
        
    Examples:
        >>> engine = get_async_engine()
        >>> assert engine is not None
    """
    global async_engine
    
    if async_engine is None:
        database_url = get_async_database_url()
        
        # SQLite requires NullPool, PostgreSQL uses QueuePool
        if database_url.startswith("sqlite"):
            pool_config = {"poolclass": NullPool}
        else:
            pool_config = {
                "poolclass": AsyncAdaptedQueuePool,
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_pre_ping": True,  # Test connections before using
            }
        
        async_engine = create_async_engine(
            database_url,
            **pool_config,
            echo=settings.debug,  # Log SQL in debug mode
            future=True,
        )
        
        logger.info(f"✅ Async database engine created: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    return async_engine


# Create async session factory
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create async session factory.
    
    Returns:
        AsyncSessionMaker instance
        
    Examples:
        >>> session_factory = get_async_session_factory()
        >>> async with session_factory() as session:
        >>>     result = await session.execute(select(Product))
    """
    global AsyncSessionLocal
    
    if AsyncSessionLocal is None:
        engine = get_async_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
    
    return AsyncSessionLocal


async def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in models using async engine.
    
    Examples:
        >>> await init_db()
        >>> # All tables created successfully
    """
    try:
        from backend.database.models import Base
        
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get async database session.
    
    Yields:
        Async database session
        
    Examples:
        >>> from fastapi import Depends
        >>> from backend.database.session import get_db
        >>> 
        >>> @app.get("/products")
        >>> async def list_products(db: AsyncSession = Depends(get_db)):
        >>>     result = await db.execute(select(Product))
        >>>     return result.scalars().all()
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
        
    Examples:
        >>> if await check_db_connection():
        >>>     print("Database is ready")
    """
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async database sessions outside of FastAPI.
    
    Yields:
        Async database session
        
    Examples:
        >>> async with get_db_session() as db:
        >>>     result = await db.execute(select(Product))
        >>>     products = result.scalars().all()
        >>>     print(f"Found {len(products)} products")
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db_connections() -> None:
    """
    Close all database connections.
    
    Should be called during application shutdown.
    
    Examples:
        >>> await close_db_connections()
        >>> # All connections closed
    """
    global async_engine
    
    if async_engine:
        await async_engine.dispose()
        async_engine = None
        logger.info("✅ Database connections closed")
