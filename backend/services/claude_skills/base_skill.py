#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Skill - Clase abstracta para Claude Skills.

Define el protocolo que todas las Skills deben implementar.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    """
    Resultado de la ejecución de una Skill.
    
    Attributes:
        success: Si la ejecución fue exitosa
        data: Datos resultantes de la skill
        error: Mensaje de error si falló
        metadata: Metadata adicional (tokens, tiempo, etc.)
    """
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Agrega timestamp al resultado."""
        if 'timestamp' not in self.metadata:
            self.metadata['timestamp'] = datetime.utcnow().isoformat()


class BaseSkill(ABC):
    """
    Clase base abstracta para todas las Claude Skills.
    
    Una Skill es un módulo especializado que:
    1. Tiene un nombre único
    2. Define un schema de entrada
    3. Define un schema de salida
    4. Implementa lógica de ejecución con Claude
    5. Maneja errores y validación
    
    Attributes:
        name: Nombre único de la skill
        description: Descripción de qué hace la skill
        version: Versión de la skill
    
    Examples:
        >>> class MySkill(BaseSkill):
        ...     name = "my_skill"
        ...     description = "Does something useful"
        ...     
        ...     async def execute(self, input_data, claude_service, **kwargs):
        ...         # Implementation
        ...         return SkillResult(success=True, data={"result": "..."})
    """
    
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    
    def __init__(self):
        """Inicializa la skill."""
        if not self.name:
            raise ValueError(f"Skill {self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"Skill {self.__class__.__name__} must define 'description'")
        
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.logger.info(f"Skill initialized: {self.name} v{self.version}")
    
    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        claude_service: Any,
        **kwargs
    ) -> SkillResult:
        """
        Ejecuta la skill con los datos de entrada.
        
        Args:
            input_data: Datos de entrada para la skill
            claude_service: Instancia de ClaudeService para interactuar con API
            **kwargs: Parámetros adicionales
        
        Returns:
            SkillResult con el resultado de la ejecución
        
        Raises:
            ValueError: Si los datos de entrada son inválidos
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Valida los datos de entrada.
        
        Args:
            input_data: Datos a validar
        
        Returns:
            True si los datos son válidos
        
        Raises:
            ValueError: Si los datos son inválidos
        """
        required_fields = self.get_input_schema().get("required", [])
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
        return True
    
    def get_input_schema(self) -> Dict[str, Any]:
        """
        Define el schema de entrada de la skill.
        
        Returns:
            Schema JSON de entrada
        
        Examples:
            >>> {
            ...     "type": "object",
            ...     "properties": {
            ...         "product_name": {"type": "string"},
            ...         "price": {"type": "number"}
            ...     },
            ...     "required": ["product_name"]
            ... }
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """
        Define el schema de salida de la skill.
        
        Returns:
            Schema JSON de salida
        
        Examples:
            >>> {
            ...     "type": "object",
            ...     "properties": {
            ...         "analysis": {"type": "string"},
            ...         "score": {"type": "number"}
            ...     }
            ... }
        """
        return {
            "type": "object",
            "properties": {}
        }
    
    def get_system_prompt(self) -> str:
        """
        Retorna el system prompt para esta skill.
        
        Returns:
            System prompt específico de la skill
        """
        return f"""You are a specialized AI assistant with expertise in {self.name}.

{self.description}

Provide detailed, accurate, and actionable insights based on the input data."""
    
    def format_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        Formatea el prompt del usuario basado en input_data.
        
        Args:
            input_data: Datos de entrada
        
        Returns:
            Prompt formateado para Claude
        """
        # Default implementation - subclasses should override
        import json
        return f"Process the following data:\n\n{json.dumps(input_data, indent=2)}"
    
    async def _handle_error(self, error: Exception) -> SkillResult:
        """
        Maneja errores durante la ejecución.
        
        Args:
            error: Excepción capturada
        
        Returns:
            SkillResult con información del error
        """
        self.logger.error(f"Error in skill {self.name}: {error}", exc_info=True)
        return SkillResult(
            success=False,
            error=str(error),
            metadata={"skill": self.name, "version": self.version}
        )
    
    def __repr__(self) -> str:
        """Representación en string de la skill."""
        return f"<{self.__class__.__name__} name='{self.name}' version='{self.version}'>"

