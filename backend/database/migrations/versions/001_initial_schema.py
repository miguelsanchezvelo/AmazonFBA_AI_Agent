"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema with all tables."""
    
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asin', sa.String(10), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bsr', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(200), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_products_asin', 'products', ['asin'])
    op.create_index('idx_products_title', 'products', ['title'])
    
    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('data', postgresql.JSON(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_analyses_product_id', 'analyses', ['product_id'])
    op.create_index('idx_analyses_type', 'analyses', ['analysis_type'])
    
    # Create suppliers table
    op.create_table(
        'suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('communication_history', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_suppliers_email', 'suppliers', ['email'])
    
    # Create supplier_products association table
    op.create_table(
        'supplier_products',
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('supplier_id', 'product_id')
    )
    op.create_index('idx_supplier_product', 'supplier_products', ['supplier_id', 'product_id'])
    
    # Create inventory table
    op.create_table(
        'inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('last_order_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_restock_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reorder_point', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_inventory_product_id', 'inventory', ['product_id'])
    op.create_index('idx_inventory_location', 'inventory', ['location'])
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('idx_events_type', 'events', ['event_type'])
    op.create_index('idx_events_status', 'events', ['status'])
    op.create_index('idx_events_created_at', 'events', ['created_at'])
    
    # Create api_cache table
    op.create_table(
        'api_cache',
        sa.Column('key', sa.String(500), primary_key=True),
        sa.Column('value', postgresql.JSON(), nullable=False),
        sa.Column('ttl', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_api_cache_key', 'api_cache', ['key'])
    op.create_index('idx_api_cache_expires_at', 'api_cache', ['expires_at'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('api_cache')
    op.drop_table('events')
    op.drop_table('inventory')
    op.drop_table('supplier_products')
    op.drop_table('suppliers')
    op.drop_table('analyses')
    op.drop_table('products')

