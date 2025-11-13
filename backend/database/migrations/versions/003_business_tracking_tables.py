"""Add business tracking tables

Revision ID: 003
Revises: 002
Create Date: 2025-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea tablas para tracking de negocio:
    - business_metrics: KPIs diarios
    - profit_opportunities: Oportunidades detectadas
    - replenishment_records: Decisiones de reabastecimiento
    - competitor_snapshots: Snapshots de competidores
    - competitor_changes: Cambios detectados en competencia
    - price_history: Historial de precios
    - business_alerts: Alertas del sistema
    - business_actions: Acciones tomadas
    - sales_forecasts: Pronósticos de ventas
    """
    # business_metrics
    op.create_table(
        'business_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_revenue', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('total_profit', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_margin', sa.Float(), nullable=False, server_default='0'),
        sa.Column('roi', sa.Float(), nullable=False, server_default='0'),
        sa.Column('active_products', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('units_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('orders_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stock_outs_prevented', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opportunities_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opportunities_value', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('growth_mom', sa.Float(), nullable=True),
        sa.Column('growth_yoy', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_business_metrics_date', 'business_metrics', ['date'])
    
    # profit_opportunities
    op.create_table(
        'profit_opportunities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('opportunity_type', sa.String(length=50), nullable=False),
        sa.Column('product_asin', sa.String(length=20), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('suggested_value', sa.Float(), nullable=False),
        sa.Column('potential_profit_monthly', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('action_required', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('actual_profit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('implemented_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_profit_opportunities_type', 'profit_opportunities', ['opportunity_type'])
    op.create_index('ix_profit_opportunities_asin', 'profit_opportunities', ['product_asin'])
    op.create_index('ix_profit_opportunities_status', 'profit_opportunities', ['status'])
    op.create_index('ix_profit_opportunities_detected', 'profit_opportunities', ['detected_at'])
    
    # replenishment_records
    op.create_table(
        'replenishment_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_asin', sa.String(length=20), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('reorder_point', sa.Integer(), nullable=False),
        sa.Column('recommended_order', sa.Integer(), nullable=False),
        sa.Column('actual_order', sa.Integer(), nullable=True),
        sa.Column('urgency', sa.String(length=20), nullable=False),
        sa.Column('estimated_stockout_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('forecast_sales_30d', sa.Integer(), nullable=False),
        sa.Column('actual_sales_30d', sa.Integer(), nullable=True),
        sa.Column('forecast_accuracy', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('decision_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ordered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_replenishment_asin', 'replenishment_records', ['product_asin'])
    op.create_index('ix_replenishment_urgency', 'replenishment_records', ['urgency'])
    op.create_index('ix_replenishment_status', 'replenishment_records', ['status'])
    op.create_index('ix_replenishment_date', 'replenishment_records', ['decision_date'])
    
    # competitor_snapshots
    op.create_table(
        'competitor_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('competitor_asin', sa.String(length=20), nullable=False),
        sa.Column('our_asin', sa.String(length=20), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('bsr', sa.Integer(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('has_promotion', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('seller_name', sa.String(length=200), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_competitor_snapshots_competitor', 'competitor_snapshots', ['competitor_asin'])
    op.create_index('ix_competitor_snapshots_our', 'competitor_snapshots', ['our_asin'])
    op.create_index('ix_competitor_snapshots_scraped', 'competitor_snapshots', ['scraped_at'])
    
    # competitor_changes
    op.create_table(
        'competitor_changes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('competitor_asin', sa.String(length=20), nullable=False),
        sa.Column('our_asin', sa.String(length=20), nullable=True),
        sa.Column('previous_value', sa.Text(), nullable=False),
        sa.Column('new_value', sa.Text(), nullable=False),
        sa.Column('change_percentage', sa.Float(), nullable=True),
        sa.Column('impact_level', sa.String(length=20), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('action_taken', sa.Text(), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_competitor_changes_type', 'competitor_changes', ['change_type'])
    op.create_index('ix_competitor_changes_competitor', 'competitor_changes', ['competitor_asin'])
    op.create_index('ix_competitor_changes_our', 'competitor_changes', ['our_asin'])
    op.create_index('ix_competitor_changes_impact', 'competitor_changes', ['impact_level'])
    op.create_index('ix_competitor_changes_detected', 'competitor_changes', ['detected_at'])
    
    # price_history
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_asin', sa.String(length=20), nullable=False),
        sa.Column('is_our_product', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('previous_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('change_percentage', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('sales_before', sa.Integer(), nullable=True),
        sa.Column('sales_after', sa.Integer(), nullable=True),
        sa.Column('sales_impact_pct', sa.Float(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_price_history_asin', 'price_history', ['product_asin'])
    op.create_index('ix_price_history_our', 'price_history', ['is_our_product'])
    op.create_index('ix_price_history_date', 'price_history', ['effective_date'])
    
    # business_alerts
    op.create_table(
        'business_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('action_required', sa.Text(), nullable=True),
        sa.Column('related_asin', sa.String(length=20), nullable=True),
        sa.Column('agent_source', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('alert_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_business_alerts_type', 'business_alerts', ['alert_type'])
    op.create_index('ix_business_alerts_severity', 'business_alerts', ['severity'])
    op.create_index('ix_business_alerts_status', 'business_alerts', ['status'])
    op.create_index('ix_business_alerts_asin', 'business_alerts', ['related_asin'])
    op.create_index('ix_business_alerts_date', 'business_alerts', ['alert_date'])
    
    # business_actions
    op.create_table(
        'business_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('product_asin', sa.String(length=20), nullable=True),
        sa.Column('triggered_by', sa.String(length=100), nullable=False),
        sa.Column('triggered_reason', sa.Text(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('revenue_impact', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('action_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_business_actions_type', 'business_actions', ['action_type'])
    op.create_index('ix_business_actions_asin', 'business_actions', ['product_asin'])
    op.create_index('ix_business_actions_status', 'business_actions', ['status'])
    op.create_index('ix_business_actions_date', 'business_actions', ['action_date'])
    
    # sales_forecasts
    op.create_table(
        'sales_forecasts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_asin', sa.String(length=20), nullable=False),
        sa.Column('forecast_method', sa.String(length=50), nullable=False),
        sa.Column('forecast_horizon_days', sa.Integer(), nullable=False),
        sa.Column('forecast_values', sa.JSON(), nullable=False),
        sa.Column('actual_values', sa.JSON(), nullable=True),
        sa.Column('mae', sa.Float(), nullable=True),
        sa.Column('mape', sa.Float(), nullable=True),
        sa.Column('rmse', sa.Float(), nullable=True),
        sa.Column('confidence_intervals', sa.JSON(), nullable=True),
        sa.Column('forecast_generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sales_forecasts_asin', 'sales_forecasts', ['product_asin'])
    op.create_index('ix_sales_forecasts_method', 'sales_forecasts', ['forecast_method'])
    op.create_index('ix_sales_forecasts_generated', 'sales_forecasts', ['forecast_generated_at'])


def downgrade() -> None:
    """
    Elimina las tablas de tracking de negocio.
    """
    op.drop_table('sales_forecasts')
    op.drop_table('business_actions')
    op.drop_table('business_alerts')
    op.drop_table('price_history')
    op.drop_table('competitor_changes')
    op.drop_table('competitor_snapshots')
    op.drop_table('replenishment_records')
    op.drop_table('profit_opportunities')
    op.drop_table('business_metrics')

