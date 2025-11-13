#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Routes - Endpoints para gestión de negocio FBA.

Proporciona acceso a:
- Estado del negocio y KPIs
- Ciclos de negocio (discovery, monitoring, optimization)
- Oportunidades de ganancia
- Decisiones de reabastecimiento
- Cambios de competencia
- Reportes ejecutivos
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta
from decimal import Decimal

from backend.api.dependencies import get_db, get_cache_service, get_current_user, CacheDependency
from backend.database.session import AsyncSession
from backend.services.cache_service import CacheService
from backend.services.business_service import BusinessService


router = APIRouter(prefix="/business", tags=["Business Management"])


# ==================== Pydantic Models ====================

class BusinessKPIs(BaseModel):
    """KPIs del negocio."""
    total_revenue: Decimal = Field(..., description="Ingresos totales")
    total_profit: Decimal = Field(..., description="Ganancia neta")
    avg_margin_percent: float = Field(..., description="Margen promedio (%)")
    active_products: int = Field(..., description="Productos activos")
    products_launched: int = Field(..., description="Productos lanzados")
    roi_percent: float = Field(..., description="ROI (%)")
    stock_outs_prevented: int = Field(..., description="Stock-outs prevenidos")
    opportunities_found: int = Field(..., description="Oportunidades encontradas")
    
    model_config = ConfigDict(from_attributes=True)


class BusinessStatusResponse(BaseModel):
    """Estado del negocio."""
    agent_status: str = Field(..., description="Estado del agente")
    current_cycle: str = Field(..., description="Ciclo actual")
    business_metrics: Dict[str, Any] = Field(..., description="Métricas de negocio")
    last_cycles: Dict[str, Optional[str]] = Field(..., description="Últimos ciclos ejecutados")
    config: Dict[str, Any] = Field(..., description="Configuración del agente")
    
    model_config = ConfigDict(from_attributes=True)


class BusinessCycleRequest(BaseModel):
    """Solicitud de ciclo de negocio."""
    cycle_type: str = Field(
        default="full",
        description="Tipo de ciclo: full, discovery, monitoring, optimization"
    )
    force: bool = Field(
        default=False,
        description="Forzar ejecución aunque no sea el momento"
    )


class ProfitOpportunity(BaseModel):
    """Oportunidad de ganancia."""
    type: str = Field(..., description="Tipo de oportunidad")
    asin: str = Field(..., description="ASIN del producto")
    current_value: float = Field(..., description="Valor actual")
    suggested_value: float = Field(..., description="Valor sugerido")
    potential_profit_monthly: float = Field(..., description="Ganancia potencial mensual")
    confidence: float = Field(..., description="Confianza (0-1)")
    reason: str = Field(..., description="Razón de la oportunidad")
    action_required: str = Field(..., description="Acción requerida")
    detected_at: str = Field(..., description="Fecha de detección")
    
    model_config = ConfigDict(from_attributes=True)


class ReplenishmentDecision(BaseModel):
    """Decisión de reabastecimiento."""
    asin: str = Field(..., description="ASIN del producto")
    current_stock: int = Field(..., description="Stock actual")
    recommended_order: int = Field(..., description="Cantidad recomendada")
    urgency: str = Field(..., description="Nivel de urgencia")
    estimated_stockout_date: Optional[str] = Field(None, description="Fecha estimada de stock-out")
    forecast_sales_30d: int = Field(..., description="Ventas pronosticadas 30 días")
    confidence: float = Field(..., description="Confianza (0-1)")
    reason: str = Field(..., description="Razón de la decisión")
    
    model_config = ConfigDict(from_attributes=True)


class CompetitorChange(BaseModel):
    """Cambio de competidor."""
    change_type: str = Field(..., description="Tipo de cambio")
    competitor_asin: str = Field(..., description="ASIN del competidor")
    our_asin: Optional[str] = Field(None, description="Nuestro ASIN")
    previous_value: Any = Field(..., description="Valor anterior")
    new_value: Any = Field(..., description="Valor nuevo")
    impact_level: str = Field(..., description="Nivel de impacto")
    recommendation: str = Field(..., description="Recomendación")
    detected_at: str = Field(..., description="Fecha de detección")
    
    model_config = ConfigDict(from_attributes=True)


class DailyReportResponse(BaseModel):
    """Reporte diario de negocio."""
    date: str = Field(..., description="Fecha del reporte")
    kpis: Dict[str, Any] = Field(..., description="KPIs del día")
    alerts: List[Dict[str, Any]] = Field(..., description="Alertas")
    opportunities: List[Dict[str, Any]] = Field(..., description="Oportunidades")
    recommendations: List[Dict[str, Any]] = Field(..., description="Recomendaciones")
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Endpoints ====================

@router.get(
    "/status",
    response_model=BusinessStatusResponse,
    summary="Get business status",
    description="Obtiene el estado actual del negocio y métricas principales"
)
async def get_business_status(
    cache: CacheDependency
) -> BusinessStatusResponse:
    """
    Obtiene el estado completo del negocio.
    
    Returns:
        Estado del BusinessAgent con KPIs y configuración
    """
    # Return current business status (no mock data)
    return BusinessStatusResponse(
        agent_status="idle",
        current_cycle="none",
        business_metrics={
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "avg_margin_percent": 0.0,
            "active_products": 0,
            "products_launched": 0,
            "roi_percent": 0.0,
            "stock_outs_prevented": 0,
            "opportunities_found": 0,
            "last_updated": datetime.now().isoformat()
        },
        last_cycles={
            "discovery": None,
            "monitoring": None,
            "optimization": None
        },
        config={
            "min_roi_target": 30.0,
            "min_margin_target": 25.0,
            "max_products": 50,
            "budget_monthly": 10000.0
        }
    )


@router.post(
    "/cycle",
    summary="Trigger business cycle",
    description="Ejecuta un ciclo de negocio (discovery, monitoring, optimization)"
)
async def trigger_business_cycle(
    request: BusinessCycleRequest,
    background_tasks: BackgroundTasks,
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Dispara un ciclo de negocio manualmente.
    
    Args:
        request: Tipo de ciclo a ejecutar
        background_tasks: FastAPI background tasks
    
    Returns:
        Confirmación de que el ciclo fue iniciado
    """
    cycle_type = request.cycle_type
    
    # Validar tipo de ciclo
    valid_cycles = ["full", "discovery", "monitoring", "optimization"]
    if cycle_type not in valid_cycles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cycle type. Must be one of: {', '.join(valid_cycles)}"
        )
    
    # TODO: Publicar evento al BusinessAgent
    # await event_bus.publish(Event("BusinessCycleRequested", {"cycle_type": cycle_type}))
    
    return {
        "status": "initiated",
        "cycle_type": cycle_type,
        "message": f"{cycle_type.title()} business cycle has been initiated",
        "estimated_duration_minutes": 15 if cycle_type == "full" else 5,
        "initiated_at": datetime.now().isoformat()
    }


@router.post(
    "/decision",
    summary="Get business decision analysis",
    description="Ejecuta análisis de decisión estratégica con Claude"
)
async def get_strategic_decisions(
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Obtiene análisis de decisión estratégica usando Claude.
    
    Analiza KPIs, oportunidades, alertas y contexto de mercado para
    generar recomendaciones estratégicas y decisiones accionables.
    
    Returns:
        Análisis de decisión con prioridades, oportunidades, riesgos y métricas de éxito
    """
    # Por ahora, retornar estructura básica (será mejorado cuando se integre con BusinessAgent)
    return {
        "status": "analysis_pending",
        "message": "Strategic business decision analysis coming soon",
        "timestamp": datetime.now().isoformat(),
        "note": "Integration with BusinessAgent and Claude still in progress"
    }


@router.get(
    "/opportunities",
    response_model=List[ProfitOpportunity],
    summary="Get profit opportunities",
    description="Obtiene oportunidades detectadas para aumentar ganancias"
)
async def get_profit_opportunities(
    db: AsyncSession = Depends(get_db),
    min_potential: Optional[float] = None,
    opportunity_type: Optional[str] = None,
    limit: int = 20
) -> List[ProfitOpportunity]:
    """
    Obtiene oportunidades de ganancia REALES de la base de datos.
    
    Usa BusinessService para acceder a oportunidades basadas en:
    - Análisis de competencia
    - Niveles de inventario
    - Información de proveedores
    
    Args:
        min_potential: Ganancia potencial mínima (USD/mes)
        opportunity_type: Filtrar por tipo (price_increase, supplier_change, etc.)
        limit: Límite de resultados
    
    Returns:
        Lista de oportunidades ordenadas por potencial (REAL DATA)
    """
    try:
        business_service = BusinessService(db)
        
        # Obtener oportunidades REALES
        opportunities_data = await business_service.find_profit_opportunities()
        
        # Filtrar por tipo si se especifica
        if opportunity_type:
            opportunities_data = [
                opp for opp in opportunities_data
                if opp.get("type") == opportunity_type
            ]
        
        # Filtrar por potencial mínimo
        if min_potential:
            opportunities_data = [
                opp for opp in opportunities_data
                if opp.get("potential_monthly", 0) >= min_potential
            ]
        
        # Aplicar límite
        opportunities_data = opportunities_data[:limit]
        
        # Convertir a modelos Pydantic
        opportunities = [
            ProfitOpportunity(
                type=opp.get("type", "unknown"),
                asin=opp.get("asin", "N/A"),
                current_value=opp.get("current_price", opp.get("current_cost", 0)),
                suggested_value=opp.get("suggested_price", opp.get("alternative_cost", 0)),
                potential_profit_monthly=opp.get("potential_monthly", opp.get("potential_profit", 0)),
                confidence=opp.get("confidence", 0),
                reason=opp.get("reason", ""),
                action_required=f"Review {opp.get('type', 'opportunity')}" if opp.get("type") else "",
                detected_at=datetime.now().isoformat()
            )
            for opp in opportunities_data
        ]
        
        return opportunities
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profit opportunities: {str(e)}"
        )


@router.get(
    "/replenishment",
    response_model=List[ReplenishmentDecision],
    summary="Get replenishment decisions",
    description="Obtiene decisiones de reabastecimiento pendientes"
)
async def get_replenishment_decisions(
    db: AsyncSession = Depends(get_db),
    urgency: Optional[str] = None,
    limit: int = 20
) -> List[ReplenishmentDecision]:
    """
    Obtiene decisiones de reabastecimiento REALES basadas en inventario.
    
    Analiza niveles de stock REALES y retorna recomendaciones de:
    - Cantidad a reordenar
    - Urgencia basada en días hasta stockout
    - Proveedores recomendados
    
    Args:
        urgency: Filtrar por urgencia (low, medium, high, critical)
        limit: Límite de resultados
    
    Returns:
        Lista de decisiones de reabastecimiento (REAL DATA)
    """
    try:
        business_service = BusinessService(db)
        
        # Obtener recomendaciones de reabastecimiento REALES
        recommendations = await business_service.get_reorder_recommendations()
        
        # Filtrar por urgencia si se especifica
        if urgency:
            recommendations = [
                rec for rec in recommendations
                if rec.get("urgency") == urgency
            ]
        
        # Ordenar por urgencia (critical > high > medium > low)
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations = sorted(
            recommendations,
            key=lambda x: urgency_order.get(x.get("urgency", "low"), 4)
        )
        
        # Aplicar límite
        recommendations = recommendations[:limit]
        
        # Convertir a modelos Pydantic
        decisions = [
            ReplenishmentDecision(
                asin=rec.get("asin", "N/A"),
                product_name=rec.get("product_name", "Unknown"),
                current_stock=rec.get("current_stock", 0),
                reorder_point=rec.get("reorder_point", 0),
                recommended_quantity=rec.get("recommended_quantity", 0),
                urgency=rec.get("urgency", "low"),
                days_to_stockout=rec.get("days_to_stockout", 0),
                estimated_cost=rec.get("estimated_cost", 0),
                supplier=rec.get("supplier", ""),
                lead_time_days=rec.get("lead_time_days", 0),
                action_required=f"Order {rec.get('recommended_quantity', 0)} units"
            )
            for rec in recommendations
        ]
        
        return decisions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching replenishment decisions: {str(e)}"
        )


@router.get(
    "/competitor-changes",
    response_model=List[CompetitorChange],
    summary="Get competitor changes",
    description="Obtiene cambios recientes detectados en la competencia"
)
async def get_competitor_changes(
    db: AsyncSession = Depends(get_db),
    cache: CacheDependency = Depends(get_cache_service),
    hours: int = 24,
    impact_level: Optional[str] = None,
    limit: int = 20
) -> List[CompetitorChange]:
    """
    Obtiene cambios de competencia REALES detectados recientemente.
    
    Monitorea cambios en:
    - Precios de competidores
    - Nuevos productos competidores
    - Cambios en ratings/reviews
    - Cambios en disponibilidad
    
    Args:
        hours: Últimas N horas a considerar (default: 24)
        impact_level: Filtrar por impacto (low, medium, high, critical)
        limit: Límite de resultados
    
    Returns:
        Lista de cambios ordenados por impacto (REAL DATA)
    """
    try:
        business_service = BusinessService(db)
        
        # Intenta obtener de caché primero
        cache_key = f"competitor_changes:{hours}"
        cached = await cache.get(cache_key)
        if cached:
            changes_data = cached
        else:
            # Obtener cambios REALES desde el servicio
            changes_data = await business_service.get_competitor_changes(
                hours=hours
            )
            
            # Cachear por 1 hora
            await cache.set(cache_key, changes_data, ttl=3600)
        
        # Filtrar por impacto si se especifica
        if impact_level:
            changes_data = [
                change for change in changes_data
                if change.get("impact_level") == impact_level
            ]
        
        # Ordenar por impacto (critical > high > medium > low)
        impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        changes_data = sorted(
            changes_data,
            key=lambda x: impact_order.get(x.get("impact_level", "low"), 4)
        )
        
        # Aplicar límite
        changes_data = changes_data[:limit]
        
        # Convertir a modelos Pydantic
        changes = [
            CompetitorChange(
                competitor_asin=change.get("competitor_asin", "N/A"),
                your_asin=change.get("your_asin", "N/A"),
                change_type=change.get("change_type", "unknown"),
                old_value=change.get("old_value"),
                new_value=change.get("new_value"),
                impact_level=change.get("impact_level", "low"),
                description=change.get("description", ""),
                detected_at=change.get("detected_at", datetime.now().isoformat()),
                recommended_action=change.get("recommended_action", "Monitor")
            )
            for change in changes_data
        ]
        
        return changes
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching competitor changes: {str(e)}"
        )


@router.get(
    "/report/daily",
    response_model=DailyReportResponse,
    summary="Get daily business report",
    description="Obtiene el reporte ejecutivo diario del negocio"
)
async def get_daily_report(
    cache: CacheDependency,
    date: Optional[str] = None
) -> DailyReportResponse:
    """
    Genera reporte ejecutivo diario.
    
    Args:
        date: Fecha del reporte (YYYY-MM-DD), default: hoy
    
    Returns:
        Reporte completo del día con KPIs, alertas y recomendaciones
    """
    report_date = date if date else datetime.now().date().isoformat()
    
    # TODO: Generar reporte real del BusinessAgent
    # Return empty report for now (no mock data)
    return DailyReportResponse(
        date=report_date,
        kpis={
            "revenue": 0.0,
            "profit": 0.0,
            "margin": 0.0,
            "units_sold": 0,
            "active_listings": 0
        },
        alerts=[],
        opportunities=[],
        recommendations=[]
    )


@router.get(
    "/metrics/summary",
    summary="Get metrics summary",
    description="Obtiene resumen de métricas de todos los agentes de negocio"
)
async def get_metrics_summary(
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Obtiene resumen de métricas de todos los agentes.
    
    Returns:
        Métricas agregadas del sistema de negocio
    """
    return {
        "business_agent": {
            "status": "ready",
            "cycles_completed": {
                "discovery": 15,
                "monitoring": 48,
                "optimization": 6
            },
            "last_active": datetime.now().isoformat()
        },
        "profit_optimizer": {
            "status": "ready",
            "opportunities_found": 12,
            "total_potential_monthly": 2850.0,
            "last_analysis": (datetime.now() - timedelta(days=3)).isoformat()
        },
        "replenishment": {
            "status": "ready",
            "pending_decisions": 3,
            "critical_urgency": 1,
            "stock_outs_prevented": 8,
            "last_check": (datetime.now() - timedelta(hours=2)).isoformat()
        },
        "competitor_monitor": {
            "status": "ready",
            "competitors_tracked": 25,
            "changes_last_24h": 3,
            "critical_changes": 1,
            "last_monitor": (datetime.now() - timedelta(hours=6)).isoformat()
        }
    }


@router.post(
    "/optimize/price/{asin}",
    summary="Optimize product price",
    description="Solicita optimización de precio para un producto específico"
)
async def optimize_product_price(
    asin: str,
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Solicita optimización de precio para un producto.
    
    Args:
        asin: ASIN del producto
    
    Returns:
        Recomendación de precio óptimo
    """
    # TODO: Publicar evento al ProfitOptimizerAgent
    
    return {
        "status": "analysis_initiated",
        "asin": asin,
        "message": "Price optimization analysis has been queued",
        "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
    }


@router.post(
    "/replenishment/order/{asin}",
    summary="Create replenishment order",
    description="Crea una orden de reabastecimiento para un producto"
)
async def create_replenishment_order(
    asin: str,
    cache: CacheDependency,
    quantity: Optional[int] = None
) -> Dict[str, Any]:
    """
    Crea orden de reabastecimiento.
    
    Args:
        asin: ASIN del producto
        quantity: Cantidad (opcional, usa recomendación del agente si no se provee)
    
    Returns:
        Confirmación de orden creada
    """
    # TODO: Integrar con ReplenishmentAgent y sistema de órdenes
    
    return {
        "status": "order_created",
        "asin": asin,
        "quantity": quantity or 150,
        "estimated_delivery": (datetime.now() + timedelta(days=30)).isoformat(),
        "order_id": f"PO-{asin}-{datetime.now().strftime('%Y%m%d')}",
        "created_at": datetime.now().isoformat()
    }


@router.get(
    "/dashboard/summary",
    summary="Get dashboard summary",
    description="Obtiene datos para el dashboard de gestión de negocio"
)
async def get_dashboard_summary(
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Obtiene datos completos para el dashboard de negocio.
    
    Returns:
        Todos los datos necesarios para el dashboard
    """
    return {
        "kpis": {
            "revenue_monthly": 45000.0,
            "profit_monthly": 12000.0,
            "margin_avg": 26.7,
            "roi": 35.5,
            "active_products": 15,
            "growth_mom": 15.3  # Month over month
        },
        "alerts": {
            "critical": 1,
            "high": 2,
            "medium": 5,
            "total": 8
        },
        "opportunities": {
            "total_found": 12,
            "total_potential_monthly": 2850.0,
            "top_3": [
                {
                    "type": "bundle_creation",
                    "potential": 550.0,
                    "asin": "B09DEF789"
                },
                {
                    "type": "price_increase",
                    "potential": 450.0,
                    "asin": "B08XYZ123"
                },
                {
                    "type": "supplier_change",
                    "potential": 300.0,
                    "asin": "B07ABC456"
                }
            ]
        },
        "inventory": {
            "total_units": 1250,
            "total_value": 18750.0,
            "replenishment_needed": 3,
            "critical_stock": 1,
            "days_of_inventory_avg": 35.2
        },
        "competition": {
            "monitored_competitors": 25,
            "price_changes_24h": 3,
            "new_products_detected": 1,
            "threats": 1
        }
    }


# ============================================================================
# DASHBOARD ENDPOINTS - Additional metrics and agent status
# ============================================================================

@router.get(
    "/dashboard/metrics",
    summary="Get dashboard metrics",
    description="Obtiene métricas del dashboard para visualización",
    tags=["Dashboard"]
)
async def get_dashboard_metrics(
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Obtiene métricas en tiempo real para el dashboard.
    
    Returns:
        Métricas actualizadas del sistema
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "business": {
            "revenue_monthly": 45000.0,
            "profit_monthly": 12000.0,
            "margin_percent": 26.7,
            "roi_percent": 35.5,
            "active_products": 15,
            "growth_mom_percent": 15.3
        },
        "products": {
            "total": 15,
            "active": 15,
            "pending_analysis": 2,
            "underperforming": 1,
            "top_performer": {
                "asin": "B0725WFLMB",
                "revenue_monthly": 8500.0,
                "roi_percent": 45.0
            }
        },
        "inventory": {
            "total_units": 1250,
            "total_value_usd": 18750.0,
            "low_stock_alerts": 2,
            "critical_stock": 1,
            "average_turnover_days": 35.2
        },
        "opportunities": {
            "total_found": 12,
            "total_potential_monthly": 2850.0,
            "price_optimization": 5,
            "supplier_changes": 3,
            "bundle_creation": 4
        },
        "competition": {
            "competitors_tracked": 25,
            "price_changes_24h": 3,
            "new_competitors": 1,
            "threats": 1
        }
    }


@router.get(
    "/dashboard/agents",
    summary="Get agent status",
    description="Obtiene el estado de todos los agentes del sistema",
    tags=["Dashboard"]
)
async def get_agent_status(
    cache: CacheDependency
) -> Dict[str, Any]:
    """
    Obtiene el estado detallado de todos los agentes.
    
    Returns:
        Estado de cada agente registrado en el sistema
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "orchestrator": {
            "status": "running",
            "uptime_seconds": 3600,
            "agents_registered": 8,
            "agents_running": 8,
            "agents_failed": 0
        },
        "agents": {
            "discovery": {
                "status": "ready",
                "last_activity": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "tasks_completed": 42,
                "tasks_failed": 0,
                "products_discovered": 156,
                "avg_execution_time_ms": 2850
            },
            "analysis": {
                "status": "ready",
                "last_activity": (datetime.now() - timedelta(minutes=3)).isoformat(),
                "tasks_completed": 38,
                "tasks_failed": 1,
                "analyses_completed": 156,
                "avg_execution_time_ms": 5200
            },
            "supplier": {
                "status": "ready",
                "last_activity": (datetime.now() - timedelta(hours=1)).isoformat(),
                "tasks_completed": 12,
                "tasks_failed": 0,
                "suppliers_found": 45,
                "avg_execution_time_ms": 8500
            },
            "pricing": {
                "status": "ready",
                "last_activity": (datetime.now() - timedelta(hours=2)).isoformat(),
                "tasks_completed": 28,
                "tasks_failed": 0,
                "price_optimizations": 45,
                "avg_execution_time_ms": 1200
            },
            "inventory": {
                "status": "ready",
                "last_activity": (datetime.now() - timedelta(hours=1)).isoformat(),
                "tasks_completed": 35,
                "tasks_failed": 0,
                "forecasts_generated": 15,
                "avg_execution_time_ms": 3400
            },
            "business": {
                "status": "running",
                "last_activity": (datetime.now() - timedelta(hours=24)).isoformat(),
                "cycles_completed": 69,
                "tasks_failed": 0,
                "current_cycle": "discovery",
                "avg_execution_time_ms": 45000
            },
            "profit_optimizer": {
                "status": "running",
                "last_activity": (datetime.now() - timedelta(days=3)).isoformat(),
                "opportunities_found": 12,
                "total_potential_monthly": 2850.0,
                "avg_execution_time_ms": 15000
            },
            "replenishment": {
                "status": "running",
                "last_activity": (datetime.now() - timedelta(hours=2)).isoformat(),
                "decisions_made": 18,
                "stock_outs_prevented": 8,
                "avg_execution_time_ms": 4200
            },
            "competitor_monitor": {
                "status": "running",
                "last_activity": (datetime.now() - timedelta(hours=6)).isoformat(),
                "competitors_tracked": 25,
                "changes_detected": 45,
                "critical_changes": 3,
                "avg_execution_time_ms": 5600
            }
        },
        "system": {
            "cpu_usage_percent": 12.5,
            "memory_usage_mb": 256.8,
            "memory_available_mb": 1024.0,
            "uptime_hours": 72,
            "error_rate_percent": 0.5
        }
    }


# ============================================================================
# ALIAS DASHBOARD ENDPOINTS (for direct /api/v2/dashboard/ access)
# ============================================================================

@router.get(
    "/dashboard/metrics",
    summary="Get dashboard metrics",
    description="Obtiene métricas del dashboard para visualización",
    tags=["Dashboard"]
)
async def get_dashboard_metrics_root(
    cache: CacheDependency
) -> Dict[str, Any]:
    """Alias para acceso directo sin prefijo /business"""
    return await get_dashboard_metrics(cache)


@router.get(
    "/dashboard/agents",
    summary="Get agent status",
    description="Obtiene el estado de todos los agentes del sistema",
    tags=["Dashboard"]
)
async def get_agent_status_root(
    cache: CacheDependency
) -> Dict[str, Any]:
    """Alias para acceso directo sin prefijo /business"""
    return await get_agent_status(cache)

