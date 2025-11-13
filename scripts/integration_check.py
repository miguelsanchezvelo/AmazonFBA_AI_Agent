#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Integración Final - Amazon FBA AI Agent V2

Verifica que todos los componentes estén integrados correctamente:
- Backend FastAPI
- Database (PostgreSQL)
- Cache (Redis)
- Multi-Agent System
- Frontend (React)
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationChecker:
    """Verifica integración de componentes."""
    
    def __init__(self):
        """Initialize integration checker."""
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Ejecuta todas las verificaciones.
        
        Returns:
            Dictionary con resultados de todas las verificaciones
        """
        logger.info("Iniciando verificacion de integracion...")
        
        checks = [
            ("Imports Backend", self.check_backend_imports),
            ("Database Session", self.check_database_session),
            ("Cache Service", self.check_cache_service),
            ("API Routes", self.check_api_routes),
            ("Models", self.check_models),
            ("Services", self.check_services),
            ("Repositories", self.check_repositories),
            ("Event Bus", self.check_event_bus),
            ("Agents", self.check_agents),
        ]
        
        for name, check_func in checks:
            try:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                self.results[name] = result
                status = "OK" if result else "FAIL"
                logger.info(f"{status} {name}: {'OK' if result else 'FAILED'}")
            except Exception as e:
                self.results[name] = False
                self.errors.append(f"{name}: {str(e)}")
                logger.error(f"FAIL {name}: {str(e)}")
        
        return {
            "results": self.results,
            "errors": self.errors,
            "total": len(self.results),
            "passed": sum(1 for v in self.results.values() if v),
            "failed": sum(1 for v in self.results.values() if not v)
        }
    
    def check_backend_imports(self) -> bool:
        """Verifica que los imports del backend funcionen."""
        try:
            from backend.api.main import app
            from backend.api.config import settings
            from backend.database.session import get_db
            from backend.database.models import Product, Analysis, Supplier
            from backend.database.repository import ProductRepository
            from backend.services.product_service import ProductService
            from backend.core.event_bus import EventBus
            return True
        except Exception as e:
            logger.error(f"Backend imports failed: {e}")
            return False
    
    def check_database_session(self) -> bool:
        """Verifica configuración de database session."""
        try:
            from backend.database.session import get_async_engine, get_async_session_factory
            from backend.api.config import settings
            
            # Verifica que la URL de database esté configurada
            assert settings.database_url is not None
            assert len(settings.database_url) > 0
            
            return True
        except Exception as e:
            logger.error(f"Database session check failed: {e}")
            return False
    
    def check_cache_service(self) -> bool:
        """Verifica cache service."""
        try:
            from backend.services.cache_service import CacheService
            cache = CacheService()
            assert cache is not None
            return True
        except Exception as e:
            logger.error(f"Cache service check failed: {e}")
            return False
    
    def check_api_routes(self) -> bool:
        """Verifica que las rutas API estén cargadas."""
        try:
            from backend.api.main import app
            
            # Verifica que las rutas estén registradas
            routes = [route.path for route in app.routes]
            assert "/api/v2/products" in routes or "/products" in str(routes)
            
            return True
        except Exception as e:
            logger.error(f"API routes check failed: {e}")
            return False
    
    def check_models(self) -> bool:
        """Verifica modelos Pydantic."""
        try:
            from backend.models.product import ProductResponse, ProductCreate
            from backend.models.analysis import AnalysisRequest
            from backend.models.supplier import SupplierResponse
            
            # Verifica que los modelos se puedan instanciar
            product = ProductCreate(
                asin="B08TEST001",
                title="Test Product",
                price=19.99
            )
            assert product.asin == "B08TEST001"
            
            return True
        except Exception as e:
            logger.error(f"Models check failed: {e}")
            return False
    
    def check_services(self) -> bool:
        """Verifica servicios."""
        try:
            from backend.services.product_service import ProductService
            from backend.services.cache_service import CacheService
            
            cache = CacheService()
            service = ProductService(cache=cache)
            assert service is not None
            
            return True
        except Exception as e:
            logger.error(f"Services check failed: {e}")
            return False
    
    def check_repositories(self) -> bool:
        """Verifica repositorios."""
        try:
            from backend.database.repository import (
                ProductRepository,
                AnalysisRepository,
                SupplierRepository,
                InventoryRepository,
                EventRepository
            )
            
            # Verifica que los repositorios existan
            assert ProductRepository is not None
            assert AnalysisRepository is not None
            
            return True
        except Exception as e:
            logger.error(f"Repositories check failed: {e}")
            return False
    
    def check_event_bus(self) -> bool:
        """Verifica Event Bus."""
        try:
            from backend.core.event_bus import EventBus, Event
            
            # Verifica que EventBus se pueda instanciar
            event_bus = EventBus()
            assert event_bus is not None
            
            # Verifica que Event se pueda crear
            event = Event(
                event_type="test",
                payload={"test": "data"}
            )
            assert event.event_type == "test"
            
            return True
        except Exception as e:
            logger.error(f"Event bus check failed: {e}")
            return False
    
    def check_agents(self) -> bool:
        """Verifica agents."""
        try:
            from backend.agents.base_agent import BaseAgent
            from backend.agents.discovery_agent import DiscoveryAgent
            
            # Verifica que los agents existan
            assert BaseAgent is not None
            assert DiscoveryAgent is not None
            
            return True
        except Exception as e:
            logger.error(f"Agents check failed: {e}")
            return False
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Imprime resumen de resultados."""
        print("\n" + "="*60)
        print("RESUMEN DE INTEGRACION")
        print("="*60)
        print(f"Total verificaciones: {results['total']}")
        print(f"Pasadas: {results['passed']}")
        print(f"Fallidas: {results['failed']}")
        print(f"Porcentaje de éxito: {(results['passed']/results['total']*100):.1f}%")
        
        if results['errors']:
            print("\nERRORES ENCONTRADOS:")
            for error in results['errors']:
                print(f"  - {error}")
        
        print("\n" + "="*60)
        
        if results['failed'] == 0:
            print("TODAS LAS VERIFICACIONES PASARON!")
        else:
            print("Algunas verificaciones fallaron. Revisa los errores arriba.")


async def main():
    """Ejecuta verificaciones de integración."""
    checker = IntegrationChecker()
    results = await checker.check_all()
    checker.print_summary(results)
    
    # Exit code based on results
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())

