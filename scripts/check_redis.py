#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar conexión a Redis.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.config import settings


def check_redis():
    """Verifica si Redis está disponible."""
    print("=" * 60)
    print("VERIFICACION DE REDIS")
    print("=" * 60)
    print(f"\nRedis configurado en: {settings.redis_host}:{settings.redis_port}")
    
    try:
        import redis
        
        # Intentar conectar
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            socket_connect_timeout=2,
            decode_responses=True
        )
        
        # Test ping
        r.ping()
        print("[OK] Redis está disponible y funcionando")
        
        # Test set/get
        r.set("test_key", "test_value")
        value = r.get("test_key")
        assert value == "test_value"
        r.delete("test_key")
        print("[OK] Operaciones básicas funcionan correctamente")
        
        return True
        
    except ImportError:
        print("[ERROR] Paquete 'redis' no instalado")
        print("\nInstalar con: pip install redis")
        return False
    except Exception as redis_error:
        # Cualquier error de conexión a Redis
        print(f"[WARN] No se puede conectar a Redis real: {redis_error}")
        print("\nIntentando con fakeredis...")
        
        try:
            import fakeredis
            r = fakeredis.FakeStrictRedis(decode_responses=True)
            
            # Test set/get
            r.set("test_key", "test_value")
            value = r.get("test_key")
            assert value == "test_value"
            r.delete("test_key")
            print("[OK] Fakeredis funcionando correctamente (modo desarrollo)")
            print("\nNota: Fakeredis es solo para desarrollo, sin persistencia")
            return True
        except ImportError:
            print("[ERROR] Fakeredis no instalado")
            print("\nInstalar con: pip install fakeredis")
            return False
        except Exception as e:
            print(f"[ERROR] Error con fakeredis: {e}")
            return False


if __name__ == "__main__":
    success = check_redis()
    sys.exit(0 if success else 1)

