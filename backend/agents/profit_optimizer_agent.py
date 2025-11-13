#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profit Optimizer Agent - Maximiza márgenes de ganancia mediante análisis inteligente.

Este agente es responsable de:
- Analizar elasticidad de precio de productos
- Identificar oportunidades de aumentar márgenes
- Encontrar proveedores alternativos más baratos
- Sugerir bundles y estrategias de precio
- Detectar productos bajo-performantes

ROI Esperado: 15-30% de aumento en márgenes netos
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import logging

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService


logger = logging.getLogger(__name__)


class PriceElasticity:
    """
    Calcula la elasticidad de precio para un producto.
    
    La elasticidad mide cómo cambia la demanda cuando cambia el precio.
    - Elasticidad > 1: Producto elástico (la demanda cae mucho con aumento de precio)
    - Elasticidad < 1: Producto inelástico (la demanda no cambia mucho)
    
    Para FBA, queremos productos con elasticidad < 0.7 para subir precios.
    """
    
    @staticmethod
    def calculate(
        price_changes: List[Tuple[float, float]],
        sales_changes: List[Tuple[int, int]]
    ) -> float:
        """
        Calcula elasticidad precio-demanda.
        
        Args:
            price_changes: Lista de (precio_antes, precio_despues)
            sales_changes: Lista de (ventas_antes, ventas_despues)
        
        Returns:
            Coeficiente de elasticidad (0-2+)
        """
        if not price_changes or not sales_changes:
            return 1.0  # Neutral por defecto
        
        total_elasticity = 0.0
        count = 0
        
        for (p1, p2), (s1, s2) in zip(price_changes, sales_changes):
            if p1 == 0 or s1 == 0:
                continue
            
            # Calcular cambio porcentual
            price_change_pct = (p2 - p1) / p1
            sales_change_pct = (s2 - s1) / s1
            
            # Elasticidad = (% cambio en demanda) / (% cambio en precio)
            if price_change_pct != 0:
                elasticity = abs(sales_change_pct / price_change_pct)
                total_elasticity += elasticity
                count += 1
        
        return total_elasticity / count if count > 0 else 1.0


class MarginOpportunity:
    """Representa una oportunidad de mejorar márgenes."""
    
    def __init__(
        self,
        opportunity_type: str,
        product_asin: str,
        current_value: float,
        suggested_value: float,
        potential_profit_monthly: float,
        confidence: float,
        reason: str,
        action_required: str
    ):
        self.opportunity_type = opportunity_type
        self.product_asin = product_asin
        self.current_value = current_value
        self.suggested_value = suggested_value
        self.potential_profit_monthly = potential_profit_monthly
        self.confidence = confidence
        self.reason = reason
        self.action_required = action_required
        self.detected_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la oportunidad a diccionario."""
        return {
            "type": self.opportunity_type,
            "asin": self.product_asin,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "potential_profit_monthly": round(self.potential_profit_monthly, 2),
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "action_required": self.action_required,
            "detected_at": self.detected_at.isoformat()
        }


class ProfitOptimizerAgent(BaseAgent):
    """
    Agente especializado en optimización de márgenes y ganancias.
    
    Funcionalidades principales:
    
    1. **Price Optimization** (Optimización de Precio):
       - Analiza elasticidad de precio
       - Identifica productos donde se puede subir precio
       - Simula impacto en ventas y ganancias
    
    2. **Supplier Optimization** (Optimización de Proveedores):
       - Compara proveedores alternativos
       - Calcula ahorro potencial
       - Evalúa trade-off precio vs. calidad/tiempo
    
    3. **Bundle Opportunities** (Oportunidades de Bundles):
       - Identifica productos que se venden bien juntos
       - Calcula margen de bundles
       - Sugiere bundles de alto margen
    
    4. **Cost Reduction** (Reducción de Costos):
       - Analiza costos FBA por producto
       - Identifica productos con costos optimizables
       - Sugiere cambios en empaque/dimensiones
    
    5. **Portfolio Analysis** (Análisis de Portafolio):
       - Identifica productos bajo-performantes
       - Sugiere productos para discontinuar
       - Recomienda rebalanceo de inventario
    
    Subscribe a:
    - PriceOptimizationRequested: Solicitud de optimización de precio
    - MarginAnalysisRequested: Solicitud de análisis de márgenes
    - SupplierComparisonRequested: Solicitud de comparación de proveedores
    
    Publica:
    - ProfitOpportunityDetected: Oportunidad de ganancia detectada
    - PriceChangeRecommended: Recomendación de cambio de precio
    - SupplierChangeRecommended: Recomendación de cambio de proveedor
    - ProductDiscontinueRecommended: Recomendación de discontinuar producto
    
    Examples:
        >>> agent = ProfitOptimizerAgent(
        ...     min_opportunity_value=100.0,
        ...     analysis_interval_hours=168  # Semanal
        ... )
        >>> await agent.start()
        >>> 
        >>> # El agente automáticamente analiza todos los productos
        >>> # y detecta oportunidades de optimización
    """
    
    def __init__(
        self,
        min_opportunity_value: float = 100.0,
        analysis_interval_hours: int = 168,  # Semanal
        max_price_increase_pct: float = 15.0,  # Máximo 15% de aumento
        min_confidence: float = 0.7  # Mínimo 70% de confianza
    ):
        """
        Inicializa el Profit Optimizer Agent.
        
        Args:
            min_opportunity_value: Valor mínimo de oportunidad en USD/mes
            analysis_interval_hours: Intervalo entre análisis completos
            max_price_increase_pct: Máximo aumento de precio permitido (%)
            min_confidence: Confianza mínima para actuar (0-1)
        """
        super().__init__(
            name="ProfitOptimizerAgent",
            subscribed_events={
                "PriceOptimizationRequested",
                "MarginAnalysisRequested",
                "SupplierComparisonRequested",
                "ProductPerformanceUpdate"
            }
        )
        
        self.min_opportunity_value = min_opportunity_value
        self.analysis_interval_hours = analysis_interval_hours
        self.max_price_increase_pct = max_price_increase_pct
        self.min_confidence = min_confidence
        
        # Servicios
        self.cache: Optional[CacheService] = None
        
        # Estado
        self.last_full_analysis: Optional[datetime] = None
        self.opportunities_detected: List[MarginOpportunity] = []
        
        # Tarea en background
        self._analysis_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """
        Inicializa el Profit Optimizer Agent.
        """
        self.logger.info(f"Initializing {self.name}...")
        
        try:
            # Inicializar caché
            self.cache = CacheService()
            await self.cache.connect()
            self.logger.info("Cache connected")
            
            # TODO: Inicializar repositorios de DB
            
            # Iniciar tarea de análisis periódico
            self._analysis_task = asyncio.create_task(self._periodic_analysis())
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def shutdown(self) -> None:
        """
        Apaga el Profit Optimizer Agent.
        """
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            # Cancelar tarea de análisis
            if self._analysis_task and not self._analysis_task.done():
                self._analysis_task.cancel()
                try:
                    await self._analysis_task
                except asyncio.CancelledError:
                    pass
            
            # Desconectar caché
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa eventos de optimización de ganancias.
        
        Args:
            event: Evento a procesar
        
        Returns:
            Evento de respuesta con recomendaciones
        """
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        self.logger.info(f"Processing {event_type}")
        
        try:
            if event_type == "PriceOptimizationRequested":
                return await self._optimize_price(payload)
            
            elif event_type == "MarginAnalysisRequested":
                return await self._analyze_margins(payload)
            
            elif event_type == "SupplierComparisonRequested":
                return await self._compare_suppliers(payload)
            
            elif event_type == "ProductPerformanceUpdate":
                return await self._analyze_product_performance(payload)
            
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing {event_type}: {e}", exc_info=True)
            return None
    
    async def _periodic_analysis(self) -> None:
        """
        Ejecuta análisis completo de optimización periódicamente.
        """
        self.logger.info("Periodic analysis task started")
        
        while self._running:
            try:
                # Verificar si es momento de analizar
                if self._should_run_full_analysis():
                    self.logger.info("Starting full profit analysis...")
                    await self._run_full_analysis()
                    self.last_full_analysis = datetime.now()
                
                # Esperar 1 hora antes del próximo check
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                self.logger.info("Periodic analysis cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in periodic analysis: {e}", exc_info=True)
                await asyncio.sleep(600)  # Esperar 10 min en caso de error
    
    def _should_run_full_analysis(self) -> bool:
        """
        Determina si debe ejecutar análisis completo.
        
        Returns:
            True si ha pasado suficiente tiempo
        """
        if not self.last_full_analysis:
            return True
        
        hours_since_last = (datetime.now() - self.last_full_analysis).total_seconds() / 3600
        return hours_since_last >= self.analysis_interval_hours
    
    async def _run_full_analysis(self) -> None:
        """
        Ejecuta análisis completo de todos los productos.
        
        Workflow:
        1. Obtiene todos los productos activos
        2. Analiza cada producto para oportunidades
        3. Prioriza oportunidades por valor
        4. Publica las más prometedoras
        """
        self.logger.info("=== FULL PROFIT ANALYSIS START ===")
        
        try:
            # TODO: Obtener productos reales de la DB
            # products = await self.product_repo.get_all_active()
            
            # Por ahora, simular análisis
            products = await self._get_mock_products()
            
            opportunities_found = []
            
            for product in products:
                # Analizar precio
                price_opp = await self._analyze_price_opportunity(product)
                if price_opp:
                    opportunities_found.append(price_opp)
                
                # Analizar proveedor
                supplier_opp = await self._analyze_supplier_opportunity(product)
                if supplier_opp:
                    opportunities_found.append(supplier_opp)
                
                # Analizar bundles
                bundle_opp = await self._analyze_bundle_opportunity(product)
                if bundle_opp:
                    opportunities_found.append(bundle_opp)
            
            # Ordenar por potencial de ganancia
            opportunities_found.sort(
                key=lambda x: x.potential_profit_monthly,
                reverse=True
            )
            
            # Guardar oportunidades
            self.opportunities_detected = opportunities_found[:20]  # Top 20
            
            total_potential = sum(opp.potential_profit_monthly for opp in self.opportunities_detected)
            
            self.logger.info(
                f"Analysis complete: Found {len(self.opportunities_detected)} opportunities "
                f"with total potential of ${total_potential:.2f}/month"
            )
            
            # Publicar las oportunidades más valiosas
            for opp in self.opportunities_detected[:5]:  # Top 5
                self.logger.info(
                    f"  🎯 {opp.opportunity_type.upper()}: {opp.product_asin} - "
                    f"${opp.potential_profit_monthly:.2f}/mo - {opp.reason}"
                )
                # await self.event_bus.publish(Event("ProfitOpportunityDetected", opp.to_dict()))
            
        except Exception as e:
            self.logger.error(f"Full analysis failed: {e}", exc_info=True)
        finally:
            self.logger.info("=== FULL PROFIT ANALYSIS END ===")
    
    async def _optimize_price(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimiza el precio de un producto específico.
        
        Args:
            payload: Datos del producto
        
        Returns:
            Recomendación de precio óptimo
        """
        product_asin = payload.get("asin")
        current_price = Decimal(str(payload.get("current_price", 0)))
        current_sales = payload.get("monthly_sales", 0)
        
        self.logger.info(f"Optimizing price for {product_asin}")
        
        # Analizar elasticidad
        # TODO: Usar datos históricos reales
        elasticity = await self._estimate_price_elasticity(product_asin)
        
        # Analizar competencia
        competitor_prices = await self._get_competitor_prices(product_asin)
        avg_competitor_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else float(current_price)
        
        # Calcular precio óptimo
        optimal_price = await self._calculate_optimal_price(
            current_price=float(current_price),
            elasticity=elasticity,
            competitor_avg=avg_competitor_price,
            current_sales=current_sales
        )
        
        # Calcular impacto
        price_increase_pct = ((optimal_price - float(current_price)) / float(current_price)) * 100
        expected_sales_change = -elasticity * (price_increase_pct / 100)  # % de cambio en ventas
        new_sales = int(current_sales * (1 + expected_sales_change))
        
        profit_increase = (optimal_price - float(current_price)) * new_sales
        
        recommendation = {
            "asin": product_asin,
            "current_price": float(current_price),
            "optimal_price": round(optimal_price, 2),
            "price_change_pct": round(price_increase_pct, 2),
            "expected_sales_impact": round(expected_sales_change * 100, 2),
            "estimated_profit_increase_monthly": round(profit_increase, 2),
            "elasticity": round(elasticity, 2),
            "competitor_avg_price": round(avg_competitor_price, 2),
            "confidence": 0.75,
            "recommendation": "increase" if optimal_price > float(current_price) else "decrease",
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Price optimization for {product_asin}: "
            f"${current_price} → ${optimal_price:.2f} "
            f"(+${profit_increase:.2f}/mo)"
        )
        
        return {
            "event_type": "PriceChangeRecommended",
            "payload": recommendation
        }
    
    async def _analyze_margins(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza márgenes de un producto o categoría.
        
        Args:
            payload: Filtros de análisis
        
        Returns:
            Análisis de márgenes detallado
        """
        scope = payload.get("scope", "all")  # all, category, product
        
        self.logger.info(f"Analyzing margins for scope: {scope}")
        
        # TODO: Query real de productos
        products = await self._get_mock_products()
        
        total_revenue = Decimal("0")
        total_cost = Decimal("0")
        margins = []
        
        for product in products:
            price = Decimal(str(product.get("price", 0)))
            cost = Decimal(str(product.get("cost", 0)))
            sales = product.get("monthly_sales", 0)
            
            revenue = price * sales
            product_cost = cost * sales
            margin = ((price - cost) / price * 100) if price > 0 else 0
            
            total_revenue += revenue
            total_cost += product_cost
            margins.append(float(margin))
        
        avg_margin = sum(margins) / len(margins) if margins else 0
        total_profit = total_revenue - total_cost
        
        analysis = {
            "scope": scope,
            "products_analyzed": len(products),
            "total_revenue": float(total_revenue),
            "total_cost": float(total_cost),
            "total_profit": float(total_profit),
            "avg_margin_pct": round(avg_margin, 2),
            "margin_range": {
                "min": round(min(margins), 2) if margins else 0,
                "max": round(max(margins), 2) if margins else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Margin analysis: Avg {avg_margin:.1f}%, "
            f"Profit ${total_profit:.2f} on ${total_revenue:.2f} revenue"
        )
        
        return {
            "event_type": "MarginAnalysisCompleted",
            "payload": analysis
        }
    
    async def _compare_suppliers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compara proveedores alternativos para un producto.
        
        Args:
            payload: Datos del producto y proveedores
        
        Returns:
            Comparación de proveedores con recomendación
        """
        product_asin = payload.get("asin")
        current_supplier = payload.get("current_supplier")
        
        self.logger.info(f"Comparing suppliers for {product_asin}")
        
        # TODO: Scraping real de Alibaba/1688
        # Por ahora, simular proveedores alternativos
        suppliers = await self._find_alternative_suppliers(product_asin)
        
        if not suppliers:
            self.logger.info("No alternative suppliers found")
            return {
                "event_type": "SupplierComparisonCompleted",
                "payload": {
                    "asin": product_asin,
                    "alternatives_found": 0,
                    "recommendation": "keep_current"
                }
            }
        
        # Comparar costos y beneficios
        best_supplier = self._select_best_supplier(suppliers)
        
        current_cost = payload.get("current_cost", 0)
        potential_savings = (current_cost - best_supplier["unit_cost"]) * payload.get("monthly_sales", 0)
        
        comparison = {
            "asin": product_asin,
            "current_supplier": current_supplier,
            "current_cost": current_cost,
            "alternatives_found": len(suppliers),
            "best_alternative": best_supplier,
            "potential_savings_monthly": round(potential_savings, 2),
            "recommendation": "switch" if potential_savings > self.min_opportunity_value else "keep_current",
            "confidence": best_supplier.get("confidence", 0.5),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Supplier comparison: Current ${current_cost:.2f} vs "
            f"Best ${best_supplier['unit_cost']:.2f} "
            f"(Save ${potential_savings:.2f}/mo)"
        )
        
        return {
            "event_type": "SupplierChangeRecommended" if potential_savings > self.min_opportunity_value else "SupplierComparisonCompleted",
            "payload": comparison
        }
    
    async def _analyze_product_performance(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analiza performance de un producto y detecta si necesita optimización.
        
        Args:
            payload: Métricas de performance del producto
        
        Returns:
            Evento si se detecta problema u oportunidad
        """
        product_asin = payload.get("asin")
        metrics = payload.get("metrics", {})
        
        margin = metrics.get("margin", 0)
        roi = metrics.get("roi", 0)
        sales_trend = metrics.get("sales_trend", "stable")  # growing, stable, declining
        
        self.logger.debug(f"Analyzing performance for {product_asin}")
        
        # Detectar bajo margen
        if margin < 20:
            self.logger.warning(f"Low margin detected for {product_asin}: {margin:.1f}%")
            return {
                "event_type": "MarginAnalysisRequested",
                "payload": {
                    "asin": product_asin,
                    "reason": "low_margin",
                    "current_margin": margin
                }
            }
        
        # Detectar ventas decrecientes
        if sales_trend == "declining":
            self.logger.warning(f"Declining sales for {product_asin}")
            return {
                "event_type": "PriceOptimizationRequested",
                "payload": {
                    "asin": product_asin,
                    "reason": "declining_sales",
                    "strategy": "competitive_pricing"
                }
            }
        
        return None
    
    async def _analyze_price_opportunity(self, product: Dict[str, Any]) -> Optional[MarginOpportunity]:
        """
        Analiza si hay oportunidad de subir precio.
        
        Args:
            product: Datos del producto
        
        Returns:
            Oportunidad si se detecta, None si no
        """
        asin = product.get("asin")
        current_price = product.get("price", 0)
        monthly_sales = product.get("monthly_sales", 0)
        
        # Estimar elasticidad
        elasticity = await self._estimate_price_elasticity(asin)
        
        # Si elasticidad es baja, podemos subir precio
        if elasticity < 0.7:
            # Calcular precio óptimo (subir hasta max_price_increase_pct%)
            suggested_price = current_price * (1 + self.max_price_increase_pct / 100)
            
            # Estimar impacto en ventas
            sales_decrease = elasticity * (self.max_price_increase_pct / 100)
            new_sales = int(monthly_sales * (1 - sales_decrease))
            
            # Calcular ganancia adicional
            current_revenue = current_price * monthly_sales
            new_revenue = suggested_price * new_sales
            potential_profit = new_revenue - current_revenue
            
            if potential_profit > self.min_opportunity_value:
                return MarginOpportunity(
                    opportunity_type="price_increase",
                    product_asin=asin,
                    current_value=current_price,
                    suggested_value=suggested_price,
                    potential_profit_monthly=potential_profit,
                    confidence=0.8,
                    reason=f"Low price elasticity ({elasticity:.2f}) allows {self.max_price_increase_pct}% increase",
                    action_required="Update product price on Amazon"
                )
        
        return None
    
    async def _analyze_supplier_opportunity(self, product: Dict[str, Any]) -> Optional[MarginOpportunity]:
        """
        Analiza si hay oportunidad de cambiar proveedor.
        
        Args:
            product: Datos del producto
        
        Returns:
            Oportunidad si se detecta, None si no
        """
        # TODO: Implementar scraping de proveedores alternativos
        # Por ahora, retornar None
        return None
    
    async def _analyze_bundle_opportunity(self, product: Dict[str, Any]) -> Optional[MarginOpportunity]:
        """
        Analiza si el producto puede ser bundleado para mayor margen.
        
        Args:
            product: Datos del producto
        
        Returns:
            Oportunidad si se detecta, None si no
        """
        # TODO: Implementar análisis de bundles
        # Usar ML para detectar productos que se compran juntos
        return None
    
    async def _estimate_price_elasticity(self, asin: str) -> float:
        """
        Estima la elasticidad de precio de un producto.
        
        Args:
            asin: ASIN del producto
        
        Returns:
            Coeficiente de elasticidad (0-2+)
        """
        # TODO: Calcular basado en datos históricos reales
        # Por ahora, retornar estimación conservadora
        
        # Categorías típicas:
        # - Commodities (papel, baterías): elasticidad alta (1.5+)
        # - Productos únicos/patentados: elasticidad baja (0.3-0.6)
        # - Productos de marca: elasticidad media (0.7-1.0)
        
        # Simulación: retornar elasticidad baja para testing
        return 0.5
    
    async def _get_competitor_prices(self, asin: str) -> List[float]:
        """
        Obtiene precios de competidores para un producto.
        
        Args:
            asin: ASIN del producto
        
        Returns:
            Lista de precios de competidores
        """
        # TODO: Scraping real de Amazon
        # Por ahora, simular precios
        return [29.99, 32.99, 27.99, 34.99, 30.99]
    
    async def _calculate_optimal_price(
        self,
        current_price: float,
        elasticity: float,
        competitor_avg: float,
        current_sales: int
    ) -> float:
        """
        Calcula el precio óptimo que maximiza ganancia.
        
        Uses:
        - Elasticidad de precio
        - Precios de competencia
        - Volumen actual de ventas
        
        Args:
            current_price: Precio actual
            elasticity: Elasticidad de precio
            competitor_avg: Precio promedio de competidores
            current_sales: Ventas mensuales actuales
        
        Returns:
            Precio óptimo calculado
        """
        # Si elasticidad es baja, podemos subir hasta el máximo permitido
        if elasticity < 0.7:
            max_increase = current_price * (1 + self.max_price_increase_pct / 100)
            
            # No superar mucho el precio promedio de competidores
            competitive_ceiling = competitor_avg * 1.10  # Máximo 10% sobre competencia
            
            optimal = min(max_increase, competitive_ceiling)
        else:
            # Elasticidad alta, ser más conservador
            safe_increase = current_price * 1.05  # Solo 5%
            optimal = min(safe_increase, competitor_avg)
        
        return round(optimal, 2)
    
    async def _find_alternative_suppliers(self, asin: str) -> List[Dict[str, Any]]:
        """
        Encuentra proveedores alternativos para un producto.
        
        Args:
            asin: ASIN del producto
        
        Returns:
            Lista de proveedores alternativos
        """
        # TODO: Implementar scraping de Alibaba, AliExpress, 1688
        # Por ahora, simular proveedores
        
        suppliers = [
            {
                "name": "Guangzhou Factory Ltd",
                "unit_cost": 10.50,
                "moq": 100,  # Minimum Order Quantity
                "lead_time_days": 30,
                "rating": 4.7,
                "total_reviews": 245,
                "confidence": 0.85
            },
            {
                "name": "Shenzhen Supplier Co",
                "unit_cost": 9.80,
                "moq": 200,
                "lead_time_days": 25,
                "rating": 4.5,
                "total_reviews": 180,
                "confidence": 0.75
            }
        ]
        
        return suppliers
    
    def _select_best_supplier(self, suppliers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Selecciona el mejor proveedor basado en múltiples factores.
        
        Factores:
        - Costo unitario (peso: 40%)
        - Rating/reviews (peso: 30%)
        - Lead time (peso: 20%)
        - MOQ (peso: 10%)
        
        Args:
            suppliers: Lista de proveedores candidatos
        
        Returns:
            Mejor proveedor
        """
        if not suppliers:
            return {}
        
        # Calcular score para cada proveedor
        scored_suppliers = []
        
        for supplier in suppliers:
            # Normalizar métricas (0-1)
            cost_score = 1 - (supplier["unit_cost"] / 20)  # Asumir max $20
            rating_score = supplier["rating"] / 5
            lead_time_score = 1 - (supplier["lead_time_days"] / 60)  # Asumir max 60 días
            moq_score = 1 - (supplier["moq"] / 500)  # Asumir max 500 unidades
            
            # Score ponderado
            total_score = (
                cost_score * 0.4 +
                rating_score * 0.3 +
                lead_time_score * 0.2 +
                moq_score * 0.1
            )
            
            scored_suppliers.append((total_score, supplier))
        
        # Ordenar por score y retornar el mejor
        scored_suppliers.sort(reverse=True, key=lambda x: x[0])
        
        return scored_suppliers[0][1]
    
    async def _get_mock_products(self) -> List[Dict[str, Any]]:
        """
        Obtiene productos mock para testing.
        
        TODO: Reemplazar con query real de DB
        """
        return [
            {
                "asin": "B08XYZ123",
                "title": "Premium Yoga Mat",
                "price": 29.99,
                "cost": 12.50,
                "monthly_sales": 120,
                "rating": 4.6,
                "category": "Sports & Outdoors"
            },
            {
                "asin": "B07ABC456",
                "title": "Resistance Bands Set",
                "price": 19.99,
                "cost": 8.00,
                "monthly_sales": 200,
                "rating": 4.5,
                "category": "Sports & Outdoors"
            },
            {
                "asin": "B09DEF789",
                "title": "Water Bottle 32oz",
                "price": 24.99,
                "cost": 7.50,
                "monthly_sales": 180,
                "rating": 4.7,
                "category": "Sports & Outdoors"
            }
        ]
    
    def get_opportunities_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen de oportunidades detectadas.
        
        Returns:
            Resumen con top oportunidades
        """
        if not self.opportunities_detected:
            return {
                "total_opportunities": 0,
                "total_potential_profit": 0,
                "top_opportunities": []
            }
        
        total_potential = sum(opp.potential_profit_monthly for opp in self.opportunities_detected)
        
        return {
            "total_opportunities": len(self.opportunities_detected),
            "total_potential_profit_monthly": round(total_potential, 2),
            "top_opportunities": [
                opp.to_dict() for opp in self.opportunities_detected[:10]
            ],
            "last_analysis": self.last_full_analysis.isoformat() if self.last_full_analysis else None
        }

