#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejemplo de uso del Multi-Agent System.

Este script demuestra cómo iniciar y usar el sistema completo de agents.
"""

import asyncio
import json
import logging
from typing import Optional

# Importar componentes del sistema
from backend.agents import (
    DiscoveryAgent,
    AnalysisAgent,
    SupplierAgent,
    PricingAgent,
    InventoryAgent
)
from backend.core import EventBus, Event, Orchestrator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    Función principal que demuestra el uso del Multi-Agent System.
    
    Flujo:
    1. Crear y configurar Event Bus
    2. Crear agents especializados
    3. Crear y configurar Orchestrator
    4. Iniciar sistema
    5. Publicar evento inicial (TrendDiscoveryRequested)
    6. Observar cómo los agents procesan eventos en cascada
    7. Detener sistema limpiamente
    """
    logger.info("=" * 80)
    logger.info("🚀 Amazon FBA Multi-Agent System - Demo")
    logger.info("=" * 80)
    
    # 1. Crear Event Bus
    logger.info("\n📡 Creating Event Bus...")
    event_bus = EventBus(
        redis_url="redis://localhost:6379",
        stream_name="fba_events",
        use_fallback=True  # Usar fallback si Redis no disponible
    )
    
    # 2. Crear agents
    logger.info("\n🤖 Creating Agents...")
    
    discovery_agent = DiscoveryAgent(
        cache_ttl=3600,
        min_rating=4.0,
        max_price=5000
    )
    logger.info("  ✓ DiscoveryAgent created")
    
    analysis_agent = AnalysisAgent(
        min_roi=30.0,
        min_viability_score=70.0
    )
    logger.info("  ✓ AnalysisAgent created")
    
    supplier_agent = SupplierAgent(
        max_suppliers=5
    )
    logger.info("  ✓ SupplierAgent created")
    
    pricing_agent = PricingAgent(
        target_roi=30.0,
        min_margin=20.0
    )
    logger.info("  ✓ PricingAgent created")
    
    inventory_agent = InventoryAgent(
        low_stock_threshold=50,
        reorder_point=30
    )
    logger.info("  ✓ InventoryAgent created")
    
    # 3. Crear Orchestrator
    logger.info("\n🎭 Creating Orchestrator...")
    orchestrator = Orchestrator(
        event_bus=event_bus,
        auto_restart=True,
        health_check_interval=30
    )
    
    # Registrar agents
    orchestrator.register_agent(discovery_agent)
    orchestrator.register_agent(analysis_agent)
    orchestrator.register_agent(supplier_agent)
    orchestrator.register_agent(pricing_agent)
    orchestrator.register_agent(inventory_agent)
    
    logger.info(f"  ✓ Registered {len(orchestrator.agents)} agents")
    
    # 4. Iniciar sistema
    logger.info("\n🎬 Starting system...")
    try:
        await orchestrator.start()
        logger.info("  ✓ System started successfully")
        
        # Esperar un momento para que todo se estabilice
        await asyncio.sleep(2)
        
        # 5. Publicar evento inicial
        logger.info("\n📤 Publishing initial event: TrendDiscoveryRequested")
        initial_event = Event(
            event_type="TrendDiscoveryRequested",
            payload={
                "budget": 3000,
                "category": "fitness",
                "keywords": ["yoga mat", "resistance bands"]
            },
            source_agent="demo_script"
        )
        
        await event_bus.publish(initial_event)
        logger.info("  ✓ Event published")
        
        # 6. Observar procesamiento (esperar eventos en cascada)
        logger.info("\n⏳ Processing events (this may take a few seconds)...")
        logger.info("   Watch the logs above to see agents processing events:")
        logger.info("   1. DiscoveryAgent discovers products")
        logger.info("   2. AnalysisAgent analyzes viability")
        logger.info("   3. SupplierAgent finds suppliers (if GO)")
        logger.info("   4. PricingAgent optimizes prices")
        logger.info("   5. InventoryAgent sets up tracking")
        
        # Esperar procesamiento
        await asyncio.sleep(10)
        
        # Mostrar métricas
        logger.info("\n📊 System Metrics:")
        metrics = orchestrator.get_metrics()
        logger.info(f"  Orchestrator Status: {metrics['orchestrator']['status']}")
        logger.info(f"  Healthy Agents: {metrics['orchestrator']['healthy_agents']}/{metrics['orchestrator']['total_agents']}")
        logger.info(f"  Total Events Processed: {metrics['aggregated']['total_events_processed']}")
        logger.info(f"  Success Rate: {metrics['aggregated']['success_rate']:.1f}%")
        
        logger.info("\n  Agent Details:")
        for agent_metrics in metrics['agents']:
            logger.info(f"    - {agent_metrics['name']}:")
            logger.info(f"      Status: {agent_metrics['status']}")
            logger.info(f"      Events Processed: {agent_metrics['metrics']['events_processed']}")
            logger.info(f"      Success Rate: {agent_metrics['metrics']['success_rate']:.1f}%")
        
        logger.info("\n  Event Bus:")
        eb_metrics = metrics['event_bus']
        logger.info(f"    Published: {eb_metrics['events_published']}")
        logger.info(f"    Delivered: {eb_metrics['events_delivered']}")
        logger.info(f"    Using Fallback: {eb_metrics['using_fallback']}")
        
        # Ejemplo de obtener reporte de inventario
        logger.info("\n📦 Inventory Report:")
        inventory_report = inventory_agent.get_inventory_report()
        logger.info(f"  Total Products Tracked: {inventory_report['total_products']}")
        logger.info(f"  Total Inventory Value: ${inventory_report['total_inventory_value']:.2f}")
        if inventory_report['by_status']:
            logger.info("  By Status:")
            for status, count in inventory_report['by_status'].items():
                logger.info(f"    - {status}: {count}")
        
        # 7. Mantener corriendo brevemente
        logger.info("\n⏱️  System running for 30 seconds...")
        logger.info("   (Press Ctrl+C to stop earlier)")
        
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt received")
        
    except Exception as e:
        logger.error(f"\n❌ Error during execution: {e}", exc_info=True)
    
    finally:
        # 8. Detener sistema
        logger.info("\n🛑 Stopping system...")
        await orchestrator.stop()
        logger.info("  ✓ System stopped cleanly")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Demo completed successfully")
        logger.info("=" * 80)


async def quick_test():
    """
    Test rápido sin orchestrator (para debugging).
    
    Prueba cada agent individualmente sin el sistema completo.
    """
    logger.info("🧪 Quick Test Mode - Testing agents individually")
    
    # Test DiscoveryAgent
    logger.info("\n1️⃣ Testing DiscoveryAgent...")
    discovery = DiscoveryAgent()
    await discovery.start()
    
    event = {
        "event_type": "TrendDiscoveryRequested",
        "payload": {"budget": 3000, "category": "fitness"},
        "event_id": "test-1",
        "timestamp": "2025-10-30T10:00:00"
    }
    
    result = await discovery.process_event(event)
    if result:
        logger.info(f"  ✓ Discovered {len(result.get('payload', {}).get('all_products', []))} products")
    
    await discovery.stop()
    
    logger.info("\n✅ Quick test completed")


if __name__ == "__main__":
    import sys
    
    # Elegir modo
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(main())

