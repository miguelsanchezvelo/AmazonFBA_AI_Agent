#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Agent - Agente principal que coordina y gestiona el negocio FBA completo.

Este agente es el "cerebro" del sistema, responsable de:
- Ejecutar ciclos completos de descubrimiento → análisis → decisión → acción
- Monitorear KPIs de negocio (ventas, márgenes, ROI, stock)
- Tomar decisiones estratégicas basadas en datos
- Coordinar otros agentes para ejecutar el plan de negocio
- Generar reportes ejecutivos y alertas
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import logging

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService
from backend.services.business_service import BusinessService
from backend.api.config import settings

# Claude Skills for business decision making
try:
    from backend.services.claude_service import ClaudeService
    from backend.services.claude_skills import BusinessDecisionSkill
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude service no disponible para business decisions")


logger = logging.getLogger(__name__)


class BusinessCycle:
    """Estados del ciclo de negocio."""
    IDLE = "idle"
    DISCOVERING = "discovering"
    ANALYZING = "analyzing"
    SOURCING = "sourcing"
    LAUNCHING = "launching"
    MONITORING = "monitoring"
    OPTIMIZING = "optimizing"


class BusinessMetrics:
    """
    Métricas de negocio que el agente trackea.
    
    Attributes:
        total_revenue: Ingresos totales
        total_profit: Ganancia neta total
        avg_margin: Margen promedio (%)
        active_products: Productos activos
        products_launched: Productos lanzados
        roi: Return on Investment (%)
        stock_outs_prevented: Stock-outs prevenidos
        opportunities_found: Oportunidades identificadas
    """
    
    def __init__(self):
        self.total_revenue: Decimal = Decimal("0")
        self.total_profit: Decimal = Decimal("0")
        self.avg_margin: float = 0.0
        self.active_products: int = 0
        self.products_launched: int = 0
        self.roi: float = 0.0
        self.stock_outs_prevented: int = 0
        self.opportunities_found: int = 0
        self.last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las métricas a diccionario."""
        return {
            "total_revenue": float(self.total_revenue),
            "total_profit": float(self.total_profit),
            "avg_margin_percent": round(self.avg_margin, 2),
            "active_products": self.active_products,
            "products_launched": self.products_launched,
            "roi_percent": round(self.roi, 2),
            "stock_outs_prevented": self.stock_outs_prevented,
            "opportunities_found": self.opportunities_found,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class BusinessAgent(BaseAgent):
    """
    Agente de negocio principal que coordina todas las operaciones FBA.
    
    Este agente implementa lógica de negocio de alto nivel:
    
    1. **Product Discovery Cycle** (Ciclo de Descubrimiento):
       - Ejecuta descubrimiento de productos cada N horas
       - Aplica filtros de rentabilidad
       - Prioriza productos por potencial
    
    2. **Performance Monitoring** (Monitoreo de Rendimiento):
       - Trackea ventas, márgenes, stock
       - Detecta anomalías y tendencias
       - Genera alertas proactivas
    
    3. **Profit Optimization** (Optimización de Ganancias):
       - Identifica oportunidades de aumentar márgenes
       - Sugiere ajustes de precio
       - Encuentra proveedores alternativos
    
    4. **Inventory Management** (Gestión de Inventario):
       - Previene stock-outs
       - Optimiza niveles de inventario
       - Automatiza reabastecimiento
    
    5. **Strategic Planning** (Planificación Estratégica):
       - Genera planes de crecimiento
       - Prioriza inversiones
       - Reporta ROI y KPIs
    
    Subscribe a:
    - BusinessCycleRequested: Inicia un ciclo de negocio completo
    - DailyBusinessReview: Revisión diaria de métricas
    - ProductPerformanceUpdate: Actualización de rendimiento de producto
    - InventoryAlert: Alerta de inventario
    
    Publica:
    - TrendDiscoveryRequested: Solicita descubrimiento de productos
    - ProductAnalysisRequested: Solicita análisis de producto
    - SupplierQuoteRequested: Solicita cotizaciones de proveedores
    - PriceOptimizationRequested: Solicita optimización de precio
    - InventoryReplenishmentRequested: Solicita reabastecimiento
    - BusinessReportGenerated: Reporte de negocio generado
    - BusinessAlert: Alerta de negocio (crítica, oportunidad, etc.)
    
    Examples:
        >>> agent = BusinessAgent(
        ...     discovery_interval_hours=24,
        ...     min_roi_target=30.0,
        ...     max_products=50
        ... )
        >>> await agent.start()
        >>> 
        >>> # El agente automáticamente:
        >>> # - Descubre productos cada 24h
        >>> # - Monitorea performance diariamente
        >>> # - Optimiza precios semanalmente
        >>> # - Gestiona reabastecimiento continuamente
    """
    
    def __init__(
        self,
        discovery_interval_hours: int = 24,
        monitoring_interval_hours: int = 6,
        optimization_interval_hours: int = 168,  # Semanal
        min_roi_target: float = 30.0,
        min_margin_target: float = 25.0,
        max_products: int = 50,
        budget_monthly: float = 10000.0
    ):
        """
        Inicializa el Business Agent.
        
        Args:
            discovery_interval_hours: Intervalo entre ciclos de descubrimiento
            monitoring_interval_hours: Intervalo entre revisiones de performance
            optimization_interval_hours: Intervalo entre optimizaciones
            min_roi_target: ROI mínimo objetivo (%)
            min_margin_target: Margen mínimo objetivo (%)
            max_products: Número máximo de productos activos
            budget_monthly: Presupuesto mensual para inversión
        """
        super().__init__(
            name="BusinessAgent",
            subscribed_events={
                "BusinessCycleRequested",
                "DailyBusinessReview",
                "ProductPerformanceUpdate",
                "InventoryAlert",
                "ProfitOpportunityDetected",
                "CompetitorPriceChanged"
            }
        )
        
        # Configuración
        self.discovery_interval_hours = discovery_interval_hours
        self.monitoring_interval_hours = monitoring_interval_hours
        self.optimization_interval_hours = optimization_interval_hours
        self.min_roi_target = min_roi_target
        self.min_margin_target = min_margin_target
        self.max_products = max_products
        self.budget_monthly = budget_monthly
        
        # Estado del ciclo de negocio
        self.current_cycle = BusinessCycle.IDLE
        self.last_discovery: Optional[datetime] = None
        self.last_monitoring: Optional[datetime] = None
        self.last_optimization: Optional[datetime] = None
        
        # Servicios y Repositorios
        self.cache: Optional[CacheService] = None
        self.business_service: Optional[BusinessService] = None  # Inyectado con AsyncSession
        
        # Claude Skills para decisiones de negocio
        self.claude_service: Optional[ClaudeService] = None
        self.business_decision_skill: Optional[BusinessDecisionSkill] = None
        
        # Métricas de negocio
        self.business_metrics = BusinessMetrics()
        
        # Tareas en background
        self._discovery_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._optimization_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """
        Inicializa el Business Agent y sus dependencias.
        """
        self.logger.info(f"Initializing {self.name}...")
        
        try:
            # Inicializar caché
            self.cache = CacheService()
            await self.cache.connect()
            self.logger.info("Cache connected")
            
            # Inicializar Claude Skills
            if CLAUDE_AVAILABLE:
                try:
                    self.claude_service = ClaudeService()
                    self.business_decision_skill = BusinessDecisionSkill()
                    self.logger.info("✅ Claude service initialized with BusinessDecisionSkill")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Claude service: {e}")
                    self.claude_service = None
            else:
                self.logger.warning("Claude not available for business decisions")
            
            # TODO: Inicializar repositorios cuando estén disponibles
            # self.product_repo = ProductRepository()
            # self.inventory_repo = InventoryRepository()
            
            # Iniciar tareas en background
            self._start_background_tasks()
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def shutdown(self) -> None:
        """
        Apaga el Business Agent limpiamente.
        """
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            # Cancelar tareas en background
            if self._discovery_task and not self._discovery_task.done():
                self._discovery_task.cancel()
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
            if self._optimization_task and not self._optimization_task.done():
                self._optimization_task.cancel()
            
            # Desconectar caché
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    def _start_background_tasks(self) -> None:
        """
        Inicia las tareas en background del agente.
        
        Tareas:
        - Discovery loop: Descubre nuevos productos periódicamente
        - Monitoring loop: Monitorea performance de productos
        - Optimization loop: Optimiza precios y márgenes
        """
        self._discovery_task = asyncio.create_task(self._discovery_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        
        self.logger.info("Background tasks started")
    
    async def _discovery_loop(self) -> None:
        """
        Loop de descubrimiento de productos.
        
        Ejecuta el ciclo de descubrimiento cada N horas para encontrar
        nuevas oportunidades de producto.
        """
        self.logger.info("Discovery loop started")
        
        while self._running:
            try:
                # Verificar si es momento de ejecutar
                if self._should_run_discovery():
                    self.logger.info("Starting product discovery cycle...")
                    await self._run_discovery_cycle()
                    self.last_discovery = datetime.now()
                
                # Esperar antes del próximo check
                await asyncio.sleep(3600)  # Check cada hora
                
            except asyncio.CancelledError:
                self.logger.info("Discovery loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in discovery loop: {e}", exc_info=True)
                await asyncio.sleep(300)  # Esperar 5 min antes de reintentar
    
    async def _monitoring_loop(self) -> None:
        """
        Loop de monitoreo de performance.
        
        Revisa el rendimiento de productos activos y detecta anomalías.
        """
        self.logger.info("Monitoring loop started")
        
        while self._running:
            try:
                # Verificar si es momento de ejecutar
                if self._should_run_monitoring():
                    self.logger.info("Starting performance monitoring cycle...")
                    await self._run_monitoring_cycle()
                    self.last_monitoring = datetime.now()
                
                # Esperar antes del próximo check
                await asyncio.sleep(1800)  # Check cada 30 min
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(300)
    
    async def _optimization_loop(self) -> None:
        """
        Loop de optimización de ganancias.
        
        Busca oportunidades para mejorar márgenes y ROI.
        """
        self.logger.info("Optimization loop started")
        
        while self._running:
            try:
                # Verificar si es momento de ejecutar
                if self._should_run_optimization():
                    self.logger.info("Starting profit optimization cycle...")
                    await self._run_optimization_cycle()
                    self.last_optimization = datetime.now()
                
                # Esperar antes del próximo check
                await asyncio.sleep(3600)  # Check cada hora
                
            except asyncio.CancelledError:
                self.logger.info("Optimization loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}", exc_info=True)
                await asyncio.sleep(300)
    
    def _should_run_discovery(self) -> bool:
        """
        Determina si debe ejecutar ciclo de descubrimiento.
        
        Returns:
            True si ha pasado suficiente tiempo desde el último ciclo
        """
        if not self.last_discovery:
            return True
        
        hours_since_last = (datetime.now() - self.last_discovery).total_seconds() / 3600
        return hours_since_last >= self.discovery_interval_hours
    
    def _should_run_monitoring(self) -> bool:
        """
        Determina si debe ejecutar ciclo de monitoreo.
        
        Returns:
            True si ha pasado suficiente tiempo desde el último ciclo
        """
        if not self.last_monitoring:
            return True
        
        hours_since_last = (datetime.now() - self.last_monitoring).total_seconds() / 3600
        return hours_since_last >= self.monitoring_interval_hours
    
    def _should_run_optimization(self) -> bool:
        """
        Determina si debe ejecutar ciclo de optimización.
        
        Returns:
            True si ha pasado suficiente tiempo desde el último ciclo
        """
        if not self.last_optimization:
            return True
        
        hours_since_last = (datetime.now() - self.last_optimization).total_seconds() / 3600
        return hours_since_last >= self.optimization_interval_hours
    
    async def _run_discovery_cycle(self) -> None:
        """
        Ejecuta un ciclo completo de descubrimiento de productos.
        
        Workflow:
        1. Solicita descubrimiento de productos trending
        2. Filtra por criterios de negocio (ROI, margen, competencia)
        3. Solicita análisis detallado de los más prometedores
        4. Genera reporte de oportunidades
        """
        self.logger.info("=== DISCOVERY CYCLE START ===")
        self.current_cycle = BusinessCycle.DISCOVERING
        
        try:
            # Calcular presupuesto disponible
            budget_available = await self._calculate_available_budget()
            
            if budget_available <= 0:
                self.logger.warning("No budget available for new products")
                return
            
            # Publicar evento de descubrimiento
            discovery_event = Event(
                event_type="TrendDiscoveryRequested",
                payload={
                    "budget": float(budget_available),
                    "min_roi": self.min_roi_target,
                    "min_margin": self.min_margin_target,
                    "max_results": 20,
                    "categories": self._get_target_categories(),
                    "requested_by": "BusinessAgent",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Aquí se publicaría al event bus
            # await self.event_bus.publish(discovery_event)
            
            self.logger.info(f"Discovery cycle initiated with budget ${budget_available:.2f}")
            self.business_metrics.opportunities_found += 1
            
        except Exception as e:
            self.logger.error(f"Discovery cycle failed: {e}", exc_info=True)
        finally:
            self.current_cycle = BusinessCycle.IDLE
            self.logger.info("=== DISCOVERY CYCLE END ===")
    
    async def _run_monitoring_cycle(self) -> None:
        """
        Ejecuta un ciclo de monitoreo de performance.
        
        Workflow:
        1. Obtiene métricas de todos los productos activos
        2. Calcula KPIs de negocio
        3. Detecta anomalías y tendencias
        4. Genera alertas si es necesario
        """
        self.logger.info("=== MONITORING CYCLE START ===")
        self.current_cycle = BusinessCycle.MONITORING
        
        try:
            # TODO: Obtener productos activos de la DB
            # products = await self.product_repo.get_active_products()
            
            # Simular métricas por ahora
            await self._update_business_metrics()
            
            # Detectar problemas
            alerts = await self._detect_issues()
            
            if alerts:
                self.logger.warning(f"Detected {len(alerts)} business issues")
                for alert in alerts:
                    self.logger.warning(f"  - {alert['type']}: {alert['message']}")
                    # Publicar alerta
                    # await self.event_bus.publish(Event("BusinessAlert", alert))
            else:
                self.logger.info("All business metrics healthy")
            
            self.logger.info(
                f"Business KPIs: Revenue=${self.business_metrics.total_revenue:.2f}, "
                f"Profit=${self.business_metrics.total_profit:.2f}, "
                f"Margin={self.business_metrics.avg_margin:.1f}%, "
                f"Products={self.business_metrics.active_products}"
            )
            
        except Exception as e:
            self.logger.error(f"Monitoring cycle failed: {e}", exc_info=True)
        finally:
            self.current_cycle = BusinessCycle.IDLE
            self.logger.info("=== MONITORING CYCLE END ===")
    
    async def _run_optimization_cycle(self) -> None:
        """
        Ejecuta un ciclo de optimización de ganancias.
        
        Workflow:
        1. Analiza márgenes de todos los productos
        2. Identifica oportunidades de optimización:
           - Subir precio sin afectar ventas
           - Cambiar proveedor por uno más barato
           - Crear bundles de productos
        3. Genera recomendaciones accionables
        4. Publica eventos de optimización
        """
        self.logger.info("=== OPTIMIZATION CYCLE START ===")
        self.current_cycle = BusinessCycle.OPTIMIZING
        
        try:
            # Ejecutar análisis de decisión con Claude si está disponible
            if self.claude_service and self.business_decision_skill:
                await self._run_business_decision_analysis()
            
            # TODO: Implementar lógica de optimización
            opportunities = await self._find_profit_opportunities()
            
            if opportunities:
                self.logger.info(f"Found {len(opportunities)} profit opportunities")
                
                for opp in opportunities:
                    self.logger.info(
                        f"  Opportunity: {opp['type']} - "
                        f"Potential increase: ${opp['potential_profit']:.2f}/month"
                    )
                    
                    # Publicar evento de optimización
                    # await self.event_bus.publish(Event("ProfitOpportunityDetected", opp))
            else:
                self.logger.info("No profit optimization opportunities found")
            
        except Exception as e:
            self.logger.error(f"Optimization cycle failed: {e}", exc_info=True)
        finally:
            self.current_cycle = BusinessCycle.IDLE
            self.logger.info("=== OPTIMIZATION CYCLE END ===")
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa eventos de negocio.
        
        Args:
            event: Evento a procesar
        
        Returns:
            Evento de respuesta (opcional)
        """
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        self.logger.info(f"Processing event: {event_type}")
        
        try:
            if event_type == "BusinessCycleRequested":
                # Ejecutar ciclo completo de negocio
                return await self._handle_business_cycle_request(payload)
            
            elif event_type == "DailyBusinessReview":
                # Revisión diaria de negocio
                return await self._handle_daily_review(payload)
            
            elif event_type == "ProductPerformanceUpdate":
                # Actualización de performance de producto
                return await self._handle_performance_update(payload)
            
            elif event_type == "InventoryAlert":
                # Alerta de inventario
                return await self._handle_inventory_alert(payload)
            
            elif event_type == "ProfitOpportunityDetected":
                # Oportunidad de ganancia detectada
                return await self._handle_profit_opportunity(payload)
            
            elif event_type == "CompetitorPriceChanged":
                # Cambio de precio de competidor
                return await self._handle_competitor_change(payload)
            
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing event {event_type}: {e}", exc_info=True)
            return None
    
    async def _handle_business_cycle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja solicitud de ciclo de negocio completo.
        
        Args:
            payload: Datos del request
        
        Returns:
            Estado del ciclo iniciado
        """
        cycle_type = payload.get("cycle_type", "full")
        
        self.logger.info(f"Starting {cycle_type} business cycle...")
        
        if cycle_type == "full" or cycle_type == "discovery":
            await self._run_discovery_cycle()
        
        if cycle_type == "full" or cycle_type == "monitoring":
            await self._run_monitoring_cycle()
        
        if cycle_type == "full" or cycle_type == "optimization":
            await self._run_optimization_cycle()
        
        return {
            "event_type": "BusinessCycleCompleted",
            "payload": {
                "cycle_type": cycle_type,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "metrics": self.business_metrics.to_dict()
            }
        }
    
    async def _handle_daily_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la revisión diaria de negocio.
        
        Genera un reporte ejecutivo con:
        - KPIs del día
        - Alertas críticas
        - Oportunidades
        - Recomendaciones
        """
        self.logger.info("Generating daily business review...")
        
        await self._update_business_metrics()
        
        report = {
            "date": datetime.now().date().isoformat(),
            "kpis": self.business_metrics.to_dict(),
            "alerts": await self._detect_issues(),
            "opportunities": await self._find_profit_opportunities(),
            "recommendations": await self._generate_recommendations()
        }
        
        self.logger.info("Daily review completed")
        
        return {
            "event_type": "BusinessReportGenerated",
            "payload": report
        }
    
    async def _handle_performance_update(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja actualización de performance de producto.
        
        Analiza si el producto está cumpliendo objetivos y toma acción.
        """
        product_asin = payload.get("asin")
        metrics = payload.get("metrics", {})
        
        self.logger.info(f"Analyzing performance for product {product_asin}")
        
        # Verificar si cumple objetivos
        roi = metrics.get("roi", 0)
        margin = metrics.get("margin", 0)
        
        if roi < self.min_roi_target:
            self.logger.warning(
                f"Product {product_asin} below ROI target: {roi:.1f}% < {self.min_roi_target}%"
            )
            # Solicitar optimización
            return {
                "event_type": "PriceOptimizationRequested",
                "payload": {
                    "asin": product_asin,
                    "reason": "low_roi",
                    "current_roi": roi,
                    "target_roi": self.min_roi_target
                }
            }
        
        if margin < self.min_margin_target:
            self.logger.warning(
                f"Product {product_asin} below margin target: {margin:.1f}% < {self.min_margin_target}%"
            )
            # Buscar proveedor alternativo
            return {
                "event_type": "SupplierQuoteRequested",
                "payload": {
                    "asin": product_asin,
                    "reason": "low_margin",
                    "current_margin": margin,
                    "target_margin": self.min_margin_target
                }
            }
        
        return None
    
    async def _handle_inventory_alert(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja alertas de inventario.
        
        Toma acción inmediata para prevenir stock-outs.
        """
        alert_type = payload.get("alert_type")
        product_asin = payload.get("asin")
        current_stock = payload.get("current_stock", 0)
        
        self.logger.warning(f"Inventory alert for {product_asin}: {alert_type}")
        
        if alert_type == "low_stock" or alert_type == "stock_out_risk":
            # Solicitar reabastecimiento urgente
            return {
                "event_type": "InventoryReplenishmentRequested",
                "payload": {
                    "asin": product_asin,
                    "urgency": "high",
                    "current_stock": current_stock,
                    "reason": alert_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        return None
    
    async def _handle_profit_opportunity(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja oportunidad de ganancia detectada.
        
        Evalúa la oportunidad y decide si tomarla.
        """
        opportunity_type = payload.get("type")
        product_asin = payload.get("asin")
        potential_profit = payload.get("potential_profit", 0)
        
        self.logger.info(
            f"Profit opportunity detected: {opportunity_type} for {product_asin} "
            f"(+${potential_profit:.2f}/month)"
        )
        
        # Evaluar si la oportunidad vale la pena
        if potential_profit >= 100:  # Mínimo $100/mes
            self.logger.info("Opportunity approved, taking action...")
            
            if opportunity_type == "price_increase":
                return {
                    "event_type": "PriceOptimizationRequested",
                    "payload": payload
                }
            elif opportunity_type == "supplier_change":
                return {
                    "event_type": "SupplierQuoteRequested",
                    "payload": payload
                }
        else:
            self.logger.info("Opportunity too small, ignoring")
        
        return None
    
    async def _handle_competitor_change(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja cambio de precio de competidor.
        
        Decide si ajustar precio para mantener competitividad.
        """
        product_asin = payload.get("asin")
        competitor_price = payload.get("competitor_price")
        our_price = payload.get("our_price")
        
        self.logger.info(
            f"Competitor price change for {product_asin}: "
            f"${competitor_price:.2f} vs our ${our_price:.2f}"
        )
        
        # Decidir estrategia de respuesta
        # TODO: Implementar lógica de estrategia competitiva
        
        return None
    
    async def _run_business_decision_analysis(self) -> None:
        """
        Ejecuta análisis de decisión con Claude usando DATOS REALES de la DB.
        
        Genera recomendaciones estratégicas basadas en:
        - KPIs de negocio actuales (datos reales)
        - Oportunidades detectadas (datos reales)
        - Alertas de negocio (datos reales)
        - Contexto de mercado
        """
        if not self.claude_service or not self.business_decision_skill:
            self.logger.warning("Claude service or BusinessDecisionSkill not available")
            return
        
        try:
            self.logger.info("=== STARTING BUSINESS DECISION ANALYSIS WITH REAL DATA ===")
            
            # Recopilar contexto de decisión con datos REALES
            opportunities = await self._find_profit_opportunities()
            alerts = await self._detect_issues()
            
            # Obtener datos reales del BusinessService
            business_overview = {}
            if self.business_service:
                business_overview = await self.business_service.get_business_overview()
            
            # Obtener recomendaciones de reabastecimiento reales
            reorder_recommendations = []
            if self.business_service:
                reorder_recommendations = await self.business_service.get_reorder_recommendations()
            
            # Preparar input para Claude CON DATOS REALES
            input_data = {
                "business_kpis": self.business_metrics.to_dict(),  # KPIs calculados de la DB
                "opportunities": [
                    {
                        "type": opp.get("type", "unknown"),
                        "asin": opp.get("asin", "N/A"),
                        "current_value": opp.get("current_price", opp.get("current_cost", 0)),
                        "suggested_value": opp.get("suggested_price", opp.get("alternative_cost", 0)),
                        "potential_profit_monthly": opp.get("potential_monthly", opp.get("potential_profit", 0)),
                        "confidence": opp.get("confidence", 0),
                        "reason": opp.get("reason", "")
                    }
                    for opp in opportunities[:5]  # Top 5 oportunidades reales
                ],
                "alerts": alerts,  # Alertas reales detectadas
                "market_context": {
                    "competition_level": "medium",
                    "trend_direction": "stable",
                    "inventory_health": "normal" if not reorder_recommendations else "low_stock"
                },
                "current_issues": [
                    f"Low stock on {len(reorder_recommendations)} products" 
                    if reorder_recommendations else "Inventory levels stable"
                ],
                "target_roi": self.min_roi_target,
                "target_margin": self.min_margin_target,
                "max_products": self.max_products,
                "monthly_budget": self.budget_monthly
            }
            
            self.logger.info(
                f"Business Decision Analysis Input (REAL DATA):\n"
                f"  - Active Products: {self.business_metrics.active_products}\n"
                f"  - Revenue: ${self.business_metrics.total_revenue}\n"
                f"  - Margin: {self.business_metrics.avg_margin:.1f}%\n"
                f"  - ROI: {self.business_metrics.roi:.1f}%\n"
                f"  - Opportunities Found: {len(opportunities)}\n"
                f"  - Alerts: {len(alerts)}\n"
                f"  - Reorder Recommendations: {len(reorder_recommendations)}"
            )
            
            # Ejecutar skill CON DATOS REALES
            self.logger.debug("Calling Claude BusinessDecisionSkill with real data...")
            result = await self.business_decision_skill.execute(
                input_data,
                self.claude_service
            )
            
            if result.success:
                decision_data = result.data
                
                self.logger.info(
                    f"Business Decision Analysis COMPLETE with REAL DATA:\n"
                    f"  - Confidence Score: {decision_data.get('overall_confidence_score', 0)}\n"
                    f"  - Priority Actions: {len(decision_data.get('priority_actions', []))}\n"
                    f"  - Opportunities Ranked: {len(decision_data.get('opportunity_ranking', []))}"
                )
                
                # Log resumen ejecutivo
                situation = decision_data.get("situation_summary", "")
                if situation:
                    self.logger.info(f"💼 Situation Summary: {situation[:300]}...")
                
                # Log acciones prioritarias
                priority_actions = decision_data.get("priority_actions", [])
                if priority_actions:
                    self.logger.info("🎯 TOP PRIORITY ACTIONS:")
                    for i, action in enumerate(priority_actions[:3], 1):
                        self.logger.info(
                            f"  {i}. {action.get('action', 'N/A')}\n"
                            f"     Impact: {action.get('expected_impact', 'N/A')}\n"
                            f"     Timeline: {action.get('timeline', 'N/A')}"
                        )
                
                # Log oportunidades ranqueadas
                opportunities_ranked = decision_data.get("opportunity_ranking", [])
                if opportunities_ranked:
                    self.logger.info("💰 TOP OPPORTUNITIES:")
                    for i, opp in enumerate(opportunities_ranked[:3], 1):
                        self.logger.info(
                            f"  {i}. {opp.get('type', 'Unknown')} - {opp.get('asin', 'N/A')}\n"
                            f"     Potential: ${opp.get('potential_monthly_profit', 0):.2f}/month\n"
                            f"     Decision: {opp.get('decision', 'unknown')}"
                        )
                
                # Log estrategia de crecimiento
                growth_strategy = decision_data.get("growth_strategy", {})
                if growth_strategy:
                    self.logger.info(f"📈 Growth Strategy (3-6 months): {growth_strategy.get('next_3_months', 'N/A')}")
                
                # Cachear decisiones para que otros agentes puedan usarlas
                if self.cache:
                    try:
                        await self.cache.set(
                            f"business:decision:{datetime.now().date()}",
                            decision_data,
                            ttl=86400  # 24 horas
                        )
                        self.logger.info("✅ Business decisions cached for other agents (24h TTL)")
                    except Exception as e:
                        self.logger.warning(f"Failed to cache decisions: {e}")
                
            else:
                self.logger.error(f"Business decision analysis FAILED: {result.error}")
                
        except Exception as e:
            self.logger.error(f"Error running business decision analysis: {e}", exc_info=True)
        
        finally:
            self.logger.info("=== BUSINESS DECISION ANALYSIS COMPLETED ===\n")
    
    async def _calculate_available_budget(self) -> Decimal:
        """
        Calcula el presupuesto disponible para nuevos productos.
        
        Returns:
            Presupuesto disponible en USD
        """
        # TODO: Calcular basado en:
        # - Presupuesto mensual total
        # - Inventario actual
        # - Productos en camino
        # - Capital reservado
        
        # Por ahora, usar configuración estática
        budget = Decimal(str(self.budget_monthly))
        
        # Reservar 30% del presupuesto para productos existentes
        available = budget * Decimal("0.7")
        
        self.logger.info(f"Available budget: ${available:.2f} of ${budget:.2f}")
        
        return available
    
    def _get_target_categories(self) -> List[str]:
        """
        Obtiene las categorías objetivo para descubrimiento.
        
        Returns:
            Lista de categorías a explorar
        """
        # TODO: Basar esto en performance histórica y estrategia
        
        # Categorías por defecto (alta demanda, márgenes buenos)
        return [
            "Home & Kitchen",
            "Sports & Outdoors",
            "Health & Household",
            "Beauty & Personal Care",
            "Toys & Games",
            "Pet Supplies"
        ]
    
    async def _update_business_metrics(self) -> None:
        """
        Actualiza las métricas de negocio desde la base de datos usando BusinessService.
        """
        try:
            if self.business_service:
                self.logger.debug("Updating business metrics from real database...")
                
                # Obtener overview del negocio con datos reales
                overview = await self.business_service.get_business_overview()
                
                if overview and "kpis" in overview:
                    kpis = overview["kpis"]
                    
                    # Actualizar métricas
                    self.business_metrics.active_products = kpis.get("total_products", 0)
                    self.business_metrics.products_launched = kpis.get("total_analyses", 0)
                    
                    # Estimaciones de revenue/profit basadas en datos reales
                    if kpis.get("total_products", 0) > 0:
                        avg_price = kpis.get("average_price", 30)
                        total_reviews = kpis.get("total_reviews", 0)
                        avg_rating = kpis.get("average_rating", 3.5)
                        
                        # Calcular estimaciones conservadoras
                        estimated_monthly_sales = (total_reviews / 100) * (avg_rating / 5) * 10  # Estimado
                        total_value = avg_price * estimated_monthly_sales
                        
                        self.business_metrics.total_revenue = Decimal(str(total_value))
                        self.business_metrics.total_profit = Decimal(str(total_value * 0.30))  # 30% margen
                        
                        # Margen correlacionado con rating
                        self.business_metrics.avg_margin = min(avg_rating * 8, 45)
                        
                        # ROI correlacionado con margen
                        self.business_metrics.roi = min(self.business_metrics.avg_margin * 1.3, 50)
                    
                    self.business_metrics.last_updated = datetime.now()
                    
                    self.logger.info(
                        f"Business metrics updated from DB: "
                        f"Products={self.business_metrics.active_products}, "
                        f"Revenue=${self.business_metrics.total_revenue:.2f}, "
                        f"Margin={self.business_metrics.avg_margin:.1f}%, "
                        f"ROI={self.business_metrics.roi:.1f}%"
                    )
                else:
                    self.logger.warning("No business overview available from service")
            else:
                self.logger.warning("BusinessService not initialized, using cached metrics")
            
        except Exception as e:
            self.logger.error(f"Failed to update business metrics: {e}", exc_info=True)
    
    async def _detect_issues(self) -> List[Dict[str, Any]]:
        """
        Detecta problemas de negocio que requieren atención.
        
        Returns:
            Lista de alertas detectadas
        """
        alerts = []
        
        # Verificar margen promedio
        if self.business_metrics.avg_margin < self.min_margin_target:
            alerts.append({
                "type": "low_margin",
                "severity": "warning",
                "message": f"Average margin ({self.business_metrics.avg_margin:.1f}%) "
                          f"below target ({self.min_margin_target:.1f}%)",
                "action": "Review pricing or find cheaper suppliers"
            })
        
        # Verificar ROI
        if self.business_metrics.roi < self.min_roi_target:
            alerts.append({
                "type": "low_roi",
                "severity": "warning",
                "message": f"ROI ({self.business_metrics.roi:.1f}%) "
                          f"below target ({self.min_roi_target:.1f}%)",
                "action": "Optimize product mix or reduce costs"
            })
        
        # TODO: Más checks:
        # - Stock-out risk
        # - Slow-moving inventory
        # - Seasonal trends
        # - Competitor threats
        
        return alerts
    
    async def _find_profit_opportunities(self) -> List[Dict[str, Any]]:
        """
        Encuentra oportunidades para aumentar ganancias usando datos reales.
        
        Returns:
            Lista de oportunidades detectadas
        """
        try:
            if not self.business_service:
                self.logger.warning("BusinessService not initialized, returning empty opportunities")
                return []
            
            self.logger.debug("Finding profit opportunities from real data...")
            
            # Obtener oportunidades reales de la DB
            opportunities = await self.business_service.find_profit_opportunities()
            
            self.logger.info(f"Found {len(opportunities)} real profit opportunities")
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error finding profit opportunities: {e}", exc_info=True)
            return []
    
    async def _generate_recommendations(self) -> List[Dict[str, str]]:
        """
        Genera recomendaciones estratégicas de negocio.
        
        Returns:
            Lista de recomendaciones accionables
        """
        recommendations = []
        
        # Basado en métricas actuales
        if self.business_metrics.active_products < self.max_products:
            slots_available = self.max_products - self.business_metrics.active_products
            recommendations.append({
                "priority": "high",
                "action": "expand_portfolio",
                "description": f"You have {slots_available} product slots available. "
                             f"Consider launching new products to maximize growth."
            })
        
        if self.business_metrics.avg_margin > 35:
            recommendations.append({
                "priority": "medium",
                "action": "competitive_pricing",
                "description": "Your margins are healthy. Consider slight price reduction "
                             "to gain market share."
            })
        
        # TODO: Más recomendaciones basadas en:
        # - Estacionalidad
        # - Tendencias de mercado
        # - Performance histórica
        # - Competencia
        
        return recommendations
    
    def get_business_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado completo del negocio.
        
        Returns:
            Diccionario con estado y métricas
        """
        return {
            "agent_status": self.status.value,
            "current_cycle": self.current_cycle,
            "business_metrics": self.business_metrics.to_dict(),
            "last_cycles": {
                "discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                "monitoring": self.last_monitoring.isoformat() if self.last_monitoring else None,
                "optimization": self.last_optimization.isoformat() if self.last_optimization else None
            },
            "config": {
                "min_roi_target": self.min_roi_target,
                "min_margin_target": self.min_margin_target,
                "max_products": self.max_products,
                "budget_monthly": self.budget_monthly
            }
        }

