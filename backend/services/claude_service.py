#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Service - Wrapper para Anthropic Claude API.

Proporciona interfaz unificada para interactuar con Claude API,
incluyendo gestión de Skills y streaming de respuestas.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from datetime import datetime

try:
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic.types import Message, MessageStreamEvent
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Anthropic SDK no disponible. Instalar con: pip install anthropic>=0.8.0")

from backend.api.config import settings


logger = logging.getLogger(__name__)


class ClaudeService:
    """
    Servicio para interactuar con Claude API.
    
    Proporciona métodos para:
    - Completions síncronas y asíncronas
    - Streaming de respuestas
    - Gestión de contexto y historial
    - Invocación de Claude Skills
    
    Attributes:
        client: Cliente síncrono de Anthropic
        async_client: Cliente asíncrono de Anthropic
        model: Modelo de Claude a usar
        max_tokens: Tokens máximos por respuesta
        temperature: Temperatura para generación (0-1)
    
    Examples:
        >>> service = ClaudeService()
        >>> response = await service.complete("Analiza este producto...")
        >>> print(response["content"])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Inicializa el servicio de Claude.
        
        Args:
            api_key: API key de Anthropic (usa settings si no se provee)
            model: Modelo a usar (usa settings si no se provee)
            max_tokens: Tokens máximos por respuesta
            temperature: Temperatura para generación (0-1)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic SDK no disponible. "
                "Instalar con: pip install anthropic>=0.8.0"
            )
        
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise ValueError(
                "anthropic_api_key no configurada. "
                "Establecer en .env o pasar como parámetro"
            )
        
        self.model = model or settings.claude_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Inicializar clientes
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        
        logger.info(f"Claude Service initialized with model: {self.model}")
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera una completion usando Claude.
        
        Args:
            prompt: Prompt del usuario
            system: System prompt opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature
            stop_sequences: Secuencias de parada opcionales
        
        Returns:
            Diccionario con respuesta y metadata:
            {
                "content": str,
                "model": str,
                "usage": dict,
                "stop_reason": str
            }
        
        Examples:
            >>> response = await service.complete(
            ...     "Analiza el mercado para yoga mats",
            ...     system="Eres un experto en análisis de mercado FBA"
            ... )
        """
        try:
            # Preparar mensajes
            messages = [{"role": "user", "content": prompt}]
            
            # Parámetros
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "messages": messages,
            }
            
            if system:
                params["system"] = system
            
            if stop_sequences:
                params["stop_sequences"] = stop_sequences
            
            # Llamar a API
            start_time = datetime.utcnow()
            message = await self.async_client.messages.create(**params)
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            # Extraer contenido
            content = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            result = {
                "content": content,
                "model": message.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "stop_reason": message.stop_reason,
                "elapsed_seconds": elapsed
            }
            
            logger.info(
                f"Claude completion successful: "
                f"{message.usage.input_tokens} in + {message.usage.output_tokens} out "
                f"in {elapsed:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}", exc_info=True)
            raise
    
    async def complete_with_context(
        self,
        prompt: str,
        context: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Genera completion con contexto de conversación.
        
        Args:
            prompt: Prompt actual del usuario
            context: Historial de conversación [{"role": "user/assistant", "content": "..."}]
            system: System prompt opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature
        
        Returns:
            Diccionario con respuesta y metadata
        
        Examples:
            >>> context = [
            ...     {"role": "user", "content": "¿Qué es Amazon FBA?"},
            ...     {"role": "assistant", "content": "FBA significa Fulfillment by Amazon..."}
            ... ]
            >>> response = await service.complete_with_context(
            ...     "¿Cuáles son las ventajas?",
            ...     context=context
            ... )
        """
        try:
            # Combinar contexto con nuevo prompt
            messages = context + [{"role": "user", "content": prompt}]
            
            # Parámetros
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "messages": messages,
            }
            
            if system:
                params["system"] = system
            
            # Llamar a API
            message = await self.async_client.messages.create(**params)
            
            # Extraer contenido
            content = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            return {
                "content": content,
                "model": message.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "stop_reason": message.stop_reason,
            }
            
        except Exception as e:
            logger.error(f"Error calling Claude API with context: {e}", exc_info=True)
            raise
    
    async def stream_complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """
        Genera completion con streaming.
        
        Args:
            prompt: Prompt del usuario
            system: System prompt opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature
        
        Yields:
            Fragmentos de texto a medida que se generan
        
        Examples:
            >>> async for chunk in service.stream_complete("Analiza..."):
            ...     print(chunk, end="", flush=True)
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "messages": messages,
            }
            
            if system:
                params["system"] = system
            
            # Stream response
            async with self.async_client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
            
        except Exception as e:
            logger.error(f"Error streaming from Claude API: {e}", exc_info=True)
            raise
    
    def complete_sync(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Versión síncrona de complete() para uso en código no-async.
        
        Args:
            prompt: Prompt del usuario
            system: System prompt opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature
        
        Returns:
            Diccionario con respuesta y metadata
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "messages": messages,
            }
            
            if system:
                params["system"] = system
            
            message = self.client.messages.create(**params)
            
            # Extraer contenido
            content = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            return {
                "content": content,
                "model": message.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "stop_reason": message.stop_reason,
            }
            
        except Exception as e:
            logger.error(f"Error calling Claude API (sync): {e}", exc_info=True)
            raise


class ClaudeSkillManager:
    """
    Gestor de Claude Skills.
    
    Coordina la invocación de Skills especializadas de Claude,
    gestionando el contexto, caching y resultados.
    
    Attributes:
        service: Instancia de ClaudeService
        skills: Registro de skills disponibles
    
    Examples:
        >>> manager = ClaudeSkillManager()
        >>> manager.register_skill(MarketAnalysisSkill())
        >>> result = await manager.invoke_skill(
        ...     "market_analysis",
        ...     {"product": product_data}
        ... )
    """
    
    def __init__(self, service: Optional[ClaudeService] = None):
        """
        Inicializa el gestor de skills.
        
        Args:
            service: Instancia de ClaudeService (crea una nueva si no se provee)
        """
        self.service = service or ClaudeService()
        self.skills: Dict[str, Any] = {}
        logger.info("ClaudeSkillManager initialized")
    
    def register_skill(self, skill: Any) -> None:
        """
        Registra una nueva skill.
        
        Args:
            skill: Instancia de skill que implementa el protocolo BaseSkill
        
        Raises:
            ValueError: Si la skill no tiene nombre o ya existe
        """
        if not hasattr(skill, 'name'):
            raise ValueError("Skill must have a 'name' attribute")
        
        name = skill.name
        if name in self.skills:
            logger.warning(f"Overwriting existing skill: {name}")
        
        self.skills[name] = skill
        logger.info(f"Registered skill: {name}")
    
    async def invoke_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invoca una skill registrada.
        
        Args:
            skill_name: Nombre de la skill a invocar
            input_data: Datos de entrada para la skill
            **kwargs: Parámetros adicionales para la skill
        
        Returns:
            Resultado de la skill
        
        Raises:
            ValueError: Si la skill no existe
        
        Examples:
            >>> result = await manager.invoke_skill(
            ...     "market_analysis",
            ...     {"product_name": "yoga mat", "price": 29.99}
            ... )
        """
        if skill_name not in self.skills:
            raise ValueError(f"Skill not found: {skill_name}")
        
        skill = self.skills[skill_name]
        
        try:
            logger.info(f"Invoking skill: {skill_name}")
            start_time = datetime.utcnow()
            
            result = await skill.execute(input_data, self.service, **kwargs)
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Skill {skill_name} completed in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error invoking skill {skill_name}: {e}", exc_info=True)
            raise
    
    def list_skills(self) -> List[str]:
        """
        Lista todas las skills registradas.
        
        Returns:
            Lista de nombres de skills
        """
        return list(self.skills.keys())
    
    def get_skill(self, skill_name: str) -> Optional[Any]:
        """
        Obtiene una skill por nombre.
        
        Args:
            skill_name: Nombre de la skill
        
        Returns:
            Instancia de la skill o None si no existe
        """
        return self.skills.get(skill_name)


# Instancia global del servicio (lazy initialization)
_claude_service: Optional[ClaudeService] = None
_skill_manager: Optional[ClaudeSkillManager] = None


def get_claude_service() -> ClaudeService:
    """
    Obtiene la instancia global de ClaudeService.
    
    Returns:
        Instancia de ClaudeService
    
    Examples:
        >>> service = get_claude_service()
        >>> response = await service.complete("Hello")
    """
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service


def get_skill_manager() -> ClaudeSkillManager:
    """
    Obtiene la instancia global de ClaudeSkillManager.
    
    Returns:
        Instancia de ClaudeSkillManager
    
    Examples:
        >>> manager = get_skill_manager()
        >>> skills = manager.list_skills()
    """
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = ClaudeSkillManager()
    return _skill_manager

