#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models para inventario.

Define esquemas para gestión de stock, alertas y reabastecimiento.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal
from enum import Enum


class InventoryStatus(str, Enum):
    """Estados del inventario."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    REORDERING = "reordering"
    ON_ORDER = "on_order"


class AlertLevel(str, Enum):
    """Niveles de alerta de inventario."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StorageLocation(str, Enum):
    """Ubicaciones de almacenamiento."""
    AMAZON_FBA = "amazon_fba"
    WAREHOUSE = "warehouse"
    SUPPLIER = "supplier"
    IN_TRANSIT = "in_transit"
    CUSTOM = "custom"


class InventoryBase(BaseModel):
    """
    Modelo base de inventario.
    
    Attributes:
        asin: ASIN del producto
        quantity: Cantidad actual en stock
        location: Ubicación del inventario
        reorder_point: Punto de reorden
        reorder_quantity: Cantidad a reordenar
        unit_cost: Costo unitario
    """
    asin: str = Field(..., min_length=10, max_length=10)
    quantity: int = Field(..., ge=0, description="Current quantity in stock")
    location: StorageLocation = StorageLocation.AMAZON_FBA
    reorder_point: int = Field(..., gt=0, description="Reorder point threshold")
    reorder_quantity: int = Field(..., gt=0, description="Quantity to reorder")
    unit_cost: Decimal = Field(..., gt=0, description="Unit cost")
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        """Validate quantity is non-negative."""
        if value < 0:
            raise ValueError("Quantity cannot be negative")
        return value


class InventoryCreate(InventoryBase):
    """Modelo para crear registro de inventario."""
    supplier_id: Optional[int] = Field(None, description="Primary supplier ID")
    notes: Optional[str] = Field(None, max_length=1000)


class InventoryUpdate(BaseModel):
    """Modelo para actualizar inventario."""
    quantity: Optional[int] = Field(None, ge=0)
    location: Optional[StorageLocation] = None
    reorder_point: Optional[int] = Field(None, gt=0)
    reorder_quantity: Optional[int] = Field(None, gt=0)
    unit_cost: Optional[Decimal] = Field(None, gt=0)
    supplier_id: Optional[int] = None
    notes: Optional[str] = None


class InventoryResponse(InventoryBase):
    """
    Modelo de respuesta de inventario.
    
    Incluye campos calculados y estadísticas.
    """
    id: int
    product_title: Optional[str] = None
    
    # Status fields
    status: InventoryStatus
    alert_level: AlertLevel
    days_of_stock: Optional[int] = Field(
        None,
        description="Estimated days until out of stock"
    )
    
    # Statistics
    avg_daily_sales: Optional[Decimal] = Field(
        None,
        description="Average daily sales"
    )
    total_value: Decimal = Field(..., description="Total inventory value")
    
    # Supplier info
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    
    # Timestamps
    last_restock_date: Optional[datetime] = None
    next_restock_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class InventoryAdjustmentRequest(BaseModel):
    """
    Request para ajustar inventario.
    
    Attributes:
        asin: ASIN del producto
        adjustment: Cantidad a ajustar (positivo = agregar, negativo = remover)
        reason: Razón del ajuste
        reference: Referencia externa (orden, factura, etc.)
    """
    asin: str = Field(..., min_length=10, max_length=10)
    adjustment: int = Field(..., description="Quantity adjustment (+ or -)")
    reason: str = Field(..., min_length=1, max_length=200)
    reference: Optional[str] = Field(None, max_length=100)
    
    @field_validator("adjustment")
    @classmethod
    def validate_adjustment(cls, value: int) -> int:
        """Ensure adjustment is not zero."""
        if value == 0:
            raise ValueError("Adjustment cannot be zero")
        return value


class InventoryAdjustmentResponse(BaseModel):
    """Response de ajuste de inventario."""
    asin: str
    previous_quantity: int
    adjustment: int
    new_quantity: int
    status: InventoryStatus
    alert_level: AlertLevel
    timestamp: datetime


class RestockRecommendation(BaseModel):
    """
    Recomendación de reabastecimiento.
    
    Generada automáticamente por Inventory Agent.
    
    Attributes:
        asin: ASIN del producto
        current_quantity: Cantidad actual
        recommended_quantity: Cantidad recomendada a ordenar
        urgency: Urgencia del reabastecimiento
        reasoning: Explicación de la recomendación
        estimated_stockout_date: Fecha estimada de agotamiento
        confidence: Confianza de la predicción (0-100)
    """
    asin: str
    product_title: str
    current_quantity: int
    recommended_quantity: int
    urgency: AlertLevel
    reasoning: str
    estimated_stockout_date: Optional[date] = None
    estimated_cost: Decimal
    potential_lost_sales: Optional[Decimal] = None
    confidence: int = Field(..., ge=0, le=100)


class InventoryForecast(BaseModel):
    """
    Forecast de inventario.
    
    Predicción de niveles futuros de stock.
    
    Attributes:
        asin: ASIN del producto
        forecast_days: Días a pronosticar
        daily_forecast: Pronóstico diario de cantidad
        stockout_risk: Riesgo de agotamiento (0-100)
        recommended_actions: Acciones recomendadas
    """
    asin: str
    forecast_days: int = Field(..., gt=0, le=90)
    daily_forecast: List[Dict[str, int]] = Field(
        ...,
        description="List of {date: quantity}"
    )
    stockout_risk: int = Field(..., ge=0, le=100)
    recommended_actions: List[str]
    confidence: int = Field(..., ge=0, le=100)


class InventoryAlertRequest(BaseModel):
    """
    Request para configurar alertas de inventario.
    
    Attributes:
        asin: ASIN del producto
        alert_level: Nivel mínimo de alerta
        notify_email: Email para notificaciones
        notify_webhook: Webhook URL para notificaciones
    """
    asin: str = Field(..., min_length=10, max_length=10)
    alert_level: AlertLevel = AlertLevel.MEDIUM
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None


class InventoryListResponse(BaseModel):
    """Lista paginada de inventario."""
    items: List[InventoryResponse]
    total: int
    total_value: Decimal = Field(..., description="Total inventory value")
    low_stock_count: int = Field(..., description="Items with low stock")
    out_of_stock_count: int = Field(..., description="Items out of stock")
    limit: int
    offset: int


class BulkInventoryUpdate(BaseModel):
    """
    Actualización masiva de inventario.
    
    Attributes:
        updates: Lista de actualizaciones
        notify_on_errors: Notificar errores
    """
    updates: List[Dict[str, Any]] = Field(
        ...,
        description="List of {asin, quantity, ...}"
    )
    notify_on_errors: bool = True


class BulkInventoryResponse(BaseModel):
    """Response de actualización masiva."""
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)

