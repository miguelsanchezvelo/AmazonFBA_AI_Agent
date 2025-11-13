#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Repositories - Data Access Layer para SQLAlchemy async.

Proporciona acceso abstracted a la base de datos para:
- ProductRepository: Gestión de productos
- InventoryRepository: Gestión de inventario
- AnalysisRepository: Gestión de análisis
- SupplierRepository: Gestión de proveedores

Usa SQLAlchemy AsyncSession para operaciones async/await.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models import (
    Product,
    Analysis,
    Inventory,
    Supplier,
)

logger = logging.getLogger(__name__)


class ProductRepository:
    """
    Repository para gestionar productos en la base de datos.
    
    Proporciona operaciones CRUD y queries avanzadas para productos.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: AsyncSession de SQLAlchemy
        """
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.ProductRepository")
    
    async def get_by_asin(self, asin: str) -> Optional[Product]:
        """
        Obtiene un producto por su ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Product o None si no existe
        """
        stmt = select(Product).where(Product.asin == asin)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        """
        Obtiene un producto por su ID.
        
        Args:
            product_id: UUID del producto
            
        Returns:
            Product o None si no existe
        """
        return await self.db.get(Product, product_id)
    
    async def get_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "updated_at"
    ) -> tuple[List[Product], int]:
        """
        Obtiene todos los productos activos con paginación.
        
        Args:
            limit: Número máximo de resultados
            offset: Número de resultados a saltar
            order_by: Campo para ordenar (updated_at, rating, reviews, price)
            
        Returns:
            Tupla (lista de productos, total count)
        """
        try:
            # Count total
            count_stmt = select(func.count()).select_from(Product)
            count_result = await self.db.execute(count_stmt)
            total = count_result.scalar()
            
            # Get paginated products
            stmt = select(Product)
            
            # Apply ordering
            if order_by == "rating":
                stmt = stmt.order_by(desc(Product.rating))
            elif order_by == "reviews":
                stmt = stmt.order_by(desc(Product.reviews))
            elif order_by == "price":
                stmt = stmt.order_by(Product.price)
            else:  # updated_at (default)
                stmt = stmt.order_by(desc(Product.updated_at))
            
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.db.execute(stmt)
            products = result.scalars().all()
            
            self.logger.debug(f"Retrieved {len(products)} active products")
            return list(products), total
            
        except Exception as e:
            self.logger.error(f"Error getting active products: {e}")
            raise
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 50
    ) -> List[Product]:
        """
        Obtiene productos por categoría.
        
        Args:
            category: Categoría del producto
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos
        """
        stmt = (
            select(Product)
            .where(Product.category == category)
            .order_by(desc(Product.reviews))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_high_performers(self, limit: int = 10) -> List[Product]:
        """
        Obtiene productos con mejor desempeño (rating + reviews).
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos ordenados por desempeño
        """
        stmt = (
            select(Product)
            .where(Product.rating.isnot(None))
            .order_by(desc(Product.rating * Product.reviews))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_low_performers(self, limit: int = 10) -> List[Product]:
        """
        Obtiene productos con bajo desempeño.
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos ordenados por desempeño (menor primero)
        """
        stmt = (
            select(Product)
            .where(Product.rating.isnot(None))
            .order_by(asc(Product.rating * Product.reviews))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_price_range(
        self,
        min_price: float,
        max_price: float,
        limit: int = 50
    ) -> List[Product]:
        """
        Obtiene productos dentro de un rango de precios.
        
        Args:
            min_price: Precio mínimo
            max_price: Precio máximo
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos
        """
        stmt = (
            select(Product)
            .where(and_(
                Product.price >= min_price,
                Product.price <= max_price
            ))
            .order_by(desc(Product.reviews))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(
        self,
        asin: str,
        title: str,
        price: float,
        rating: Optional[float] = None,
        reviews: int = 0,
        bsr: Optional[int] = None,
        category: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Product:
        """
        Crea un nuevo producto.
        
        Args:
            asin: ASIN del producto
            title: Título del producto
            price: Precio del producto
            rating: Rating del producto
            reviews: Número de reviews
            bsr: Best Seller Rank
            category: Categoría
            image_url: URL de imagen
            
        Returns:
            Producto creado
        """
        try:
            product = Product(
                asin=asin,
                title=title,
                price=price,
                rating=rating,
                reviews=reviews,
                bsr=bsr,
                category=category,
                image_url=image_url
            )
            self.db.add(product)
            await self.db.flush()
            self.logger.info(f"Created product {asin}")
            return product
        except Exception as e:
            self.logger.error(f"Error creating product {asin}: {e}")
            raise
    
    async def update(
        self,
        product_id: UUID,
        **kwargs
    ) -> Optional[Product]:
        """
        Actualiza un producto.
        
        Args:
            product_id: UUID del producto
            **kwargs: Campos a actualizar
            
        Returns:
            Producto actualizado o None
        """
        try:
            product = await self.get_by_id(product_id)
            if not product:
                return None
            
            for key, value in kwargs.items():
                if hasattr(product, key) and key != 'id':
                    setattr(product, key, value)
            
            await self.db.flush()
            self.logger.info(f"Updated product {product_id}")
            return product
        except Exception as e:
            self.logger.error(f"Error updating product {product_id}: {e}")
            raise
    
    async def get_products_with_analyses(self) -> List[Product]:
        """
        Obtiene productos con sus análisis asociados.
        
        Returns:
            Lista de productos con analyses precargados
        """
        stmt = select(Product).options(selectinload(Product.analyses))
        result = await self.db.execute(stmt)
        return result.scalars().unique().all()
    
    async def get_count(self) -> int:
        """
        Obtiene el total de productos.
        
        Returns:
            Número total de productos
        """
        stmt = select(func.count()).select_from(Product)
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class InventoryRepository:
    """
    Repository para gestionar inventario.
    
    Proporciona operaciones para inventory management y tracking.
    """
    
    def __init__(self, db: AsyncSession):
        """Inicializa el repositorio con una sesión de base de datos."""
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.InventoryRepository")
    
    async def get_by_product_id(self, product_id: UUID) -> Optional[Inventory]:
        """Obtiene inventario de un producto."""
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_low_stock_products(self, threshold: int = 50) -> List[Inventory]:
        """Obtiene productos con stock bajo."""
        stmt = (
            select(Inventory)
            .where(Inventory.current_stock < threshold)
            .order_by(asc(Inventory.current_stock))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del inventario."""
        try:
            stmt = select(Inventory)
            result = await self.db.execute(stmt)
            inventory_items = result.scalars().all()
            
            total_units = sum(inv.current_stock for inv in inventory_items)
            total_value = sum(
                (inv.current_stock * (inv.price or 0)) 
                for inv in inventory_items
            )
            low_stock_count = len([inv for inv in inventory_items if inv.current_stock < 50])
            
            return {
                "total_units": total_units,
                "total_value_usd": round(total_value, 2),
                "low_stock_alerts": low_stock_count,
                "total_items": len(inventory_items),
                "average_turnover_days": sum(
                    (inv.days_of_supply or 0) for inv in inventory_items
                ) / len(inventory_items) if inventory_items else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting inventory summary: {e}")
            return {
                "total_units": 0,
                "total_value_usd": 0,
                "low_stock_alerts": 0,
                "total_items": 0,
                "average_turnover_days": 0
            }
    
    async def update_stock(
        self,
        product_id: UUID,
        new_stock: int
    ) -> Optional[Inventory]:
        """Actualiza el stock de un producto."""
        try:
            inventory = await self.get_by_product_id(product_id)
            if not inventory:
                return None
            
            inventory.current_stock = new_stock
            await self.db.flush()
            self.logger.info(f"Updated stock for product {product_id} to {new_stock}")
            return inventory
        except Exception as e:
            self.logger.error(f"Error updating stock: {e}")
            raise
    
    async def get_count(self) -> int:
        """Obtiene el total de items de inventario."""
        stmt = select(func.count()).select_from(Inventory)
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class AnalysisRepository:
    """
    Repository para gestionar análisis de productos.
    """
    
    def __init__(self, db: AsyncSession):
        """Inicializa el repositorio con una sesión de base de datos."""
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.AnalysisRepository")
    
    async def get_by_product_id(
        self,
        product_id: UUID,
        analysis_type: Optional[str] = None
    ) -> List[Analysis]:
        """Obtiene análisis de un producto."""
        stmt = select(Analysis).where(Analysis.product_id == product_id)
        
        if analysis_type:
            stmt = stmt.where(Analysis.analysis_type == analysis_type)
        
        stmt = stmt.order_by(desc(Analysis.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_latest_by_product(self, product_id: UUID) -> Optional[Analysis]:
        """Obtiene el análisis más reciente de un producto."""
        stmt = (
            select(Analysis)
            .where(Analysis.product_id == product_id)
            .order_by(desc(Analysis.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(
        self,
        product_id: UUID,
        analysis_type: str,
        data: Dict[str, Any],
        confidence_score: Optional[float] = None
    ) -> Analysis:
        """Crea un nuevo análisis."""
        try:
            analysis = Analysis(
                product_id=product_id,
                analysis_type=analysis_type,
                data=data,
                confidence_score=confidence_score
            )
            self.db.add(analysis)
            await self.db.flush()
            self.logger.info(f"Created analysis for product {product_id}")
            return analysis
        except Exception as e:
            self.logger.error(f"Error creating analysis: {e}")
            raise
    
    async def get_count(self) -> int:
        """Obtiene el total de análisis."""
        stmt = select(func.count()).select_from(Analysis)
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class SupplierRepository:
    """
    Repository para gestionar proveedores.
    """
    
    def __init__(self, db: AsyncSession):
        """Inicializa el repositorio con una sesión de base de datos."""
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.SupplierRepository")
    
    async def get_by_id(self, supplier_id: UUID) -> Optional[Supplier]:
        """Obtiene un proveedor por ID."""
        return await self.db.get(Supplier, supplier_id)
    
    async def get_by_country(self, country: str, limit: int = 20) -> List[Supplier]:
        """Obtiene proveedores por país."""
        stmt = (
            select(Supplier)
            .where(Supplier.country == country)
            .order_by(desc(Supplier.rating))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_high_rated(self, min_rating: float = 4.0, limit: int = 20) -> List[Supplier]:
        """Obtiene proveedores con alta calificación."""
        stmt = (
            select(Supplier)
            .where(Supplier.rating >= min_rating)
            .order_by(desc(Supplier.rating))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_for_product(self, product_id: UUID) -> List[Supplier]:
        """Obtiene proveedores para un producto específico."""
        stmt = (
            select(Supplier)
            .join(Supplier.products)
            .where(Product.id == product_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_count(self) -> int:
        """Obtiene el total de proveedores."""
        stmt = select(func.count()).select_from(Supplier)
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class BusinessMetricsRepository:
    """
    Repository para calcular métricas de negocio agregadas.
    
    Proporciona KPIs y estadísticas de alto nivel.
    """
    
    def __init__(self, db: AsyncSession):
        """Inicializa el repositorio con una sesión de base de datos."""
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.BusinessMetricsRepository")
    
    async def get_kpis(self) -> Dict[str, Any]:
        """
        Calcula KPIs principales del negocio.
        
        Returns:
            Diccionario con KPIs
        """
        try:
            # Count de productos
            product_count_stmt = select(func.count()).select_from(Product)
            product_count_result = await self.db.execute(product_count_stmt)
            total_products = product_count_result.scalar() or 0
            
            # Count de análisis
            analysis_count_stmt = select(func.count()).select_from(Analysis)
            analysis_count_result = await self.db.execute(analysis_count_stmt)
            total_analyses = analysis_count_result.scalar() or 0
            
            # Count de proveedores
            supplier_count_stmt = select(func.count()).select_from(Supplier)
            supplier_count_result = await self.db.execute(supplier_count_stmt)
            total_suppliers = supplier_count_result.scalar() or 0
            
            # Obtener productos para calcular métricas
            products_stmt = select(Product)
            products_result = await self.db.execute(products_stmt)
            products = products_result.scalars().all()
            
            # Calcular average rating y reviews
            avg_rating = sum(p.rating for p in products if p.rating) / len([p for p in products if p.rating]) if any(p.rating for p in products) else 0
            total_reviews = sum(p.reviews for p in products)
            avg_price = sum(p.price for p in products) / len(products) if products else 0
            
            return {
                "total_products": total_products,
                "total_analyses": total_analyses,
                "total_suppliers": total_suppliers,
                "average_rating": round(avg_rating, 2),
                "total_reviews": total_reviews,
                "average_price": round(avg_price, 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error calculating KPIs: {e}")
            return {
                "total_products": 0,
                "total_analyses": 0,
                "total_suppliers": 0,
                "average_rating": 0.0,
                "total_reviews": 0,
                "average_price": 0.0,
                "timestamp": datetime.now().isoformat()
            }
