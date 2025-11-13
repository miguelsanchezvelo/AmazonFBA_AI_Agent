#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Models - Modelos de base de datos para tracking de negocio FBA.

Estos modelos almacenan datos históricos de:
- KPIs de negocio
- Oportunidades de ganancia detectadas
- Decisiones de reabastecimiento
- Snapshots de competencia
- Historial de precios
- Alertas y acciones tomadas
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Numeric, Boolean, DateTime, Text, JSON, Enum as SQLEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.models import Base


class BusinessMetrics(Base):
    """
    Registro diario de métricas de negocio.
    
    Permite tracking histórico de KPIs para:
    - Análisis de tendencias
    - Reportes mensuales/anuales
    - Comparaciones período a período
    - Alertas de anomalías
    
    Attributes:
        date: Fecha del registro
        total_revenue: Ingresos totales del día
        total_profit: Ganancia neta del día
        avg_margin: Margen promedio (%)
        active_products: Número de productos activos
        units_sold: Unidades vendidas
        roi: ROI del período (%)
        stock_outs_prevented: Stock-outs prevenidos
        opportunities_found: Oportunidades detectadas
        opportunities_value: Valor total de oportunidades (USD/mes)
        metadata: Datos adicionales en JSON
    """
    
    __tablename__ = "business_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación temporal
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    
    # Métricas financieras
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    avg_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roi: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Métricas operacionales
    active_products: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Métricas de eficiencia
    stock_outs_prevented: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opportunities_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    
    # Comparativa
    growth_mom: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Month over month
    growth_yoy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Year over year
    
    # Datos adicionales
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


class ProfitOpportunityRecord(Base):
    """
    Registro histórico de oportunidades de ganancia detectadas.
    
    Permite:
    - Tracking de oportunidades a lo largo del tiempo
    - Análisis de efectividad (¿se aprovechó? ¿funcionó?)
    - ML para mejorar detección
    
    Attributes:
        opportunity_type: Tipo de oportunidad (price_increase, supplier_change, etc.)
        product_asin: ASIN del producto
        current_value: Valor actual
        suggested_value: Valor sugerido
        potential_profit_monthly: Ganancia potencial estimada (USD/mes)
        confidence: Nivel de confianza (0-1)
        reason: Razón de la oportunidad
        status: Estado (pending, approved, rejected, implemented)
        result: Resultado si se implementó (success, failed, neutral)
        actual_profit: Ganancia real obtenida (si aplica)
    """
    
    __tablename__ = "profit_opportunities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    opportunity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Valores
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_value: Mapped[float] = mapped_column(Float, nullable=False)
    potential_profit_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Confianza y razón
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_required: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Estado y resultado
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )  # pending, approved, rejected, implemented
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # success, failed, neutral
    actual_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Fechas
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    implemented_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


class ReplenishmentRecord(Base):
    """
    Registro histórico de decisiones de reabastecimiento.
    
    Permite:
    - Tracking de órdenes de compra
    - Análisis de accuracy del pronóstico
    - Optimización de parámetros (lead time, safety stock)
    
    Attributes:
        product_asin: ASIN del producto
        current_stock: Stock al momento de la decisión
        recommended_order: Cantidad recomendada por el agente
        actual_order: Cantidad realmente ordenada
        urgency: Nivel de urgencia
        forecast_sales_30d: Ventas pronosticadas
        actual_sales_30d: Ventas reales (rellenado después)
        status: Estado de la orden
        supplier_id: ID del proveedor
        estimated_delivery: Fecha estimada de recepción
        actual_delivery: Fecha real de recepción
    """
    
    __tablename__ = "replenishment_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Producto
    product_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Stock
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_order: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Urgencia
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # low, medium, high, critical
    estimated_stockout_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Pronóstico vs Real
    forecast_sales_30d: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_sales_30d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    forecast_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % de accuracy
    
    # Confianza y razón
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Estado y seguimiento
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )  # pending, approved, ordered, in_transit, received, cancelled
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Fechas
    decision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


class CompetitorSnapshot(Base):
    """
    Snapshots históricos de competidores.
    
    Permite:
    - Tracking de cambios a lo largo del tiempo
    - Análisis de estrategias de competencia
    - Detección de patrones (estacionalidad, promociones)
    
    Attributes:
        competitor_asin: ASIN del competidor
        our_asin: Nuestro ASIN relacionado
        price: Precio del competidor
        rating: Rating promedio
        review_count: Número de reviews
        bsr: Best Sellers Rank
        in_stock: Si está en stock
        has_promotion: Si tiene promoción activa
        seller_name: Nombre del vendedor
    """
    
    __tablename__ = "competitor_snapshots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    competitor_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    our_asin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Datos del competidor
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bsr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Estado
    in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    has_promotion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    seller_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Datos adicionales
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamp del snapshot
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now()
    )


class CompetitorChange(Base):
    """
    Registro de cambios detectados en competidores.
    
    Permite:
    - Auditoría de cambios competitivos
    - Análisis de efectividad de respuestas
    - ML para predecir movimientos competitivos
    
    Attributes:
        change_type: Tipo de cambio (price_drop, price_increase, etc.)
        competitor_asin: ASIN del competidor
        our_asin: Nuestro ASIN afectado
        previous_value: Valor anterior
        new_value: Valor nuevo
        impact_level: Nivel de impacto (low, medium, high, critical)
        recommendation: Recomendación del agente
        action_taken: Acción que tomamos en respuesta
        result: Resultado de la acción
    """
    
    __tablename__ = "competitor_changes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    competitor_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    our_asin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Cambio detectado
    previous_value: Mapped[str] = mapped_column(Text, nullable=False)  # Stored as string for flexibility
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    change_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Impacto y recomendación
    impact_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # low, medium, high, critical
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Respuesta y resultado
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # positive, neutral, negative
    
    # Fechas
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


class PriceHistory(Base):
    """
    Historial de precios de productos.
    
    Registra todos los cambios de precio para:
    - Análisis de elasticidad
    - Optimización de estrategias
    - Detección de patrones estacionales
    - Comparación con competencia
    
    Attributes:
        product_asin: ASIN del producto
        price: Precio
        is_our_product: Si es nuestro producto o de competidor
        source: Fuente del dato (manual, automated, competitor_scrape)
        reason: Razón del cambio (si aplica)
        sales_impact: Impacto en ventas observado
    """
    
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    product_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_our_product: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    # Precio
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    change_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Contexto
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # manual, automated, competitor_scrape
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Impacto (rellenado después)
    sales_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Ventas período anterior
    sales_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Ventas período posterior
    sales_impact_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % cambio en ventas
    
    # Timestamp
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now()
    )
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


class BusinessAlert(Base):
    """
    Registro de alertas de negocio.
    
    Centraliza todas las alertas generadas por los agentes:
    - Stock-outs inminentes
    - Bajo margen
    - Amenazas competitivas
    - Oportunidades urgentes
    
    Attributes:
        alert_type: Tipo de alerta
        severity: Severidad (low, medium, high, critical)
        title: Título breve
        message: Mensaje detallado
        action_required: Acción recomendada
        related_asin: ASIN relacionado (si aplica)
        status: Estado (pending, acknowledged, resolved, dismissed)
        acknowledged_by: Usuario que reconoció la alerta
        resolved_by: Usuario que resolvió la alerta
    """
    
    __tablename__ = "business_alerts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Tipo y severidad
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # low, medium, high, critical
    
    # Contenido
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relación
    related_asin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    agent_source: Mapped[str] = mapped_column(String(50), nullable=False)  # Agente que generó la alerta
    
    # Estado
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )  # pending, acknowledged, resolved, dismissed
    
    # Auditoría
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Fechas
    alert_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


class BusinessAction(Base):
    """
    Registro de acciones tomadas por el sistema o el usuario.
    
    Permite:
    - Auditoría completa de decisiones
    - Análisis de efectividad
    - Compliance y trazabilidad
    
    Attributes:
        action_type: Tipo de acción (price_change, order_placed, etc.)
        product_asin: ASIN afectado
        triggered_by: Quién/qué disparó la acción (agent, user, scheduled)
        parameters: Parámetros de la acción
        status: Estado de la acción
        result: Resultado de la acción
        cost: Costo de la acción (si aplica)
        revenue_impact: Impacto en revenue (si aplica)
    """
    
    __tablename__ = "business_actions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_asin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Origen
    triggered_by: Mapped[str] = mapped_column(String(100), nullable=False)  # agent name, user email, system
    triggered_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Detalles
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)  # Parámetros de la acción
    
    # Estado y resultado
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )  # pending, in_progress, completed, failed, cancelled
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Impacto financiero
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    revenue_impact: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Fechas
    action_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


class SalesForecast(Base):
    """
    Histórico de pronósticos de ventas.
    
    Permite:
    - Tracking de accuracy de modelos
    - Optimización de parámetros de pronóstico
    - Comparación de métodos (SMA vs Exp vs Prophet)
    
    Attributes:
        product_asin: ASIN del producto
        forecast_method: Método usado (sma, exp, holt_winters, prophet)
        forecast_horizon_days: Días pronosticados
        forecast_values: Array de valores pronosticados
        actual_values: Array de valores reales (rellenado después)
        mae: Mean Absolute Error
        mape: Mean Absolute Percentage Error
        confidence_intervals: Intervalos de confianza (si aplica)
    """
    
    __tablename__ = "sales_forecasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    product_asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    forecast_method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Datos del pronóstico
    forecast_values: Mapped[list] = mapped_column(JSON, nullable=False)  # Array de valores
    actual_values: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Rellenado después
    
    # Accuracy metrics (calculados después)
    mae: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Mean Absolute Error
    mape: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Mean Absolute Percentage Error
    rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Root Mean Squared Error
    
    # Intervalos de confianza (para Prophet)
    confidence_intervals: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Fechas
    forecast_generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    forecast_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

