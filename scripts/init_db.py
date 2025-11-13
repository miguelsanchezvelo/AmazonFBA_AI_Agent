#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para inicializar la base de datos SQLite.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database.session import init_db, get_async_engine
from backend.api.config import settings
from sqlalchemy import text


async def setup_database():
    """Configura la base de datos."""
    print("=" * 60)
    print("CONFIGURACION DE BASE DE DATOS")
    print("=" * 60)
    print(f"\nDatabase URL: {settings.database_url}")
    
    try:
        # Crear tablas usando init_db
        print("\nCreando tablas...")
        await init_db()
        print("[OK] Tablas creadas exitosamente")
        
        # Verificar conexión
        print("\nVerificando conexion...")
        engine = get_async_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("[OK] Conexion verificada")
        await engine.dispose()
        
        print("\n" + "=" * 60)
        print("[OK] CONFIGURACION COMPLETADA")
        print("=" * 60)
        print("\nBase de datos SQLite creada en: ./fba.db")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    sys.exit(0 if success else 1)

