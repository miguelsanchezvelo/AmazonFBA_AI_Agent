#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supplier Evaluation Skill - Evalúa credibilidad y confiabilidad de proveedores.

Analiza proveedores considerando múltiples factores para determinar
si son confiables para sourcing de productos FBA.
"""

from typing import Any, Dict
import json

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class SupplierEvaluationSkill(BaseSkill):
    """
    Skill para evaluar proveedores de productos.
    
    Evalúa:
    - Credibilidad y reputación
    - Términos comerciales (MOQ, precios, payment terms)
    - Capacidad de producción
    - Control de calidad
    - Riesgos potenciales
    - Recomendaciones de verificación
    
    Examples:
        >>> skill = SupplierEvaluationSkill()
        >>> result = await skill.execute({
        ...     "supplier": {
        ...         "name": "AcmeCorp",
        ...         "country": "China",
        ...         "rating": 4.5,
        ...         "years_in_business": 8
        ...     },
        ...     "product_context": {
        ...         "name": "Yoga Mat",
        ...         "complexity": "medium"
        ...     }
        ... }, claude_service)
    """
    
    name = "supplier_evaluation"
    description = "Evaluates supplier credibility, reliability, and fit for FBA sourcing"
    version = "1.0.0"
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define schema de entrada."""
        return {
            "type": "object",
            "properties": {
                "supplier": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "country": {"type": "string"},
                        "rating": {"type": "number"},
                        "contact_email": {"type": "string"},
                        "website": {"type": "string"},
                        "years_in_business": {"type": "integer"},
                        "certifications": {"type": "array"},
                        "moq": {"type": "integer"},
                        "price_per_unit": {"type": "number"},
                        "lead_time_days": {"type": "integer"}
                    }
                },
                "product_context": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "complexity": {"type": "string"},
                        "quality_requirements": {"type": "string"}
                    }
                },
                "communication_history": {"type": "array"}
            },
            "required": ["supplier"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "trust_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "credibility_assessment": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "concerns": {"type": "array", "items": {"type": "string"}},
                "pricing_analysis": {"type": "object"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "verification_steps": {"type": "array", "items": {"type": "string"}},
                "recommendation": {"type": "string", "enum": ["proceed", "verify_first", "find_alternative"]},
                "negotiation_tips": {"type": "array", "items": {"type": "string"}}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert international sourcing specialist with 15+ years of experience working with manufacturers, particularly in Asia.

Your expertise includes:
- Supplier vetting and due diligence
- B2B negotiation and contract terms
- Quality control and manufacturing processes
- International trade and logistics
- Risk assessment and fraud prevention
- Cultural business practices

When evaluating suppliers, you:
1. Assess credibility based on available information
2. Identify red flags and warning signs
3. Evaluate commercial terms (MOQ, pricing, payment terms)
4. Consider production capabilities and quality control
5. Provide specific verification steps
6. Give negotiation strategies
7. Make clear recommendations

Red flags you watch for:
- Unrealistic pricing or promises
- Poor communication or evasiveness
- Lack of verifiable information
- Unusual payment terms
- No physical address or certifications
- Pressure tactics

Positive signals:
- Alibaba Gold Supplier / Trade Assurance
- ISO certifications or industry standards
- Years in business (5+ is good)
- Detailed product specifications
- Professional communication
- Reasonable MOQs and lead times

Return your evaluation as a JSON object matching the output schema. Be thorough, specific, and practical."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para evaluación de proveedor."""
        supplier = input_data.get("supplier", {})
        product_context = input_data.get("product_context", {})
        comm_history = input_data.get("communication_history", [])
        
        prompt = f"""Evaluate the following supplier for Amazon FBA product sourcing:

SUPPLIER INFORMATION:
Company Name: {supplier.get('name', 'N/A')}
Country: {supplier.get('country', 'N/A')}
Rating: {supplier.get('rating', 'N/A')}
Email: {supplier.get('contact_email', 'N/A')}
Website: {supplier.get('website', 'N/A')}
Years in Business: {supplier.get('years_in_business', 'Unknown')}
"""
        
        # Agregar certificaciones si existen
        if supplier.get('certifications'):
            prompt += f"\nCertifications: {', '.join(supplier['certifications'])}"
        
        # Agregar términos comerciales
        if supplier.get('moq'):
            prompt += f"\nMinimum Order Quantity (MOQ): {supplier.get('moq')} units"
        if supplier.get('price_per_unit'):
            prompt += f"\nPrice per Unit: ${supplier.get('price_per_unit')}"
        if supplier.get('lead_time_days'):
            prompt += f"\nLead Time: {supplier.get('lead_time_days')} days"
        
        # Agregar contexto del producto
        if product_context:
            prompt += f"\n\nPRODUCT CONTEXT:"
            prompt += f"\nProduct: {product_context.get('name', 'N/A')}"
            prompt += f"\nComplexity: {product_context.get('complexity', 'N/A')}"
            if 'quality_requirements' in product_context:
                prompt += f"\nQuality Requirements: {product_context['quality_requirements']}"
        
        # Agregar historial de comunicación si existe
        if comm_history:
            prompt += f"\n\nCOMMUNICATION HISTORY:"
            for i, comm in enumerate(comm_history[:3], 1):  # Máximo 3 comunicaciones
                prompt += f"\n\n{i}. {comm.get('date', 'N/A')} - {comm.get('type', 'N/A')}"
                if 'summary' in comm:
                    prompt += f"\n   Summary: {comm['summary']}"
        
        prompt += """

EVALUATION REQUIRED:

1. TRUST SCORE (0-100): Overall trustworthiness rating

2. CREDIBILITY ASSESSMENT: Detailed assessment of supplier's credibility

3. STRENGTHS: List specific advantages of working with this supplier

4. CONCERNS: List any red flags or concerns

5. PRICING ANALYSIS:
   - Is pricing competitive?
   - Are terms reasonable?
   - Any hidden costs to watch for?

6. RISK LEVEL: low/medium/high

7. VERIFICATION STEPS: Specific steps to verify supplier before ordering

8. RECOMMENDATION: proceed / verify_first / find_alternative

9. NEGOTIATION TIPS: Specific tips for negotiating better terms

Return your evaluation as a valid JSON object matching the output schema.
"""
        
        return prompt
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta evaluación de proveedor.
        
        Args:
            input_data: Datos del proveedor y contexto
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con evaluación completa
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
                temperature=0.4,  # Más determinístico para evaluación
                max_tokens=2500
            )
            
            # Intentar parsear como JSON
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    evaluation_data = json.loads(json_str)
                else:
                    evaluation_data = self._create_fallback_evaluation(content, input_data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                evaluation_data = self._create_fallback_evaluation(content, input_data)
            
            # Validar campos obligatorios
            if "trust_score" not in evaluation_data:
                evaluation_data["trust_score"] = self._estimate_trust_score(input_data)
            
            if "risk_level" not in evaluation_data:
                score = evaluation_data.get("trust_score", 50)
                evaluation_data["risk_level"] = "low" if score >= 70 else "medium" if score >= 40 else "high"
            
            if "recommendation" not in evaluation_data:
                score = evaluation_data.get("trust_score", 50)
                evaluation_data["recommendation"] = "proceed" if score >= 70 else "verify_first" if score >= 40 else "find_alternative"
            
            return SkillResult(
                success=True,
                data=evaluation_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "supplier_name": input_data.get("supplier", {}).get("name", "Unknown")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)
    
    def _create_fallback_evaluation(
        self,
        content: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea evaluación fallback si falla el parseo JSON."""
        supplier = input_data.get("supplier", {})
        trust_score = self._estimate_trust_score(input_data)
        
        return {
            "trust_score": trust_score,
            "credibility_assessment": content[:500] if len(content) > 500 else content,
            "strengths": [f"Review full analysis for {supplier.get('name', 'supplier')} strengths"],
            "concerns": ["Further verification recommended"],
            "pricing_analysis": {
                "competitive": "unknown",
                "notes": "Requires market comparison"
            },
            "risk_level": "medium",
            "verification_steps": [
                "Request business license",
                "Video call to verify facility",
                "Order samples",
                "Check references"
            ],
            "recommendation": "verify_first",
            "negotiation_tips": [content] if content else ["Conduct thorough due diligence"]
        }
    
    def _estimate_trust_score(self, input_data: Dict[str, Any]) -> int:
        """Estima score básico basado en información del proveedor."""
        supplier = input_data.get("supplier", {})
        
        score = 50  # Base score
        
        # Ajustar por rating
        rating = supplier.get("rating", 0)
        if rating >= 4.5:
            score += 15
        elif rating >= 4.0:
            score += 10
        elif rating < 3.0:
            score -= 20
        
        # Ajustar por años en negocio
        years = supplier.get("years_in_business", 0)
        if years >= 10:
            score += 15
        elif years >= 5:
            score += 10
        elif years < 2:
            score -= 10
        
        # Ajustar por certificaciones
        certs = supplier.get("certifications", [])
        score += min(len(certs) * 5, 15)  # Máximo +15 por certificaciones
        
        # Ajustar por MOQ (razonable vs extremo)
        moq = supplier.get("moq", 0)
        if 100 <= moq <= 1000:
            score += 5  # MOQ razonable
        elif moq > 5000:
            score -= 5  # MOQ muy alto
        
        return max(0, min(100, score))  # Clamp entre 0-100

