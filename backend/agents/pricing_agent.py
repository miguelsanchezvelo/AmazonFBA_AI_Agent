#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pricing Agent - Optimiza estrategias de pricing dinámicas.

Responsabilidades:
- Optimizar precios para maximizar ROI
- Ajustar precios según competencia
- Simular diferentes escenarios de pricing
- Recomendar estrategias de pricing
- Publicar eventos PriceOptimized
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import asyncio
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService

# Claude Skills for pricing strategy
try:
    from backend.services.claude_service import ClaudeService
    from backend.services.claude_skills import PricingStrategySkill
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude service no disponible para pricing strategy")


class PricingStrategy:
    """Estrategias de pricing disponibles."""
    COST_PLUS = "cost_plus"  # Costo + margen fijo
    COMPETITIVE = "competitive"  # Basado en competencia
    VALUE_BASED = "value_based"  # Basado en valor percibido
    DYNAMIC = "dynamic"  # Dinámico según demanda
    PENETRATION = "penetration"  # Precio bajo para penetrar mercado


class PricingAgent(BaseAgent):
    """
    Agent especializado en optimización de precios.
    
    Subscribe a:
    - AnalysisComplete: Análisis completado para optimizar pricing
    
    Publica:
    - PriceOptimized: Precio optimizado con estrategia
    
    Algoritmos:
    - Cost-plus pricing
    - Competitive pricing
    - Value-based pricing
    - Dynamic pricing
    - A/B testing simulation
    
    Examples:
        >>> agent = PricingAgent()
        >>> await agent.start()
        >>> 
        >>> event = {
        ...     "event_type": "AnalysisComplete",
        ...     "payload": {"product": {...}, "roi_analysis": {...}}
        ... }
        >>> result = await agent.process_event(event)
    """
    
    def __init__(
        self,
        target_roi: float = 30.0,
        min_margin: float = 20.0,
        cache_ttl: int = 3600
    ):
        """
        Inicializa el Pricing Agent.
        
        Args:
            target_roi: ROI objetivo (%)
            min_margin: Margen mínimo aceptable (%)
            cache_ttl: TTL del caché en segundos
        """
        super().__init__(
            name="PricingAgent",
            subscribed_events={"AnalysisComplete"}
        )
        
        self.target_roi = target_roi
        self.min_margin = min_margin
        self.cache_ttl = cache_ttl
        
        # Servicios
        self.cache: Optional[CacheService] = None
        self.claude_service: Optional[ClaudeService] = None
        self.pricing_strategy_skill: Optional[PricingStrategySkill] = None
    
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
                    self.pricing_strategy_skill = PricingStrategySkill()
                    self.logger.info("✅ Claude service initialized with PricingStrategySkill")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Claude service: {e}, using basic pricing")
                    self.claude_service = None
            else:
                self.logger.warning("Claude not available, using basic pricing strategies")
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento de análisis completado.
        
        Args:
            event: Evento con análisis del producto
        
        Returns:
            Evento PriceOptimized con estrategia de pricing
        """
        payload = event.get("payload", {})
        product = payload.get("product", {})
        roi_analysis = payload.get("roi_analysis", {})
        demand_analysis = payload.get("demand_analysis", {})
        competition_analysis = payload.get("competition_analysis", {})
        
        asin = product.get("asin", "unknown")
        current_price = product.get("price", 0)
        
        self.logger.info(f"Optimizing pricing for product: {asin} (current: ${current_price})")
        
        try:
            # 1. Calcular múltiples estrategias de pricing
            strategies = await self._calculate_pricing_strategies(
                product,
                roi_analysis,
                demand_analysis,
                competition_analysis
            )
            
            # 2. Evaluar cada estrategia
            evaluated_strategies = self._evaluate_strategies(strategies, roi_analysis)
            
            # 3. Seleccionar mejor estrategia
            best_strategy = self._select_best_strategy(evaluated_strategies)
            
            # 4. Generar recomendaciones
            recommendations = self._generate_recommendations(
                current_price,
                best_strategy,
                evaluated_strategies
            )
            
            self.logger.info(
                f"Optimized pricing for {asin}: ${best_strategy['price']:.2f} "
                f"(strategy: {best_strategy['strategy']})"
            )
            
            # 5. Publicar evento
            return Event(
                event_type="PriceOptimized",
                payload={
                    "product": product,
                    "asin": asin,
                    "current_price": current_price,
                    "optimized_price": best_strategy["price"],
                    "strategy": best_strategy,
                    "all_strategies": evaluated_strategies,
                    "recommendations": recommendations,
                    "optimized_at": datetime.now().isoformat()
                },
                source_agent=self.name
            ).to_dict()
            
        except Exception as e:
            self.logger.error(f"Error optimizing pricing for {asin}: {e}", exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """Apaga el agent limpiamente."""
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def _calculate_pricing_strategies(
        self,
        product: Dict[str, Any],
        roi_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calcula múltiples estrategias de pricing.
        
        Si Claude está disponible, usa PricingStrategySkill para análisis avanzado.
        De lo contrario, usa cálculos básicos.
        
        Args:
            product: Datos del producto
            roi_analysis: Análisis de ROI
            demand_analysis: Análisis de demanda
            competition_analysis: Análisis de competencia
        
        Returns:
            Lista de estrategias calculadas
        """
        # Intentar usar Claude para estrategia avanzada
        if self.claude_service and self.pricing_strategy_skill:
            try:
                claude_strategy = await self._calculate_with_claude(
                    product,
                    roi_analysis,
                    demand_analysis,
                    competition_analysis
                )
                self.logger.info("Claude pricing strategy generated successfully")
                return [claude_strategy]  # Claude genera la mejor estrategia directamente
            except Exception as e:
                self.logger.warning(f"Claude pricing failed: {e}, using basic strategies")
        
        # Fallback: Estrategias básicas
        current_price = product.get("price", 0)
        costs = roi_analysis.get("costs", {})
        total_cost = costs.get("total", 0)
        
        strategies = []
        
        # 1. Cost-Plus Strategy
        cost_plus = self._calculate_cost_plus(total_cost, self.target_roi)
        strategies.append(cost_plus)
        
        # 2. Competitive Strategy
        competitive = self._calculate_competitive(current_price, competition_analysis)
        strategies.append(competitive)
        
        # 3. Value-Based Strategy
        value_based = self._calculate_value_based(
            current_price,
            demand_analysis,
            product
        )
        strategies.append(value_based)
        
        # 4. Dynamic Strategy
        dynamic = self._calculate_dynamic(
            current_price,
            demand_analysis,
            competition_analysis
        )
        strategies.append(dynamic)
        
        # 5. Penetration Strategy
        penetration = self._calculate_penetration(current_price, total_cost)
        strategies.append(penetration)
        
        return strategies
    
    async def _calculate_with_claude(
        self,
        product: Dict[str, Any],
        roi_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcula estrategia de pricing usando Claude.
        
        Args:
            product: Datos del producto
            roi_analysis: Análisis de ROI
            demand_analysis: Análisis de demanda
            competition_analysis: Análisis de competencia
        
        Returns:
            Estrategia de pricing de Claude
        """
        # Preparar datos para la skill
        costs = roi_analysis.get("costs", {})
        input_data = {
            "product": {
                "title": product.get("title", "Product"),
                "current_price": float(product.get("price", 0)),
                "cost": float(costs.get("product_cost", 0)),
                "amazon_fees": float(costs.get("amazon_fees", 0)),
                "shipping_cost": float(costs.get("shipping", 0)),
                "rating": float(product.get("rating", 0)),
                "reviews": int(product.get("reviews", 0))
            },
            "market_data": {
                "avg_competitor_price": float(competition_analysis.get("avg_competitor_price", 0)),
                "min_competitor_price": float(competition_analysis.get("avg_competitor_price", 0) * 0.8) if competition_analysis.get("avg_competitor_price") else 0,
                "max_competitor_price": float(competition_analysis.get("avg_competitor_price", 0) * 1.2) if competition_analysis.get("avg_competitor_price") else 0,
                "demand_level": demand_analysis.get("demand_level", "unknown"),
                "competition_level": competition_analysis.get("competition_level", "unknown"),
                "seasonality_level": "unknown"  # Could be enhanced
            },
            "business_goals": {
                "target_roi": self.target_roi,
                "target_margin": self.min_margin,
                "growth_priority": "balanced",
                "market_position": "mid-tier"
            }
        }
        
        # Ejecutar skill
        self.logger.info(f"Calculating pricing strategy with Claude for {product.get('asin', 'unknown')}")
        result = await self.pricing_strategy_skill.execute(
            input_data,
            self.claude_service
        )
        
        if result.success:
            data = result.data
            # Convertir formato de Claude a formato del agent
            return {
                "strategy": data.get("strategy", "dynamic"),
                "price": data.get("recommended_price", 0),
                "margin": data.get("expected_metrics", {}).get("margin_percentage", 0),
                "expected_roi": data.get("expected_metrics", {}).get("roi_percentage", 0),
                "description": data.get("strategy_rationale", ""),
                "pros": [data.get("competitive_positioning", "")],
                "cons": data.get("risk_factors", []),
                "price_range": data.get("price_range", {}),
                "dynamic_adjustments": data.get("dynamic_adjustments", []),
                "confidence_score": data.get("confidence_score", 80)
            }
        else:
            raise Exception(f"Pricing strategy skill failed: {result.error}")
    
    
    def _calculate_cost_plus(self, total_cost: float, target_roi: float) -> Dict[str, Any]:
        """
        Estrategia Cost-Plus: Costo + margen objetivo.
        
        Precio = Costo * (1 + Target_ROI/100)
        
        Args:
            total_cost: Costo total por unidad
            target_roi: ROI objetivo (%)
        
        Returns:
            Diccionario con estrategia
        """
        price = total_cost * (1 + target_roi / 100)
        margin = ((price - total_cost) / price * 100) if price > 0 else 0
        
        return {
            "strategy": PricingStrategy.COST_PLUS,
            "price": round(price, 2),
            "margin": round(margin, 2),
            "expected_roi": target_roi,
            "description": f"Cost-plus pricing with {target_roi}% ROI target",
            "pros": ["Guaranteed margin", "Simple to calculate", "Predictable profits"],
            "cons": ["Ignores market demand", "May be uncompetitive"]
        }
    
    def _calculate_competitive(
        self,
        current_price: float,
        competition_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia Competitive: Basada en competencia.
        
        Ajusta precio según nivel de competencia.
        
        Args:
            current_price: Precio actual
            competition_analysis: Análisis de competencia
        
        Returns:
            Diccionario con estrategia
        """
        competition_level = competition_analysis.get("competition_level", "medium")
        
        # Ajustar precio según competencia
        if competition_level == "very_high":
            # Precio más bajo para competir
            price = current_price * 0.85
        elif competition_level == "high":
            price = current_price * 0.90
        elif competition_level == "medium":
            price = current_price * 0.95
        else:  # low
            # Precio más alto, menos competencia
            price = current_price * 1.05
        
        return {
            "strategy": PricingStrategy.COMPETITIVE,
            "price": round(price, 2),
            "competition_level": competition_level,
            "description": f"Competitive pricing based on {competition_level} competition",
            "pros": ["Market-aligned", "Competitive position"],
            "cons": ["May reduce margins", "Race to bottom risk"]
        }
    
    def _calculate_value_based(
        self,
        current_price: float,
        demand_analysis: Dict[str, Any],
        product: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia Value-Based: Basada en valor percibido.
        
        Precio más alto si alta demanda y buen rating.
        
        Args:
            current_price: Precio actual
            demand_analysis: Análisis de demanda
            product: Datos del producto
        
        Returns:
            Diccionario con estrategia
        """
        demand_level = demand_analysis.get("demand_level", "medium")
        rating = product.get("rating", 0)
        
        # Ajustar por demanda
        if demand_level == "very_high":
            price_multiplier = 1.15
        elif demand_level == "high":
            price_multiplier = 1.10
        elif demand_level == "medium":
            price_multiplier = 1.05
        else:
            price_multiplier = 1.0
        
        # Ajustar por rating (calidad)
        if rating >= 4.5:
            price_multiplier *= 1.05
        elif rating >= 4.0:
            price_multiplier *= 1.02
        
        price = current_price * price_multiplier
        
        return {
            "strategy": PricingStrategy.VALUE_BASED,
            "price": round(price, 2),
            "demand_level": demand_level,
            "rating": rating,
            "description": f"Value-based pricing for {demand_level} demand",
            "pros": ["Captures value", "Higher margins possible"],
            "cons": ["Risk of overpricing", "Requires strong brand"]
        }
    
    def _calculate_dynamic(
        self,
        current_price: float,
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia Dynamic: Ajuste dinámico según múltiples factores.
        
        Balancea demanda y competencia.
        
        Args:
            current_price: Precio actual
            demand_analysis: Análisis de demanda
            competition_analysis: Análisis de competencia
        
        Returns:
            Diccionario con estrategia
        """
        demand_score = demand_analysis.get("demand_score", 50) / 100
        competition_score = competition_analysis.get("competition_score", 50) / 100
        
        # Formula: precio base * (1 + demand_factor - competition_factor)
        # Alta demanda = subir precio
        # Alta competencia = bajar precio
        price_adjustment = 1 + (demand_score * 0.1) - (competition_score * 0.1)
        price = current_price * price_adjustment
        
        return {
            "strategy": PricingStrategy.DYNAMIC,
            "price": round(price, 2),
            "demand_factor": round(demand_score, 2),
            "competition_factor": round(competition_score, 2),
            "description": "Dynamic pricing balancing demand and competition",
            "pros": ["Adaptive", "Balances factors", "Optimizes revenue"],
            "cons": ["Complex", "Requires monitoring"]
        }
    
    def _calculate_penetration(
        self,
        current_price: float,
        total_cost: float
    ) -> Dict[str, Any]:
        """
        Estrategia Penetration: Precio bajo para ganar mercado.
        
        Precio bajo inicial para ganar market share rápidamente.
        
        Args:
            current_price: Precio actual
            total_cost: Costo total
        
        Returns:
            Diccionario con estrategia
        """
        # Precio = costo + margen mínimo
        price = total_cost * (1 + self.min_margin / 100)
        
        # No bajar más del 30% del precio actual
        min_price = current_price * 0.70
        price = max(price, min_price)
        
        return {
            "strategy": PricingStrategy.PENETRATION,
            "price": round(price, 2),
            "margin": self.min_margin,
            "description": "Penetration pricing to gain market share",
            "pros": ["Fast market entry", "High volume potential"],
            "cons": ["Low margins initially", "Hard to raise later"]
        }
    
    def _evaluate_strategies(
        self,
        strategies: List[Dict[str, Any]],
        roi_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evalúa cada estrategia calculando métricas.
        
        Args:
            strategies: Lista de estrategias
            roi_analysis: Análisis de ROI base
        
        Returns:
            Estrategias con evaluación
        """
        costs = roi_analysis.get("costs", {})
        total_cost = costs.get("total", 0)
        
        evaluated = []
        
        for strategy in strategies:
            price = strategy["price"]
            
            # Calcular ROI real con este precio
            profit = price - total_cost
            roi = (profit / total_cost * 100) if total_cost > 0 else 0
            margin = (profit / price * 100) if price > 0 else 0
            
            # Score de viabilidad (0-100)
            score = self._calculate_strategy_score(roi, margin)
            
            strategy_eval = {
                **strategy,
                "evaluation": {
                    "roi": round(roi, 2),
                    "margin": round(margin, 2),
                    "profit_per_unit": round(profit, 2),
                    "viability_score": round(score, 2),
                    "meets_target_roi": roi >= self.target_roi,
                    "meets_min_margin": margin >= self.min_margin
                }
            }
            
            evaluated.append(strategy_eval)
        
        return evaluated
    
    def _calculate_strategy_score(self, roi: float, margin: float) -> float:
        """
        Calcula score de viabilidad de una estrategia.
        
        Args:
            roi: ROI de la estrategia (%)
            margin: Margen de la estrategia (%)
        
        Returns:
            Score (0-100)
        """
        # Score basado en qué tan cerca está del objetivo
        roi_score = min((roi / self.target_roi) * 60, 60)
        margin_score = min((margin / self.min_margin) * 40, 40)
        
        return roi_score + margin_score
    
    def _select_best_strategy(
        self,
        strategies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Selecciona la mejor estrategia.
        
        Criterios:
        1. Debe cumplir ROI mínimo
        2. Debe cumplir margen mínimo
        3. Mayor viability score
        
        Args:
            strategies: Estrategias evaluadas
        
        Returns:
            Mejor estrategia
        """
        # Filtrar estrategias viables
        viable = [
            s for s in strategies
            if s["evaluation"]["meets_target_roi"] and
               s["evaluation"]["meets_min_margin"]
        ]
        
        # Si no hay viables, tomar la mejor disponible
        if not viable:
            viable = strategies
        
        # Ordenar por viability score
        best = max(viable, key=lambda s: s["evaluation"]["viability_score"])
        
        return best
    
    def _generate_recommendations(
        self,
        current_price: float,
        best_strategy: Dict[str, Any],
        all_strategies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Genera recomendaciones de pricing.
        
        Args:
            current_price: Precio actual
            best_strategy: Mejor estrategia
            all_strategies: Todas las estrategias
        
        Returns:
            Diccionario con recomendaciones
        """
        optimized_price = best_strategy["price"]
        price_change = ((optimized_price - current_price) / current_price * 100) if current_price > 0 else 0
        
        # Recomendación principal
        if abs(price_change) < 5:
            main_recommendation = "maintain"
            action = "Keep current price, it's already optimized"
        elif price_change > 0:
            main_recommendation = "increase"
            action = f"Increase price by {price_change:.1f}% to ${optimized_price:.2f}"
        else:
            main_recommendation = "decrease"
            action = f"Decrease price by {abs(price_change):.1f}% to ${optimized_price:.2f}"
        
        # A/B testing suggestion
        ab_test_prices = self._suggest_ab_test_prices(optimized_price)
        
        return {
            "main_recommendation": main_recommendation,
            "action": action,
            "price_change_percent": round(price_change, 2),
            "strategy_name": best_strategy["strategy"],
            "expected_roi": best_strategy["evaluation"]["roi"],
            "expected_margin": best_strategy["evaluation"]["margin"],
            "ab_test_suggestion": ab_test_prices,
            "monitoring_kpis": [
                "Conversion rate",
                "Sales volume",
                "Revenue",
                "Customer reviews",
                "Competitor prices"
            ]
        }
    
    def _suggest_ab_test_prices(self, base_price: float) -> Dict[str, float]:
        """
        Sugiere precios para A/B testing.
        
        Args:
            base_price: Precio base optimizado
        
        Returns:
            Precios sugeridos para testing
        """
        return {
            "control": round(base_price, 2),
            "variant_a": round(base_price * 0.95, 2),  # 5% menos
            "variant_b": round(base_price * 1.05, 2)   # 5% más
        }

