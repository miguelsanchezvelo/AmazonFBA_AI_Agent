#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrator - Coordinador central de agents.

Responsable de:
- Iniciar y detener agents
- Health monitoring
- Restart automático
- Métricas agregadas
- Coordinación de lifecycle
"""

import asyncio
import signal
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from backend.agents.base_agent import BaseAgent, AgentStatus
from backend.core.event_bus import EventBus


logger = logging.getLogger(__name__)


class OrchestratorStatus:
    """Estado del orquestador."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class Orchestrator:
    """
    Orquestador central que coordina todos los agents del sistema.
    
    Features:
    - Gestión del lifecycle de agents
    - Health monitoring continuo
    - Restart automático de agents fallidos
    - Métricas agregadas del sistema
    - Graceful shutdown
    
    Attributes:
        event_bus: Bus de eventos para comunicación
        agents: Lista de agents gestionados
        status: Estado actual del orquestador
        
    Examples:
        >>> orchestrator = Orchestrator(event_bus)
        >>> 
        >>> # Registrar agents
        >>> orchestrator.register_agent(discovery_agent)
        >>> orchestrator.register_agent(analysis_agent)
        >>> 
        >>> # Iniciar sistema
        >>> await orchestrator.start()
        >>> 
        >>> # Detener sistema
        >>> await orchestrator.stop()
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        auto_restart: bool = True,
        health_check_interval: int = 30
    ):
        """
        Inicializa el orquestador.
        
        Args:
            event_bus: Event bus para comunicación entre agents
            auto_restart: Si reiniciar automáticamente agents fallidos
            health_check_interval: Intervalo de health checks en segundos
        """
        self.event_bus = event_bus
        self.auto_restart = auto_restart
        self.health_check_interval = health_check_interval
        
        self.agents: List[BaseAgent] = []
        self.status = OrchestratorStatus.INITIALIZING
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._event_loop_task: Optional[asyncio.Task] = None
        
        # Métricas
        self.start_time: Optional[datetime] = None
        self.total_restarts = 0
        
        logger.info("Orchestrator initialized")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Registra un agent para ser gestionado.
        
        Args:
            agent: Agent a registrar
        """
        if agent in self.agents:
            logger.warning(f"Agent {agent.name} already registered")
            return
        
        self.agents.append(agent)
        logger.info(f"Registered agent: {agent.name}")
    
    def unregister_agent(self, agent: BaseAgent) -> None:
        """
        Desregistra un agent.
        
        Args:
            agent: Agent a desregistrar
        """
        if agent in self.agents:
            self.agents.remove(agent)
            logger.info(f"Unregistered agent: {agent.name}")
    
    async def start(self) -> None:
        """
        Inicia el orquestador y todos los agents registrados.
        
        1. Conecta al event bus
        2. Inicia todos los agents
        3. Suscribe agents a eventos
        4. Inicia health monitoring
        5. Inicia event loop
        """
        try:
            logger.info("Starting Orchestrator...")
            self.status = OrchestratorStatus.INITIALIZING
            self.start_time = datetime.now()
            
            # Conectar event bus
            if not self.event_bus.connected:
                await self.event_bus.connect()
                logger.info("Event bus connected")
            
            # Iniciar agents
            logger.info(f"Starting {len(self.agents)} agents...")
            for agent in self.agents:
                try:
                    await agent.start()
                    logger.info(f"✓ {agent.name} started")
                except Exception as e:
                    logger.error(f"✗ Failed to start {agent.name}: {e}")
                    if not self.auto_restart:
                        raise
            
            # Suscribir agents a eventos
            await self._subscribe_agents()
            
            # Iniciar health monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())
            logger.info("Health monitoring started")
            
            # Iniciar event loop
            self._event_loop_task = asyncio.create_task(self._event_loop())
            logger.info("Event loop started")
            
            self._running = True
            self.status = OrchestratorStatus.RUNNING
            logger.info("✓ Orchestrator started successfully")
            
            # Setup signal handlers para graceful shutdown
            self._setup_signal_handlers()
            
        except Exception as e:
            self.status = OrchestratorStatus.ERROR
            logger.error(f"Failed to start Orchestrator: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """
        Detiene el orquestador y todos los agents limpiamente.
        """
        try:
            logger.info("Stopping Orchestrator...")
            self.status = OrchestratorStatus.STOPPING
            self._running = False
            
            # Cancelar health monitoring
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Cancelar event loop
            if self._event_loop_task and not self._event_loop_task.done():
                self._event_loop_task.cancel()
                try:
                    await self._event_loop_task
                except asyncio.CancelledError:
                    pass
            
            # Detener agents
            logger.info(f"Stopping {len(self.agents)} agents...")
            for agent in self.agents:
                try:
                    await agent.stop()
                    logger.info(f"✓ {agent.name} stopped")
                except Exception as e:
                    logger.error(f"✗ Error stopping {agent.name}: {e}")
            
            # Desconectar event bus
            await self.event_bus.disconnect()
            
            self.status = OrchestratorStatus.STOPPED
            logger.info("✓ Orchestrator stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Orchestrator: {e}", exc_info=True)
            raise
    
    async def _subscribe_agents(self) -> None:
        """
        Suscribe todos los agents a sus eventos correspondientes.
        """
        for agent in self.agents:
            for event_type in agent.subscribed_events:
                # Crear handler que llame al agent
                async def create_handler(ag=agent):
                    async def handler(event_dict: Dict[str, Any]) -> None:
                        await ag.handle_event(event_dict)
                    return handler
                
                handler = await create_handler()
                await self.event_bus.subscribe(event_type, handler)
                
                logger.info(f"Subscribed {agent.name} to {event_type}")
    
    async def _health_monitor(self) -> None:
        """
        Monitorea la salud de todos los agents periódicamente.
        
        Si un agent falla y auto_restart está habilitado, intenta reiniciarlo.
        """
        logger.info("Health monitor started")
        
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                for agent in self.agents:
                    if not agent.is_healthy():
                        logger.warning(
                            f"Agent {agent.name} unhealthy (status: {agent.status.value})"
                        )
                        
                        if self.auto_restart and agent.status == AgentStatus.ERROR:
                            logger.info(f"Attempting to restart {agent.name}...")
                            try:
                                await agent.stop()
                                await asyncio.sleep(1)
                                await agent.start()
                                self.total_restarts += 1
                                logger.info(f"✓ {agent.name} restarted successfully")
                            except Exception as e:
                                logger.error(
                                    f"✗ Failed to restart {agent.name}: {e}"
                                )
                
            except asyncio.CancelledError:
                logger.info("Health monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    async def _event_loop(self) -> None:
        """
        Loop principal de procesamiento de eventos.
        
        Mantiene el sistema corriendo y permite procesamiento asíncrono.
        """
        logger.info("Event loop started")
        
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Event loop cancelled")
    
    def _setup_signal_handlers(self) -> None:
        """
        Configura handlers para señales del sistema (SIGINT, SIGTERM).
        
        Permite graceful shutdown cuando se recibe Ctrl+C.
        """
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.info("Signal handlers configured")
        except Exception as e:
            logger.warning(f"Could not setup signal handlers: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas agregadas del sistema completo.
        
        Returns:
            Diccionario con métricas del orquestador y todos los agents
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        agent_metrics = [agent.get_metrics() for agent in self.agents]
        
        # Agregados
        total_events_processed = sum(
            agent.metrics.events_processed for agent in self.agents
        )
        total_events_failed = sum(
            agent.metrics.events_failed for agent in self.agents
        )
        
        healthy_agents = sum(1 for agent in self.agents if agent.is_healthy())
        
        return {
            "orchestrator": {
                "status": self.status,
                "uptime_seconds": uptime,
                "total_agents": len(self.agents),
                "healthy_agents": healthy_agents,
                "total_restarts": self.total_restarts
            },
            "aggregated": {
                "total_events_processed": total_events_processed,
                "total_events_failed": total_events_failed,
                "success_rate": (
                    (total_events_processed / (total_events_processed + total_events_failed) * 100)
                    if (total_events_processed + total_events_failed) > 0
                    else 100.0
                )
            },
            "event_bus": self.event_bus.get_metrics(),
            "agents": agent_metrics
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema de forma resumida.
        
        Returns:
            Estado resumido
        """
        return {
            "status": self.status,
            "agents": {
                agent.name: {
                    "status": agent.status.value,
                    "healthy": agent.is_healthy(),
                    "events_processed": agent.metrics.events_processed
                }
                for agent in self.agents
            },
            "event_bus_connected": self.event_bus.connected
        }
    
    async def run_forever(self) -> None:
        """
        Ejecuta el orquestador indefinidamente.
        
        Útil para correr como servicio standalone.
        """
        await self.start()
        
        try:
            # Mantener corriendo hasta que se detenga
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            await self.stop()
    
    def __repr__(self) -> str:
        """Representación en string del orquestador."""
        return (
            f"<Orchestrator(status='{self.status}', "
            f"agents={len(self.agents)}, "
            f"running={self._running})>"
        )


# Función helper para crear y correr el sistema completo
async def run_system(agents: List[BaseAgent], redis_url: str = "redis://localhost:6379") -> None:
    """
    Helper function para iniciar sistema completo con agents.
    
    Args:
        agents: Lista de agents a ejecutar
        redis_url: URL de Redis
        
    Examples:
        >>> from backend.agents.discovery_agent import DiscoveryAgent
        >>> from backend.agents.analysis_agent import AnalysisAgent
        >>> 
        >>> agents = [DiscoveryAgent(), AnalysisAgent()]
        >>> asyncio.run(run_system(agents))
    """
    # Crear event bus
    event_bus = EventBus(redis_url=redis_url)
    
    # Crear orchestrator
    orchestrator = Orchestrator(event_bus, auto_restart=True)
    
    # Registrar agents
    for agent in agents:
        orchestrator.register_agent(agent)
    
    # Ejecutar
    await orchestrator.run_forever()

