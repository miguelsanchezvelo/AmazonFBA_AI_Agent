#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alembic Environment Configuration for Async SQLAlchemy.

Configures Alembic to work with async SQLAlchemy models and asyncpg.
"""

import asyncio
from logging.config import fileConfig
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import models to ensure all are registered with Base
from backend.database.models import Base
from backend.database.models_business import (
    BusinessMetrics,
    ProfitOpportunityRecord,
    ReplenishmentRecord,
    CompetitorSnapshot,
    CompetitorChange,
    PriceHistory,
    BusinessAlert,
    BusinessAction,
    SalesForecast
)
from backend.api.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Set database URL from settings
database_url = settings.database_url
# Convert to async URL based on database type
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql+psycopg2://"):
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite+aiosqlite://"):
    # SQLite URL is already correct for async
    pass
elif not database_url.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
    # If it's already correct or unknown format, use as is
    pass

config.set_main_option("sqlalchemy.url", database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with a connection.
    
    Args:
        connection: Database connection
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

