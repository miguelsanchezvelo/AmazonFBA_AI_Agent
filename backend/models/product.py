#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models para productos Amazon.

Define esquemas de validación para productos, búsquedas y descubrimientos.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from decimal import Decimal


class ProductBase(BaseModel):
    """
    Modelo base de producto Amazon.
    
    Attributes:
        asin: Amazon Standard Identification Number
        title: Título del producto
        price: Precio actual en USD
        rating: Calificación promedio (0-5)
        reviews_count: Número de reviews
        bsr: Best Seller Rank
        category: Categoría principal del producto
    """
    asin: str = Field(..., description="Amazon ASIN", min_length=10, max_length=10)
    title: str = Field(..., description="Product title", min_length=1, max_length=500)
    price: Decimal = Field(..., description="Current price in USD", gt=0)
    rating: Optional[float] = Field(None, description="Average rating", ge=0, le=5)
    reviews_count: int = Field(default=0, description="Number of reviews", ge=0)
    bsr: Optional[int] = Field(None, description="Best Seller Rank", gt=0)
    category: Optional[str] = Field(None, description="Main category")
    
    @field_validator("asin")
    @classmethod
    def validate_asin(cls, value: str) -> str:
        """Validate ASIN format (alphanumeric, 10 chars)."""
        if not value.isalnum():
            raise ValueError("ASIN must be alphanumeric")
        return value.upper()


class ProductCreate(ProductBase):
    """Modelo para crear nuevo producto."""
    image_url: Optional[str] = Field(None, description="Product image URL")
    url: Optional[str] = Field(None, description="Amazon product URL")
    
    # Additional discovery metadata
    search_keyword: Optional[str] = Field(None, description="Keyword used to discover")
    discovery_source: Optional[str] = Field(None, description="Discovery source (serpapi, trends, etc.)")


class ProductUpdate(BaseModel):
    """Modelo para actualizar producto existente."""
    title: Optional[str] = None
    price: Optional[Decimal] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    bsr: Optional[int] = None
    category: Optional[str] = None


class ProductResponse(ProductBase):
    """
    Modelo de respuesta de producto (incluye ID y timestamps).
    
    Se usa para retornar productos desde la API.
    """
    id: str = Field(..., description="Internal database ID (UUID as string)")
    image_url: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    
    # Calculated fields
    estimated_profit: Optional[Decimal] = None
    viability_score: Optional[float] = Field(None, ge=0, le=100)
    
    model_config = ConfigDict(from_attributes=True)


class ProductSearchRequest(BaseModel):
    """
    Request para buscar/filtrar productos.
    
    Attributes:
        keyword: Palabra clave para buscar
        category: Filtrar por categoría
        min_price: Precio mínimo
        max_price: Precio máximo
        min_rating: Rating mínimo
        max_bsr: BSR máximo (menor = mejor)
        limit: Límite de resultados
        offset: Offset para paginación
    """
    keyword: Optional[str] = Field(None, description="Search keyword")
    category: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, gt=0)
    max_price: Optional[Decimal] = Field(None, gt=0)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_bsr: Optional[int] = Field(None, gt=0)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    
    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductSearchRequest":
        """Ensure max_price > min_price when both are provided."""
        if self.max_price and self.min_price and self.max_price <= self.min_price:
            raise ValueError("max_price must be greater than min_price")
        return self


class ProductDiscoveryRequest(BaseModel):
    """
    Request para descubrir nuevos productos.
    
    Activa el Discovery Agent para encontrar productos basados en tendencias.
    
    Attributes:
        budget: Presupuesto máximo por producto
        categories: Categorías de interés
        exclude_keywords: Keywords a excluir
        min_demand_score: Score mínimo de demanda (0-100)
        max_competition: Nivel máximo de competencia (0-100)
        auto_analyze: Analizar automáticamente productos descubiertos
    """
    budget: Decimal = Field(..., description="Max budget per product", gt=0)
    categories: Optional[List[str]] = Field(
        default=None,
        description="Categories of interest"
    )
    exclude_keywords: Optional[List[str]] = Field(
        default=None,
        description="Keywords to exclude"
    )
    min_demand_score: int = Field(default=60, ge=0, le=100)
    max_competition: int = Field(default=70, ge=0, le=100)
    auto_analyze: bool = Field(
        default=True,
        description="Automatically trigger analysis for discovered products"
    )


class ProductDiscoveryResponse(BaseModel):
    """
    Response del proceso de descubrimiento.
    
    Attributes:
        task_id: ID de la tarea async
        status: Estado (pending, processing, completed)
        products_found: Número de productos encontrados
        estimated_time: Tiempo estimado en segundos
        products: Lista de productos encontrados (solo si completed)
    """
    task_id: str = Field(..., description="Async task ID")
    status: str = Field(..., description="Task status")
    products_found: int = Field(default=0, description="Products found so far")
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")
    message: str = Field(..., description="Status message")
    products: Optional[List[Dict[str, Any]]] = Field(default=None, description="Discovered products")


class ProductListResponse(BaseModel):
    """
    Response paginado de lista de productos.
    
    Attributes:
        products: Lista de productos
        total: Total de productos (sin paginación)
        limit: Límite aplicado
        offset: Offset aplicado
        has_more: Hay más resultados disponibles
    """
    products: List[ProductResponse]
    total: int = Field(..., description="Total products matching query")
    limit: int
    offset: int
    has_more: bool = Field(..., description="More results available")
    
    @property
    def count(self) -> int:
        """Número de productos en esta respuesta."""
        return len(self.products)

