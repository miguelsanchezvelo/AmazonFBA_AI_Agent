#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Analysis Skill - Análisis profundo de mercado para productos FBA.

Analiza oportunidades de mercado combinando datos de:
- Demanda (reviews, BSR, tendencias)
- Competencia (precios, saturación, ratings)
- Estacionalidad (Google Trends, patrones)
- ROI potencial (márgenes, costos)
"""

from typing import Any, Dict
import json

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class MarketAnalysisSkill(BaseSkill):
    """
    Skill para análisis profundo de mercado FBA.
    
    Genera análisis completo que incluye:
    - Evaluación de demanda y tendencias
    - Análisis de competencia
    - Oportunidades y riesgos
    - Recomendaciones estratégicas
    - Score de oportunidad (0-100)
    
    Examples:
        >>> skill = MarketAnalysisSkill()
        >>> result = await skill.execute({
        ...     "product": {
        ...         "title": "Yoga Mat",
        ...         "price": 29.99,
        ...         "rating": 4.5,
        ...         "reviews": 1500,
        ...         "bsr": 2500
        ...     },
        ...     "competitors": [...],
        ...     "trend_data": {...}
        ... }, claude_service)
    """
    
    name = "market_analysis"
    description = "Performs deep market analysis for Amazon FBA products"
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
                        "price": {"type": "number"},
                        "rating": {"type": "number"},
                        "reviews": {"type": "integer"},
                        "bsr": {"type": "integer"}
                    }
                },
                "competitors": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "trend_data": {"type": "object"},
                "market_context": {"type": "object"}
            },
            "required": ["product"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "opportunity_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "demand_analysis": {"type": "string"},
                "competition_analysis": {"type": "string"},
                "profitability_estimate": {"type": "object"},
                "risks": {"type": "array", "items": {"type": "string"}},
                "opportunities": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "market_insights": {"type": "array", "items": {"type": "string"}}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert Amazon FBA market analyst with 10+ years of experience helping sellers identify profitable products.

Your expertise includes:
- Amazon marketplace dynamics and algorithms
- Product demand forecasting
- Competitive landscape analysis
- Profit margin optimization
- Risk assessment and mitigation
- Seasonal trend analysis
- Private label strategy

When analyzing products, you:
1. Evaluate demand indicators (reviews, BSR, search volume)
2. Assess competition level and saturation
3. Calculate realistic profit margins considering all FBA fees
4. Identify opportunities and risks
5. Provide actionable, data-driven recommendations
6. Give honest assessments - not every product is a good opportunity

Key metrics you consider:
- BSR (Best Seller Rank): Lower is better, <5000 in main category is good
- Reviews: 100-1000 reviews shows proven demand without oversaturation
- Rating: >4.0 stars indicates quality products
- Price point: $15-$50 is sweet spot for FBA
- Review velocity: Recent reviews indicate current demand

Return your analysis as a JSON object with the structure specified in your output schema. Be specific, quantitative, and actionable."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para análisis de mercado."""
        product = input_data.get("product", {})
        competitors = input_data.get("competitors", [])
        trend_data = input_data.get("trend_data", {})
        market_context = input_data.get("market_context", {})
        
        prompt = f"""Analyze the following Amazon FBA product opportunity:

PRODUCT INFORMATION:
Title: {product.get('title', 'N/A')}
Price: ${product.get('price', 0)}
Rating: {product.get('rating', 0)} stars
Reviews: {product.get('reviews', 0)} reviews
BSR: {product.get('bsr', 'N/A')}
ASIN: {product.get('asin', 'N/A')}

"""
        
        # Agregar información de competidores si existe
        if competitors:
            prompt += f"\nCOMPETITOR DATA:\n"
            for i, comp in enumerate(competitors[:5], 1):  # Máximo 5 competidores
                prompt += f"\nCompetitor {i}:"
                prompt += f"\n  Price: ${comp.get('price', 0)}"
                prompt += f"\n  Rating: {comp.get('rating', 0)} stars"
                prompt += f"\n  Reviews: {comp.get('reviews', 0)}"
                if 'bsr' in comp:
                    prompt += f"\n  BSR: {comp.get('bsr')}"
        
        # Agregar datos de tendencias si existen
        if trend_data:
            prompt += f"\n\nTREND DATA:\n{json.dumps(trend_data, indent=2)}"
        
        # Agregar contexto de mercado si existe
        if market_context:
            prompt += f"\n\nMARKET CONTEXT:\n{json.dumps(market_context, indent=2)}"
        
        prompt += """

ANALYSIS REQUIRED:

1. OPPORTUNITY SCORE (0-100): Overall opportunity rating considering all factors

2. DEMAND ANALYSIS: 
   - Is there sufficient proven demand?
   - Are sales volumes sustainable?
   - What does review velocity indicate?
   - Any seasonality concerns?

3. COMPETITION ANALYSIS:
   - How saturated is this market?
   - Can a new seller compete?
   - What are competitor strengths/weaknesses?
   - Entry barriers?

4. PROFITABILITY ESTIMATE:
   - Estimated unit economics
   - Expected profit margins
   - Break-even analysis

5. RISKS: List key risks (market, operational, financial)

6. OPPORTUNITIES: List specific opportunities to differentiate or capitalize

7. RECOMMENDATIONS: Actionable next steps

8. MARKET INSIGHTS: Key takeaways about this market

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
        Ejecuta análisis de mercado.
        
        Args:
            input_data: Datos del producto, competencia y tendencias
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con análisis completo
        """
        try:
            # Validar entrada
            self.validate_input(input_data)
            
            # Generar prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.format_prompt(input_data)
            
            # Llamar a Claude con mayor cantidad de tokens para análisis completo
            response = await claude_service.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.5,  # Más determinístico para análisis
                max_tokens=3000
            )
            
            # Parsear respuesta JSON
            content = response.get("content", "")
            
            # Intentar parsear como JSON
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    analysis_data = json.loads(json_str)
                else:
                    # Fallback: estructura básica
                    analysis_data = self._create_fallback_analysis(content, input_data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                analysis_data = self._create_fallback_analysis(content, input_data)
            
            # Validar campos obligatorios
            if "opportunity_score" not in analysis_data:
                analysis_data["opportunity_score"] = self._estimate_score(input_data)
            
            return SkillResult(
                success=True,
                data=analysis_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "usage": response.get("usage", {}),
                    "model": response.get("model", "")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)
    
    def _create_fallback_analysis(
        self,
        content: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea análisis fallback si falla el parseo JSON."""
        product = input_data.get("product", {})
        
        return {
            "opportunity_score": self._estimate_score(input_data),
            "demand_analysis": content[:500] if len(content) > 500 else content,
            "competition_analysis": "Analysis available in full content",
            "profitability_estimate": {
                "estimated_margin": "To be calculated",
                "confidence": "medium"
            },
            "risks": ["Further analysis required"],
            "opportunities": ["Review full analysis for details"],
            "recommendations": [content] if content else ["Request detailed analysis"],
            "market_insights": [f"Product: {product.get('title', 'Unknown')}"]
        }
    
    def _estimate_score(self, input_data: Dict[str, Any]) -> int:
        """Estima score básico basado en métricas del producto."""
        product = input_data.get("product", {})
        
        score = 50  # Base score
        
        # Ajustar por rating
        rating = product.get("rating", 0)
        if rating >= 4.5:
            score += 10
        elif rating >= 4.0:
            score += 5
        elif rating < 3.5:
            score -= 10
        
        # Ajustar por reviews (sweet spot: 100-1000)
        reviews = product.get("reviews", 0)
        if 100 <= reviews <= 1000:
            score += 15
        elif 50 <= reviews < 100:
            score += 10
        elif reviews > 2000:
            score -= 10  # Muy competido
        
        # Ajustar por BSR
        bsr = product.get("bsr", 999999)
        if bsr < 5000:
            score += 15
        elif bsr < 10000:
            score += 10
        elif bsr > 50000:
            score -= 10
        
        # Ajustar por precio
        price = product.get("price", 0)
        if 15 <= price <= 50:
            score += 10
        elif price < 10:
            score -= 5  # Márgenes muy bajos
        
        return max(0, min(100, score))  # Clamp entre 0-100

