#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Configuración de Base de Datos.

Facilita la creación de la base de datos y ejecución de migraciones.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.api.config import settings
from backend.database.session import get_async_engine, init_db
from sqlalchemy import text


async def create_database_if_not_exists():
    """
    Crea la base de datos si no existe.
    
    Nota: PostgreSQL requiere conexión sin especificar DB para crear DB.
    """
    database_url = settings.database_url
    
    # Extraer componentes de la URL
    if database_url.startswith("postgresql://"):
        # Parsear URL: postgresql://user:pass@host:port/dbname
        parts = database_url.replace("postgresql://", "").split("/")
        auth_host = parts[0]
        db_name = parts[1] if len(parts) > 1 else None
        
        if db_name:
            # Conectar a postgres para crear la nueva DB
            admin_url = f"postgresql+asyncpg://{auth_host}/postgres"
            
            try:
                from sqlalchemy.ext.asyncio import create_async_engine
                admin_engine = create_async_engine(admin_url)
                
                async with admin_engine.begin() as conn:
                    # Verificar si la DB existe
                    result = await conn.execute(
                        text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
                    )
                    exists = result.scalar()
                    
                    if not exists:
                        # Crear la base de datos
                        await conn.execute(text(f"CREATE DATABASE {db_name}"))
                        print(f"✅ Base de datos '{db_name}' creada exitosamente")
                    else:
                        print(f"ℹ️  Base de datos '{db_name}' ya existe")
                
                await admin_engine.dispose()
                
            except Exception as e:
                print(f"⚠️  No se pudo crear la base de datos automáticamente: {e}")
                print(f"   Por favor créala manualmente:")
                print(f"   CREATE DATABASE {db_name};")
    else:
        print(f"ℹ️  Usando SQLite - no se requiere creación manual de DB")


async def setup_database():
    """Configura la base de datos completa."""
    print("=" * 60)
    print("🔧 CONFIGURACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    print(f"\n📊 Configuración actual:")
    print(f"   Database URL: {settings.database_url}")
    print(f"   Environment: {settings.environment}")
    
    # Paso 1: Crear DB si no existe
    print("\n📝 Paso 1: Verificando base de datos...")
    await create_database_if_not_exists()
    
    # Paso 2: Inicializar tablas
    print("\n📝 Paso 2: Creando tablas...")
    try:
        await init_db()
        print("✅ Tablas creadas exitosamente")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        print("\n💡 Intentando con migraciones de Alembic...")
        return False
    
    # Paso 3: Verificar conexión
    print("\n📝 Paso 3: Verificando conexión...")
    try:
        engine = get_async_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("✅ Conexión verificada exitosamente")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Error verificando conexión: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    print("\n📚 Próximos pasos:")
    print("   1. Ejecutar migraciones: alembic upgrade head")
    print("   2. Probar endpoints en: http://localhost:8000/api/v2/docs")
    print("   3. Cargar datos de prueba si es necesario")
    
    return True


async def main():
    """Ejecuta configuración de base de datos."""
    try:
        success = await setup_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuración cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


