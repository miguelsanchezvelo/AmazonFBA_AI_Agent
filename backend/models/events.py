#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models para eventos del sistema.

Define esquemas de eventos que fluyen entre agents a través del Event Bus.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum


class EventType(str, Enum):
    """Tipos de eventos del sistema."""
    # Discovery events
    TREND_DISCOVERY_REQUESTED = "trend_discovery_requested"
    PRODUCT_DISCOVERED = "product_discovered"
    
    # Analysis events
    ANALYSIS_REQUESTED = "analysis_requested"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    
    # Supplier events
    SUPPLIER_SEARCH_REQUESTED = "supplier_search_requested"
    SUPPLIER_FOUND = "supplier_found"
    SUPPLIER_CONTACTED = "supplier_contacted"
    SUPPLIER_RESPONSE_RECEIVED = "supplier_response_received"
    
    # Pricing events
    PRICING_REQUESTED = "pricing_requested"
    PRICE_OPTIMIZED = "price_optimized"
    PRICE_CHANGED = "price_changed"
    
    # Inventory events
    INVENTORY_UPDATED = "inventory_updated"
    INVENTORY_LOW = "inventory_low"
    INVENTORY_CRITICAL = "inventory_critical"
    RESTOCK_RECOMMENDED = "restock_recommended"
    
    # Order events
    ORDER_PLACED = "order_placed"
    ORDER_RECEIVED = "order_received"
    
    # System events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"


class EventPriority(str, Enum):
    """Prioridad de eventos."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """
    Evento base del sistema.
    
    Todos los eventos heredan de esta clase base.
    
    Attributes:
        event_id: ID único del evento
        event_type: Tipo de evento
        timestamp: Timestamp de creación
        source: Agent o sistema que genera el evento
        priority: Prioridad del evento
        correlation_id: ID para correlacionar eventos relacionados
        payload: Datos específicos del evento
    """
    event_id: str = Field(..., description="Unique event ID")
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="Source agent or system")
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = Field(
        None,
        description="ID to correlate related events"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class ProductDiscoveredEvent(BaseEvent):
    """
    Evento: Producto descubierto.
    
    Emitido por Discovery Agent cuando encuentra un producto prometedor.
    """
    event_type: EventType = EventType.PRODUCT_DISCOVERED
    
    class Payload(BaseModel):
        """Payload específico del evento."""
        asin: str
        title: str
        price: Decimal
        rating: Optional[float] = None
        reviews_count: int
        bsr: Optional[int] = None
        category: Optional[str] = None
        discovery_keyword: str
        discovery_score: int = Field(..., ge=0, le=100)


class AnalysisCompletedEvent(BaseEvent):
    """
    Evento: Análisis completado.
    
    Emitido por Analysis Agent cuando completa el análisis de un producto.
    """
    event_type: EventType = EventType.ANALYSIS_COMPLETED
    
    class Payload(BaseModel):
        """Payload específico del evento."""
        asin: str
        analysis_id: int
        viability_score: int = Field(..., ge=0, le=100)
        recommended_action: str
        profit_margin: Optional[float] = None
        roi: Optional[float] = None
        demand_score: Optional[int] = None


class SupplierFoundEvent(BaseEvent):
    """
    Evento: Proveedor encontrado.
    
    Emitido por Supplier Agent cuando encuentra proveedores potenciales.
    """
    event_type: EventType = EventType.SUPPLIER_FOUND
    
    class Payload(BaseModel):
        """Payload específico del evento."""
        asin: str
        suppliers: List[Dict[str, Any]]
        best_supplier_id: Optional[int] = None
        estimated_cost: Decimal


class PriceOptimizedEvent(BaseEvent):
    """
    Evento: Precio optimizado.
    
    Emitido por Pricing Agent cuando optimiza el precio de venta.
    """
    event_type: EventType = EventType.PRICE_OPTIMIZED
    
    class Payload(BaseModel):
        """Payload específico del evento."""
        asin: str
        old_price: Optional[Decimal] = None
        new_price: Decimal
        expected_profit: Decimal
        confidence: int = Field(..., ge=0, le=100)


class InventoryAlertEvent(BaseEvent):
    """
    Evento: Alerta de inventario.
    
    Emitido por Inventory Agent cuando el stock está bajo o crítico.
    """
    event_type: EventType = EventType.INVENTORY_LOW
    
    class Payload(BaseModel):
        """Payload específico del evento."""
        asin: str
        current_quantity: int
        reorder_point: int
        recommended_reorder: int
        urgency: str = Field(..., pattern="^(low|medium|high|critical)$")


class EventPublishRequest(BaseModel):
    """
    Request para publicar evento manualmente (debugging/testing).
    
    Permite publicar eventos desde la API para testing o triggers manuales.
    """
    event_type: EventType
    source: str = Field(default="api", description="Event source")
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    payload: Dict[str, Any]


class EventResponse(BaseModel):
    """
    Response de evento publicado.
    
    Confirma que el evento fue publicado exitosamente.
    """
    event_id: str
    event_type: EventType
    timestamp: datetime
    status: str = Field(default="published")
    subscribers_notified: int = Field(..., description="Number of subscribers notified")


class EventListResponse(BaseModel):
    """
    Lista paginada de eventos.
    
    Para consultar historial de eventos del sistema.
    """
    events: List[BaseEvent]
    total: int
    limit: int
    offset: int
    
    
class EventSubscription(BaseModel):
    """
    Suscripción a eventos para WebSocket.
    
    Cliente especifica qué eventos quiere recibir.
    """
    event_types: List[EventType] = Field(
        default_factory=list,
        description="Event types to subscribe to (empty = all)"
    )
    asins: Optional[List[str]] = Field(
        None,
        description="Filter by specific ASINs"
    )
    min_priority: EventPriority = Field(
        default=EventPriority.NORMAL,
        description="Minimum priority to receive"
    )

