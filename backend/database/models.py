#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM Models for Amazon FBA AI Agent V2.

Define todos los modelos de base de datos PostgreSQL usando SQLAlchemy async.
Todos los modelos usan UUID como primary key y soportan relaciones complejas.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, JSON,
    ForeignKey, Index, Table, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with async support."""
    pass


# Association table for many-to-many relationship between Supplier and Product
supplier_product_association = Table(
    'supplier_products',
    Base.metadata,
    Column('supplier_id', PostgresUUID(as_uuid=True), ForeignKey('suppliers.id'), primary_key=True),
    Column('product_id', PostgresUUID(as_uuid=True), ForeignKey('products.id'), primary_key=True),
    Index('idx_supplier_product', 'supplier_id', 'product_id')
)


class Product(Base):
    """
    Product model representing Amazon products.
    
    Attributes:
        id: UUID primary key
        asin: Amazon Standard Identification Number (unique, indexed)
        title: Product title (indexed)
        price: Current price
        rating: Average rating
        reviews: Number of reviews
        bsr: Best Seller Rank
        category: Product category
        image_url: Product image URL
        created_at: Creation timestamp
        updated_at: Last update timestamp
        
    Relationships:
        analyses: One-to-many relationship with Analysis
        suppliers: Many-to-many relationship with Supplier
        inventory: One-to-one relationship with Inventory
        
    Examples:
        >>> product = Product(
        ...     asin="B08EXAMPLE",
        ...     title="Example Product",
        ...     price=29.99,
        ...     rating=4.5,
        ...     reviews=1250
        ... )
    """
    __tablename__ = "products"
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    asin: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    rating: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    reviews: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    bsr: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    suppliers: Mapped[List["Supplier"]] = relationship(
        "Supplier",
        secondary=supplier_product_association,
        back_populates="products"
    )
    inventory: Mapped[Optional["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
        uselist=False
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_products_asin', 'asin'),
        Index('idx_products_title', 'title'),
    )


class Analysis(Base):
    """
    Analysis model storing analysis results for products.
    
    Attributes:
        id: UUID primary key
        product_id: Foreign key to Product
        analysis_type: Type of analysis ('market', 'profitability', 'demand', etc.)
        data: JSON field containing analysis results
        confidence_score: Confidence score (0.0 to 1.0)
        created_at: Creation timestamp
        
    Relationships:
        product: Many-to-one relationship with Product
        
    Examples:
        >>> analysis = Analysis(
        ...     product_id=product.id,
        ...     analysis_type="market",
        ...     data={"competition": "low", "trend": "rising"},
        ...     confidence_score=0.85
        ... )
    """
    __tablename__ = "analyses"
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey('products.id'),
        nullable=False
    )
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="analyses"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_analyses_product_id', 'product_id'),
        Index('idx_analyses_type', 'analysis_type'),
    )


class Supplier(Base):
    """
    Supplier model storing supplier information.
    
    Attributes:
        id: UUID primary key
        name: Supplier name
        email: Supplier email (unique)
        rating: Supplier rating (0.0 to 5.0)
        country: Supplier country
        communication_history: JSON field storing message history
        created_at: Creation timestamp
        updated_at: Last update timestamp
        
    Relationships:
        products: Many-to-many relationship with Product
        
    Examples:
        >>> supplier = Supplier(
        ...     name="ABC Trading Co",
        ...     email="contact@abc.com",
        ...     rating=4.5,
        ...     country="China"
        ... )
    """
    __tablename__ = "suppliers"
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )
    rating: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    communication_history: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    products: Mapped[List["Product"]] = relationship(
        "Product",
        secondary=supplier_product_association,
        back_populates="suppliers"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_suppliers_email', 'email'),
    )


class Inventory(Base):
    """
    Inventory model tracking product stock levels.
    
    Attributes:
        id: UUID primary key
        product_id: Foreign key to Product (unique)
        quantity: Current stock quantity
        location: FBA warehouse location
        last_order_date: Date of last order
        next_restock_date: Scheduled restock date
        reorder_point: Minimum stock level before reordering
        created_at: Creation timestamp
        updated_at: Last update timestamp
        
    Relationships:
        product: Many-to-one relationship with Product
        
    Examples:
        >>> inventory = Inventory(
        ...     product_id=product.id,
        ...     quantity=100,
        ...     location="FBA_LAX9",
        ...     reorder_point=50
        ... )
    """
    __tablename__ = "inventory"
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey('products.id'),
        nullable=False,
        unique=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    last_order_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    next_restock_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="inventory"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_inventory_product_id', 'product_id'),
        Index('idx_inventory_location', 'location'),
    )


class Event(Base):
    """
    Event model for event-driven architecture.
    
    Stores all events flowing through the system for audit and replay.
    
    Attributes:
        id: UUID primary key
        event_type: Type of event ('product_discovered', 'analysis_complete', etc.)
        payload: JSON field containing event data
        created_at: Event creation timestamp
        processed_at: When event was processed (nullable)
        status: Event status ('pending', 'processed', 'failed')
        error_message: Error message if processing failed (nullable)
        
    Examples:
        >>> event = Event(
        ...     event_type="product_discovered",
        ...     payload={"asin": "B08EXAMPLE", "title": "Example"},
        ...     status="pending"
        ... )
    """
    __tablename__ = "events"
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='pending'
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_events_type', 'event_type'),
        Index('idx_events_status', 'status'),
        Index('idx_events_created_at', 'created_at'),
    )


class APICache(Base):
    """
    API Cache model for caching external API responses.
    
    Attributes:
        key: String primary key (cache key)
        value: JSON field containing cached API response
        ttl: Time to live in seconds
        created_at: Creation timestamp
        expires_at: Expiration timestamp (indexed)
        
    Examples:
        >>> cache = APICache(
        ...     key="serpapi:product:B08EXAMPLE",
        ...     value={"asin": "B08EXAMPLE", "price": 29.99},
        ...     ttl=3600
        ... )
    """
    __tablename__ = "api_cache"
    
    key: Mapped[str] = mapped_column(
        String(500),
        primary_key=True
    )
    value: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    ttl: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_api_cache_key', 'key'),
        Index('idx_api_cache_expires_at', 'expires_at'),
    )
