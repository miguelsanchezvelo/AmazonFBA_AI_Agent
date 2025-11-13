#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación Completa del Sistema.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.config import settings
from backend.database.session import get_async_engine, get_db
from sqlalchemy import text


async def verify_system():
    """Verifica todos los componentes del sistema."""
    print("=" * 60)
    print("VERIFICACION COMPLETA DEL SISTEMA")
    print("=" * 60)
    print(f"\nAmbiente: {settings.environment}")
    print(f"Debug: {settings.debug}")
    
    all_ok = True
    
    # 1. Base de datos
    print("\n[1/5] Verificando base de datos...")
    try:
        engine = get_async_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5"))
            tables = [row[0] for row in result]
            print(f"[OK] Base de datos conectada. Tablas: {', '.join(tables[:5])}")
        await engine.dispose()
    except Exception as e:
        print(f"[ERROR] Base de datos: {e}")
        all_ok = False
    
    # 2. Redis/Cache
    print("\n[2/5] Verificando Redis/Cache...")
    try:
        from core.cache_manager import CacheManager
        cache = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        cache.set("test_key", "test_value", ttl=10)
        value = cache.get("test_key")
        assert value == "test_value"
        cache.delete("test_key")
        if cache.connected:
            print("[OK] Redis conectado y funcionando")
        else:
            print("[OK] Usando cache en memoria (fallback)")
    except Exception as e:
        print(f"[ERROR] Cache: {e}")
        all_ok = False
    
    # 3. Event Bus
    print("\n[3/5] Verificando Event Bus...")
    try:
        from backend.core.event_bus import EventBus, Event
        bus = EventBus(
            redis_url=settings.redis_url or f"redis://{settings.redis_host}:{settings.redis_port}",
            stream_name=settings.event_stream_name,
            consumer_group=settings.event_consumer_group
        )
        await bus.connect()
        
        # Test publicación
        test_event = Event(
            event_type="SystemTest",
            payload={"test": True},
            source_agent="verification"
        )
        event_id = await bus.publish(test_event)
        
        if bus.using_fallback:
            print("[OK] Event Bus usando memoria (fallback)")
        else:
            print("[OK] Event Bus conectado a Redis")
        
        await bus.disconnect()
    except Exception as e:
        print(f"[ERROR] Event Bus: {e}")
        all_ok = False
    
    # 4. Agents
    print("\n[4/5] Verificando Agents...")
    try:
        from backend.agents.discovery_agent import DiscoveryAgent
        from backend.agents.analysis_agent import AnalysisAgent
        from backend.agents.supplier_agent import SupplierAgent
        from backend.agents.pricing_agent import PricingAgent
        from backend.agents.inventory_agent import InventoryAgent
        
        agents = [
            DiscoveryAgent,
            AnalysisAgent,
            SupplierAgent,
            PricingAgent,
            InventoryAgent
        ]
        print(f"[OK] {len(agents)} agents importados correctamente")
    except Exception as e:
        print(f"[ERROR] Agents: {e}")
        all_ok = False
    
    # 5. API Keys
    print("\n[5/5] Verificando API Keys...")
    warnings = []
    if not settings.serpapi_key and not settings.serpapi_api_key:
        warnings.append("SERPAPI_KEY no configurada")
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY no configurada")
    
    if warnings:
        print("[WARN] " + ", ".join(warnings))
        print("       Agents tendrán funcionalidad limitada sin API keys")
    else:
        print("[OK] API keys configuradas")
    
    # Resumen
    print("\n" + "=" * 60)
    if all_ok:
        print("[OK] SISTEMA VERIFICADO Y FUNCIONANDO")
        print("=" * 60)
        print("\nProximos pasos:")
        print("1. Iniciar backend: python -m uvicorn backend.api.main:app --reload")
        print("2. Acceder docs: http://localhost:8000/api/v2/docs")
        print("3. Configurar API keys en .env para funcionalidad completa")
    else:
        print("[ERROR] SISTEMA CON ERRORES")
        print("=" * 60)
        print("\nRevisar los errores arriba y corregir")
    
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(verify_system())
    sys.exit(0 if success else 1)


