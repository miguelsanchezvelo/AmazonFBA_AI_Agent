#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point for running the orchestrator as a standalone worker.

Usage:
    python -m backend.orchestrator
"""

import asyncio
import logging
import sys

from backend.core.orchestrator import Orchestrator
from backend.core.event_bus import get_event_bus
from backend.api.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_orchestrator():
    """Run the orchestrator worker."""
    logger.info("Starting Amazon FBA AI Agent V2 Orchestrator...")
    
    # Initialize event bus
    event_bus = get_event_bus()
    await event_bus.connect()
    logger.info("Event bus connected")
    
    # Initialize orchestrator
    orchestrator = Orchestrator(event_bus)
    
    # Register enabled agents based on settings
    from backend.agents.discovery_agent import DiscoveryAgent
    from backend.agents.analysis_agent import AnalysisAgent
    from backend.agents.supplier_agent import SupplierAgent
    from backend.agents.pricing_agent import PricingAgent
    from backend.agents.inventory_agent import InventoryAgent
    
    if settings.agent_discovery_enabled:
        orchestrator.register_agent(DiscoveryAgent())
        logger.info("Registered DiscoveryAgent")
    
    if settings.agent_analysis_enabled:
        orchestrator.register_agent(AnalysisAgent())
        logger.info("Registered AnalysisAgent")
    
    if settings.agent_supplier_enabled:
        orchestrator.register_agent(SupplierAgent())
        logger.info("Registered SupplierAgent")
    
    if settings.agent_pricing_enabled:
        orchestrator.register_agent(PricingAgent())
        logger.info("Registered PricingAgent")
    
    if settings.agent_inventory_enabled:
        orchestrator.register_agent(InventoryAgent())
        logger.info("Registered InventoryAgent")
    
    # Start orchestrator
    await orchestrator.start()
    logger.info("Orchestrator started successfully")
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down orchestrator...")
    finally:
        # Cleanup
        await orchestrator.stop()
        await event_bus.disconnect()
        logger.info("Orchestrator stopped")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_orchestrator())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

