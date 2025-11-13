#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models para análisis de mercado.

Define esquemas para análisis de productos, profitabilidad y demanda.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from enum import Enum


class AnalysisType(str, Enum):
    """Tipos de análisis disponibles."""
    MARKET = "market"
    PROFITABILITY = "profitability"
    DEMAND = "demand"
    COMPETITION = "competition"
    TREND = "trend"
    FULL = "full"


class AnalysisStatus(str, Enum):
    """Estados del análisis."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CompetitionLevel(str, Enum):
    """Niveles de competencia."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarketAnalysis(BaseModel):
    """
    Análisis de mercado del producto.
    
    Attributes:
        total_competitors: Número de competidores
        avg_price: Precio promedio del mercado
        price_range: Rango de precios (min, max)
        avg_rating: Rating promedio de competidores
        market_saturation: Saturación del mercado (0-100)
        competition_level: Nivel de competencia
    """
    total_competitors: int = Field(..., ge=0)
    avg_price: Decimal = Field(..., gt=0)
    price_range: tuple[Decimal, Decimal]
    avg_rating: float = Field(..., ge=0, le=5)
    market_saturation: int = Field(..., ge=0, le=100)
    competition_level: CompetitionLevel


class ProfitabilityAnalysis(BaseModel):
    """
    Análisis de profitabilidad.
    
    Calcula costos, márgenes y ROI estimado.
    
    Attributes:
        estimated_cost: Costo estimado del producto
        shipping_cost: Costo de envío estimado
        amazon_fees: Fees de Amazon estimados
        total_cost: Costo total (producto + envío + fees)
        selling_price: Precio de venta recomendado
        profit_margin: Margen de ganancia (%)
        roi: Return on Investment (%)
        break_even_units: Unidades para break-even
    """
    estimated_cost: Decimal = Field(..., gt=0)
    shipping_cost: Decimal = Field(..., ge=0)
    amazon_fees: Decimal = Field(..., ge=0)
    total_cost: Decimal = Field(..., gt=0)
    selling_price: Decimal = Field(..., gt=0)
    profit_per_unit: Decimal
    profit_margin: float = Field(..., ge=0, le=100)
    roi: float = Field(..., description="ROI percentage")
    break_even_units: int = Field(..., gt=0)


class DemandAnalysis(BaseModel):
    """
    Análisis de demanda del producto.
    
    Attributes:
        search_volume: Volumen de búsquedas mensuales
        trend_direction: Dirección de la tendencia (up, down, stable)
        seasonality_score: Score de estacionalidad (0-100)
        estimated_monthly_sales: Ventas mensuales estimadas
        demand_score: Score de demanda (0-100)
    """
    search_volume: int = Field(..., ge=0)
    trend_direction: str = Field(..., pattern="^(up|down|stable)$")
    seasonality_score: int = Field(..., ge=0, le=100)
    estimated_monthly_sales: int = Field(..., ge=0)
    demand_score: int = Field(..., ge=0, le=100)


class TrendAnalysis(BaseModel):
    """
    Análisis de tendencias temporales.
    
    Attributes:
        trend_data: Datos históricos de tendencia
        peak_months: Meses pico de demanda
        growth_rate: Tasa de crecimiento (% mensual)
        is_trending: Si está en tendencia actualmente
        confidence: Confianza del análisis (0-100)
    """
    trend_data: Dict[str, int] = Field(..., description="Month: search volume")
    peak_months: List[str]
    growth_rate: float = Field(..., description="Monthly growth rate %")
    is_trending: bool
    confidence: int = Field(..., ge=0, le=100)


class FullAnalysisResponse(BaseModel):
    """
    Análisis completo del producto.
    
    Combina todos los tipos de análisis en una respuesta única.
    """
    id: int
    product_asin: str
    analysis_type: AnalysisType = AnalysisType.FULL
    status: AnalysisStatus
    
    # Analysis components
    market: Optional[MarketAnalysis] = None
    profitability: Optional[ProfitabilityAnalysis] = None
    demand: Optional[DemandAnalysis] = None
    trend: Optional[TrendAnalysis] = None
    
    # Overall scores
    viability_score: int = Field(..., ge=0, le=100, description="Overall viability score")
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    
    # Recommendations
    recommended_action: str = Field(
        ...,
        pattern="^(buy|wait|avoid)$",
        description="Recommended action"
    )
    confidence: int = Field(..., ge=0, le=100)
    summary: str = Field(..., description="Analysis summary in plain text")
    
    # Metadata
    analyzed_at: datetime
    analysis_duration: float = Field(..., description="Duration in seconds")
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisRequest(BaseModel):
    """
    Request para iniciar análisis de producto.
    
    Attributes:
        asin: ASIN del producto a analizar
        analysis_types: Tipos de análisis a realizar
        force_refresh: Forzar análisis nuevo (ignorar caché)
        notify_on_complete: Enviar notificación WebSocket al completar
    """
    asin: str = Field(..., min_length=10, max_length=10)
    analysis_types: List[AnalysisType] = Field(
        default=[AnalysisType.FULL],
        description="Types of analysis to perform"
    )
    force_refresh: bool = Field(
        default=False,
        description="Force new analysis, ignore cache"
    )
    notify_on_complete: bool = Field(
        default=True,
        description="Send WebSocket notification on completion"
    )


class AnalysisTaskResponse(BaseModel):
    """
    Response inicial de tarea de análisis.
    
    Retorna inmediatamente con task_id para tracking async.
    """
    task_id: str
    asin: str
    status: AnalysisStatus
    estimated_time: int = Field(..., description="Estimated completion time in seconds")
    message: str


class QuickAnalysisResponse(BaseModel):
    """
    Análisis rápido simplificado.
    
    Para mostrar en listas o dashboards sin detalles completos.
    """
    asin: str
    viability_score: int = Field(..., ge=0, le=100)
    risk_level: str
    recommended_action: str
    profit_margin: Optional[float] = None
    roi: Optional[float] = None
    demand_score: Optional[int] = None
    competition_level: Optional[CompetitionLevel] = None

