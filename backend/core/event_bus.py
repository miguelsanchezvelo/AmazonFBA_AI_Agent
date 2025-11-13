#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Bus - Sistema de mensajería pub/sub para comunicación entre agents.

Usa Redis Streams para proporcionar:
- Comunicación asíncrona
- Event replay capability
- Dead letter queue
- Persistencia de eventos
"""

import asyncio
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis asyncio no disponible. Instalar con: pip install redis[asyncio]")

try:
    import fakeredis.aioredis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False


logger = logging.getLogger(__name__)


class Event:
    """
    Representa un evento en el sistema.
    
    Attributes:
        event_type: Tipo del evento (ej: "ProductDiscovered")
        payload: Datos del evento
        event_id: ID único del evento
        timestamp: Momento de creación del evento
        source_agent: Agent que generó el evento
    """
    
    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source_agent: Optional[str] = None
    ):
        """
        Crea un nuevo evento.
        
        Args:
            event_type: Tipo del evento
            payload: Datos del evento
            source_agent: Nombre del agent que genera el evento
        """
        self.event_type = event_type
        self.payload = payload
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.source_agent = source_agent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario."""
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source_agent": self.source_agent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Crea un evento desde un diccionario."""
        event = cls(
            event_type=data["event_type"],
            payload=data["payload"],
            source_agent=data.get("source_agent")
        )
        event.event_id = data.get("event_id", event.event_id)
        event.timestamp = data.get("timestamp", event.timestamp)
        return event
    
    def __repr__(self) -> str:
        """Representación en string del evento."""
        return f"<Event(type='{self.event_type}', id='{self.event_id}')>"


class EventBus:
    """
    Event Bus usando Redis Streams para comunicación pub/sub.
    
    Features:
    - Pub/Sub asíncrono
    - Event replay (replayar eventos desde timestamp)
    - Dead letter queue para eventos fallidos
    - Persistencia en Redis
    - Consumer groups para múltiples workers
    
    Examples:
        >>> bus = EventBus(redis_url="redis://localhost:6379")
        >>> await bus.connect()
        >>> 
        >>> # Suscribir handler
        >>> async def handler(event: Event):
        ...     print(f"Received: {event.event_type}")
        >>> 
        >>> await bus.subscribe("ProductDiscovered", handler)
        >>> 
        >>> # Publicar evento
        >>> event = Event("ProductDiscovered", {"asin": "B08TEST"})
        >>> await bus.publish(event)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream_name: str = "fba_events",
        consumer_group: str = "agents",
        use_fallback: bool = True
    ):
        """
        Inicializa el Event Bus.
        
        Args:
            redis_url: URL de conexión a Redis
            stream_name: Nombre del stream de Redis
            consumer_group: Nombre del consumer group
            use_fallback: Si usar fallback a memoria si Redis no disponible
        """
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.use_fallback = use_fallback
        
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        
        # Subscribers: event_type -> list of handlers
        self.subscribers: Dict[str, List[Callable]] = {}
        
        # Fallback: in-memory queue si Redis no disponible
        self.fallback_queue: asyncio.Queue = asyncio.Queue()
        self.using_fallback = False
        
        # Métricas
        self.events_published = 0
        self.events_delivered = 0
        self.events_failed = 0
        
        logger.info(f"EventBus initialized with stream '{stream_name}'")
    
    async def connect(self) -> None:
        """
        Conecta al Redis.
        
        Si Redis no está disponible y use_fallback=True,
        usa una cola en memoria.
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory fallback")
            self.using_fallback = True
            self.connected = True
            return
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Verificar conexión
            await self.redis_client.ping()
            
            # Crear consumer group si no existe
            try:
                await self.redis_client.xgroup_create(
                    self.stream_name,
                    self.consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}'")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"Consumer group '{self.consumer_group}' already exists")
                else:
                    raise
            
            self.connected = True
            logger.info("EventBus connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            
            if self.use_fallback:
                logger.warning("Falling back to in-memory queue")
                self.using_fallback = True
                self.connected = True
            else:
                raise
    
    async def disconnect(self) -> None:
        """Desconecta del Redis."""
        if self.redis_client:
            await self.redis_client.aclose()
            self.connected = False
            logger.info("EventBus disconnected from Redis")
    
    async def publish(self, event: Event) -> str:
        """
        Publica un evento en el bus.
        
        Args:
            event: Evento a publicar
        
        Returns:
            ID del evento publicado
        
        Raises:
            Exception: Si falla la publicación
        """
        if not self.connected:
            raise RuntimeError("EventBus not connected")
        
        event_dict = event.to_dict()
        
        try:
            if self.using_fallback:
                # Usar cola en memoria
                await self.fallback_queue.put(event_dict)
                logger.debug(f"Published to fallback queue: {event.event_type}")
                
            else:
                # Usar Redis Stream
                event_json = json.dumps(event_dict)
                message_id = await self.redis_client.xadd(
                    self.stream_name,
                    {"event": event_json}
                )
                logger.debug(f"Published to Redis: {event.event_type} (ID: {message_id})")
            
            self.events_published += 1
            logger.info(f"Published event: {event.event_type} (ID: {event.event_id})")
            
            # Si hay subscribers, entregar inmediatamente (para testing/desarrollo)
            await self._deliver_to_subscribers(event_dict)
            
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            self.events_failed += 1
            raise
    
    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Suscribe un handler a un tipo de evento.
        
        Args:
            event_type: Tipo de evento a suscribirse
            handler: Función async que procesará el evento
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler to event type: {event_type}")
    
    async def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Desuscribe un handler de un tipo de evento.
        
        Args:
            event_type: Tipo de evento
            handler: Función a desuscribir
        """
        if event_type in self.subscribers:
            if handler in self.subscribers[event_type]:
                self.subscribers[event_type].remove(handler)
                logger.info(f"Unsubscribed handler from event type: {event_type}")
    
    async def _deliver_to_subscribers(self, event_dict: Dict[str, Any]) -> None:
        """
        Entrega un evento a todos los subscribers suscritos.
        
        Args:
            event_dict: Diccionario con datos del evento
        """
        event_type = event_dict.get("event_type")
        
        if event_type in self.subscribers:
            handlers = self.subscribers[event_type]
            
            for handler in handlers:
                try:
                    # Ejecutar handler asíncronamente
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_dict)
                    else:
                        handler(event_dict)
                    
                    self.events_delivered += 1
                    
                except Exception as e:
                    logger.error(
                        f"Error in handler for {event_type}: {e}",
                        exc_info=True
                    )
                    self.events_failed += 1
    
    async def start_consuming(self, consumer_name: str) -> None:
        """
        Inicia el consumo de eventos del stream (para producción).
        
        Args:
            consumer_name: Nombre único del consumidor
        """
        if not self.connected:
            raise RuntimeError("EventBus not connected")
        
        if self.using_fallback:
            await self._consume_from_fallback()
        else:
            await self._consume_from_redis(consumer_name)
    
    async def _consume_from_redis(self, consumer_name: str) -> None:
        """
        Consume eventos desde Redis Stream.
        
        Args:
            consumer_name: Nombre del consumidor
        """
        logger.info(f"Starting Redis consumer: {consumer_name}")
        
        while self.connected:
            try:
                # Leer nuevos mensajes
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    consumer_name,
                    {self.stream_name: '>'},
                    count=10,
                    block=1000  # 1 segundo
                )
                
                for stream, events in messages:
                    for message_id, data in events:
                        try:
                            event_json = data.get('event')
                            event_dict = json.loads(event_json)
                            
                            # Entregar a subscribers
                            await self._deliver_to_subscribers(event_dict)
                            
                            # Acknowledge (marcar como procesado)
                            await self.redis_client.xack(
                                self.stream_name,
                                self.consumer_group,
                                message_id
                            )
                            
                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")
                            # El mensaje no se hace ACK y puede ser reintentado
                
            except asyncio.CancelledError:
                logger.info(f"Consumer {consumer_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer {consumer_name}: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _consume_from_fallback(self) -> None:
        """Consume eventos desde la cola en memoria (fallback)."""
        logger.info("Starting fallback consumer")
        
        while self.connected:
            try:
                # Obtener evento de la cola
                event_dict = await asyncio.wait_for(
                    self.fallback_queue.get(),
                    timeout=1.0
                )
                
                # Entregar a subscribers
                await self._deliver_to_subscribers(event_dict)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Fallback consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error in fallback consumer: {e}")
    
    async def replay_events(
        self,
        from_timestamp: Optional[str] = None,
        event_types: Optional[Set[str]] = None
    ) -> List[Event]:
        """
        Replay eventos desde un timestamp.
        
        Args:
            from_timestamp: Timestamp ISO desde donde replayar (None = todos)
            event_types: Filtrar por tipos de evento (None = todos)
        
        Returns:
            Lista de eventos
        """
        if self.using_fallback:
            logger.warning("Event replay not available in fallback mode")
            return []
        
        if not self.redis_client:
            return []
        
        try:
            # Leer todos los mensajes del stream
            messages = await self.redis_client.xrange(self.stream_name)
            
            events = []
            for message_id, data in messages:
                event_json = data.get('event')
                event_dict = json.loads(event_json)
                
                # Filtrar por timestamp
                if from_timestamp and event_dict.get('timestamp') < from_timestamp:
                    continue
                
                # Filtrar por tipo
                if event_types and event_dict.get('event_type') not in event_types:
                    continue
                
                events.append(Event.from_dict(event_dict))
            
            logger.info(f"Replayed {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error replaying events: {e}")
            return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas del Event Bus.
        
        Returns:
            Diccionario con métricas
        """
        return {
            "connected": self.connected,
            "using_fallback": self.using_fallback,
            "events_published": self.events_published,
            "events_delivered": self.events_delivered,
            "events_failed": self.events_failed,
            "subscribers_count": sum(len(handlers) for handlers in self.subscribers.values()),
            "subscribed_event_types": list(self.subscribers.keys())
        }
    
    def __repr__(self) -> str:
        """Representación en string del EventBus."""
        return (
            f"<EventBus(stream='{self.stream_name}', "
            f"connected={self.connected}, "
            f"subscribers={len(self.subscribers)})>"
        )


# Singleton instance for global access
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get or create singleton EventBus instance.
    
    Returns:
        Global EventBus instance
        
    Examples:
        >>> event_bus = get_event_bus()
        >>> await event_bus.connect()
        >>> event = Event("TestEvent", {"test": "data"})
        >>> await event_bus.publish(event)
    """
    global _event_bus_instance
    
    if _event_bus_instance is None:
        from backend.api.config import settings
        
        _event_bus_instance = EventBus(
            redis_url=settings.redis_url,
            stream_name=settings.event_stream_name,
            consumer_group=settings.event_consumer_group,
            use_fallback=True  # Fallback to in-memory if Redis unavailable
        )
    
    return _event_bus_instance
