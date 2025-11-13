#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models para proveedores.

Define esquemas para gestión de proveedores, cotizaciones y comunicación.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from decimal import Decimal
from enum import Enum


class SupplierStatus(str, Enum):
    """Estados del proveedor."""
    PENDING = "pending"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    NEGOTIATING = "negotiating"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLACKLISTED = "blacklisted"


class SupplierRating(str, Enum):
    """Rating de confiabilidad del proveedor."""
    UNKNOWN = "unknown"
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"
    VERIFIED = "verified"


class CommunicationType(str, Enum):
    """Tipos de comunicación."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    PLATFORM = "platform"


class SupplierBase(BaseModel):
    """
    Modelo base de proveedor.
    
    Attributes:
        name: Nombre del proveedor
        country: País de origen
        email: Email de contacto
        phone: Teléfono de contacto
        website: Sitio web
        rating: Rating de confiabilidad
        min_order_quantity: Cantidad mínima de orden (MOQ)
        payment_terms: Términos de pago
    """
    name: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    rating: SupplierRating = SupplierRating.UNKNOWN
    min_order_quantity: Optional[int] = Field(None, gt=0)
    payment_terms: Optional[str] = Field(None, max_length=200)


class SupplierCreate(SupplierBase):
    """Modelo para crear nuevo proveedor."""
    # Additional fields for creation
    notes: Optional[str] = Field(None, max_length=2000)
    source: Optional[str] = Field(
        None,
        description="Discovery source (alibaba, amazon, manual, etc.)"
    )


class SupplierUpdate(BaseModel):
    """Modelo para actualizar proveedor."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[SupplierRating] = None
    status: Optional[SupplierStatus] = None
    min_order_quantity: Optional[int] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(SupplierBase):
    """
    Modelo de respuesta de proveedor.
    
    Incluye ID, timestamps y estadísticas.
    """
    id: int
    status: SupplierStatus
    products_count: int = Field(default=0, description="Number of products supplied")
    total_orders: int = Field(default=0, description="Total orders placed")
    total_spent: Decimal = Field(default=Decimal("0"), description="Total amount spent")
    last_contact_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductQuote(BaseModel):
    """
    Cotización de producto por proveedor.
    
    Attributes:
        product_name: Nombre del producto
        unit_price: Precio unitario
        moq: Minimum Order Quantity
        lead_time_days: Tiempo de entrega en días
        shipping_cost: Costo de envío
        sample_available: Muestra disponible
        sample_cost: Costo de muestra
    """
    product_name: str
    unit_price: Decimal = Field(..., gt=0)
    moq: int = Field(..., gt=0)
    lead_time_days: int = Field(..., ge=0)
    shipping_cost: Optional[Decimal] = Field(None, ge=0)
    sample_available: bool = False
    sample_cost: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None


class SupplierQuoteResponse(BaseModel):
    """
    Respuesta de cotización del proveedor.
    
    Agrupa múltiples productos cotizados.
    """
    supplier_id: int
    supplier_name: str
    quotes: List[ProductQuote]
    total_cost: Decimal
    estimated_delivery: date
    valid_until: date
    received_at: datetime


class SupplierContactRequest(BaseModel):
    """
    Request para contactar proveedores.
    
    Genera y envía mensajes automáticos a proveedores.
    
    Attributes:
        asin: ASIN del producto de interés
        supplier_ids: IDs de proveedores a contactar (vacío = buscar automáticamente)
        message_template: Template de mensaje personalizado
        quantity: Cantidad de interés
        auto_send: Enviar automáticamente (sin confirmación)
    """
    asin: str = Field(..., min_length=10, max_length=10)
    supplier_ids: Optional[List[int]] = Field(
        None,
        description="Specific supplier IDs to contact (empty = auto-find)"
    )
    message_template: Optional[str] = Field(
        None,
        description="Custom message template"
    )
    quantity: int = Field(default=100, gt=0, description="Quantity of interest")
    auto_send: bool = Field(
        default=False,
        description="Send automatically without confirmation"
    )


class SupplierContactResponse(BaseModel):
    """
    Response de contacto con proveedores.
    
    Confirma envío de mensajes.
    """
    task_id: str
    asin: str
    suppliers_contacted: int
    messages_generated: List[Dict[str, Any]]
    status: str
    estimated_response_time: str = Field(
        default="24-48 hours",
        description="Expected response time"
    )


class CommunicationLog(BaseModel):
    """
    Log de comunicación con proveedor.
    
    Attributes:
        supplier_id: ID del proveedor
        type: Tipo de comunicación
        direction: Dirección (inbound/outbound)
        subject: Asunto del mensaje
        content: Contenido del mensaje
        timestamp: Timestamp de la comunicación
        response_to: ID del mensaje al que responde
    """
    id: int
    supplier_id: int
    type: CommunicationType
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    subject: Optional[str] = None
    content: str
    timestamp: datetime
    response_to: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class SupplierSearchRequest(BaseModel):
    """
    Request para buscar proveedores.
    
    Attributes:
        product_name: Nombre del producto a buscar
        category: Categoría del producto
        max_results: Máximo de resultados
        countries: Países preferidos
        min_rating: Rating mínimo
    """
    product_name: str = Field(..., min_length=1)
    category: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)
    countries: Optional[List[str]] = Field(
        None,
        description="Preferred countries (e.g., ['China', 'Vietnam'])"
    )
    min_rating: Optional[SupplierRating] = None


class SupplierListResponse(BaseModel):
    """Lista paginada de proveedores."""
    suppliers: List[SupplierResponse]
    total: int
    limit: int
    offset: int

