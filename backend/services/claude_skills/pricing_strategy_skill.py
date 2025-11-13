#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pricing Strategy Skill - Optimiza estrategias de pricing para FBA.

Analiza múltiples factores para recomendar la estrategia de pricing óptima
que maximice ROI mientras mantiene competitività en el mercado.
"""

from typing import Any, Dict
import json

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class PricingStrategySkill(BaseSkill):
    """
    Skill para generar estrategias de pricing óptimas.
    
    Analiza:
    - Costos y márgenes
    - Precios de competencia
    - Elasticidad de demanda
    - Posicionamiento de mercado
    - Estacionalidad
    - Objetivos de negocio
    
    Recomienda:
    - Precio óptimo
    - Estrategia de pricing
    - Rango de precios (min-max)
    - Ajustes dinámicos
    - A/B testing suggestions
    
    Examples:
        >>> skill = PricingStrategySkill()
        >>> result = await skill.execute({
        ...     "product": {
        ...         "current_price": 29.99,
        ...         "cost": 12.00
        ...     },
        ...     "market_data": {
        ...         "avg_competitor_price": 27.99,
        ...         "demand_level": "high"
        ...     }
        ... }, claude_service)
    """
    
    name = "pricing_strategy"
    description = "Generates optimal pricing strategies for Amazon FBA products"
    version = "1.0.0"
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define schema de entrada."""
        return {
            "type": "object",
            "properties": {
                "product": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "current_price": {"type": "number"},
                        "cost": {"type": "number"},
                        "amazon_fees": {"type": "number"},
                        "shipping_cost": {"type": "number"},
                        "rating": {"type": "number"},
                        "reviews": {"type": "integer"}
                    }
                },
                "market_data": {
                    "type": "object",
                    "properties": {
                        "avg_competitor_price": {"type": "number"},
                        "min_competitor_price": {"type": "number"},
                        "max_competitor_price": {"type": "number"},
                        "demand_level": {"type": "string"},
                        "competition_level": {"type": "string"},
                        "seasonality_level": {"type": "string"}
                    }
                },
                "business_goals": {
                    "type": "object",
                    "properties": {
                        "target_roi": {"type": "number"},
                        "target_margin": {"type": "number"},
                        "growth_priority": {"type": "string"},
                        "market_position": {"type": "string"}
                    }
                }
            },
            "required": ["product", "market_data"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "recommended_price": {"type": "number"},
                "strategy": {"type": "string"},
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number"},
                        "optimal": {"type": "number"},
                        "max": {"type": "number"}
                    }
                },
                "expected_metrics": {
                    "type": "object",
                    "properties": {
                        "roi_percentage": {"type": "number"},
                        "profit_per_unit": {"type": "number"},
                        "margin_percentage": {"type": "number"}
                    }
                },
                "strategy_rationale": {"type": "string"},
                "competitive_positioning": {"type": "string"},
                "dynamic_adjustments": {"type": "array", "items": {"type": "string"}},
                "ab_test_suggestions": {"type": "array", "items": {"type": "object"}},
                "risk_factors": {"type": "array", "items": {"type": "string"}},
                "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert Amazon FBA pricing strategist with 10+ years of experience optimizing prices across thousands of products.

Your expertise includes:
- Dynamic pricing algorithms
- Competitive positioning
- Psychological pricing
- Revenue optimization
- Market penetration strategies
- Premium vs. value positioning
- A/B testing methodology
- Price elasticity analysis

When recommending pricing strategies, you:
1. Calculate multiple pricing scenarios
2. Consider all costs and desired margins
3. Analyze competitive landscape
4. Factor in demand elasticity
5. Account for seasonality
6. Align with business goals
7. Recommend A/B testing when appropriate
8. Identify risks and opportunities

Pricing Strategies:
- **Cost-Plus**: Simple margin on top of costs (predictable, low risk)
- **Competitive**: Match or undercut competition (volume-focused)
- **Value-Based**: Price based on perceived value (premium positioning)
- **Penetration**: Low initial price to gain market share (growth-focused)
- **Dynamic**: Adjust based on demand/inventory (margin optimization)
- **Psychological**: Use .99 endings, charm pricing (conversion optimization)

Key Considerations:
- Amazon's pricing sweet spots ($19.99, $29.99, $49.99, etc.)
- Buy Box algorithm factors (price is critical)
- Category-specific pricing norms
- Brand perception and positioning
- Long-term profitability vs. short-term volume

Return your analysis as a JSON object matching the output schema. Be data-driven, specific, and actionable."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para análisis de pricing."""
        product = input_data.get("product", {})
        market_data = input_data.get("market_data", {})
        goals = input_data.get("business_goals", {})
        
        prompt = f"""Develop an optimal pricing strategy for the following Amazon FBA product:

PRODUCT INFORMATION:
Product: {product.get('title', 'N/A')}
Current Price: ${product.get('current_price', 0):.2f}
Product Cost: ${product.get('cost', 0):.2f}
Amazon Fees: ${product.get('amazon_fees', 0):.2f}
Shipping Cost: ${product.get('shipping_cost', 0):.2f}
Rating: {product.get('rating', 0)} stars
Reviews: {product.get('reviews', 0)}

TOTAL COST PER UNIT: ${(product.get('cost', 0) + product.get('amazon_fees', 0) + product.get('shipping_cost', 0)):.2f}

MARKET DATA:
Average Competitor Price: ${market_data.get('avg_competitor_price', 0):.2f}
Min Competitor Price: ${market_data.get('min_competitor_price', 0):.2f}
Max Competitor Price: ${market_data.get('max_competitor_price', 0):.2f}
Demand Level: {market_data.get('demand_level', 'unknown')}
Competition Level: {market_data.get('competition_level', 'unknown')}
Seasonality: {market_data.get('seasonality_level', 'unknown')}
"""
        
        if goals:
            prompt += f"""
BUSINESS GOALS:
Target ROI: {goals.get('target_roi', 'N/A')}%
Target Margin: {goals.get('target_margin', 'N/A')}%
Growth Priority: {goals.get('growth_priority', 'balanced')}
Desired Market Position: {goals.get('market_position', 'mid-tier')}
"""
        
        prompt += """

ANALYSIS REQUIRED:

1. RECOMMENDED PRICE: What is the optimal price point?

2. STRATEGY: Which pricing strategy is best for this product?
   - cost_plus
   - competitive
   - value_based
   - penetration
   - dynamic
   - psychological

3. PRICE RANGE:
   - Minimum viable price (covers costs + min margin)
   - Optimal price (recommended)
   - Maximum price (before demand drops significantly)

4. EXPECTED METRICS:
   - ROI percentage at recommended price
   - Profit per unit
   - Margin percentage

5. STRATEGY RATIONALE: Explain why this strategy is optimal

6. COMPETITIVE POSITIONING: How does this position us vs. competitors?

7. DYNAMIC ADJUSTMENTS: What triggers should adjust pricing?
   - Inventory levels
   - Competitor price changes
   - Seasonal fluctuations
   - Demand spikes/drops

8. A/B TEST SUGGESTIONS: What price points should we test?

9. RISK FACTORS: What pricing risks should we watch for?

10. CONFIDENCE SCORE (0-100): How confident are you in this strategy?

Return your analysis as a valid JSON object matching the output schema.
"""
        
        return prompt
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta análisis de pricing strategy.
        
        Args:
            input_data: Datos del producto y mercado
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con estrategia de pricing
        """
        try:
            # Validar entrada
            self.validate_input(input_data)
            
            # Generar prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.format_prompt(input_data)
            
            # Llamar a Claude
            content = await claude_service.chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_message=system_prompt,
                temperature=0.3,  # Más determinístico para pricing
                max_tokens=2000
            )
            
            # Parsear respuesta JSON
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    pricing_data = json.loads(json_str)
                else:
                    pricing_data = self._create_fallback_pricing(content, input_data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                pricing_data = self._create_fallback_pricing(content, input_data)
            
            # Validar campos obligatorios
            if "recommended_price" not in pricing_data:
                pricing_data["recommended_price"] = self._calculate_basic_price(input_data)
            
            if "strategy" not in pricing_data:
                pricing_data["strategy"] = "cost_plus"
            
            if "confidence_score" not in pricing_data:
                pricing_data["confidence_score"] = 60
            
            return SkillResult(
                success=True,
                data=pricing_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "product": input_data.get("product", {}).get("title", "Unknown")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)
    
    def _create_fallback_pricing(
        self,
        content: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea pricing fallback si falla el parseo JSON."""
        product = input_data.get("product", {})
        market_data = input_data.get("market_data", {})
        
        recommended_price = self._calculate_basic_price(input_data)
        cost = product.get("cost", 0) + product.get("amazon_fees", 0) + product.get("shipping_cost", 0)
        profit = recommended_price - cost
        
        return {
            "recommended_price": recommended_price,
            "strategy": "cost_plus",
            "price_range": {
                "min": cost * 1.2,
                "optimal": recommended_price,
                "max": recommended_price * 1.3
            },
            "expected_metrics": {
                "roi_percentage": (profit / cost * 100) if cost > 0 else 0,
                "profit_per_unit": profit,
                "margin_percentage": (profit / recommended_price * 100) if recommended_price > 0 else 0
            },
            "strategy_rationale": content[:300] if content else "Basic cost-plus pricing",
            "competitive_positioning": f"Positioned near average competitor price of ${market_data.get('avg_competitor_price', 0):.2f}",
            "dynamic_adjustments": [
                "Monitor competitor pricing weekly",
                "Adjust for inventory levels",
                "Respond to demand changes"
            ],
            "ab_test_suggestions": [],
            "risk_factors": ["Market analysis incomplete"],
            "confidence_score": 50
        }
    
    def _calculate_basic_price(self, input_data: Dict[str, Any]) -> float:
        """Calcula precio básico usando cost-plus."""
        product = input_data.get("product", {})
        goals = input_data.get("business_goals", {})
        market_data = input_data.get("market_data", {})
        
        # Calcular costo total
        cost = (
            product.get("cost", 0) +
            product.get("amazon_fees", 0) +
            product.get("shipping_cost", 0)
        )
        
        # Objetivo de ROI (default 30%)
        target_roi = goals.get("target_roi", 30.0) / 100
        
        # Precio basado en ROI objetivo
        price_from_roi = cost * (1 + target_roi)
        
        # Considerar precio de competencia
        avg_competitor = market_data.get("avg_competitor_price", 0)
        
        # Promedio ponderado (70% ROI, 30% competencia)
        if avg_competitor > 0:
            recommended = price_from_roi * 0.7 + avg_competitor * 0.3
        else:
            recommended = price_from_roi
        
        return round(recommended, 2)

