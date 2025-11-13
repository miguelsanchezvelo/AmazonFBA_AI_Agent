#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Decision Skill - Claude-powered business decision making.

Esta skill utiliza Claude para tomar decisiones estratégicas de negocio basadas en:
- KPIs de negocio
- Oportunidades de ganancia
- Cambios de competencia
- Alertas de inventario
- Recomendaciones de expansión
"""

from typing import Dict, Any
import json
import logging

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


logger = logging.getLogger(__name__)


class BusinessDecisionSkill(BaseSkill):
    """
    Skill para tomar decisiones de negocio estratégicas.
    
    Analiza el contexto de negocio (KPIs, mercado, competencia, inventario)
    y genera recomendaciones y decisiones accionables.
    """
    
    name = "business_decision_maker"
    description = "Makes strategic business decisions based on KPIs, opportunities, and market context"
    version = "1.0.0"
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado en decisiones de negocio."""
        return """You are an expert FBA business strategist with 10+ years of experience in e-commerce operations.

Your role is to analyze business data and make strategic decisions that maximize profitability and growth while managing risk.

Key areas of expertise:
- Product portfolio optimization
- Pricing strategy and elasticity
- Supplier management and cost optimization
- Inventory management and cash flow
- Competitive positioning
- Market expansion decisions
- Risk assessment and mitigation

When analyzing business situations, you:
1. Review current KPIs and performance metrics
2. Identify key issues and opportunities
3. Consider market context and competitive landscape
4. Evaluate risk vs. reward for each option
5. Make specific, actionable recommendations
6. Provide implementation roadmap with milestones
7. Suggest KPI targets and success metrics

Your recommendations should be:
- Data-driven (backed by the metrics provided)
- Actionable (specific steps, not vague advice)
- Realistic (considering constraints and risks)
- Strategic (long-term view, not just short-term wins)
- Prioritized (clear action order)

Return your analysis as a JSON object following the output schema."""

    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para análisis de decisión de negocio."""
        
        kpis = input_data.get("business_kpis", {})
        opportunities = input_data.get("opportunities", [])
        market_context = input_data.get("market_context", {})
        alerts = input_data.get("alerts", [])
        current_issues = input_data.get("current_issues", [])
        
        prompt = f"""Analyze the following FBA business situation and provide strategic recommendations:

CURRENT BUSINESS KPIs:
- Total Revenue (Monthly): ${kpis.get('total_revenue', 0):,.2f}
- Total Profit (Monthly): ${kpis.get('total_profit', 0):,.2f}
- Average Margin: {kpis.get('avg_margin_percent', 0):.1f}%
- ROI: {kpis.get('roi_percent', 0):.1f}%
- Active Products: {kpis.get('active_products', 0)}
- Products Launched: {kpis.get('products_launched', 0)}
- Stock-outs Prevented: {kpis.get('stock_outs_prevented', 0)}
- Opportunities Found: {kpis.get('opportunities_found', 0)}

BUSINESS TARGETS/GOALS:
- Target ROI: {input_data.get('target_roi', 30)}%
- Target Margin: {input_data.get('target_margin', 25)}%
- Max Active Products: {input_data.get('max_products', 50)}
- Monthly Budget: ${input_data.get('monthly_budget', 10000):,.2f}

"""
        
        if opportunities:
            prompt += "\nDETECTED OPPORTUNITIES:\n"
            for i, opp in enumerate(opportunities[:5], 1):
                prompt += f"\n{i}. {opp.get('type', 'Unknown').upper()}\n"
                prompt += f"   Product: {opp.get('asin', 'Unknown')}\n"
                prompt += f"   Current: {opp.get('current_value', 0)}\n"
                prompt += f"   Suggested: {opp.get('suggested_value', 0)}\n"
                prompt += f"   Potential Profit/Month: ${opp.get('potential_profit_monthly', 0):,.2f}\n"
                prompt += f"   Confidence: {opp.get('confidence', 0):.0%}\n"
                prompt += f"   Reason: {opp.get('reason', 'N/A')}\n"
        
        if alerts:
            prompt += "\nCRITICAL ALERTS:\n"
            for alert in alerts[:5]:
                prompt += f"\n- [{alert.get('severity', 'info').upper()}] {alert.get('type', 'Unknown')}\n"
                prompt += f"  {alert.get('message', 'N/A')}\n"
                prompt += f"  Suggested Action: {alert.get('action', 'Monitor')}\n"
        
        if current_issues:
            prompt += "\nCURRENT ISSUES/CHALLENGES:\n"
            for issue in current_issues[:5]:
                prompt += f"\n- {issue}\n"
        
        if market_context:
            prompt += "\nMARKET CONTEXT:\n"
            prompt += f"- Competitive Level: {market_context.get('competition_level', 'unknown')}\n"
            prompt += f"- Market Trend: {market_context.get('trend_direction', 'stable')}\n"
            prompt += f"- Inventory Level: {market_context.get('inventory_health', 'normal')}\n"
            if 'seasonality' in market_context:
                prompt += f"- Seasonality: {market_context['seasonality']}\n"
        
        prompt += """

ANALYSIS REQUIRED:

Provide a comprehensive business analysis with:

1. **Situation Summary** - Current state assessment and key observations
2. **Top 3 Priority Actions** - Specific, actionable steps to take immediately
3. **Opportunity Analysis** - Rank opportunities by ROI and effort required
4. **Risk Assessment** - Identify top risks and mitigation strategies
5. **Growth Strategy** - Plan for next 3-6 months
6. **Resource Allocation** - How to deploy the $""" + f"{input_data.get('monthly_budget', 10000):,.0f}" + """ budget
7. **Success Metrics** - KPI targets and how to measure progress
8. **Decision Matrix** - For each opportunity: proceed / review further / defer / reject

Return as a JSON object with this structure:
{
    "situation_summary": "Brief overview of current state",
    "key_findings": [
        "Finding 1",
        "Finding 2",
        ...
    ],
    "priority_actions": [
        {
            "rank": 1,
            "action": "Specific action description",
            "expected_impact": "Financial impact or outcome",
            "timeline": "When to execute (days/weeks)",
            "effort": "Low/Medium/High",
            "required_resources": ["Resource 1", "Resource 2"],
            "success_criteria": "How to measure if it worked"
        },
        ...
    ],
    "opportunity_ranking": [
        {
            "asin": "Product ASIN",
            "type": "Opportunity type",
            "potential_monthly_profit": 0.00,
            "effort_required": "Low/Medium/High",
            "implementation_steps": ["Step 1", "Step 2"],
            "decision": "proceed/review/defer/reject",
            "rationale": "Why this decision"
        },
        ...
    ],
    "risk_assessment": {
        "critical_risks": ["Risk 1", "Risk 2"],
        "medium_risks": ["Risk 3"],
        "low_risks": ["Risk 4"],
        "mitigation_strategies": {
            "Risk 1": "Mitigation strategy"
        }
    },
    "growth_strategy": {
        "next_3_months": "What to focus on",
        "next_6_months": "Medium-term goals",
        "target_metrics": {
            "revenue": 0.00,
            "profit": 0.00,
            "margin_percent": 0.0,
            "roi_percent": 0.0,
            "active_products": 0
        }
    },
    "budget_allocation": {
        "new_product_sourcing": 0.00,
        "inventory_replenishment": 0.00,
        "marketing_optimization": 0.00,
        "supplier_development": 0.00,
        "reserved": 0.00
    },
    "success_metrics": [
        {
            "metric": "Revenue growth",
            "current": 0.00,
            "target": 0.00,
            "timeline": "30 days"
        }
    ],
    "overall_confidence_score": 85,
    "notes": "Any additional context or warnings"
}
"""
        return prompt
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,  # ClaudeService
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta análisis de decisión de negocio.
        """
        try:
            system_prompt = self.get_system_prompt()
            user_prompt = self.format_prompt(input_data)
            
            logger.info("Running business decision analysis with Claude...")
            
            response_content = await claude_service.chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_message=system_prompt,
                max_tokens=2500,
                temperature=0.5  # Más determinístico para decisiones de negocio
            )
            
            # Intentar parsear como JSON
            try:
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_content[start_idx:end_idx]
                    decision_data = json.loads(json_str)
                else:
                    # Fallback: crear estructura básica con el contenido
                    decision_data = {
                        "situation_summary": response_content,
                        "key_findings": [],
                        "priority_actions": [],
                        "opportunity_ranking": [],
                        "risk_assessment": {},
                        "growth_strategy": {},
                        "budget_allocation": {},
                        "success_metrics": [],
                        "overall_confidence_score": 50,
                        "notes": "Could not parse full JSON, summary provided"
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                decision_data = {
                    "situation_summary": response_content,
                    "key_findings": [],
                    "priority_actions": [],
                    "opportunity_ranking": [],
                    "risk_assessment": {},
                    "growth_strategy": {},
                    "budget_allocation": {},
                    "success_metrics": [],
                    "overall_confidence_score": 50,
                    "notes": "Parsed as text, not full JSON"
                }
            
            logger.info(f"Business decision analysis complete, confidence: {decision_data.get('overall_confidence_score', 0)}")
            
            return SkillResult(
                success=True,
                data=decision_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "analyzed_kpis": input_data.get("business_kpis", {}).get("total_revenue", 0),
                    "opportunities_analyzed": len(input_data.get("opportunities", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Business decision analysis failed: {e}")
            return SkillResult(
                success=False,
                error=str(e)
            )
