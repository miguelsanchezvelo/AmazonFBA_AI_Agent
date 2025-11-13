#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supplier Message Skill - Genera mensajes profesionales para proveedores.

Reemplaza la funcionalidad de OpenAI en SupplierAgent para generar
mensajes contextualizados de negociación y comunicación con proveedores.
"""

from typing import Any, Dict
import json

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult


class SupplierMessageSkill(BaseSkill):
    """
    Skill para generar mensajes profesionales a proveedores.
    
    Genera mensajes personalizados para:
    - Solicitudes iniciales de información
    - Negociación de precios y términos
    - Seguimiento de pedidos
    - Resolución de problemas
    
    Examples:
        >>> skill = SupplierMessageSkill()
        >>> result = await skill.execute({
        ...     "product_name": "Yoga Mat",
        ...     "supplier_name": "AcmeCorp",
        ...     "message_type": "initial_inquiry",
        ...     "quantity": 500
        ... }, claude_service)
    """
    
    name = "supplier_message"
    description = "Generates professional, contextual messages for supplier communication"
    version = "1.0.0"
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define schema de entrada."""
        return {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product to inquire about"},
                "supplier_name": {"type": "string", "description": "Supplier company name"},
                "message_type": {
                    "type": "string",
                    "enum": ["initial_inquiry", "price_negotiation", "follow_up", "issue_resolution"],
                    "description": "Type of message to generate"
                },
                "quantity": {"type": "integer", "description": "Desired order quantity"},
                "context": {"type": "object", "description": "Additional context"}
            },
            "required": ["product_name", "supplier_name", "message_type"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida."""
        return {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "message": {"type": "string"},
                "tone": {"type": "string"},
                "follow_up_days": {"type": "integer"}
            }
        }
    
    def get_system_prompt(self) -> str:
        """Retorna system prompt especializado."""
        return """You are an expert B2B procurement specialist with extensive experience in international supplier communication, particularly with Chinese manufacturers.

Your role is to craft professional, effective business messages that:
1. Build trust and establish credibility
2. Are clear, concise, and culturally appropriate
3. Include all necessary details for the supplier to respond effectively
4. Set proper expectations and next steps
5. Maintain a professional yet friendly tone

When crafting messages:
- Use proper business English
- Be specific about quantities, timelines, and requirements
- Show that you're a serious buyer, not a time-waster
- Respect cultural communication styles
- Include relevant certifications or quality standards when applicable
- Always provide clear next steps

Return your response as a JSON object with:
{
  "subject": "Email subject line",
  "message": "Full message body",
  "tone": "professional/friendly/formal",
  "follow_up_days": <number of days to wait before follow-up>
}"""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Formatea el prompt para generar el mensaje."""
        product_name = input_data.get("product_name", "")
        supplier_name = input_data.get("supplier_name", "")
        message_type = input_data.get("message_type", "initial_inquiry")
        quantity = input_data.get("quantity", 0)
        context = input_data.get("context", {})
        
        # Determinar tipo de mensaje
        message_types = {
            "initial_inquiry": "an initial inquiry to learn about their products, pricing, MOQ, and terms",
            "price_negotiation": "a price negotiation message to get better terms",
            "follow_up": "a professional follow-up message",
            "issue_resolution": "a message to address and resolve an issue"
        }
        
        purpose = message_types.get(message_type, "a business inquiry")
        
        prompt = f"""Generate {purpose} for the following scenario:

Product: {product_name}
Supplier: {supplier_name}
Desired Quantity: {quantity} units
Message Type: {message_type}

"""
        
        # Agregar contexto adicional si existe
        if context:
            prompt += f"\nAdditional Context:\n{json.dumps(context, indent=2)}\n"
        
        # Agregar instrucciones específicas según tipo
        if message_type == "initial_inquiry":
            prompt += """
Please ask about:
- Unit pricing at different quantities
- Minimum Order Quantity (MOQ)
- Lead times and shipping options
- Payment terms
- Product certifications and quality standards
- Sample availability
"""
        elif message_type == "price_negotiation":
            prompt += """
Please negotiate on:
- Better unit pricing for bulk orders
- Reduced MOQ if applicable
- More favorable payment terms
- Included shipping or better rates
"""
        
        prompt += "\nReturn the response as a valid JSON object as specified in your instructions."
        
        return prompt
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta la skill para generar mensaje de proveedor.
        
        Args:
            input_data: Datos del producto y proveedor
            claude_service: Instancia de ClaudeService
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con el mensaje generado
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
                temperature=0.7,
                max_tokens=1500
            )
            
            # Parsear respuesta JSON
            content = response.get("content", "")
            
            # Intentar parsear como JSON
            try:
                # Buscar JSON en la respuesta
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    message_data = json.loads(json_str)
                else:
                    # Si no hay JSON, usar respuesta completa como mensaje
                    message_data = {
                        "subject": f"Inquiry about {input_data.get('product_name', 'Product')}",
                        "message": content,
                        "tone": "professional",
                        "follow_up_days": 7
                    }
            except json.JSONDecodeError:
                # Fallback si JSON inválido
                message_data = {
                    "subject": f"Inquiry about {input_data.get('product_name', 'Product')}",
                    "message": content,
                    "tone": "professional",
                    "follow_up_days": 7
                }
            
            return SkillResult(
                success=True,
                data=message_data,
                metadata={
                    "skill": self.name,
                    "version": self.version,
                    "usage": response.get("usage", {}),
                    "model": response.get("model", "")
                }
            )
            
        except Exception as e:
            return await self._handle_error(e)

