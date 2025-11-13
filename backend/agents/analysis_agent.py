#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis Agent - Analiza viabilidad y rentabilidad de productos.

Responsabilidades:
- Calcular ROI esperado
- Analizar demanda y tendencias
- Evaluar competencia
- Determinar viabilidad
- Publicar eventos AnalysisComplete
"""

from typing import Any, Dict, List, Optional, Set
import asyncio
from datetime import datetime, timedelta
import logging

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService

# Claude Skills for deep market analysis
try:
    from backend.services.claude_service import ClaudeService
    from backend.services.claude_skills import MarketAnalysisSkill
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude service no disponible para análisis profundo")

# SerpAPI for competitor analysis
try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    print("⚠️  SerpAPI no disponible para análisis de competencia")

# PyTrends for seasonality analysis
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    print("⚠️  PyTrends no disponible para análisis de estacionalidad")


class AnalysisAgent(BaseAgent):
    """
    Agent especializado en análisis de rentabilidad y viabilidad.
    
    Subscribe a:
    - ProductDiscovered: Producto descubierto para analizar
    
    Publica:
    - AnalysisComplete: Análisis completado con veredicto
    
    Calcula:
    - ROI estimado
    - Demanda proyectada
    - Nivel de competencia
    - Score de viabilidad
    - Recomendación (Go/No-Go)
    - Deep market analysis (using Claude Skills)
    
    Examples:
        >>> agent = AnalysisAgent()
        >>> await agent.start()
        >>> 
        >>> event = {
        ...     "event_type": "ProductDiscovered",
        ...     "payload": {"product": {...}}
        ... }
        >>> result = await agent.process_event(event)
    """
    
    def __init__(
        self,
        min_roi: float = 30.0,
        min_viability_score: float = 70.0,
        cache_ttl: int = 7200,
        serpapi_key: Optional[str] = None
    ):
        """
        Inicializa el Analysis Agent.
        
        Args:
            min_roi: ROI mínimo requerido (%)
            min_viability_score: Score mínimo de viabilidad (0-100)
            cache_ttl: TTL del caché en segundos (default: 2 horas)
            serpapi_key: API key para SerpAPI (análisis de competencia)
        """
        super().__init__(
            name="AnalysisAgent",
            subscribed_events={"ProductDiscovered"}
        )
        
        self.min_roi = min_roi
        self.min_viability_score = min_viability_score
        self.cache_ttl = cache_ttl
        self.serpapi_key = serpapi_key
        
        # Servicios
        self.cache: Optional[CacheService] = None
        self.claude_service: Optional[ClaudeService] = None
        self.market_analysis_skill: Optional[MarketAnalysisSkill] = None
        self.pytrends: Optional[TrendReq] = None
    
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
                    self.market_analysis_skill = MarketAnalysisSkill()
                    self.logger.info("✅ Claude service initialized with MarketAnalysisSkill")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Claude service: {e}, will use basic analysis")
                    self.claude_service = None
            else:
                self.logger.warning("Claude not available, using basic analysis only")
            
            # Inicializar PyTrends
            if PYTRENDS_AVAILABLE:
                try:
                    self.pytrends = TrendReq(hl='en-US', tz=360)
                    self.logger.info("✅ PyTrends initialized for seasonality analysis")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize PyTrends: {e}")
                    self.pytrends = None
            else:
                self.logger.warning("PyTrends not available, skipping seasonality analysis")
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento de producto descubierto.
        
        Args:
            event: Evento con producto a analizar
        
        Returns:
            Evento AnalysisComplete con resultados del análisis
        """
        payload = event.get("payload", {})
        product = payload.get("product", {})
        
        if not product:
            self.logger.warning("No product data in event")
            return None
        
        asin = product.get("asin", "unknown")
        self.logger.info(f"Analyzing product: {asin}")
        
        try:
            # 1. Calcular ROI
            roi_analysis = await self._calculate_roi(product)
            self.logger.info(f"ROI: {roi_analysis['roi_percentage']:.1f}%")
            
            # 2. Analizar demanda
            demand_analysis = await self._analyze_demand(product)
            self.logger.info(f"Demand score: {demand_analysis['demand_score']:.1f}")
            
            # 3. Analizar competencia (real con SerpAPI)
            competition_analysis = await self._analyze_competition(product)
            self.logger.info(f"Competition level: {competition_analysis['competition_level']}")
            
            # 4. Analizar estacionalidad (con PyTrends)
            seasonality_analysis = await self._analyze_seasonality(product)
            self.logger.info(f"Seasonality: {seasonality_analysis.get('seasonality_level', 'unknown')}")
            
            # 5. Calcular score de viabilidad
            viability_score = self._calculate_viability_score(
                roi_analysis,
                demand_analysis,
                competition_analysis,
                seasonality_analysis
            )
            self.logger.info(f"Viability score: {viability_score:.1f}/100")
            
            # 6. Determinar recomendación
            recommendation = self._make_recommendation(
                viability_score,
                roi_analysis,
                seasonality_analysis
            )
            
            # 7. Deep market analysis con Claude (si disponible)
            deep_analysis = None
            if self.claude_service and self.market_analysis_skill:
                try:
                    deep_analysis = await self._deep_market_analysis(
                        product,
                        roi_analysis,
                        demand_analysis,
                        competition_analysis,
                        seasonality_analysis
                    )
                    self.logger.info(f"Deep analysis completed with opportunity score: {deep_analysis.get('opportunity_score', 'N/A')}")
                except Exception as e:
                    self.logger.warning(f"Deep analysis failed: {e}, using basic analysis only")
            
            # 8. Crear análisis completo
            analysis = {
                "asin": asin,
                "product": product,
                "roi_analysis": roi_analysis,
                "demand_analysis": demand_analysis,
                "competition_analysis": competition_analysis,
                "seasonality_analysis": seasonality_analysis,
                "viability_score": viability_score,
                "recommendation": recommendation,
                "deep_analysis": deep_analysis,  # Claude-powered insights
                "analyzed_at": datetime.now().isoformat()
            }
            
            self.logger.info(
                f"Analysis complete for {asin}: {recommendation['decision']} "
                f"(score: {viability_score:.1f})"
            )
            
            # 7. Publicar resultado
            return Event(
                event_type="AnalysisComplete",
                payload=analysis,
                source_agent=self.name
            ).to_dict()
            
        except Exception as e:
            self.logger.error(f"Error analyzing product {asin}: {e}", exc_info=True)
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
    
    async def _calculate_roi(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula el ROI esperado del producto.
        
        Formula:
        ROI = ((Precio_Venta - Costo_Total) / Costo_Total) * 100
        
        Costos incluyen:
        - Costo del producto (asumido 40% del precio)
        - Fees de Amazon (~15%)
        - Shipping (~10%)
        - Marketing (~10%)
        
        Args:
            product: Datos del producto
        
        Returns:
            Diccionario con análisis de ROI
        """
        price = product.get("price", 0)
        
        # Estimaciones de costos (% del precio)
        product_cost_pct = 0.40  # 40% del precio
        amazon_fees_pct = 0.15   # 15% fees
        shipping_pct = 0.10      # 10% shipping
        marketing_pct = 0.10     # 10% marketing
        
        # Calcular costos
        product_cost = price * product_cost_pct
        amazon_fees = price * amazon_fees_pct
        shipping = price * shipping_pct
        marketing = price * marketing_pct
        
        total_cost = product_cost + amazon_fees + shipping + marketing
        profit = price - total_cost
        
        roi_percentage = (profit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "selling_price": price,
            "costs": {
                "product_cost": round(product_cost, 2),
                "amazon_fees": round(amazon_fees, 2),
                "shipping": round(shipping, 2),
                "marketing": round(marketing, 2),
                "total": round(total_cost, 2)
            },
            "profit_per_unit": round(profit, 2),
            "roi_percentage": round(roi_percentage, 2),
            "profit_margin": round((profit / price * 100) if price > 0 else 0, 2)
        }
    
    async def _analyze_demand(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza la demanda del producto.
        
        Indicadores:
        - Número de reviews (más reviews = más ventas)
        - Rating (mejor rating = más conversión)
        - Trend score (si disponible)
        
        Args:
            product: Datos del producto
        
        Returns:
            Diccionario con análisis de demanda
        """
        reviews_count = product.get("reviews_count", 0)
        rating = product.get("rating", 0)
        
        # Calcular demand score (0-100)
        # Basado en reviews y rating
        import math
        
        if reviews_count > 0:
            # Score logarítmico de reviews (normalizado a 0-60)
            review_score = min(math.log10(reviews_count) * 15, 60)
        else:
            review_score = 0
        
        # Rating score (normalizado a 0-40)
        rating_score = (rating / 5.0) * 40 if rating > 0 else 0
        
        demand_score = review_score + rating_score
        
        # Estimar ventas mensuales (aproximación)
        # Formula: reviews * 100 / edad_producto_meses
        # Asumimos edad promedio de 24 meses
        estimated_monthly_sales = (reviews_count * 100) / 24
        
        # Clasificar demanda
        if demand_score >= 80:
            demand_level = "very_high"
        elif demand_score >= 60:
            demand_level = "high"
        elif demand_score >= 40:
            demand_level = "medium"
        elif demand_score >= 20:
            demand_level = "low"
        else:
            demand_level = "very_low"
        
        return {
            "demand_score": round(demand_score, 2),
            "demand_level": demand_level,
            "reviews_count": reviews_count,
            "rating": rating,
            "estimated_monthly_sales": round(estimated_monthly_sales, 0),
            "estimated_monthly_revenue": round(
                estimated_monthly_sales * product.get("price", 0), 2
            )
        }
    
    async def _analyze_competition(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza el nivel de competencia buscando competidores reales via SerpAPI.
        
        Indicadores:
        - Número de competidores similares
        - Reviews count (muchas reviews = alta competencia)
        - Rating (alto rating = competidores establecidos)
        - Price point (precio bajo = competencia en precio)
        
        Args:
            product: Datos del producto
        
        Returns:
            Diccionario con análisis de competencia
        """
        reviews_count = product.get("reviews_count", product.get("reviews", 0))
        rating = product.get("rating", 0)
        price = product.get("price", 0)
        title = product.get("title", "")
        
        # Buscar competidores reales si SerpAPI está disponible
        competitors = []
        if SERPAPI_AVAILABLE and self.serpapi_key:
            try:
                competitors = await self._fetch_competitors(title, price)
                self.logger.info(f"Found {len(competitors)} competitors for {product.get('asin', 'unknown')}")
            except Exception as e:
                self.logger.warning(f"Failed to fetch competitors: {e}")
        
        # Calcular competition score (0-100)
        import math
        
        # Score basado en reviews del producto actual
        if reviews_count > 1000:
            review_competition = 60
        elif reviews_count > 500:
            review_competition = 45
        elif reviews_count > 100:
            review_competition = 30
        else:
            review_competition = 15
        
        # Score basado en rating
        rating_competition = (rating / 5.0) * 15 if rating > 0 else 0
        
        # Score basado en número de competidores encontrados
        if len(competitors) > 20:
            competitor_count_score = 25
        elif len(competitors) > 10:
            competitor_count_score = 18
        elif len(competitors) > 5:
            competitor_count_score = 10
        else:
            competitor_count_score = 5
        
        competition_score = review_competition + rating_competition + competitor_count_score
        
        # Analizar precios de competidores
        avg_competitor_price = 0
        if competitors:
            prices = [c.get("price", 0) for c in competitors if c.get("price", 0) > 0]
            avg_competitor_price = sum(prices) / len(prices) if prices else 0
        
        # Clasificar competencia
        if competition_score >= 80:
            competition_level = "very_high"
            entry_difficulty = "hard"
        elif competition_score >= 60:
            competition_level = "high"
            entry_difficulty = "moderate"
        elif competition_score >= 40:
            competition_level = "medium"
            entry_difficulty = "easy"
        else:
            competition_level = "low"
            entry_difficulty = "very_easy"
        
        return {
            "competition_score": round(competition_score, 2),
            "competition_level": competition_level,
            "entry_difficulty": entry_difficulty,
            "market_saturation": "high" if reviews_count > 1000 else "medium" if reviews_count > 100 else "low",
            "competitor_count": len(competitors),
            "avg_competitor_price": round(avg_competitor_price, 2) if avg_competitor_price > 0 else None,
            "top_competitors": competitors[:5] if competitors else []
        }
    
    async def _fetch_competitors(self, product_title: str, price: float) -> List[Dict[str, Any]]:
        """
        Busca competidores similares usando SerpAPI.
        
        Args:
            product_title: Título del producto
            price: Precio del producto
        
        Returns:
            Lista de competidores encontrados
        """
        if not SERPAPI_AVAILABLE or not self.serpapi_key:
            return []
        
        try:
            # Extraer keywords principales del título
            keywords = " ".join(product_title.split()[:4])  # Primeras 4 palabras
            
            # Buscar en Amazon
            search = GoogleSearch({
                "engine": "amazon",
                "amazon_domain": "amazon.com",
                "q": keywords,
                "api_key": self.serpapi_key
            })
            
            # Ejecutar búsqueda en thread separado (GoogleSearch es blocking)
            results = await asyncio.to_thread(lambda: search.get_dict())
            
            competitors = []
            organic_results = results.get("organic_results", [])
            
            for result in organic_results[:10]:  # Top 10 competidores
                competitor_price = result.get("price")
                if competitor_price:
                    # Parsear precio (puede venir como "$19.99" o {"value": 19.99})
                    if isinstance(competitor_price, dict):
                        competitor_price = competitor_price.get("value", 0)
                    elif isinstance(competitor_price, str):
                        competitor_price = float(competitor_price.replace("$", "").replace(",", ""))
                    else:
                        competitor_price = float(competitor_price)
                else:
                    competitor_price = 0
                
                competitors.append({
                    "asin": result.get("asin", ""),
                    "title": result.get("title", ""),
                    "price": competitor_price,
                    "rating": result.get("rating", 0),
                    "reviews": result.get("reviews", 0)
                })
            
            return competitors
            
        except Exception as e:
            self.logger.error(f"Error fetching competitors: {e}", exc_info=True)
            return []
    
    async def _analyze_seasonality(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza la estacionalidad del producto usando Google Trends.
        
        Args:
            product: Datos del producto
        
        Returns:
            Diccionario con análisis de estacionalidad
        """
        title = product.get("title", "")
        
        # Extraer keywords principales
        keywords = " ".join(title.split()[:3])  # Primeras 3 palabras
        
        if not PYTRENDS_AVAILABLE or not self.pytrends or not keywords:
            return {
                "seasonality_level": "unknown",
                "seasonality_score": 0,
                "trend_direction": "stable",
                "peak_months": [],
                "current_trend": "stable"
            }
        
        try:
            # Obtener datos de tendencia de los últimos 12 meses
            await asyncio.to_thread(
                self.pytrends.build_payload,
                [keywords],
                timeframe='today 12-m'
            )
            
            # Obtener datos de interés a lo largo del tiempo
            trend_data = await asyncio.to_thread(self.pytrends.interest_over_time)
            
            if trend_data.empty or keywords not in trend_data.columns:
                return {
                    "seasonality_level": "low",
                    "seasonality_score": 0,
                    "trend_direction": "stable",
                    "peak_months": [],
                    "current_trend": "stable"
                }
            
            # Calcular métricas de estacionalidad
            values = trend_data[keywords].values
            mean_val = values.mean()
            std_val = values.std()
            max_val = values.max()
            min_val = values.min()
            
            # Coefficient of variation (CV) - medida de estacionalidad
            cv = (std_val / mean_val * 100) if mean_val > 0 else 0
            
            # Clasificar estacionalidad
            if cv > 40:
                seasonality_level = "very_high"
                seasonality_score = min(cv, 100)
            elif cv > 25:
                seasonality_level = "high"
                seasonality_score = min(cv * 2, 100)
            elif cv > 15:
                seasonality_level = "medium"
                seasonality_score = min(cv * 3, 100)
            else:
                seasonality_level = "low"
                seasonality_score = max(10, cv * 4)
            
            # Identificar meses pico
            threshold = mean_val + std_val
            peak_indices = [i for i, v in enumerate(values) if v > threshold]
            peak_months = [trend_data.index[i].strftime("%B") for i in peak_indices if i < len(trend_data)]
            
            # Tendencia actual (últimos 3 meses vs anteriores)
            recent_mean = values[-3:].mean()
            previous_mean = values[-6:-3].mean()
            
            if recent_mean > previous_mean * 1.1:
                trend_direction = "growing"
                current_trend = "upward"
            elif recent_mean < previous_mean * 0.9:
                trend_direction = "declining"
                current_trend = "downward"
            else:
                trend_direction = "stable"
                current_trend = "stable"
            
            return {
                "seasonality_level": seasonality_level,
                "seasonality_score": round(seasonality_score, 2),
                "trend_direction": trend_direction,
                "current_trend": current_trend,
                "peak_months": peak_months,
                "coefficient_of_variation": round(cv, 2),
                "avg_interest": round(mean_val, 2),
                "max_interest": round(max_val, 2),
                "min_interest": round(min_val, 2)
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze seasonality: {e}")
            return {
                "seasonality_level": "unknown",
                "seasonality_score": 0,
                "trend_direction": "stable",
                "peak_months": [],
                "current_trend": "stable"
            }
    
    def _calculate_viability_score(
        self,
        roi_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any],
        seasonality_analysis: Dict[str, Any]
    ) -> float:
        """
        Calcula score global de viabilidad (0-100).
        
        Pesos:
        - ROI: 35%
        - Demanda: 30%
        - Competencia: 25% (inverso - menos competencia es mejor)
        - Estacionalidad: 10% (penaliza alta estacionalidad)
        
        Args:
            roi_analysis: Análisis de ROI
            demand_analysis: Análisis de demanda
            competition_analysis: Análisis de competencia
            seasonality_analysis: Análisis de estacionalidad
        
        Returns:
            Score de viabilidad (0-100)
        """
        # ROI score (normalizado a 0-100)
        roi_pct = roi_analysis.get("roi_percentage", 0)
        roi_score = min((roi_pct / 100) * 100, 100)
        
        # Demand score (ya está 0-100)
        demand_score = demand_analysis.get("demand_score", 0)
        
        # Competition score (invertido - menos competencia es mejor)
        competition_score = 100 - competition_analysis.get("competition_score", 0)
        
        # Seasonality score (penalizar alta estacionalidad)
        seasonality_score = seasonality_analysis.get("seasonality_score", 50)
        # Invertir: menos estacionalidad = mejor
        seasonality_score = 100 - min(seasonality_score, 100)
        
        # Ajustar por tendencia
        trend_direction = seasonality_analysis.get("trend_direction", "stable")
        if trend_direction == "growing":
            seasonality_score = min(seasonality_score * 1.2, 100)
        elif trend_direction == "declining":
            seasonality_score = seasonality_score * 0.8
        
        # Calcular weighted average
        viability_score = (
            roi_score * 0.35 +
            demand_score * 0.30 +
            competition_score * 0.25 +
            seasonality_score * 0.10
        )
        
        return round(viability_score, 2)
    
    def _make_recommendation(
        self,
        viability_score: float,
        roi_analysis: Dict[str, Any],
        seasonality_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera recomendación basada en análisis.
        
        Args:
            viability_score: Score de viabilidad
            roi_analysis: Análisis de ROI
            seasonality_analysis: Análisis de estacionalidad
        
        Returns:
            Diccionario con recomendación
        """
        roi_pct = roi_analysis.get("roi_percentage", 0)
        seasonality_level = seasonality_analysis.get("seasonality_level", "unknown")
        trend_direction = seasonality_analysis.get("trend_direction", "stable")
        
        # Decisión: Go / No-Go / Maybe
        if viability_score >= self.min_viability_score and roi_pct >= self.min_roi:
            decision = "GO"
            confidence = "high"
            reason = "Product meets all criteria for profitability"
        elif viability_score >= self.min_viability_score * 0.8:
            decision = "MAYBE"
            confidence = "medium"
            reason = "Product shows potential but requires careful evaluation"
        else:
            decision = "NO_GO"
            confidence = "high"
            reason = "Product does not meet minimum viability criteria"
        
        # Ajustar decisión por estacionalidad
        if seasonality_level == "very_high" and decision == "GO":
            decision = "MAYBE"
            confidence = "medium"
            reason = "Good metrics but very high seasonality introduces risk"
        
        # Factores de riesgo
        risks = []
        if roi_pct < self.min_roi:
            risks.append("Low ROI - may not be profitable enough")
        if viability_score < 50:
            risks.append("Low viability score - high risk")
        if seasonality_level in ["high", "very_high"]:
            risks.append(f"High seasonality - demand fluctuates significantly")
        if trend_direction == "declining":
            risks.append("Declining trend - market interest is decreasing")
        
        # Oportunidades
        opportunities = []
        if roi_pct >= self.min_roi:
            opportunities.append("Good profit margins")
        if viability_score >= 70:
            opportunities.append("High viability - good market fit")
        if trend_direction == "growing":
            opportunities.append("Growing trend - increasing market interest")
        if seasonality_level == "low":
            opportunities.append("Low seasonality - stable demand year-round")
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reason": reason,
            "risks": risks,
            "opportunities": opportunities,
            "next_actions": self._get_next_actions(decision)
        }
    
    async def _deep_market_analysis(
        self,
        product: Dict[str, Any],
        roi_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any],
        seasonality_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Realiza análisis de mercado profundo usando Claude Skills.
        
        Args:
            product: Datos del producto
            roi_analysis: Análisis de ROI
            demand_analysis: Análisis de demanda
            competition_analysis: Análisis de competencia
            seasonality_analysis: Análisis de estacionalidad
        
        Returns:
            Diccionario con análisis profundo de Claude
        """
        try:
            # Preparar datos para la skill
            input_data = {
                "product": {
                    "title": product.get("title", "Unknown"),
                    "price": float(product.get("price", 0)),
                    "rating": float(product.get("rating", 0)),
                    "reviews": int(product.get("reviews", 0)),
                    "bsr": int(product.get("bsr", 999999)),
                    "asin": product.get("asin", "N/A")
                },
                "market_context": {
                    "roi_percentage": roi_analysis.get("roi_percentage", 0),
                    "profit_per_unit": roi_analysis.get("profit_per_unit", 0),
                    "demand_score": demand_analysis.get("demand_score", 0),
                    "demand_level": demand_analysis.get("demand_level", "unknown"),
                    "estimated_monthly_sales": demand_analysis.get("estimated_monthly_sales", 0),
                    "competition_level": competition_analysis.get("competition_level", "unknown"),
                    "competition_score": competition_analysis.get("competition_score", 0),
                    "competitor_count": competition_analysis.get("competitor_count", 0),
                    "seasonality_level": seasonality_analysis.get("seasonality_level", "unknown"),
                    "trend_direction": seasonality_analysis.get("trend_direction", "stable"),
                    "peak_months": seasonality_analysis.get("peak_months", [])
                }
            }
            
            # Invocar skill
            self.logger.info(f"Running deep market analysis with Claude for {product.get('asin', 'unknown')}")
            result = await self.market_analysis_skill.execute(
                input_data,
                self.claude_service
            )
            
            if result.success:
                self.logger.info(f"Deep analysis successful, opportunity score: {result.data.get('opportunity_score', 'N/A')}")
                return result.data
            else:
                self.logger.error(f"Deep analysis skill failed: {result.error}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error in deep market analysis: {e}", exc_info=True)
            raise
    
    def _get_next_actions(self, decision: str) -> List[str]:
        """
        Determina las acciones siguientes basadas en la decisión.
        
        Args:
            decision: Decisión tomada (GO/NO_GO/MAYBE)
        
        Returns:
            Lista de acciones recomendadas
        """
        if decision == "GO":
            return [
                "Contact suppliers for quotes",
                "Optimize pricing strategy",
                "Setup inventory tracking",
                "Create product listing"
            ]
        elif decision == "MAYBE":
            return [
                "Perform deeper market research",
                "Analyze similar products",
                "Test with small inventory",
                "Monitor for 30 days"
            ]
        else:  # NO_GO
            return [
                "Discard product",
                "Search for alternatives",
                "Analyze why it failed criteria"
            ]

