#!/usr/bin/env python3
"""
Tests para el sistema de caché.
"""

import pytest
import time
from unittest.mock import Mock, patch
from core.cache_manager import CacheManager, get_cache


class TestCacheManager:
    """Tests para CacheManager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Fixture que crea un cache manager para testing."""
        # Usar solo memoria para tests (no requiere Redis)
        return CacheManager(use_memory_fallback=True)
    
    def test_cache_initialization(self, cache_manager):
        """Test inicialización del cache manager."""
        assert cache_manager is not None
        assert cache_manager.memory_cache == {}
    
    def test_set_and_get(self, cache_manager):
        """Test guardar y recuperar valores."""
        # Set
        result = cache_manager.set("test_key", {"data": "test_value"})
        assert result is True
        
        # Get
        value = cache_manager.get("test_key")
        assert value == {"data": "test_value"}
    
    def test_get_nonexistent_key(self, cache_manager):
        """Test obtener key que no existe."""
        value = cache_manager.get("nonexistent_key")
        assert value is None
    
    def test_delete(self, cache_manager):
        """Test eliminar valor del caché."""
        # Guardar valor
        cache_manager.set("delete_test", "value")
        assert cache_manager.get("delete_test") == "value"
        
        # Eliminar
        result = cache_manager.delete("delete_test")
        assert result is True
        
        # Verificar que ya no existe
        assert cache_manager.get("delete_test") is None
    
    def test_clear_cache(self, cache_manager):
        """Test limpiar caché completo."""
        # Agregar varios valores
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.set("key3", "value3")
        
        # Limpiar
        count = cache_manager.clear()
        assert count == 3
        
        # Verificar que están vacíos
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
    
    def test_clear_with_pattern(self, cache_manager):
        """Test limpiar caché con patrón."""
        # Agregar valores con diferentes prefijos
        cache_manager.set("api:key1", "value1")
        cache_manager.set("api:key2", "value2")
        cache_manager.set("db:key1", "value1")
        
        # Limpiar solo api:*
        count = cache_manager.clear("api:*")
        assert count == 2
        
        # Verificar
        assert cache_manager.get("api:key1") is None
        assert cache_manager.get("db:key1") == "value1"
    
    def test_cached_decorator(self, cache_manager):
        """Test decorator de caché."""
        call_count = 0
        
        @cache_manager.cached(ttl=60, key_prefix="test")
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # Primera llamada - debe ejecutar función
        result1 = expensive_function(2, 3)
        assert result1 == 5
        assert call_count == 1
        
        # Segunda llamada - debe usar caché
        result2 = expensive_function(2, 3)
        assert result2 == 5
        assert call_count == 1  # No aumentó
        
        # Llamada con diferentes parámetros - debe ejecutar función
        result3 = expensive_function(4, 5)
        assert result3 == 9
        assert call_count == 2
    
    def test_cached_decorator_with_kwargs(self, cache_manager):
        """Test decorator con argumentos nombrados."""
        call_count = 0
        
        @cache_manager.cached(ttl=60, key_prefix="test")
        def function_with_kwargs(a, b=10, c=20):
            nonlocal call_count
            call_count += 1
            return a + b + c
        
        # Primera llamada
        result1 = function_with_kwargs(1, b=2, c=3)
        assert result1 == 6
        assert call_count == 1
        
        # Segunda llamada con mismos parámetros - caché
        result2 = function_with_kwargs(1, b=2, c=3)
        assert result2 == 6
        assert call_count == 1
        
        # Llamada con diferentes kwargs - nueva ejecución
        result3 = function_with_kwargs(1, b=5, c=10)
        assert result3 == 16
        assert call_count == 2
    
    def test_cache_key_generation(self, cache_manager):
        """Test generación de cache keys."""
        key1 = cache_manager._generate_cache_key(
            "prefix", "func", (1, 2), {"a": 3}
        )
        key2 = cache_manager._generate_cache_key(
            "prefix", "func", (1, 2), {"a": 3}
        )
        key3 = cache_manager._generate_cache_key(
            "prefix", "func", (1, 3), {"a": 3}
        )
        
        # Mismos parámetros = misma key
        assert key1 == key2
        
        # Diferentes parámetros = diferente key
        assert key1 != key3
    
    def test_get_stats(self, cache_manager):
        """Test obtener estadísticas del caché."""
        # Agregar algunos valores
        cache_manager.set("stat_key1", "value1")
        cache_manager.set("stat_key2", "value2")
        
        stats = cache_manager.get_stats()
        
        assert 'memory_cache_size' in stats
        assert stats['memory_cache_size'] == 2
        assert 'redis_connected' in stats
        assert 'using_fallback' in stats
    
    def test_serialization_of_complex_objects(self, cache_manager):
        """Test serialización de objetos complejos."""
        complex_obj = {
            'string': 'test',
            'number': 42,
            'float': 3.14,
            'list': [1, 2, 3],
            'nested': {
                'key': 'value'
            }
        }
        
        cache_manager.set("complex", complex_obj)
        retrieved = cache_manager.get("complex")
        
        assert retrieved == complex_obj
    
    def test_singleton_pattern(self):
        """Test que get_cache() retorna el mismo instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2


class TestCacheIntegration:
    """Tests de integración del sistema de caché."""
    
    def test_cache_reduces_execution_time(self):
        """Test que el caché realmente mejora performance."""
        cache_manager = CacheManager()
        
        @cache_manager.cached(ttl=10)
        def slow_function():
            time.sleep(0.1)  # Simula operación lenta
            return "result"
        
        # Primera llamada - lenta
        start = time.time()
        slow_function()
        first_call_time = time.time() - start
        
        # Segunda llamada - rápida (caché)
        start = time.time()
        slow_function()
        second_call_time = time.time() - start
        
        # La segunda debe ser significativamente más rápida
        assert second_call_time < first_call_time / 2
    
    def test_cache_with_api_simulation(self):
        """Test simulando llamadas a API."""
        cache_manager = CacheManager()
        api_call_count = 0
        
        @cache_manager.cached(ttl=60, key_prefix="api")
        def mock_api_call(endpoint: str, params: dict):
            nonlocal api_call_count
            api_call_count += 1
            return {
                'endpoint': endpoint,
                'params': params,
                'data': [1, 2, 3]
            }
        
        # Múltiples llamadas al mismo endpoint
        for _ in range(5):
            result = mock_api_call("/products", {"category": "electronics"})
        
        # Solo debería haber 1 llamada real a la API
        assert api_call_count == 1
        assert result['data'] == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


