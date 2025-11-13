#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Dependencies - Inyección de dependencias para repositorios.

Proporciona factories para crear instancias de repositorios
con la sesión de base de datos inyectada.

Se utiliza con FastAPI Depends() para inyectar repositorios
en endpoints y servicios.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repositories import (
    ProductRepository,
    InventoryRepository,
    AnalysisRepository,
    SupplierRepository,
    BusinessMetricsRepository,
)
from backend.database.session import get_db


async def get_product_repository(
    db: AsyncSession = Depends(get_db),
) -> ProductRepository:
    """Factory para ProductRepository."""
    return ProductRepository(db)


async def get_inventory_repository(
    db: AsyncSession = Depends(get_db),
) -> InventoryRepository:
    """Factory para InventoryRepository."""
    return InventoryRepository(db)


async def get_analysis_repository(
    db: AsyncSession = Depends(get_db),
) -> AnalysisRepository:
    """Factory para AnalysisRepository."""
    return AnalysisRepository(db)


async def get_supplier_repository(
    db: AsyncSession = Depends(get_db),
) -> SupplierRepository:
    """Factory para SupplierRepository."""
    return SupplierRepository(db)


async def get_business_metrics_repository(
    db: AsyncSession = Depends(get_db),
) -> BusinessMetricsRepository:
    """Factory para BusinessMetricsRepository."""
    return BusinessMetricsRepository(db)

