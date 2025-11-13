#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Service - Orquestador de servicios de negocio.

Proporciona una interfaz simplificada para que el BusinessAgent
acceda a datos de negocio a través de los repositorios.

Maneja:
- KPIs y métricas de negocio
- Oportunidades de ganancias
- Decisiones de reabastecimiento
- Análisis de competencia
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repositories import (
    ProductRepository,
    InventoryRepository,
    AnalysisRepository,
    SupplierRepository,
    BusinessMetricsRepository,
)

logger = logging.getLogger(__name__)


class BusinessService:
    """
    Servicio de negocio que coordina acceso a datos a través de repositorios.
    
    Proporciona métodos de alto nivel para que el BusinessAgent
    pueda tomar decisiones basadas en datos reales.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Inicializa el servicio con una sesión de base de datos.
        
        Args:
            db: AsyncSession de SQLAlchemy
        """
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.BusinessService")
        
        # Inicializar repositorios
        self.products = ProductRepository(db)
        self.inventory = InventoryRepository(db)
        self.analyses = AnalysisRepository(db)
        self.suppliers = SupplierRepository(db)
        self.metrics = BusinessMetricsRepository(db)
    
    async def get_business_overview(self) -> Dict[str, Any]:
        """
        Obtiene un resumen ejecutivo del negocio.
        
        Returns:
            Diccionario con estado actual del negocio
        """
        try:
            self.logger.info("Fetching business overview...")
            
            # Obtener KPIs
            kpis = await self.metrics.get_kpis()
            
            # Obtener inventory summary
            inventory_summary = await self.inventory.get_summary()
            
            # Obtener productos de alto desempeño
            high_performers = await self.products.get_high_performers(limit=5)
            
            # Obtener productos de bajo desempeño
            low_performers = await self.products.get_low_performers(limit=5)
            
            # Obtener alertas de stock bajo
            low_stock = await self.inventory.get_low_stock_products(threshold=50)
            
            overview = {
                "kpis": kpis,
                "inventory": inventory_summary,
                "high_performers": [
                    {
                        "asin": p.asin,
                        "title": p.title,
                        "price": p.price,
                        "rating": p.rating,
                        "reviews": p.reviews
                    }
                    for p in high_performers
                ],
                "low_performers": [
                    {
                        "asin": p.asin,
                        "title": p.title,
                        "price": p.price,
                        "rating": p.rating,
                        "reviews": p.reviews
                    }
                    for p in low_performers
                ],
                "low_stock_alerts": len(low_stock),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Business overview fetched: {len(overview['kpis'])} KPIs")
            return overview
            
        except Exception as e:
            self.logger.error(f"Error fetching business overview: {e}")
            return {}
    
    async def find_profit_opportunities(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Encuentra oportunidades de ganancias en el portfolio de productos.
        
        Args:
            min_price: Precio mínimo (opcional)
            max_price: Precio máximo (opcional)
            
        Returns:
            Lista de oportunidades ordenadas por potencial
        """
        try:
            opportunities = []
            
            # Obtener todos los productos
            products, _ = await self.products.get_all_active(limit=1000)
            
            for product in products:
                # Obtener análisis más reciente
                latest_analysis = await self.analyses.get_latest_by_product(product.id)
                
                if not latest_analysis:
                    continue
                
                analysis_data = latest_analysis.data or {}
                
                # Calcular potencial de ganancias
                profit_potential = self._calculate_profit_potential(
                    product,
                    analysis_data
                )
                
                if profit_potential and profit_potential["potential"] > 0:
                    opportunities.append({
                        "asin": product.asin,
                        "title": product.title,
                        "type": profit_potential["type"],
                        "potential_monthly": profit_potential["potential"],
                        "current_price": product.price,
                        "suggested_price": profit_potential.get("suggested_price", product.price),
                        "confidence": profit_potential.get("confidence", 0.5),
                        "reason": profit_potential.get("reason", "Price optimization opportunity")
                    })
            
            # Ordenar por potencial
            opportunities.sort(key=lambda x: x["potential_monthly"], reverse=True)
            
            self.logger.info(f"Found {len(opportunities)} profit opportunities")
            return opportunities[:20]  # Top 20
            
        except Exception as e:
            self.logger.error(f"Error finding profit opportunities: {e}")
            return []
    
    def _calculate_profit_potential(
        self,
        product: Any,
        analysis_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calcula el potencial de ganancias para un producto.
        
        Args:
            product: Product ORM object
            analysis_data: Análisis del producto
            
        Returns:
            Diccionario con potencial o None
        """
        try:
            roi = analysis_data.get("roi_percentage", 0)
            competition_score = analysis_data.get("competition_analysis", {}).get("competition_score", 50)
            
            # Oportunidad de aumento de precio si hay bajo inventario de competencia
            if competition_score < 40 and roi > 20:
                return {
                    "type": "price_increase",
                    "potential": roi * 2,  # Multiplicador de potencial
                    "suggested_price": product.price * 1.15,
                    "confidence": 0.8,
                    "reason": "Low competition detected, price increase potential"
                }
            
            # Oportunidad de encontrar proveedor más barato
            if roi < 25:
                return {
                    "type": "supplier_optimization",
                    "potential": 150,  # Estimado
                    "confidence": 0.6,
                    "reason": "Low ROI, supplier optimization needed"
                }
            
            # Oportunidad de bundle
            if product.reviews > 500:
                return {
                    "type": "bundle_creation",
                    "potential": 300,
                    "confidence": 0.7,
                    "reason": "High-review product suitable for bundling"
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error calculating profit potential: {e}")
            return None
    
    async def get_reorder_recommendations(self) -> List[Dict[str, Any]]:
        """
        Obtiene recomendaciones de reabastecimiento.
        
        Returns:
            Lista de recomendaciones de reabastecimiento
        """
        try:
            recommendations = []
            
            # Obtener inventario con stock bajo
            low_stock_items = await self.inventory.get_low_stock_products(threshold=50)
            
            for inventory in low_stock_items:
                if inventory.product:
                    recommendation = {
                        "asin": inventory.product.asin,
                        "title": inventory.product.title,
                        "current_stock": inventory.current_stock,
                        "reorder_point": max(50, inventory.current_stock),
                        "recommended_quantity": max(100, inventory.current_stock * 2),
                        "urgency": "critical" if inventory.current_stock < 20 else "high",
                        "estimated_stockout_days": self._estimate_stockout_days(inventory)
                    }
                    recommendations.append(recommendation)
            
            self.logger.info(f"Generated {len(recommendations)} reorder recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting reorder recommendations: {e}")
            return []
    
    def _estimate_stockout_days(self, inventory: Any) -> int:
        """Estima días hasta agotarse el stock."""
        try:
            daily_sales = inventory.daily_sales or 1
            if daily_sales > 0:
                return max(1, int(inventory.current_stock / daily_sales))
            return 30
        except:
            return 30
    
    async def get_product_by_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles de un producto por ASIN.
        
        Args:
            asin: ASIN del producto
            
        Returns:
            Diccionario con detalles del producto
        """
        try:
            product = await self.products.get_by_asin(asin)
            if not product:
                return None
            
            # Obtener análisis más reciente
            latest_analysis = await self.analyses.get_latest_by_product(product.id)
            
            # Obtener inventario
            inventory = await self.inventory.get_by_product_id(product.id)
            
            # Obtener proveedores
            suppliers = await self.suppliers.get_for_product(product.id)
            
            return {
                "asin": product.asin,
                "title": product.title,
                "price": product.price,
                "rating": product.rating,
                "reviews": product.reviews,
                "bsr": product.bsr,
                "category": product.category,
                "analysis": latest_analysis.data if latest_analysis else None,
                "inventory": {
                    "current_stock": inventory.current_stock if inventory else 0,
                    "price": inventory.price if inventory else product.price,
                    "days_of_supply": inventory.days_of_supply if inventory else 0
                } if inventory else None,
                "suppliers_count": len(suppliers),
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting product {asin}: {e}")
            return None
    
    async def get_competitor_changes(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene cambios detectados en la competencia en las últimas N horas.
        
        Args:
            hours: Número de horas a considerar (default: 24)
            
        Returns:
            Lista de cambios de competencia detectados
        """
        try:
            changes = []
            
            # Obtener todos los análisis recientes
            recent_analyses = await self.analyses.get_recent(hours=hours)
            
            for analysis in recent_analyses:
                if analysis.data and "competition_analysis" in analysis.data:
                    competition_data = analysis.data["competition_analysis"]
                    competitors = competition_data.get("top_competitors", [])
                    
                    for competitor in competitors:
                        # Simular detección de cambios (en producción, esto vendría de un servicio de monitoreo)
                        competitor_change = {
                            "competitor_asin": competitor.get("asin", "N/A"),
                            "your_asin": analysis.product_id,
                            "change_type": "price_change",  # O rating, availability, etc.
                            "old_value": competitor.get("old_price", competitor.get("price", 0)),
                            "new_value": competitor.get("price", 0),
                            "impact_level": "low" if abs(competitor.get("price", 0) - competitor.get("old_price", 0)) < 5 else "high",
                            "description": f"Price changed from ${competitor.get('old_price', 0):.2f} to ${competitor.get('price', 0):.2f}",
                            "detected_at": datetime.now().isoformat(),
                            "recommended_action": "Review pricing strategy"
                        }
                        changes.append(competitor_change)
            
            self.logger.info(f"Found {len(changes)} competitor changes in last {hours} hours")
            return changes
            
        except Exception as e:
            self.logger.error(f"Error getting competitor changes: {e}")
            return []

