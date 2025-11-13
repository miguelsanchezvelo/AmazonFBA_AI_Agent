#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generation Skill - Genera reportes ejecutivos para Business Agent.

Transforma datos crudos de análisis en reportes profesionales
con insights accionables para toma de decisiones estratégicas.
"""

from typing import Any, Dict, List
import json
from datetime import datetime

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class ReportGenerationSkill(BaseSkill):
    """
    Skill para generar reportes ejecutivos.
    
    Genera reportes que incluyen:
    - Executive summary
    - Key metrics y KPIs
    - Insights y hallazgos principales
    - Recomendaciones estratégicas
    - Próximos pasos
    
    Examples:
        >>> skill = ReportGenerationSkill()
        >>> result = await skill.execute({
        ...     "report_type": "weekly_performance",
        ...     "data": {
        ...         "products_discovered": 50,
        ...         "opportunities": 12,
        ...         "revenue": 15000
        ...     },
        ...     "period": "2024-W01"
        ... }, claude_service)
    """
    
    name = "report_generation"
    description = "Generates professional executive reports with actionable insights"
    version = "1.0.0"
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define schema de entrada."""
        return {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["weekly_performance", "product_analysis", "market_summary", "business_review"],
                    "description": "Type of report to generate"
                },
                "data": {
                    "type": "object",
                    "description": "Data to include in report"
                },
                "period": {"type": "string", "description": "Time period for report"},
                "context": {"type": "object", "description": "Additional context"}
            },
            "required": ["report_type", "data"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "executive_summary": {"type": "string"},
                "key_metrics": {"type": "array", "items": {"type": "object"}},
                "insights": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "report_sections": {"type": "array", "items": {"type": "object"}}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert business analyst and report writer specializing in Amazon FBA operations.

Your reports are:
- Clear, concise, and executive-friendly
- Data-driven with actionable insights
- Professional but accessible
- Focused on what matters most
- Forward-looking with specific recommendations

When creating reports, you:
1. Start with a compelling executive summary (2-3 paragraphs)
2. Highlight the most important metrics and trends
3. Provide context and interpretation, not just numbers
4. Identify patterns, opportunities, and risks
5. Give specific, actionable recommendations
6. Outline clear next steps

Report structure:
- Title and period
- Executive Summary (key takeaways)
- Key Metrics (quantitative highlights)
- Insights (what the data tells us)
- Recommendations (what to do)
- Next Steps (specific actions)

Your tone is professional yet conversational, avoiding jargon while demonstrating expertise.

Return your report as a JSON object matching the output schema."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para generación de reporte."""
        report_type = input_data.get("report_type", "business_review")
        data = input_data.get("data", {})
        period = input_data.get("period", datetime.utcnow().strftime("%Y-%m-%d"))
        context = input_data.get("context", {})
        
        # Mapear tipos de reporte a títulos descriptivos
        report_titles = {
            "weekly_performance": "Weekly Performance Review",
            "product_analysis": "Product Analysis Report",
            "market_summary": "Market Intelligence Summary",
            "business_review": "Business Review Report"
        }
        
        title = report_titles.get(report_type, "Business Report")
        
        prompt = f"""Generate a professional {title} for the following data:

REPORT TYPE: {report_type}
PERIOD: {period}

DATA:
{json.dumps(data, indent=2)}
"""
        
        # Agregar contexto si existe
        if context:
            prompt += f"\nCONTEXT:\n{json.dumps(context, indent=2)}\n"
        
        # Instrucciones específicas por tipo de reporte
        if report_type == "weekly_performance":
            prompt += """
Focus on:
- Performance trends (week-over-week changes)
- Achievement vs targets
- Standout performers and underperformers
- Operational efficiency
- Priorities for next week
"""
        elif report_type == "product_analysis":
            prompt += """
Focus on:
- Product performance metrics
- Market opportunity assessment
- Competitive positioning
- Profitability analysis
- Launch/expansion recommendations
"""
        elif report_type == "market_summary":
            prompt += """
Focus on:
- Market trends and shifts
- Emerging opportunities
- Competitive landscape changes
- Risk factors
- Strategic implications
"""
        elif report_type == "business_review":
            prompt += """
Focus on:
- Overall business health
- Revenue and profitability
- Growth trajectory
- Operational efficiency
- Strategic priorities
"""
        
        prompt += """

REQUIREMENTS:

1. EXECUTIVE SUMMARY: Compelling 2-3 paragraph summary of key findings

2. KEY METRICS: Array of metric objects, each with:
   - name: metric name
   - value: current value
   - change: % or absolute change
   - trend: "up"/"down"/"stable"
   - interpretation: what it means

3. INSIGHTS: 3-5 key insights that tell the story behind the numbers

4. RECOMMENDATIONS: 3-5 specific, actionable recommendations

5. NEXT STEPS: Concrete actions to take in the next week/month

6. REPORT SECTIONS: Optional detailed sections with:
   - title: section title
   - content: section content

Return as a valid JSON object matching the output schema.
"""
        
        return prompt
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta generación de reporte.
        
        Args:
            input_data: Datos para el reporte
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con reporte generado
        """
        try:
            # Validar entrada
            self.validate_input(input_data)
            
            # Generar prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.format_prompt(input_data)
            
            # Llamar a Claude
            response = await claude_service.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.6,
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
                    report_data = json.loads(json_str)
                else:
                    report_data = self._create_fallback_report(content, input_data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                report_data = self._create_fallback_report(content, input_data)
            
            # Asegurar campos obligatorios
            if "title" not in report_data:
                report_data["title"] = f"{input_data.get('report_type', 'Business')} Report"
            
            return SkillResult(
                success=True,
                data=report_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "usage": response.get("usage", {}),
                    "model": response.get("model", "")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)
    
    def _create_fallback_report(
        self,
        content: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea reporte fallback si falla el parseo JSON."""
        report_type = input_data.get("report_type", "business_review")
        period = input_data.get("period", datetime.utcnow().strftime("%Y-%m-%d"))
        
        return {
            "title": f"{report_type.replace('_', ' ').title()} - {period}",
            "executive_summary": content[:500] if len(content) > 500 else content,
            "key_metrics": [],
            "insights": [content] if content else ["Report data available for detailed review"],
            "recommendations": ["Review full analysis for detailed recommendations"],
            "next_steps": ["Continue monitoring performance metrics"],
            "report_sections": []
        }

