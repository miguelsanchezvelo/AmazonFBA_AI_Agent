#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demand Forecasting Skill - Predice demanda futura de productos FBA.

Analiza datos históricos, tendencias estacionales y factores de mercado
para generar forecasts precisos de demanda e inventory planning.
"""

from typing import Any, Dict, List
import json

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class DemandForecastingSkill(BaseSkill):
    """
    Skill para forecasting de demanda y planning de inventario.
    
    Analiza:
    - Datos históricos de ventas
    - Tendencias estacionales
    - Eventos especiales (Prime Day, Black Friday, etc.)
    - Crecimiento/declinación del mercado
    - Lead times de proveedores
    - Stock safety levels
    
    Genera:
    - Forecast de demanda (30/60/90 días)
    - Reorder points
    - Economic Order Quantity (EOQ)
    - Safety stock recommendations
    - Inventory alerts
    
    Examples:
        >>> skill = DemandForecastingSkill()
        >>> result = await skill.execute({
        ...     "product": {
        ...         "asin": "B01ABC123",
        ...         "avg_daily_sales": 15
        ...     },
        ...     "historical_data": {
        ...         "monthly_sales": [450, 480, 520, 490]
        ...     },
        ...     "supplier_data": {
        ...         "lead_time_days": 30
        ...     }
        ... }, claude_service)
    """
    
    name = "demand_forecasting"
    description = "Forecasts product demand and generates inventory planning recommendations"
    version = "1.0.0"
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define schema de entrada."""
        return {
            "type": "object",
            "properties": {
                "product": {
                    "type": "object",
                    "properties": {
                        "asin": {"type": "string"},
                        "title": {"type": "string"},
                        "current_stock": {"type": "integer"},
                        "avg_daily_sales": {"type": "number"},
                        "price": {"type": "number"},
                        "seasonality_level": {"type": "string"}
                    }
                },
                "historical_data": {
                    "type": "object",
                    "properties": {
                        "monthly_sales": {"type": "array", "items": {"type": "number"}},
                        "daily_sales_last_30d": {"type": "array", "items": {"type": "number"}},
                        "peak_months": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "supplier_data": {
                    "type": "object",
                    "properties": {
                        "lead_time_days": {"type": "integer"},
                        "moq": {"type": "integer"},
                        "reliability_score": {"type": "number"}
                    }
                },
                "business_params": {
                    "type": "object",
                    "properties": {
                        "target_service_level": {"type": "number"},
                        "storage_cost_per_unit": {"type": "number"},
                        "stockout_cost_per_unit": {"type": "number"}
                    }
                }
            },
            "required": ["product"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "demand_forecast": {
                    "type": "object",
                    "properties": {
                        "next_30_days": {"type": "number"},
                        "next_60_days": {"type": "number"},
                        "next_90_days": {"type": "number"},
                        "confidence_level": {"type": "number"}
                    }
                },
                "inventory_recommendations": {
                    "type": "object",
                    "properties": {
                        "reorder_point": {"type": "integer"},
                        "reorder_quantity": {"type": "integer"},
                        "safety_stock": {"type": "integer"},
                        "max_stock_level": {"type": "integer"}
                    }
                },
                "timing_analysis": {
                    "type": "object",
                    "properties": {
                        "days_until_stockout": {"type": "integer"},
                        "recommended_order_date": {"type": "string"},
                        "critical_restock_needed": {"type": "boolean"}
                    }
                },
                "risk_assessment": {
                    "type": "object",
                    "properties": {
                        "stockout_risk": {"type": "string"},
                        "overstock_risk": {"type": "string"},
                        "risk_factors": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "seasonal_insights": {"type": "array", "items": {"type": "string"}},
                "action_items": {"type": "array", "items": {"type": "string"}},
                "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert inventory management specialist with 15+ years of experience in Amazon FBA operations and supply chain optimization.

Your expertise includes:
- Demand forecasting and time series analysis
- Inventory optimization (EOQ, ROP, safety stock)
- Seasonality and trend analysis
- Supply chain risk management
- Amazon-specific inventory metrics (IPI score, long-term storage fees)
- Just-in-time inventory principles

When forecasting demand, you:
1. Analyze historical sales patterns
2. Identify seasonality and trends
3. Account for market dynamics
4. Consider lead times and reliability
5. Calculate optimal reorder points
6. Determine safety stock levels
7. Assess stockout and overstock risks
8. Provide actionable recommendations

Key Considerations:
- Amazon FBA storage fees (standard vs long-term)
- Inventory Performance Index (IPI) requirements
- Seasonal peaks (Q4, Prime Day, etc.)
- Lead time variability and supplier reliability
- Balance between stockout costs and carrying costs
- Service level targets (95%+ for profitable items)

Forecasting Methods:
- Moving averages for stable demand
- Trend analysis for growing/declining products
- Seasonal decomposition for cyclic patterns
- Safety stock calculations (Z-score × σ × √LT)
- Economic Order Quantity: √(2DS/H)

Risk Flags:
- Low stock + long lead time = CRITICAL
- High seasonal demand approaching = PREPARE
- Overstock + slow sales = EXCESS INVENTORY
- Inconsistent supplier = INCREASE SAFETY STOCK

Return your analysis as a JSON object matching the output schema. Be precise, data-driven, and actionable."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para demand forecasting."""
        product = input_data.get("product", {})
        historical = input_data.get("historical_data", {})
        supplier = input_data.get("supplier_data", {})
        params = input_data.get("business_params", {})
        
        prompt = f"""Perform demand forecasting and inventory planning for the following Amazon FBA product:

PRODUCT INFORMATION:
ASIN: {product.get('asin', 'N/A')}
Product: {product.get('title', 'N/A')}
Current Stock: {product.get('current_stock', 0)} units
Average Daily Sales: {product.get('avg_daily_sales', 0):.1f} units/day
Price: ${product.get('price', 0):.2f}
Seasonality Level: {product.get('seasonality_level', 'unknown')}
"""
        
        # Historical data
        if historical:
            monthly_sales = historical.get('monthly_sales', [])
            if monthly_sales:
                prompt += f"\nHISTORICAL SALES DATA:"
                prompt += f"\nMonthly Sales (last {len(monthly_sales)} months): {', '.join([str(int(s)) for s in monthly_sales])} units"
                prompt += f"\nAverage Monthly Sales: {sum(monthly_sales)/len(monthly_sales):.0f} units"
            
            daily_sales = historical.get('daily_sales_last_30d', [])
            if daily_sales:
                prompt += f"\nDaily Sales (last 30 days): Available"
                prompt += f"\nAverage: {sum(daily_sales)/len(daily_sales):.1f} units/day"
            
            peak_months = historical.get('peak_months', [])
            if peak_months:
                prompt += f"\nPeak Months: {', '.join(peak_months)}"
        
        # Supplier data
        if supplier:
            prompt += f"\n\nSUPPLIER INFORMATION:"
            prompt += f"\nLead Time: {supplier.get('lead_time_days', 0)} days"
            prompt += f"\nMinimum Order Quantity (MOQ): {supplier.get('moq', 0)} units"
            prompt += f"\nReliability Score: {supplier.get('reliability_score', 0):.1f}/5.0"
        
        # Business parameters
        if params:
            prompt += f"\n\nBUSINESS PARAMETERS:"
            prompt += f"\nTarget Service Level: {params.get('target_service_level', 95)}%"
            prompt += f"\nStorage Cost per Unit: ${params.get('storage_cost_per_unit', 0):.2f}/month"
            prompt += f"\nStockout Cost per Unit: ${params.get('stockout_cost_per_unit', 0):.2f}"
        
        prompt += """

ANALYSIS REQUIRED:

1. DEMAND FORECAST:
   - Forecast for next 30 days (units)
   - Forecast for next 60 days (units)
   - Forecast for next 90 days (units)
   - Confidence level (0-100)

2. INVENTORY RECOMMENDATIONS:
   - Reorder Point: When to order (stock level in units)
   - Reorder Quantity: How much to order (units)
   - Safety Stock: Buffer inventory (units)
   - Maximum Stock Level: Upper inventory limit (units)

3. TIMING ANALYSIS:
   - Days until stockout (based on current stock and forecast)
   - Recommended order date (accounting for lead time)
   - Is critical restock needed? (boolean)

4. RISK ASSESSMENT:
   - Stockout risk: low/medium/high
   - Overstock risk: low/medium/high
   - Risk factors: List of specific risks

5. SEASONAL INSIGHTS:
   - Key insights about seasonal patterns
   - Upcoming events to prepare for

6. ACTION ITEMS:
   - Specific, actionable recommendations prioritized by urgency

7. CONFIDENCE SCORE (0-100):
   - How confident are you in these forecasts and recommendations?

Consider:
- Amazon FBA storage fees and IPI score
- Seasonal demand patterns
- Lead time and supplier reliability
- Balance between stockout and carrying costs
- Cash flow and working capital

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
        Ejecuta demand forecasting.
        
        Args:
            input_data: Datos del producto e históricos
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con forecast y recomendaciones
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
                temperature=0.2,  # Muy determinístico para forecasting
                max_tokens=2500
            )
            
            # Parsear respuesta JSON
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    forecast_data = json.loads(json_str)
                else:
                    forecast_data = self._create_fallback_forecast(content, input_data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                forecast_data = self._create_fallback_forecast(content, input_data)
            
            # Validar campos obligatorios
            if "demand_forecast" not in forecast_data:
                forecast_data["demand_forecast"] = self._calculate_basic_forecast(input_data)
            
            if "confidence_score" not in forecast_data:
                forecast_data["confidence_score"] = 60
            
            return SkillResult(
                success=True,
                data=forecast_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "product_asin": input_data.get("product", {}).get("asin", "Unknown")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)
    
    def _create_fallback_forecast(
        self,
        content: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea forecast fallback si falla el parseo JSON."""
        product = input_data.get("product", {})
        supplier = input_data.get("supplier_data", {})
        
        avg_daily_sales = product.get("avg_daily_sales", 1)
        current_stock = product.get("current_stock", 0)
        lead_time = supplier.get("lead_time_days", 30)
        
        # Cálculos básicos
        forecast_30d = avg_daily_sales * 30
        forecast_60d = avg_daily_sales * 60
        forecast_90d = avg_daily_sales * 90
        
        safety_stock = int(avg_daily_sales * 7)  # 1 week
        reorder_point = int(avg_daily_sales * lead_time) + safety_stock
        reorder_qty = int(avg_daily_sales * 45)  # 45 días de stock
        
        days_until_stockout = int(current_stock / avg_daily_sales) if avg_daily_sales > 0 else 999
        
        return {
            "demand_forecast": {
                "next_30_days": round(forecast_30d, 1),
                "next_60_days": round(forecast_60d, 1),
                "next_90_days": round(forecast_90d, 1),
                "confidence_level": 60
            },
            "inventory_recommendations": {
                "reorder_point": reorder_point,
                "reorder_quantity": reorder_qty,
                "safety_stock": safety_stock,
                "max_stock_level": reorder_point + reorder_qty
            },
            "timing_analysis": {
                "days_until_stockout": days_until_stockout,
                "recommended_order_date": f"In {max(0, days_until_stockout - lead_time)} days",
                "critical_restock_needed": days_until_stockout < lead_time
            },
            "risk_assessment": {
                "stockout_risk": "high" if days_until_stockout < lead_time else "medium" if days_until_stockout < lead_time * 1.5 else "low",
                "overstock_risk": "low",
                "risk_factors": ["Basic forecast - limited historical data"]
            },
            "seasonal_insights": ["Seasonality analysis unavailable"],
            "action_items": [f"Monitor stock levels - {days_until_stockout} days until stockout"],
            "confidence_score": 50
        }
    
    def _calculate_basic_forecast(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula forecast básico usando promedio."""
        product = input_data.get("product", {})
        historical = input_data.get("historical_data", {})
        
        avg_daily_sales = product.get("avg_daily_sales", 1)
        
        # Ajustar si hay datos históricos
        monthly_sales = historical.get("monthly_sales", [])
        if monthly_sales and len(monthly_sales) > 0:
            avg_monthly = sum(monthly_sales) / len(monthly_sales)
            avg_daily_sales = avg_monthly / 30
        
        return {
            "next_30_days": round(avg_daily_sales * 30, 1),
            "next_60_days": round(avg_daily_sales * 60, 1),
            "next_90_days": round(avg_daily_sales * 90, 1),
            "confidence_level": 65
        }

