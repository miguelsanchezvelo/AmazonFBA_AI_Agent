#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Products API Routes.

Endpoints para gestión y descubrimiento de productos.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.product import (
    ProductResponse,
    ProductCreate,
    ProductUpdate,
    ProductSearchRequest,
    ProductDiscoveryRequest,
    ProductDiscoveryResponse,
    ProductListResponse
)
from backend.api.dependencies import (
    DbDependency,
    CurrentUser,
    CacheDependency,
    RateLimited
)
from backend.services.product_service import ProductService


router = APIRouter()


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List products",
    description="Obtiene lista paginada de productos con filtros opcionales"
)
async def list_products(
    keyword: str = Query(None, description="Search keyword"),
    category: str = Query(None, description="Filter by category"),
    min_price: float = Query(None, ge=0, description="Minimum price"),
    max_price: float = Query(None, ge=0, description="Maximum price"),
    min_rating: float = Query(None, ge=0, le=5, description="Minimum rating"),
    max_bsr: int = Query(None, gt=0, description="Maximum BSR"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: DbDependency = ...,
    cache: CacheDependency = ...
) -> ProductListResponse:
    """
    List products with optional filtering and pagination.
    
    Args:
        keyword: Search keyword to filter products
        category: Product category filter
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_rating: Minimum rating filter
        max_bsr: Maximum Best Seller Rank filter
        limit: Number of results per page
        offset: Pagination offset
        db: Database session dependency
        cache: Cache service dependency
        
    Returns:
        Paginated list of products matching filters
        
    Examples:
        >>> GET /api/v2/products?keyword=yoga&min_rating=4.0&limit=10
    """
    service = ProductService(db, cache)
    
    search_request = ProductSearchRequest(
        keyword=keyword,
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        max_bsr=max_bsr,
        limit=limit,
        offset=offset
    )
    
    return await service.search_products(search_request)


@router.get(
    "/{asin}",
    response_model=ProductResponse,
    summary="Get product by ASIN",
    description="Obtiene detalles completos de un producto por su ASIN"
)
async def get_product(
    asin: str,
    db: DbDependency = ...,
    cache: CacheDependency = ...
) -> ProductResponse:
    """
    Get product details by ASIN.
    
    Args:
        asin: Amazon Standard Identification Number
        db: Database session dependency
        cache: Cache service dependency
        
    Returns:
        Product details
        
    Raises:
        HTTPException: 404 if product not found
        
    Examples:
        >>> GET /api/v2/products/B08N5WRWNW
    """
    service = ProductService(db, cache)
    product = await service.get_by_asin(asin)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ASIN {asin} not found"
        )
    
    return product


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Crea un nuevo producto manualmente",
    dependencies=[RateLimited]
)
async def create_product(
    product: ProductCreate,
    db: DbDependency = ...,
    cache: CacheDependency = ...,
    user: CurrentUser = ...
) -> ProductResponse:
    """
    Create a new product manually.
    
    Args:
        product: Product data to create
        db: Database session dependency
        user: Current authenticated user
        
    Returns:
        Created product
        
    Raises:
        HTTPException: 409 if product with ASIN already exists
        
    Examples:
        >>> POST /api/v2/products
        >>> {
        >>>   "asin": "B08N5WRWNW",
        >>>   "title": "Yoga Mat Premium",
        >>>   "price": 29.99,
        >>>   "rating": 4.5,
        >>>   "reviews_count": 1234
        >>> }
    """
    service = ProductService(db, cache)
    
    # Check if product already exists
    existing = await service.get_by_asin(product.asin)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with ASIN {product.asin} already exists"
        )
    
    return await service.create_product(product)


@router.put(
    "/{asin}",
    response_model=ProductResponse,
    summary="Update product",
    description="Actualiza un producto existente",
    dependencies=[RateLimited]
)
async def update_product(
    asin: str,
    product: ProductUpdate,
    db: DbDependency = ...,
    cache: CacheDependency = ...,
    user: CurrentUser = ...
) -> ProductResponse:
    """
    Update an existing product.
    
    Args:
        asin: Product ASIN to update
        product: Updated product data
        db: Database session dependency
        user: Current authenticated user
        
    Returns:
        Updated product
        
    Raises:
        HTTPException: 404 if product not found
        
    Examples:
        >>> PUT /api/v2/products/B08N5WRWNW
        >>> {
        >>>   "price": 24.99,
        >>>   "rating": 4.6
        >>> }
    """
    service = ProductService(db, cache)
    
    updated = await service.update_product(asin, product)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ASIN {asin} not found"
        )
    
    return updated


@router.delete(
    "/{asin}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
    description="Elimina un producto",
    dependencies=[RateLimited]
)
async def delete_product(
    asin: str,
    db: DbDependency = ...,
    cache: CacheDependency = ...,
    user: CurrentUser = ...
) -> None:
    """
    Delete a product.
    
    Args:
        asin: Product ASIN to delete
        db: Database session dependency
        user: Current authenticated user
        
    Raises:
        HTTPException: 404 if product not found
        
    Examples:
        >>> DELETE /api/v2/products/B08N5WRWNW
    """
    service = ProductService(db, cache)
    
    success = await service.delete_product(asin)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ASIN {asin} not found"
        )


@router.post(
    "/discover",
    response_model=ProductDiscoveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Discover products",
    description="Inicia proceso de descubrimiento automático de productos",
    dependencies=[RateLimited]
)
async def discover_products(
    request: ProductDiscoveryRequest,
    db: DbDependency = ...,
    cache: CacheDependency = ...
) -> ProductDiscoveryResponse:
    """
    Start product discovery process.
    
    Triggers Discovery Agent to find profitable products based on trends
    and criteria. Returns immediately with task ID for async tracking.
    
    Args:
        request: Discovery request with criteria
        db: Database session dependency
        user: Current authenticated user
        
    Returns:
        Discovery task information
        
    Examples:
        >>> POST /api/v2/products/discover
        >>> {
        >>>   "budget": 3000,
        >>>   "categories": ["Sports", "Home"],
        >>>   "min_demand_score": 70,
        >>>   "auto_analyze": true
        >>> }
    """
    service = ProductService(db, cache)
    
    task_id = await service.start_discovery(request)
    
    return ProductDiscoveryResponse(
        task_id=task_id,
        status="pending",
        products_found=0,
        estimated_time=30,
        message="Product discovery started. Check status using task_id."
    )


@router.get(
    "/discover/{task_id}",
    response_model=ProductDiscoveryResponse,
    summary="Get discovery status",
    description="Obtiene el estado de una tarea de descubrimiento"
)
async def get_discovery_status(
    task_id: str,
    db: DbDependency = ...,
    cache: CacheDependency = ...
) -> ProductDiscoveryResponse:
    """
    Get status of product discovery task.
    
    Args:
        task_id: Discovery task ID
        db: Database session dependency
        
    Returns:
        Current status of discovery task
        
    Raises:
        HTTPException: 404 if task not found
        
    Examples:
        >>> GET /api/v2/products/discover/abc-123-def
    """
    service = ProductService(db, cache)
    
    status_info = await service.get_discovery_status(task_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery task {task_id} not found"
        )
    
    return status_info


@router.get(
    "/trending/keywords",
    response_model=List[dict],
    summary="Get trending keywords",
    description="Obtiene keywords en tendencia para discovery"
)
async def get_trending_keywords(
    category: str = Query(None, description="Filter by category"),
    limit: int = Query(10, ge=1, le=50),
    cache: CacheDependency = ...
) -> List[dict]:
    """
    Get trending search keywords.
    
    Uses Google Trends to identify trending keywords for product discovery.
    
    Args:
        category: Filter by category
        limit: Number of keywords to return
        cache: Cache service dependency
        
    Returns:
        List of trending keywords with scores
        
    Examples:
        >>> GET /api/v2/products/trending/keywords?category=Sports&limit=10
    """
    # TODO: Implement actual trending keywords fetching
    # TODO: Use Google Trends API
    # TODO: Cache results
    
    return [
        {"keyword": "yoga mat", "score": 95, "trend": "up"},
        {"keyword": "resistance bands", "score": 88, "trend": "up"},
        {"keyword": "water bottle", "score": 76, "trend": "stable"}
    ]

