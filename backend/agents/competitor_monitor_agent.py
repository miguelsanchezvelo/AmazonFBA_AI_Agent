#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Competitor Monitor Agent - Monitorea la competencia en tiempo real.

Este agente vigila a los competidores 24/7 y detecta:
- Cambios de precio
- Nuevos productos lanzados
- Cambios en reviews y ratings
- Estrategias de promoción
- Entrada/salida de vendedores
- Cambios en BSR (Best Sellers Rank)

ROI Esperado:
- Reacción rápida a guerras de precios
- Detección temprana de oportunidades
- Ventaja competitiva sostenible
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import logging

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService


logger = logging.getLogger(__name__)


class CompetitorChangeType:
    """Tipos de cambios de competidor."""
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    NEW_PRODUCT = "new_product"
    RATING_CHANGE = "rating_change"
    REVIEW_SPIKE = "review_spike"
    BSR_CHANGE = "bsr_change"
    SELLER_CHANGE = "seller_change"
    PROMOTION_DETECTED = "promotion_detected"


class CompetitorChange:
    """Representa un cambio detectado en la competencia."""
    
    def __init__(
        self,
        change_type: str,
        competitor_asin: str,
        our_asin: Optional[str],
        previous_value: Any,
        new_value: Any,
        impact_level: str,  # low, medium, high, critical
        recommendation: str,
        detected_at: datetime
    ):
        self.change_type = change_type
        self.competitor_asin = competitor_asin
        self.our_asin = our_asin
        self.previous_value = previous_value
        self.new_value = new_value
        self.impact_level = impact_level
        self.recommendation = recommendation
        self.detected_at = detected_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el cambio a diccionario."""
        return {
            "change_type": self.change_type,
            "competitor_asin": self.competitor_asin,
            "our_asin": self.our_asin,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "impact_level": self.impact_level,
            "recommendation": self.recommendation,
            "detected_at": self.detected_at.isoformat()
        }


class CompetitorMonitorAgent(BaseAgent):
    """
    Agente especializado en monitoreo de competencia.
    
    Funcionalidades principales:
    
    1. **Price Monitoring** (Monitoreo de Precios):
       - Trackea precios de competidores cada N horas
       - Detecta bajadas/subidas de precio
       - Alerta sobre guerras de precios
       - Sugiere respuestas estratégicas
    
    2. **Product Monitoring** (Monitoreo de Productos):
       - Detecta nuevos productos en el nicho
       - Analiza amenazas competitivas
       - Identifica gaps de mercado
    
    3. **Review Monitoring** (Monitoreo de Reviews):
       - Trackea cambios en ratings
       - Detecta picos de reviews (posible manipulación o campaña)
       - Analiza sentimiento de competidores
    
    4. **BSR Tracking** (Seguimiento de Best Sellers Rank):
       - Monitorea cambios en ranking
       - Detecta productos trending
       - Identifica pérdida de posición
    
    5. **Promotion Detection** (Detección de Promociones):
       - Detecta cupones y descuentos
       - Identifica Lightning Deals
       - Alerta sobre campañas agresivas
    
    Subscribe a:
    - CompetitorMonitoringRequested: Solicitud de monitoreo
    - CompetitorAdded: Nuevo competidor a monitorear
    - CompetitorRemoved: Remover competidor del monitoreo
    
    Publica:
    - CompetitorPriceChanged: Cambio de precio detectado
    - CompetitorProductLaunched: Nuevo producto competidor
    - CompetitorRatingChanged: Cambio en rating
    - CompetitorPromotionDetected: Promoción detectada
    - CompetitiveActionRequired: Acción competitiva requerida
    
    Examples:
        >>> agent = CompetitorMonitorAgent(
        ...     monitor_interval_hours=6,
        ...     price_change_threshold=5.0
        ... )
        >>> await agent.start()
        >>> 
        >>> # El agente automáticamente monitorea competidores
        >>> # y alerta sobre cambios significativos
    """
    
    def __init__(
        self,
        monitor_interval_hours: int = 6,
        price_change_threshold: float = 5.0,  # % de cambio para alertar
        max_competitors_per_product: int = 10,
        enable_auto_response: bool = False  # Respuesta automática a cambios
    ):
        """
        Inicializa el Competitor Monitor Agent.
        
        Args:
            monitor_interval_hours: Intervalo entre checks de competencia
            price_change_threshold: % mínimo de cambio de precio para alertar
            max_competitors_per_product: Máximo de competidores a monitorear por producto
            enable_auto_response: Si responder automáticamente a cambios
        """
        super().__init__(
            name="CompetitorMonitorAgent",
            subscribed_events={
                "CompetitorMonitoringRequested",
                "CompetitorAdded",
                "CompetitorRemoved"
            }
        )
        
        self.monitor_interval_hours = monitor_interval_hours
        self.price_change_threshold = price_change_threshold
        self.max_competitors_per_product = max_competitors_per_product
        self.enable_auto_response = enable_auto_response
        
        # Servicios
        self.cache: Optional[CacheService] = None
        
        # Estado
        self.monitored_competitors: Dict[str, List[str]] = {}  # our_asin -> [competitor_asins]
        self.competitor_snapshots: Dict[str, Dict[str, Any]] = {}  # asin -> last_snapshot
        self.changes_detected: List[CompetitorChange] = []
        self.last_monitor_run: Optional[datetime] = None
        
        # Tarea en background
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """
        Inicializa el Competitor Monitor Agent.
        """
        self.logger.info(f"Initializing {self.name}...")
        
        try:
            # Inicializar caché
            self.cache = CacheService()
            await self.cache.connect()
            self.logger.info("Cache connected")
            
            # TODO: Cargar competidores monitoreados desde DB
            
            # Iniciar monitoreo continuo
            self._monitoring_task = asyncio.create_task(self._continuous_monitoring())
            
            self.logger.info(f"{self.name} initialized successfully")
            self.logger.info(
                f"Monitoring {len(self.monitored_competitors)} products "
                f"every {self.monitor_interval_hours}h"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def shutdown(self) -> None:
        """
        Apaga el Competitor Monitor Agent.
        """
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            # Cancelar monitoreo
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Desconectar caché
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa eventos de monitoreo de competencia.
        
        Args:
            event: Evento a procesar
        
        Returns:
            Evento de respuesta
        """
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        self.logger.info(f"Processing {event_type}")
        
        try:
            if event_type == "CompetitorMonitoringRequested":
                return await self._handle_monitoring_request(payload)
            
            elif event_type == "CompetitorAdded":
                return await self._handle_competitor_added(payload)
            
            elif event_type == "CompetitorRemoved":
                return await self._handle_competitor_removed(payload)
            
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing {event_type}: {e}", exc_info=True)
            return None
    
    async def _continuous_monitoring(self) -> None:
        """
        Monitoreo continuo de todos los competidores.
        """
        self.logger.info("Continuous competitor monitoring started")
        
        while self._running:
            try:
                # Ejecutar monitoreo
                await self._monitor_all_competitors()
                self.last_monitor_run = datetime.now()
                
                # Esperar hasta el próximo check
                await asyncio.sleep(self.monitor_interval_hours * 3600)
                
            except asyncio.CancelledError:
                self.logger.info("Continuous monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring: {e}", exc_info=True)
                await asyncio.sleep(600)  # Esperar 10 min en caso de error
    
    async def _monitor_all_competitors(self) -> None:
        """
        Monitorea todos los competidores registrados.
        """
        self.logger.info("=== COMPETITOR MONITORING START ===")
        
        try:
            # TODO: Obtener productos reales con competidores
            # Por ahora, usar datos mock
            products_with_competitors = await self._get_mock_competitors()
            
            changes_found = []
            
            for our_asin, competitor_asins in products_with_competitors.items():
                for comp_asin in competitor_asins:
                    changes = await self._check_competitor(our_asin, comp_asin)
                    if changes:
                        changes_found.extend(changes)
            
            self.changes_detected = changes_found
            
            if changes_found:
                self.logger.warning(f"Detected {len(changes_found)} competitor changes")
                
                for change in changes_found:
                    if change.impact_level in ["high", "critical"]:
                        self.logger.warning(
                            f"  🚨 {change.change_type.upper()}: {change.competitor_asin} - "
                            f"{change.recommendation}"
                        )
                        # await self.event_bus.publish(Event("CompetitiveActionRequired", change.to_dict()))
            else:
                self.logger.info("No significant competitor changes detected")
            
        except Exception as e:
            self.logger.error(f"Competitor monitoring failed: {e}", exc_info=True)
        finally:
            self.logger.info("=== COMPETITOR MONITORING END ===")
    
    async def _check_competitor(
        self,
        our_asin: str,
        competitor_asin: str
    ) -> List[CompetitorChange]:
        """
        Revisa un competidor específico y detecta cambios.
        
        Args:
            our_asin: Nuestro ASIN
            competitor_asin: ASIN del competidor
        
        Returns:
            Lista de cambios detectados
        """
        changes = []
        
        # Obtener snapshot anterior
        previous_snapshot = self.competitor_snapshots.get(competitor_asin)
        
        # Obtener snapshot actual
        current_snapshot = await self._scrape_competitor_data(competitor_asin)
        
        if not current_snapshot:
            self.logger.warning(f"Failed to scrape {competitor_asin}")
            return changes
        
        # Si no hay snapshot anterior, solo guardar el actual
        if not previous_snapshot:
            self.competitor_snapshots[competitor_asin] = current_snapshot
            return changes
        
        # Comparar y detectar cambios
        
        # 1. Cambio de precio
        price_change = self._detect_price_change(
            our_asin, competitor_asin, previous_snapshot, current_snapshot
        )
        if price_change:
            changes.append(price_change)
        
        # 2. Cambio de rating
        rating_change = self._detect_rating_change(
            our_asin, competitor_asin, previous_snapshot, current_snapshot
        )
        if rating_change:
            changes.append(rating_change)
        
        # 3. Spike de reviews
        review_spike = self._detect_review_spike(
            our_asin, competitor_asin, previous_snapshot, current_snapshot
        )
        if review_spike:
            changes.append(review_spike)
        
        # Guardar snapshot actual
        self.competitor_snapshots[competitor_asin] = current_snapshot
        
        return changes
    
    def _detect_price_change(
        self,
        our_asin: str,
        competitor_asin: str,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Optional[CompetitorChange]:
        """
        Detecta cambios significativos de precio.
        
        Args:
            our_asin: Nuestro ASIN
            competitor_asin: ASIN del competidor
            previous: Snapshot anterior
            current: Snapshot actual
        
        Returns:
            Cambio detectado o None
        """
        prev_price = previous.get("price", 0)
        curr_price = current.get("price", 0)
        
        if prev_price == 0 or curr_price == 0:
            return None
        
        # Calcular cambio porcentual
        change_pct = ((curr_price - prev_price) / prev_price) * 100
        
        # Solo alertar si supera threshold
        if abs(change_pct) < self.price_change_threshold:
            return None
        
        # Determinar impacto
        if abs(change_pct) > 20:
            impact = "critical"
        elif abs(change_pct) > 15:
            impact = "high"
        elif abs(change_pct) > 10:
            impact = "medium"
        else:
            impact = "low"
        
        # Generar recomendación
        if change_pct < 0:  # Competidor bajó precio
            recommendation = (
                f"Competitor dropped price by {abs(change_pct):.1f}%. "
                f"Consider matching or highlighting differentiation."
            )
            change_type = CompetitorChangeType.PRICE_DROP
        else:  # Competidor subió precio
            recommendation = (
                f"Competitor increased price by {change_pct:.1f}%. "
                f"Opportunity to gain market share or follow suit."
            )
            change_type = CompetitorChangeType.PRICE_INCREASE
        
        return CompetitorChange(
            change_type=change_type,
            competitor_asin=competitor_asin,
            our_asin=our_asin,
            previous_value=prev_price,
            new_value=curr_price,
            impact_level=impact,
            recommendation=recommendation,
            detected_at=datetime.now()
        )
    
    def _detect_rating_change(
        self,
        our_asin: str,
        competitor_asin: str,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Optional[CompetitorChange]:
        """
        Detecta cambios en rating.
        """
        prev_rating = previous.get("rating", 0)
        curr_rating = current.get("rating", 0)
        
        # Solo alertar si cambio es > 0.2 estrellas
        if abs(curr_rating - prev_rating) < 0.2:
            return None
        
        if curr_rating < prev_rating:
            # Competidor perdió rating - oportunidad
            impact = "medium"
            recommendation = (
                f"Competitor rating dropped from {prev_rating:.1f} to {curr_rating:.1f}. "
                f"Opportunity to capture dissatisfied customers."
            )
        else:
            # Competidor mejoró rating - amenaza
            impact = "low"
            recommendation = (
                f"Competitor rating improved from {prev_rating:.1f} to {curr_rating:.1f}. "
                f"Monitor customer satisfaction and improve if needed."
            )
        
        return CompetitorChange(
            change_type=CompetitorChangeType.RATING_CHANGE,
            competitor_asin=competitor_asin,
            our_asin=our_asin,
            previous_value=prev_rating,
            new_value=curr_rating,
            impact_level=impact,
            recommendation=recommendation,
            detected_at=datetime.now()
        )
    
    def _detect_review_spike(
        self,
        our_asin: str,
        competitor_asin: str,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Optional[CompetitorChange]:
        """
        Detecta picos anormales de reviews (posible campaña o manipulación).
        """
        prev_reviews = previous.get("review_count", 0)
        curr_reviews = current.get("review_count", 0)
        
        new_reviews = curr_reviews - prev_reviews
        
        # Calcular tasa normal de reviews (basado en intervalo de monitoreo)
        hours_elapsed = self.monitor_interval_hours
        expected_reviews = (prev_reviews / 720) * hours_elapsed  # Asumir 720h = 30 días
        
        # Detectar spike (3x o más de lo esperado)
        if new_reviews > expected_reviews * 3 and new_reviews > 10:
            impact = "high"
            recommendation = (
                f"Competitor gained {new_reviews} reviews in {hours_elapsed}h "
                f"(expected: ~{int(expected_reviews)}). Possible review campaign or viral moment. "
                f"Monitor closely and consider increasing marketing."
            )
            
            return CompetitorChange(
                change_type=CompetitorChangeType.REVIEW_SPIKE,
                competitor_asin=competitor_asin,
                our_asin=our_asin,
                previous_value=prev_reviews,
                new_value=curr_reviews,
                impact_level=impact,
                recommendation=recommendation,
                detected_at=datetime.now()
            )
        
        return None
    
    async def _scrape_competitor_data(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Scrape datos actuales de un competidor.
        
        TODO: Implementar scraping real de Amazon
        
        Args:
            asin: ASIN del competidor
        
        Returns:
            Snapshot de datos del competidor
        """
        # Mock data por ahora
        import random
        
        # Simular variación de precio
        base_price = 25.0 + random.uniform(-5, 5)
        
        return {
            "asin": asin,
            "price": round(base_price, 2),
            "rating": 4.5 + random.uniform(-0.3, 0.3),
            "review_count": 150 + random.randint(-5, 20),
            "bsr": 5000 + random.randint(-1000, 1000),
            "in_stock": True,
            "seller_name": "Competitor Seller",
            "has_promotion": random.choice([True, False]),
            "scraped_at": datetime.now().isoformat()
        }
    
    async def _handle_monitoring_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja solicitud de monitoreo manual.
        """
        our_asin = payload.get("asin")
        
        self.logger.info(f"Manual monitoring requested for {our_asin}")
        
        if our_asin not in self.monitored_competitors:
            # Buscar competidores
            competitors = await self._find_competitors(our_asin)
            self.monitored_competitors[our_asin] = competitors[:self.max_competitors_per_product]
        
        # Ejecutar monitoreo inmediato
        changes = []
        for comp_asin in self.monitored_competitors[our_asin]:
            comp_changes = await self._check_competitor(our_asin, comp_asin)
            changes.extend(comp_changes)
        
        return {
            "event_type": "CompetitorMonitoringCompleted",
            "payload": {
                "asin": our_asin,
                "competitors_monitored": len(self.monitored_competitors[our_asin]),
                "changes_detected": len(changes),
                "changes": [c.to_dict() for c in changes]
            }
        }
    
    async def _handle_competitor_added(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja adición de competidor a monitorear.
        """
        our_asin = payload.get("our_asin")
        competitor_asin = payload.get("competitor_asin")
        
        if our_asin not in self.monitored_competitors:
            self.monitored_competitors[our_asin] = []
        
        if competitor_asin not in self.monitored_competitors[our_asin]:
            self.monitored_competitors[our_asin].append(competitor_asin)
            self.logger.info(f"Added competitor {competitor_asin} for product {our_asin}")
            
            # Hacer snapshot inicial
            snapshot = await self._scrape_competitor_data(competitor_asin)
            if snapshot:
                self.competitor_snapshots[competitor_asin] = snapshot
        
        return {
            "event_type": "CompetitorAdded",
            "payload": {
                "our_asin": our_asin,
                "competitor_asin": competitor_asin,
                "status": "monitoring"
            }
        }
    
    async def _handle_competitor_removed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja remoción de competidor del monitoreo.
        """
        our_asin = payload.get("our_asin")
        competitor_asin = payload.get("competitor_asin")
        
        if our_asin in self.monitored_competitors:
            if competitor_asin in self.monitored_competitors[our_asin]:
                self.monitored_competitors[our_asin].remove(competitor_asin)
                self.logger.info(f"Removed competitor {competitor_asin} from {our_asin}")
        
        # Limpiar snapshot
        if competitor_asin in self.competitor_snapshots:
            del self.competitor_snapshots[competitor_asin]
        
        return {
            "event_type": "CompetitorRemoved",
            "payload": {
                "our_asin": our_asin,
                "competitor_asin": competitor_asin,
                "status": "removed"
            }
        }
    
    async def _find_competitors(self, our_asin: str) -> List[str]:
        """
        Encuentra competidores para un producto.
        
        TODO: Implementar búsqueda real usando:
        - Misma categoría
        - Keywords similares
        - Rango de precio similar
        
        Args:
            our_asin: Nuestro ASIN
        
        Returns:
            Lista de ASINs de competidores
        """
        # Mock competitors
        return [
            f"B0{i}COMP{our_asin[-3:]}"
            for i in range(1, self.max_competitors_per_product + 1)
        ]
    
    async def _get_mock_competitors(self) -> Dict[str, List[str]]:
        """
        Obtiene datos mock de competidores para testing.
        """
        return {
            "B08XYZ123": ["B08COMP1", "B08COMP2", "B08COMP3"],
            "B07ABC456": ["B07COMP1", "B07COMP2"],
            "B09DEF789": ["B09COMP1", "B09COMP2", "B09COMP3", "B09COMP4"]
        }
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen del monitoreo de competencia.
        
        Returns:
            Resumen con estadísticas y cambios recientes
        """
        total_competitors = sum(len(comps) for comps in self.monitored_competitors.values())
        
        recent_changes = [
            c for c in self.changes_detected
            if (datetime.now() - c.detected_at).total_seconds() < 86400  # Últimas 24h
        ]
        
        critical_changes = [
            c for c in recent_changes
            if c.impact_level in ["high", "critical"]
        ]
        
        return {
            "products_monitored": len(self.monitored_competitors),
            "total_competitors": total_competitors,
            "changes_last_24h": len(recent_changes),
            "critical_changes": len(critical_changes),
            "last_monitor_run": self.last_monitor_run.isoformat() if self.last_monitor_run else None,
            "recent_changes": [c.to_dict() for c in recent_changes[:10]]
        }

