#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Initialization Script

Crea todas las tablas en la base de datos PostgreSQL.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.models import Base
from backend.database.models_business import (
    BusinessMetrics,
    ProfitOpportunityRecord,
    ReplenishmentRecord,
    CompetitorSnapshot,
    CompetitorChange,
    PriceHistory,
    BusinessAlert,
    BusinessAction,
    SalesForecast
)
from backend.database.session import get_async_engine
from backend.api.config import settings

async def init_db():
    """Crea todas las tablas en la base de datos."""
    print("[INFO] Initializing database...")
    print(f"[INFO] Database URL: {settings.database_url}")
    
    engine = get_async_engine()
    
    try:
        async with engine.begin() as conn:
            print("[INFO] Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            
            print("[INFO] Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            
        print("[SUCCESS] Database initialized successfully!")
        print("\n[INFO] Tables created:")
        print("   - products")
        print("   - inventory")
        print("   - suppliers")
        print("   - business_metrics")
        print("   - profit_opportunities")
        print("   - replenishment_records")
        print("   - competitor_snapshots")
        print("   - competitor_changes")
        print("   - price_history")
        print("   - business_alerts")
        print("   - business_actions")
        print("   - sales_forecasts")
        
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())

