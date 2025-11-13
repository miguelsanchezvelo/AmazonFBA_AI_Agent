"""Seed data migration

Revision ID: 002_seed_data
Revises: 001_initial_schema
Create Date: 2025-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_seed_data'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add seed data for development/testing."""
    # This migration can be used to add initial seed data
    # For now, it's empty - seed data can be added via CSV migration script
    pass


def downgrade() -> None:
    """Remove seed data."""
    # Remove seed data if needed
    pass

