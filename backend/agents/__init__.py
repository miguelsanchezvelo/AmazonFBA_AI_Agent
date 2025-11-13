#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Agents Module - Sistema multi-agent para Amazon FBA.

Este módulo contiene todos los agents especializados del sistema:
- BaseAgent: Clase base abstracta
- DiscoveryAgent: Descubrimiento de productos
- AnalysisAgent: Análisis de rentabilidad
- SupplierAgent: Gestión de proveedores
- PricingAgent: Optimización de precios
- InventoryAgent: Gestión de inventario
- BusinessAgent: Coordinador principal de negocio
- ProfitOptimizerAgent: Optimización de márgenes
- ReplenishmentAgent: Reabastecimiento predictivo
- CompetitorMonitorAgent: Monitoreo de competencia
"""

from backend.agents.base_agent import BaseAgent, AgentStatus, AgentMetrics
from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.supplier_agent import SupplierAgent
from backend.agents.pricing_agent import PricingAgent, PricingStrategy
from backend.agents.inventory_agent import InventoryAgent, InventoryStatus
from backend.agents.business_agent import BusinessAgent, BusinessCycle, BusinessMetrics
from backend.agents.profit_optimizer_agent import ProfitOptimizerAgent
from backend.agents.replenishment_agent import ReplenishmentAgent
from backend.agents.competitor_monitor_agent import CompetitorMonitorAgent

__all__ = [
    # Base
    "BaseAgent",
    "AgentStatus",
    "AgentMetrics",
    # Core Agents
    "DiscoveryAgent",
    "AnalysisAgent",
    "SupplierAgent",
    "PricingAgent",
    "InventoryAgent",
    # Business Agents
    "BusinessAgent",
    "ProfitOptimizerAgent",
    "ReplenishmentAgent",
    "CompetitorMonitorAgent",
    # Enums & Classes
    "PricingStrategy",
    "InventoryStatus",
    "BusinessCycle",
    "BusinessMetrics",
]

__version__ = "2.0.0"

