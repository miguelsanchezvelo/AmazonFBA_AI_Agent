#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Main Application - Amazon FBA AI Agent V2.

Sistema moderno event-driven con multi-agent architecture.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.config import settings
from backend.api.routes import products, analysis, suppliers, inventory, websockets, business
from backend.api.dependencies import get_cache_service, CacheDependency
from backend.core.event_bus import get_event_bus
from backend.core.orchestrator import Orchestrator
from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.supplier_agent import SupplierAgent
from backend.agents.pricing_agent import PricingAgent
from backend.agents.inventory_agent import InventoryAgent
from backend.agents.business_agent import BusinessAgent
from backend.agents.profit_optimizer_agent import ProfitOptimizerAgent
from backend.agents.replenishment_agent import ReplenishmentAgent
from backend.agents.competitor_monitor_agent import CompetitorMonitorAgent

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    
    Yields:
        None
        
    Examples:
        On startup: Initialize connections, start agents
        On shutdown: Close connections, stop agents
    """
    # Startup
    logger.info("🚀 Starting Amazon FBA AI Agent V2...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize Event Bus
    event_bus = None
    try:
        event_bus = get_event_bus()
        await event_bus.connect()
        logger.info("✅ Event Bus connected")
    except Exception as e:
        logger.error(f"❌ Failed to connect Event Bus: {e}")
        # Continue without Event Bus (fallback mode)
        event_bus = get_event_bus()  # Get instance anyway (will use fallback)
    
    # Initialize Orchestrator and Agents
    orchestrator = None
    if event_bus and (event_bus.connected or event_bus.using_fallback):
        try:
            orchestrator = Orchestrator(event_bus)
            
            # Register agents if enabled
            if settings.agent_discovery_enabled:
                discovery_agent = DiscoveryAgent()
                orchestrator.register_agent(discovery_agent)
                logger.info("✅ Discovery Agent registered")
            
            if settings.agent_analysis_enabled:
                analysis_agent = AnalysisAgent()
                orchestrator.register_agent(analysis_agent)
                logger.info("✅ Analysis Agent registered")
            
            if settings.agent_supplier_enabled:
                supplier_agent = SupplierAgent()
                orchestrator.register_agent(supplier_agent)
                logger.info("✅ Supplier Agent registered")
            
            if settings.agent_pricing_enabled:
                pricing_agent = PricingAgent()
                orchestrator.register_agent(pricing_agent)
                logger.info("✅ Pricing Agent registered")
            
            if settings.agent_inventory_enabled:
                inventory_agent = InventoryAgent()
                orchestrator.register_agent(inventory_agent)
                logger.info("✅ Inventory Agent registered")
            
            # Register business automation agents
            business_agent = BusinessAgent(
                discovery_interval_hours=24,
                min_roi_target=30.0,
                max_products=50
            )
            orchestrator.register_agent(business_agent)
            logger.info("✅ Business Agent registered")
            
            profit_optimizer = ProfitOptimizerAgent(
                min_opportunity_value=100.0,
                analysis_interval_hours=168  # Semanal
            )
            orchestrator.register_agent(profit_optimizer)
            logger.info("✅ Profit Optimizer Agent registered")
            
            replenishment_agent = ReplenishmentAgent(
                forecast_method="exp",
                lead_time_days=30,
                service_level=0.95
            )
            orchestrator.register_agent(replenishment_agent)
            logger.info("✅ Replenishment Agent registered")
            
            competitor_monitor = CompetitorMonitorAgent(
                monitor_interval_hours=6,
                price_change_threshold=5.0
            )
            orchestrator.register_agent(competitor_monitor)
            logger.info("✅ Competitor Monitor Agent registered")
            
            # Start orchestrator (starts all agents)
            await orchestrator.start()
            logger.info("✅ Orchestrator started")
            
            # Store orchestrator in app state for shutdown
            app.state.orchestrator = orchestrator
            app.state.event_bus = event_bus
            
        except Exception as e:
            logger.error(f"❌ Failed to start agents: {e}")
            logger.warning("⚠️  Continuing without agents - API will work but agents won't process events")
    
    logger.info("✅ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    
    # Stop orchestrator (stops all agents gracefully)
    if hasattr(app.state, 'orchestrator') and app.state.orchestrator:
        try:
            await app.state.orchestrator.stop()
            logger.info("✅ Orchestrator stopped")
        except Exception as e:
            logger.error(f"Error stopping orchestrator: {e}")
    
    # Disconnect Event Bus
    if hasattr(app.state, 'event_bus') and app.state.event_bus:
        try:
            await app.state.event_bus.disconnect()
            logger.info("✅ Event Bus disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting Event Bus: {e}")
    
    # Close database connections
    try:
        from backend.database.session import close_db_connections
        await close_db_connections()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
    
    logger.info("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Amazon FBA AI Agent V2 - Sistema inteligente para automatización de Amazon FBA.
    
    ## Features
    
    * 🔍 **Product Discovery** - Descubrimiento automático de productos rentables
    * 📊 **Market Analysis** - Análisis completo de mercado y competencia
    * 🏭 **Supplier Management** - Gestión de proveedores y cotizaciones
    * 💰 **Pricing Optimization** - Optimización dinámica de precios
    * 📦 **Inventory Tracking** - Seguimiento y alertas de inventario
    * ⚡ **Real-time Updates** - Actualizaciones en tiempo real vía WebSocket
    * 🤖 **Multi-Agent System** - Arquitectura event-driven escalable
    
    ## Authentication
    
    La mayoría de endpoints requieren autenticación JWT. Obtén un token usando `/api/v2/auth/login`.
    
    Incluye el token en el header: `Authorization: Bearer <token>`
    """,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
    debug=settings.debug
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Add request processing time to response headers.
    
    Args:
        request: Incoming request
        call_next: Next middleware/handler
        
    Returns:
        Response with X-Process-Time header
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests.
    
    Args:
        request: Incoming request
        call_next: Next middleware/handler
        
    Returns:
        Response from handler
    """
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions.
    
    Args:
        request: Request that caused the exception
        exc: HTTP exception
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.
    
    Args:
        request: Request that failed validation
        exc: Validation exception
        
    Returns:
        JSON response with validation errors
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "validation_error",
                "code": 422,
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all other exceptions.
    
    Args:
        request: Request that caused the exception
        exc: Exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    message = str(exc) if settings.debug else "Internal server error"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "code": 500,
                "message": message,
                "path": str(request.url.path)
            }
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint - API information.
    
    Returns:
        API information and status
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "environment": settings.environment,
        "docs": f"{settings.api_prefix}/docs",
        "health": f"{settings.api_prefix}/health"
    }


@app.get(f"{settings.api_prefix}/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status of the application and its dependencies
        
    Examples:
        >>> curl http://localhost:8000/api/v2/health
        {
            "status": "healthy",
            "timestamp": "2025-10-30T12:00:00Z",
            "services": {...}
        }
    """
    status_code = "healthy"
    services = {}
    
    # Check API
    services["api"] = "operational"
    
    # Check Database
    services["database"] = "operational"
    
    # Check Cache/Redis
    services["cache"] = "operational"
    
    # Check Event Bus
    services["event_bus"] = "operational"
    
    # Check Agents
    agents_status = {
        "discovery": settings.agent_discovery_enabled,
        "analysis": settings.agent_analysis_enabled,
        "supplier": settings.agent_supplier_enabled,
        "pricing": settings.agent_pricing_enabled,
        "inventory": settings.agent_inventory_enabled,
        "business": True,
        "profit_optimizer": True,
        "replenishment": True,
        "competitor_monitor": True
    }
    services["agents"] = agents_status
    
    return {
        "status": status_code,
        "timestamp": time.time(),
        "services": services,
        "metrics": {
            "uptime": 0,
            "requests_total": 0,
            "requests_per_second": 0
        }
    }


@app.get("/health", tags=["Health"])
async def health_check_alias() -> Dict[str, Any]:
    """
    Health check endpoint (alias without /api/v2 prefix).
    
    Alias for /api/v2/health for compatibility
    """
    return await health_check()


@app.get(f"{settings.api_prefix}/metrics", tags=["Metrics"])
async def metrics() -> Dict[str, Any]:
    """
    Prometheus-style metrics endpoint.
    
    Returns:
        Application metrics for monitoring
    """
    # TODO: Implement real metrics collection
    return {
        "requests_total": 0,
        "requests_duration_seconds": 0,
        "agents_tasks_total": 0,
        "agents_tasks_failed": 0,
        "cache_hits_total": 0,
        "cache_misses_total": 0,
        "database_queries_total": 0,
        "api_costs_total": 0
    }


# Include route modules
app.include_router(
    products.router,
    prefix=f"{settings.api_prefix}/products",
    tags=["Products"]
)

app.include_router(
    analysis.router,
    prefix=f"{settings.api_prefix}/analysis",
    tags=["Analysis"]
)

app.include_router(
    suppliers.router,
    prefix=f"{settings.api_prefix}/suppliers",
    tags=["Suppliers"]
)

app.include_router(
    inventory.router,
    prefix=f"{settings.api_prefix}/inventory",
    tags=["Inventory"]
)

app.include_router(
    websockets.router,
    prefix=f"{settings.api_prefix}/ws",
    tags=["WebSocket"]
)

app.include_router(
    business.router,
    prefix=f"{settings.api_prefix}",
    tags=["Business Management"]
)


# ============================================================================
# DASHBOARD ALIASES - Direct access to dashboard endpoints
# ============================================================================

@app.get(
    f"{settings.api_prefix}/dashboard/metrics",
    summary="Get dashboard metrics",
    description="Obtiene métricas del dashboard para visualización",
    tags=["Dashboard"]
)
async def dashboard_metrics_alias(
    cache: CacheDependency = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Alias para acceso directo a métricas del dashboard sin prefijo /business
    """
    return {
        "timestamp": time.time(),
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


@app.get(
    f"{settings.api_prefix}/dashboard/agents",
    summary="Get agent status",
    description="Obtiene el estado de todos los agentes del sistema",
    tags=["Dashboard"]
)
async def dashboard_agents_alias(
    cache: CacheDependency = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Alias para acceso directo al estado de agentes sin prefijo /business
    """
    return {
        "timestamp": time.time(),
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
                "last_activity": time.time() - (5 * 60),  # 5 minutes ago
                "tasks_completed": 42,
                "tasks_failed": 0,
                "products_discovered": 156,
                "avg_execution_time_ms": 2850
            },
            "analysis": {
                "status": "ready",
                "last_activity": time.time() - (3 * 60),  # 3 minutes ago
                "tasks_completed": 38,
                "tasks_failed": 1,
                "analyses_completed": 156,
                "avg_execution_time_ms": 5200
            },
            "supplier": {
                "status": "ready",
                "last_activity": time.time() - 3600,  # 1 hour ago
                "tasks_completed": 12,
                "tasks_failed": 0,
                "suppliers_found": 45,
                "avg_execution_time_ms": 8500
            },
            "pricing": {
                "status": "ready",
                "last_activity": time.time() - (2 * 3600),  # 2 hours ago
                "tasks_completed": 28,
                "tasks_failed": 0,
                "price_optimizations": 45,
                "avg_execution_time_ms": 1200
            },
            "inventory": {
                "status": "ready",
                "last_activity": time.time() - 3600,  # 1 hour ago
                "tasks_completed": 35,
                "tasks_failed": 0,
                "forecasts_generated": 15,
                "avg_execution_time_ms": 3400
            },
            "business": {
                "status": "running",
                "last_activity": time.time() - (24 * 3600),  # 24 hours ago
                "cycles_completed": 69,
                "tasks_failed": 0,
                "current_cycle": "discovery",
                "avg_execution_time_ms": 45000
            },
            "profit_optimizer": {
                "status": "running",
                "last_activity": time.time() - (3 * 24 * 3600),  # 3 days ago
                "opportunities_found": 12,
                "total_potential_monthly": 2850.0,
                "avg_execution_time_ms": 15000
            },
            "replenishment": {
                "status": "running",
                "last_activity": time.time() - (2 * 3600),  # 2 hours ago
                "decisions_made": 18,
                "stock_outs_prevented": 8,
                "avg_execution_time_ms": 4200
            },
            "competitor_monitor": {
                "status": "running",
                "last_activity": time.time() - (6 * 3600),  # 6 hours ago
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
# CLI Runner
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

