#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Core Module - Componentes centrales del sistema.

Este módulo contiene:
- EventBus: Sistema de mensajería pub/sub
- Orchestrator: Coordinador de agents
- Event: Clase de eventos
"""

from backend.core.event_bus import EventBus, Event
from backend.core.orchestrator import Orchestrator, OrchestratorStatus, run_system

__all__ = [
    "EventBus",
    "Event",
    "Orchestrator",
    "OrchestratorStatus",
    "run_system",
]

__version__ = "2.0.0"

