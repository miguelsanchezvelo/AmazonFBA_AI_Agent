#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventory Agent - Gestiona tracking y reabastecimiento de inventario.

Responsabilidades:
- Trackear niveles de inventario en tiempo real
- Predecir cuándo reabastecer
- Generar alertas de stock bajo
- Optimizar cantidad de pedidos
- Publicar eventos InventoryAlert
"""

from typing import Any, Dict, List, Optional, Set
import asyncio
from datetime import datetime, timedelta

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService

# Claude Skills for demand forecasting
try:
    from backend.services.claude_service import ClaudeService
    from backend.services.claude_skills import DemandForecastingSkill
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude service no disponible para demand forecasting")


class InventoryStatus:
    """Estados de inventario."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    REORDER_NEEDED = "reorder_needed"
    OVERSTOCK = "overstock"


class InventoryAgent(BaseAgent):
    """
    Agent especializado en gestión de inventario.
    
    Subscribe a:
    - PriceOptimized: Precio optimizado (iniciar tracking)
    - SalesMade: Venta realizada (actualizar inventario)
    - InventoryUpdate: Actualización manual de inventario
    
    Publica:
    - InventoryAlert: Alerta de nivel de inventario
    - ReorderSuggestion: Sugerencia de reabastecimiento
    
    Features:
    - Tracking en tiempo real
    - Predicción de stockout
    - Optimización de EOQ (Economic Order Quantity)
    - Alertas automáticas
    
    Examples:
        >>> agent = InventoryAgent()
        >>> await agent.start()
        >>> 
        >>> event = {
        ...     "event_type": "PriceOptimized",
        ...     "payload": {"product": {...}, "optimized_price": 29.99}
        ... }
        >>> result = await agent.process_event(event)
    """
    
    def __init__(
        self,
        low_stock_threshold: int = 50,
        reorder_point: int = 30,
        lead_time_days: int = 30,
        cache_ttl: int = 3600
    ):
        """
        Inicializa el Inventory Agent.
        
        Args:
            low_stock_threshold: Umbral de stock bajo (unidades)
            reorder_point: Punto de reorden (unidades)
            lead_time_days: Tiempo de entrega del proveedor (días)
            cache_ttl: TTL del caché en segundos
        """
        super().__init__(
            name="InventoryAgent",
            subscribed_events={"PriceOptimized", "SalesMade", "InventoryUpdate"}
        )
        
        self.low_stock_threshold = low_stock_threshold
        self.reorder_point = reorder_point
        self.lead_time_days = lead_time_days
        self.cache_ttl = cache_ttl
        
        # Servicios
        self.cache: Optional[CacheService] = None
        self.claude_service: Optional[ClaudeService] = None
        self.demand_forecasting_skill: Optional[DemandForecastingSkill] = None
        
        # Inventario en memoria (en producción, usar base de datos)
        self.inventory: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Inicializa el agent y sus dependencias."""
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
                    self.demand_forecasting_skill = DemandForecastingSkill()
                    self.logger.info("✅ Claude service initialized with DemandForecastingSkill")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Claude service: {e}, using basic forecasting")
                    self.claude_service = None
            else:
                self.logger.warning("Claude not available, using basic demand forecasting")
            
            # Cargar inventario existente (si hay)
            await self._load_inventory()
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa eventos de inventario.
        
        Args:
            event: Evento a procesar
        
        Returns:
            Evento de alerta si es necesario
        """
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})
        
        if event_type == "PriceOptimized":
            return await self._handle_price_optimized(payload)
        elif event_type == "SalesMade":
            return await self._handle_sales_made(payload)
        elif event_type == "InventoryUpdate":
            return await self._handle_inventory_update(payload)
        else:
            self.logger.warning(f"Unknown event type: {event_type}")
            return None
    
    async def shutdown(self) -> None:
        """Apaga el agent limpiamente."""
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            # Guardar inventario
            await self._save_inventory()
            
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def _handle_price_optimized(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja evento de precio optimizado.
        
        Inicializa tracking de inventario para el producto.
        
        Args:
            payload: Datos del evento
        
        Returns:
            Evento de configuración inicial
        """
        product = payload.get("product", {})
        asin = product.get("asin", "")
        optimized_price = payload.get("optimized_price", 0)
        
        if not asin:
            return None
        
        self.logger.info(f"Initializing inventory tracking for: {asin}")
        
        # Inicializar inventario
        self.inventory[asin] = {
            "asin": asin,
            "product_name": product.get("title", ""),
            "current_stock": 0,  # Inicialmente 0, actualizar manualmente
            "price": optimized_price,
            "status": InventoryStatus.OUT_OF_STOCK,
            "last_updated": datetime.now().isoformat(),
            "sales_history": [],
            "reorder_history": []
        }
        
        # Sugerir pedido inicial
        initial_order = await self._calculate_initial_order(product, optimized_price)
        
        return Event(
            event_type="InventoryAlert",
            payload={
                "alert_type": "initial_setup",
                "asin": asin,
                "product": product,
                "initial_order_suggestion": initial_order,
                "message": f"Inventory tracking initialized for {asin}"
            },
            source_agent=self.name
        ).to_dict()
    
    async def _handle_sales_made(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja evento de venta realizada.
        
        Actualiza inventario y verifica si hay que reabastecer.
        
        Args:
            payload: Datos del evento
        
        Returns:
            Evento de alerta si es necesario
        """
        asin = payload.get("asin", "")
        quantity_sold = payload.get("quantity", 1)
        
        if asin not in self.inventory:
            self.logger.warning(f"Product {asin} not in inventory system")
            return None
        
        # Actualizar stock
        inv = self.inventory[asin]
        inv["current_stock"] = max(0, inv["current_stock"] - quantity_sold)
        inv["last_updated"] = datetime.now().isoformat()
        
        # Registrar venta
        inv["sales_history"].append({
            "date": datetime.now().isoformat(),
            "quantity": quantity_sold,
            "price": inv["price"]
        })
        
        self.logger.info(
            f"Sale recorded for {asin}: {quantity_sold} units "
            f"(remaining: {inv['current_stock']})"
        )
        
        # Verificar si necesita reorden
        alert = await self._check_reorder_needed(asin)
        
        # Guardar cambios
        await self._save_inventory()
        
        return alert
    
    async def _handle_inventory_update(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maneja actualización manual de inventario.
        
        Args:
            payload: Datos del evento
        
        Returns:
            Confirmación de actualización
        """
        asin = payload.get("asin", "")
        new_stock = payload.get("stock", 0)
        
        if asin not in self.inventory:
            self.logger.warning(f"Product {asin} not in inventory system")
            return None
        
        old_stock = self.inventory[asin]["current_stock"]
        self.inventory[asin]["current_stock"] = new_stock
        self.inventory[asin]["last_updated"] = datetime.now().isoformat()
        
        # Si es un reabastecimiento, registrar
        if new_stock > old_stock:
            self.inventory[asin]["reorder_history"].append({
                "date": datetime.now().isoformat(),
                "quantity": new_stock - old_stock,
                "new_total": new_stock
            })
        
        self.logger.info(
            f"Inventory updated for {asin}: {old_stock} → {new_stock}"
        )
        
        # Actualizar status
        status = self._determine_status(new_stock)
        self.inventory[asin]["status"] = status
        
        await self._save_inventory()
        
        return Event(
            event_type="InventoryAlert",
            payload={
                "alert_type": "update_confirmed",
                "asin": asin,
                "old_stock": old_stock,
                "new_stock": new_stock,
                "status": status
            },
            source_agent=self.name
        ).to_dict()
    
    async def _check_reorder_needed(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Verifica si es necesario reabastecer.
        
        Args:
            asin: ASIN del producto
        
        Returns:
            Evento de alerta si es necesario
        """
        inv = self.inventory[asin]
        current_stock = inv["current_stock"]
        
        # Determinar status
        status = self._determine_status(current_stock)
        inv["status"] = status
        
        # Generar alerta si es necesario
        if status in [InventoryStatus.LOW_STOCK, InventoryStatus.REORDER_NEEDED]:
            # Calcular cuánto pedir
            reorder_quantity = await self._calculate_reorder_quantity(asin)
            
            # Estimar cuándo se agotará
            days_until_stockout = await self._estimate_stockout_date(asin)
            
            return Event(
                event_type="InventoryAlert",
                payload={
                    "alert_type": "reorder_needed",
                    "asin": asin,
                    "product_name": inv["product_name"],
                    "current_stock": current_stock,
                    "status": status,
                    "reorder_suggestion": {
                        "quantity": reorder_quantity,
                        "estimated_cost": reorder_quantity * inv["price"] * 0.4,  # 40% costo
                        "urgency": "high" if status == InventoryStatus.REORDER_NEEDED else "medium"
                    },
                    "forecast": {
                        "days_until_stockout": days_until_stockout,
                        "lead_time_days": self.lead_time_days
                    },
                    "message": f"⚠️ {status.replace('_', ' ').title()} for {asin}"
                },
                source_agent=self.name
            ).to_dict()
        
        return None
    
    def _determine_status(self, current_stock: int) -> str:
        """
        Determina el status del inventario.
        
        Args:
            current_stock: Stock actual
        
        Returns:
            Status del inventario
        """
        if current_stock == 0:
            return InventoryStatus.OUT_OF_STOCK
        elif current_stock <= self.reorder_point:
            return InventoryStatus.REORDER_NEEDED
        elif current_stock <= self.low_stock_threshold:
            return InventoryStatus.LOW_STOCK
        elif current_stock > self.low_stock_threshold * 3:
            return InventoryStatus.OVERSTOCK
        else:
            return InventoryStatus.IN_STOCK
    
    async def _calculate_initial_order(
        self,
        product: Dict[str, Any],
        price: float
    ) -> Dict[str, Any]:
        """
        Calcula pedido inicial basado en demanda estimada.
        
        Args:
            product: Datos del producto
            price: Precio optimizado
        
        Returns:
            Sugerencia de pedido inicial
        """
        # Estimar ventas mensuales basadas en reviews
        reviews_count = product.get("reviews_count", 0)
        estimated_monthly_sales = max((reviews_count * 100) / 24, 10)
        
        # Pedido inicial = 2 meses de inventario
        initial_quantity = int(estimated_monthly_sales * 2)
        
        # Redondear a MOQ típicos
        if initial_quantity < 100:
            initial_quantity = 100
        elif initial_quantity < 500:
            initial_quantity = 500
        elif initial_quantity < 1000:
            initial_quantity = 1000
        
        product_cost = price * 0.4  # Asumimos 40% del precio
        total_cost = initial_quantity * product_cost
        
        return {
            "quantity": initial_quantity,
            "estimated_monthly_sales": int(estimated_monthly_sales),
            "months_of_supply": round(initial_quantity / max(estimated_monthly_sales, 1), 1),
            "unit_cost": round(product_cost, 2),
            "total_cost": round(total_cost, 2)
        }
    
    async def _generate_demand_forecast(
        self,
        asin: str,
        product_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Genera forecast de demanda usando Claude DemandForecastingSkill.
        
        Args:
            asin: ASIN del producto
            product_data: Datos del producto e inventario
        
        Returns:
            Forecast de demanda y recomendaciones de inventario
        """
        if not self.claude_service or not self.demand_forecasting_skill:
            return None
        
        try:
            inv = self.inventory.get(asin, {})
            sales_history = inv.get("sales_history", [])
            
            # Calcular avg daily sales
            if sales_history:
                total_sales = sum(s["quantity"] for s in sales_history[-30:])
                avg_daily_sales = total_sales / 30
            else:
                avg_daily_sales = 1.67  # ~50/month default
            
            # Preparar datos para la skill
            input_data = {
                "product": {
                    "asin": asin,
                    "title": product_data.get("title", "Product"),
                    "current_stock": inv.get("current_stock", 0),
                    "avg_daily_sales": avg_daily_sales,
                    "price": inv.get("price", 0),
                    "seasonality_level": product_data.get("seasonality_level", "unknown")
                },
                "historical_data": {
                    "monthly_sales": self._get_monthly_sales(sales_history),
                    "daily_sales_last_30d": [s["quantity"] for s in sales_history[-30:]],
                    "peak_months": product_data.get("peak_months", [])
                },
                "supplier_data": {
                    "lead_time_days": self.lead_time_days,
                    "moq": 100,  # Could be from supplier data
                    "reliability_score": 4.0  # Could be from supplier evaluation
                },
                "business_params": {
                    "target_service_level": 95,
                    "storage_cost_per_unit": 0.75,
                    "stockout_cost_per_unit": inv.get("price", 0) * 0.2
                }
            }
            
            # Ejecutar skill
            self.logger.info(f"Generating demand forecast with Claude for {asin}")
            result = await self.demand_forecasting_skill.execute(
                input_data,
                self.claude_service
            )
            
            if result.success:
                self.logger.info(f"Demand forecast generated for {asin}: {result.data.get('demand_forecast', {}).get('next_30_days', 0):.0f} units/30d")
                return result.data
            else:
                self.logger.warning(f"Demand forecast failed: {result.error}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating demand forecast: {e}", exc_info=True)
            return None
    
    def _get_monthly_sales(self, sales_history: List[Dict[str, Any]]) -> List[float]:
        """Extrae ventas mensuales del historial."""
        if not sales_history:
            return []
        
        # Agrupar por mes (simplificado - asume ventas consecutivas)
        monthly = []
        current_month_sales = 0
        days_in_month = 0
        
        for sale in sales_history:
            current_month_sales += sale["quantity"]
            days_in_month += 1
            
            if days_in_month >= 30:
                monthly.append(current_month_sales)
                current_month_sales = 0
                days_in_month = 0
        
        if current_month_sales > 0:
            monthly.append(current_month_sales)
        
        return monthly[-6:]  # Últimos 6 meses
    
    async def _calculate_reorder_quantity(self, asin: str, forecast: Optional[Dict[str, Any]] = None) -> int:
        """
        Calcula cantidad óptima de reorden (EOQ).
        
        Si hay forecast de Claude, usa sus recomendaciones.
        De lo contrario, usa fórmula EOQ básica.
        
        Formula EOQ: sqrt((2 * D * S) / H)
        D = Demanda anual
        S = Costo por pedido
        H = Costo de mantener inventario
        
        Args:
            asin: ASIN del producto
            forecast: Forecast de Claude (opcional)
        
        Returns:
            Cantidad a pedir
        """
        # Si tenemos forecast de Claude, usar sus recomendaciones
        if forecast and "inventory_recommendations" in forecast:
            reorder_qty = forecast["inventory_recommendations"].get("reorder_quantity", 0)
            if reorder_qty > 0:
                self.logger.info(f"Using Claude forecast reorder quantity: {reorder_qty}")
                return int(reorder_qty)
        
        # Fallback: Cálculo básico EOQ
        inv = self.inventory[asin]
        
        # Calcular demanda mensual promedio
        sales_history = inv.get("sales_history", [])
        if sales_history:
            total_sales = sum(s["quantity"] for s in sales_history)
            monthly_demand = total_sales / max(len(sales_history) / 30, 1)
        else:
            monthly_demand = 50  # Default
        
        annual_demand = monthly_demand * 12
        
        # Parámetros simplificados
        order_cost = 100  # $100 por pedido
        holding_cost_pct = 0.20  # 20% anual del valor del producto
        unit_value = inv["price"] * 0.4  # Costo del producto
        holding_cost = unit_value * holding_cost_pct
        
        # EOQ formula
        import math
        if holding_cost > 0:
            eoq = math.sqrt((2 * annual_demand * order_cost) / holding_cost)
        else:
            eoq = monthly_demand * 2  # 2 meses
        
        # Redondear y ajustar a MOQs típicos
        eoq = int(eoq)
        if eoq < 100:
            eoq = 100
        elif eoq < 500:
            eoq = 500
        
        return eoq
    
    async def _estimate_stockout_date(self, asin: str) -> int:
        """
        Estima en cuántos días se agotará el stock.
        
        Args:
            asin: ASIN del producto
        
        Returns:
            Días hasta stockout
        """
        inv = self.inventory[asin]
        current_stock = inv["current_stock"]
        
        # Calcular tasa de ventas diaria
        sales_history = inv.get("sales_history", [])
        if not sales_history or current_stock == 0:
            return 0
        
        # Tomar últimos 30 días
        recent_sales = sales_history[-30:] if len(sales_history) > 30 else sales_history
        total_sold = sum(s["quantity"] for s in recent_sales)
        days = len(recent_sales)
        
        daily_sales_rate = total_sold / max(days, 1)
        
        if daily_sales_rate > 0:
            days_until_stockout = int(current_stock / daily_sales_rate)
        else:
            days_until_stockout = 999  # Muchos días
        
        return max(days_until_stockout, 0)
    
    async def _load_inventory(self) -> None:
        """Carga inventario desde caché/DB."""
        if self.cache:
            cached = await self.cache.get("inventory_data")
            if cached:
                self.inventory = cached
                self.logger.info(f"Loaded {len(self.inventory)} products from cache")
    
    async def _save_inventory(self) -> None:
        """Guarda inventario en caché/DB."""
        if self.cache:
            await self.cache.set(
                "inventory_data",
                self.inventory,
                ttl=self.cache_ttl
            )
    
    def get_inventory_report(self) -> Dict[str, Any]:
        """
        Genera reporte de inventario.
        
        Returns:
            Reporte completo
        """
        total_products = len(self.inventory)
        total_value = sum(
            inv["current_stock"] * inv["price"] * 0.4
            for inv in self.inventory.values()
        )
        
        by_status = {}
        for inv in self.inventory.values():
            status = inv["status"]
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_products": total_products,
            "total_inventory_value": round(total_value, 2),
            "by_status": by_status,
            "products": list(self.inventory.values())
        }

