#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Agent Class - Clase abstracta para todos los agents del sistema.

Proporciona la estructura común y métodos base que todos los agents
especializados deben implementar.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import asyncio
import logging
from enum import Enum


class AgentStatus(Enum):
    """Estado del agent."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class AgentMetrics:
    """
    Métricas de rendimiento del agent.
    
    Attributes:
        events_processed: Número total de eventos procesados
        events_failed: Número de eventos fallidos
        avg_processing_time: Tiempo promedio de procesamiento (ms)
        last_event_time: Timestamp del último evento procesado
    """
    
    def __init__(self):
        self.events_processed: int = 0
        self.events_failed: int = 0
        self.total_processing_time: float = 0.0
        self.last_event_time: Optional[datetime] = None
        self.errors: List[Dict[str, Any]] = []
    
    @property
    def avg_processing_time(self) -> float:
        """Calcula el tiempo promedio de procesamiento en ms."""
        if self.events_processed == 0:
            return 0.0
        return (self.total_processing_time / self.events_processed) * 1000
    
    @property
    def success_rate(self) -> float:
        """Calcula la tasa de éxito (%)."""
        total = self.events_processed + self.events_failed
        if total == 0:
            return 100.0
        return (self.events_processed / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las métricas a diccionario."""
        return {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "avg_processing_time_ms": round(self.avg_processing_time, 2),
            "success_rate": round(self.success_rate, 2),
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "recent_errors": self.errors[-5:] if self.errors else []
        }


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agents del sistema.
    
    Todos los agents especializados deben heredar de esta clase e
    implementar los métodos abstractos: initialize(), process_event(), shutdown().
    
    Attributes:
        name: Nombre único del agent
        status: Estado actual del agent
        subscribed_events: Conjunto de tipos de eventos a los que está suscrito
        metrics: Métricas de rendimiento del agent
        logger: Logger específico del agent
        
    Examples:
        >>> class MyAgent(BaseAgent):
        ...     def __init__(self):
        ...         super().__init__(name="MyAgent", subscribed_events={"ProductDiscovered"})
        ...     
        ...     async def initialize(self):
        ...         self.logger.info("Initializing MyAgent")
        ...         
        ...     async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...         # Process event logic
        ...         return {"status": "processed"}
        ...         
        ...     async def shutdown(self):
        ...         self.logger.info("Shutting down MyAgent")
    """
    
    def __init__(self, name: str, subscribed_events: Set[str]):
        """
        Inicializa el agent base.
        
        Args:
            name: Nombre único del agent
            subscribed_events: Conjunto de tipos de eventos a los que se suscribe
        """
        self.name = name
        self.status = AgentStatus.INITIALIZING
        self.subscribed_events = subscribed_events
        self.metrics = AgentMetrics()
        self.logger = logging.getLogger(f"agent.{name.lower()}")
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Configurar logging
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Inicializa el agent (método abstracto).
        
        Este método debe ser implementado por cada agent especializado.
        Se llama una vez al arrancar el agent.
        
        Debe configurar:
        - Conexiones a servicios externos
        - Caché
        - Estado inicial
        
        Raises:
            Exception: Si falla la inicialización
        """
        pass
    
    @abstractmethod
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento (método abstracto).
        
        Este método debe ser implementado por cada agent especializado.
        Se llama cada vez que se recibe un evento al que está suscrito.
        
        Args:
            event: Diccionario con datos del evento
                - event_type: Tipo del evento (str)
                - payload: Datos del evento (dict)
                - timestamp: Timestamp del evento (str)
                - event_id: ID único del evento (str)
        
        Returns:
            Opcional: Evento(s) a publicar como resultado del procesamiento
            None si no hay eventos para publicar
        
        Raises:
            Exception: Si falla el procesamiento
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Apaga el agent limpiamente (método abstracto).
        
        Este método debe ser implementado por cada agent especializado.
        Se llama al detener el agent.
        
        Debe cerrar:
        - Conexiones a servicios externos
        - Recursos abiertos
        - Liberar memoria
        
        Raises:
            Exception: Si falla el shutdown
        """
        pass
    
    async def start(self) -> None:
        """
        Inicia el agent y cambia su estado a READY.
        
        Llama a initialize() y maneja errores.
        """
        try:
            self.logger.info(f"Starting {self.name}...")
            await self.initialize()
            self.status = AgentStatus.READY
            self._running = True
            self.logger.info(f"{self.name} started successfully")
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to start {self.name}: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """
        Detiene el agent y cambia su estado a SHUTDOWN.
        
        Llama a shutdown() y maneja errores.
        """
        try:
            self.logger.info(f"Stopping {self.name}...")
            self._running = False
            
            # Cancelar tareas pendientes
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Esperar a que terminen
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            await self.shutdown()
            self.status = AgentStatus.SHUTDOWN
            self.logger.info(f"{self.name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping {self.name}: {e}", exc_info=True)
            raise
    
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """
        Maneja un evento con error handling y métricas.
        
        Args:
            event: Evento a procesar
        """
        if not self._running:
            self.logger.warning(f"{self.name} received event but is not running")
            return
        
        event_type = event.get("event_type", "unknown")
        event_id = event.get("event_id", "unknown")
        
        # Verificar si el agent está suscrito a este tipo de evento
        if event_type not in self.subscribed_events:
            self.logger.debug(f"{self.name} ignoring event {event_type}")
            return
        
        start_time = asyncio.get_event_loop().time()
        self.status = AgentStatus.PROCESSING
        
        try:
            self.logger.info(f"{self.name} processing event {event_type} (ID: {event_id})")
            
            # Procesar el evento
            result = await self.process_event(event)
            
            # Actualizar métricas
            processing_time = asyncio.get_event_loop().time() - start_time
            self.metrics.events_processed += 1
            self.metrics.total_processing_time += processing_time
            self.metrics.last_event_time = datetime.now()
            
            self.status = AgentStatus.READY
            self.logger.info(
                f"{self.name} processed event {event_type} in {processing_time*1000:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            # Registrar error
            processing_time = asyncio.get_event_loop().time() - start_time
            self.metrics.events_failed += 1
            self.metrics.errors.append({
                "event_type": event_type,
                "event_id": event_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "processing_time": processing_time
            })
            
            self.status = AgentStatus.ERROR
            self.logger.error(
                f"{self.name} failed to process event {event_type}: {e}",
                exc_info=True
            )
            
            # Re-intentar después de un delay
            await asyncio.sleep(1)
            self.status = AgentStatus.READY
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas actuales del agent.
        
        Returns:
            Diccionario con métricas
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "subscribed_events": list(self.subscribed_events),
            "metrics": self.metrics.to_dict()
        }
    
    def is_healthy(self) -> bool:
        """
        Verifica si el agent está saludable.
        
        Returns:
            True si el agent está READY, False en caso contrario
        """
        return self.status == AgentStatus.READY
    
    def __repr__(self) -> str:
        """Representación en string del agent."""
        return (
            f"<{self.__class__.__name__}(name='{self.name}', "
            f"status='{self.status.value}', "
            f"events_processed={self.metrics.events_processed})>"
        )

