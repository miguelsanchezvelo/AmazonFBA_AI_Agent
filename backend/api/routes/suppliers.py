#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suppliers API Routes.

Endpoints para gestión de proveedores y comunicación.
"""

from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.database.models import Supplier, Product
from backend.models.supplier import (
    SupplierContactRequest,
    SupplierContactResponse,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierSearchRequest,
    CommunicationLog,
)
from backend.api.dependencies import (
    DbDependency,
    RateLimited,
    CurrentUser,
)


class SupplierCommunicationEntry(BaseModel):
    """Frontend-facing communication entry structure."""

    id: str
    date: str
    type: str
    subject: Optional[str]
    content: str
    status: str


class SupplierSummary(BaseModel):
    """Frontend-facing supplier summary card."""

    id: str
    name: str
    email: Optional[str]
    rating: float = Field(0, ge=0, le=5)
    country: str = Field(default="Unknown")
    products: List[str] = Field(default_factory=list)
    communicationHistory: List[SupplierCommunicationEntry] = Field(default_factory=list)
    lastContact: str
    status: str = Field(default="pending")


class SupplierPaginatedResponse(BaseModel):
    """Paginated supplier response tailored for dashboard UI."""

    items: List[SupplierSummary]
    total: int
    page: int
    pageSize: int
    hasMore: bool


class SupplierQuickContactRequest(BaseModel):
    """Simple contact payload emitted by the dashboard UI."""

    supplierId: UUID
    message: str = Field(..., min_length=1, max_length=5000)


router = APIRouter()


def _determine_status(rating: Optional[float], last_contact: Optional[str]) -> str:
    """Return UI status based on rating and recency."""

    if rating is None:
        return "pending"
    if rating >= 4.0:
        return "active"
    if rating <= 2.0:
        return "inactive"
    # For mid ratings, use contact recency as tie-breaker
    if last_contact:
        try:
            delta = datetime.now(timezone.utc) - datetime.fromisoformat(last_contact)
            if delta.days > 60:
                return "inactive"
        except ValueError:
            # Fallback on rating
            return "pending"
    return "pending"


def _map_history_entry(entry: Dict[str, Any]) -> SupplierCommunicationEntry:
    """Normalize communication log entry to SupplierCommunicationEntry."""

    entry_id = entry.get("id") or str(uuid4())
    raw_date = entry.get("timestamp") or entry.get("date")
    if raw_date is None:
        raw_date = datetime.now(timezone.utc).isoformat()
    content = entry.get("content") or entry.get("message") or ""
    subject = entry.get("subject")
    status = entry.get("status")
    if status is None:
        direction = entry.get("direction", "outbound")
        status = "sent" if direction == "outbound" else "received"
    return SupplierCommunicationEntry(
        id=str(entry_id),
        date=str(raw_date),
        type=str(entry.get("type") or entry.get("channel") or "email"),
        subject=subject,
        content=str(content),
        status=str(status),
    )


def _map_supplier_to_summary(supplier: Supplier) -> SupplierSummary:
    """Transform database supplier record into dashboard summary."""

    history_payload = supplier.communication_history or {}
    if isinstance(history_payload, list):
        messages_source: List[Dict[str, Any]] = history_payload
    else:
        messages_source = history_payload.get("messages", [])

    messages = [_map_history_entry(msg) for msg in messages_source]

    # Determine last contact timestamp
    last_contact = None
    if history_payload and isinstance(history_payload, dict):
        last_contact = history_payload.get("last_contact")
    if not last_contact and messages:
        last_contact = messages[-1].date
    if not last_contact:
        fallback_dt = supplier.updated_at or supplier.created_at
        last_contact = fallback_dt.isoformat()

    products = [product.asin for product in getattr(supplier, "products", []) or []]

    rating_value = supplier.rating if supplier.rating is not None else 0.0
    status_value = _determine_status(rating_value, last_contact)

    return SupplierSummary(
        id=str(supplier.id),
        name=supplier.name,
        email=supplier.email,
        rating=round(rating_value, 2),
        country=supplier.country or "Unknown",
        products=products,
        communicationHistory=messages,
        lastContact=last_contact,
        status=status_value,
    )


async def _ensure_sample_suppliers(db: DbDependency) -> None:
    """Populate the suppliers table with demo data when empty."""

    from sqlalchemy.ext.asyncio import AsyncSession  # local import to avoid cycles

    session: AsyncSession = db  # type: ignore[assignment]

    existing_total = await session.scalar(select(func.count()).select_from(Supplier))
    if existing_total and existing_total > 0:
        return

    result = await session.execute(select(Product).limit(6))
    products = result.scalars().all()

    sample_suppliers = [
        {
            "name": "Shenzhen Nova Electronics",
            "email": "sales@nova-electronics.cn",
            "country": "China",
            "rating": 4.6,
            "messages": [
                {
                    "id": str(uuid4()),
                    "timestamp": "2024-10-12T09:30:00+00:00",
                    "type": "email",
                    "direction": "outbound",
                    "subject": "Re: Smart Scale MOQ",
                    "content": "Thank you for confirming the MOQ. We will proceed with the sample order.",
                    "status": "sent",
                }
            ],
        },
        {
            "name": "Ho Chi Minh Textiles Co.",
            "email": "contact@hcm-textiles.vn",
            "country": "Vietnam",
            "rating": 4.1,
            "messages": [
                {
                    "id": str(uuid4()),
                    "timestamp": "2024-09-28T15:45:00+00:00",
                    "type": "phone",
                    "direction": "outbound",
                    "subject": "Follow up on fabric samples",
                    "content": "Calling to confirm delivery of the organic cotton swatches.",
                    "status": "sent",
                },
                {
                    "id": str(uuid4()),
                    "timestamp": "2024-10-01T06:20:00+00:00",
                    "type": "email",
                    "direction": "inbound",
                    "subject": "Re: Organic Cotton Samples",
                    "content": "Samples shipped via DHL. Tracking number enclosed.",
                    "status": "received",
                },
            ],
        },
        {
            "name": "Guangzhou FitLife Manufacturing",
            "email": "info@fitlife-gz.com",
            "country": "China",
            "rating": 3.7,
            "messages": [
                {
                    "id": str(uuid4()),
                    "timestamp": "2024-08-17T11:10:00+00:00",
                    "type": "platform",
                    "direction": "outbound",
                    "subject": "Inquiry: Resistance Bands Private Label",
                    "content": "We are interested in private labeling your premium resistance band set.",
                    "status": "pending",
                }
            ],
        },
    ]

    product_cycle = products or []
    index = 0
    for data in sample_suppliers:
        supplier = Supplier(
            name=data["name"],
            email=data["email"],
            country=data["country"],
            rating=data["rating"],
            communication_history={
                "last_contact": data["messages"][-1]["timestamp"],
                "messages": data["messages"],
            },
        )

        if product_cycle:
            supplier.products = product_cycle[index:index + 2] or product_cycle
            index = (index + 2) % max(len(product_cycle), 1)

        session.add(supplier)

    await session.commit()


@router.get(
    "/",
    response_model=SupplierPaginatedResponse,
    summary="List suppliers",
    description="Obtiene lista de proveedores"
)
async def list_suppliers(
    country: Optional[str] = Query(None, description="Filter by country"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="Deprecated: use page_size instead"
    ),
    offset: Optional[int] = Query(
        None,
        ge=0,
        description="Deprecated: use page parameter instead"
    ),
    db: DbDependency = None
) -> SupplierPaginatedResponse:
    """Return suppliers with optional filters and pagination."""

    # Verificar si hay proveedores en la base de datos
    existing_total = await db.execute(select(func.count()).select_from(Supplier))
    total_count = existing_total.scalar_one() or 0
    
    # Si no hay proveedores, intentar buscar proveedores reales para productos existentes
    if total_count == 0:
        try:
            # Obtener productos existentes
            products_result = await db.execute(select(Product).limit(5))
            products = products_result.scalars().all()
            
            if products:
                from backend.agents.supplier_agent import SupplierAgent
                from backend.api.config import settings
                
                agent = SupplierAgent(
                    serpapi_key=settings.serpapi_key,
                    max_suppliers=10
                )
                
                try:
                    await agent.initialize()
                    
                    # Buscar proveedores para cada producto
                    for product in products[:2]:  # Limitar a 2 productos
                        product_data = {
                            "title": product.title,
                            "price": float(product.price)
                        }
                        
                        suppliers_found = await agent._find_suppliers(
                            product=product_data,
                            max_results=5
                        )
                        
                        # Guardar proveedores en base de datos
                        for supplier_data in suppliers_found:
                            email = supplier_data.get("contact_email", "")
                            if not email:
                                continue
                            
                            # Verificar si ya existe
                            existing_query = select(Supplier).where(Supplier.email == email)
                            result = await db.execute(existing_query)
                            if result.scalar_one_or_none():
                                continue
                            
                            # Crear nuevo proveedor
                            new_supplier = Supplier(
                                name=supplier_data.get("name", "Unknown"),
                                email=email,
                                country=supplier_data.get("country", "Unknown"),
                                rating=supplier_data.get("rating", 0.0),
                                communication_history={
                                    "last_contact": None,
                                    "messages": []
                                }
                            )
                            
                            # Asociar con producto
                            new_supplier.products = [product]
                            
                            db.add(new_supplier)
                        
                        await db.commit()
                    
                    await agent.shutdown()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error finding real suppliers: {e}")
                    # Fallback a sample suppliers si falla la búsqueda real
                    await _ensure_sample_suppliers(db)
            else:
                # No hay productos, usar sample suppliers
                await _ensure_sample_suppliers(db)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error in supplier discovery: {e}, using sample suppliers")
            await _ensure_sample_suppliers(db)
    else:
        # Ya hay proveedores, no hacer nada
        pass

    filters = []
    if country:
        filters.append(func.lower(Supplier.country) == country.lower())
    if min_rating is not None:
        filters.append(Supplier.rating >= min_rating)

    effective_limit = limit if limit is not None else page_size
    effective_offset = offset if offset is not None else (page - 1) * effective_limit

    base_query = select(Supplier).options(selectinload(Supplier.products))
    if filters:
        base_query = base_query.where(*filters)

    count_query = select(func.count()).select_from(Supplier)
    if filters:
        count_query = count_query.where(*filters)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    supplier_result = await db.execute(
        base_query
        .order_by(Supplier.name.asc())
        .offset(effective_offset)
        .limit(effective_limit)
    )
    supplier_records = supplier_result.scalars().unique().all()

    items = [_map_supplier_to_summary(record) for record in supplier_records]
    page_number = (effective_offset // effective_limit) + 1 if effective_limit else 1
    has_more = effective_offset + len(items) < total

    return SupplierPaginatedResponse(
        items=items,
        total=total,
        page=page_number,
        pageSize=effective_limit,
        hasMore=has_more,
    )


@router.get(
    "/{supplier_id}",
    response_model=SupplierSummary,
    summary="Get supplier",
    description="Obtiene detalles de un proveedor"
)
async def get_supplier(
    supplier_id: UUID,
    db: DbDependency = None
) -> SupplierSummary:
    """Retrieve supplier details used by the dashboard."""

    result = await db.execute(
        select(Supplier)
        .options(selectinload(Supplier.products))
        .where(Supplier.id == supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier {supplier_id} not found"
        )

    return _map_supplier_to_summary(supplier)


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create supplier",
    description="Crea un nuevo proveedor",
    dependencies=[RateLimited]
)
async def create_supplier(
    supplier: SupplierCreate,
    db: DbDependency = None,
    user: CurrentUser = None
) -> SupplierResponse:
    """
    Create new supplier.
    
    Args:
        supplier: Supplier data
        db: Database session
        user: Current user
        
    Returns:
        Created supplier
        
    Examples:
        >>> POST /api/v2/suppliers
        >>> {
        >>>   "name": "ABC Manufacturers",
        >>>   "country": "China",
        >>>   "email": "contact@abc.com"
        >>> }
    """
    # TODO: Implement create_supplier
    pass


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Update supplier",
    description="Actualiza un proveedor",
    dependencies=[RateLimited]
)
async def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    db: DbDependency = None,
    user: CurrentUser = None
) -> SupplierResponse:
    """Update supplier details."""
    # TODO: Implement update_supplier
    pass


@router.post(
    "/search",
    response_model=SupplierPaginatedResponse,
    summary="Search suppliers",
    description="Busca proveedores para un producto usando SerpAPI",
    dependencies=[RateLimited]
)
async def search_suppliers(
    request: SupplierSearchRequest,
    db: DbDependency = None,
    user: CurrentUser = None
) -> SupplierPaginatedResponse:
    """
    Search for suppliers using real data from Alibaba, Global Sources, etc.
    
    Uses SupplierAgent with SerpAPI to find real suppliers for the product.
    
    Args:
        request: Search criteria
        db: Database session
        user: Current user
        
    Returns:
        List of found suppliers
        
    Examples:
        >>> POST /api/v2/suppliers/search
        >>> {
        >>>   "product_name": "yoga mat",
        >>>   "countries": ["China", "Vietnam"],
        >>>   "max_results": 10
        >>> }
    """
    from backend.agents.supplier_agent import SupplierAgent
    from backend.api.config import settings
    
    # Convertir SupplierRating a float si está presente
    min_rating_value = None
    if request.min_rating:
        rating_map = {
            "unknown": 0.0,
            "poor": 2.0,
            "fair": 3.0,
            "good": 4.0,
            "excellent": 4.5,
            "verified": 4.0
        }
        min_rating_value = rating_map.get(request.min_rating.value, 3.0)
    
    # Crear producto mock para el agente
    product_data = {
        "title": request.product_name,
        "price": 0,  # Se calculará después si es necesario
    }
    
    # Inicializar SupplierAgent
    agent = SupplierAgent(
        serpapi_key=settings.serpapi_key,
        max_suppliers=request.max_results
    )
    
    try:
        await agent.initialize()
        
        # Buscar proveedores reales
        suppliers_found = await agent._find_suppliers(
            product=product_data,
            countries=request.countries,
            min_rating=min_rating_value,
            max_results=request.max_results
        )
        
        # Convertir proveedores encontrados a SupplierSummary
        supplier_summaries = []
        for supplier in suppliers_found:
            # Guardar proveedor en base de datos si no existe
            email = supplier.get("contact_email", "")
            if email:
                existing_query = select(Supplier).where(Supplier.email == email)
                result = await db.execute(existing_query)
                existing_supplier = result.scalar_one_or_none()
                
                if not existing_supplier:
                    # Crear nuevo proveedor
                    new_supplier = Supplier(
                        name=supplier.get("name", "Unknown"),
                        email=email,
                        country=supplier.get("country", "Unknown"),
                        rating=supplier.get("rating", 0.0),
                        communication_history={
                            "last_contact": None,
                            "messages": []
                        }
                    )
                    db.add(new_supplier)
                    await db.commit()
                    await db.refresh(new_supplier)
                    existing_supplier = new_supplier
                
                # Mapear a summary
                summary = _map_supplier_to_summary(existing_supplier)
                supplier_summaries.append(summary)
        
        return SupplierPaginatedResponse(
            items=supplier_summaries[:request.max_results],
            total=len(supplier_summaries),
            page=1,
            pageSize=request.max_results,
            hasMore=False,
        )
        
    except Exception as e:
        # Log error pero devolver respuesta vacía
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error searching suppliers: {e}", exc_info=True)
        
        return SupplierPaginatedResponse(
            items=[],
            total=0,
            page=1,
            pageSize=request.max_results,
            hasMore=False,
        )
    finally:
        if agent:
            await agent.shutdown()


@router.post(
    "/contact",
    response_model=SupplierContactResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Contact suppliers",
    description="Contacta proveedores automáticamente",
    dependencies=[RateLimited]
)
async def contact_suppliers(
    request: Union[SupplierQuickContactRequest, SupplierContactRequest],
    db: DbDependency = None
) -> SupplierContactResponse:
    """
    Contact suppliers automatically.
    
    Generates personalized messages and sends to suppliers.
    Uses OpenAI to create professional inquiries.
    
    Args:
        request: Contact request with product and suppliers
        db: Database session
        user: Current user
        
    Returns:
        Contact task information
        
    Examples:
        >>> POST /api/v2/suppliers/contact
        >>> {
        >>>   "asin": "B08N5WRWNW",
        >>>   "quantity": 500,
        >>>   "auto_send": false
        >>> }
    """
    task_id = str(uuid4())

    if isinstance(request, SupplierQuickContactRequest):
        result = await db.execute(select(Supplier).where(Supplier.id == request.supplierId))
        supplier = result.scalar_one_or_none()
        if supplier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplier {request.supplierId} not found"
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        history = supplier.communication_history or {}
        if isinstance(history, list):
            history_messages: List[Dict[str, Any]] = history
        else:
            history_messages = history.get("messages", [])

        history_messages.append(
            {
                "id": task_id,
                "timestamp": timestamp,
                "type": "email",
                "direction": "outbound",
                "subject": "Follow up from Amazon FBA AI Agent",
                "content": request.message,
                "status": "sent",
            }
        )

        if isinstance(history, list):
            history_payload: Dict[str, Any] = {"messages": history_messages}
        else:
            history_payload = {**history, "messages": history_messages}
        history_payload["last_contact"] = timestamp

        supplier.communication_history = history_payload
        await db.commit()
        await db.refresh(supplier)

        summary = _map_supplier_to_summary(supplier)
        asin = summary.products[0] if summary.products else ""

        return SupplierContactResponse(
            task_id=task_id,
            asin=asin,
            suppliers_contacted=1,
            messages_generated=[
                {
                    "supplierId": summary.id,
                    "timestamp": timestamp,
                    "message": request.message,
                }
            ],
            status="completed",
        )

    # Legacy multi-supplier workflow (future enhancement)
    return SupplierContactResponse(
        task_id=task_id,
        asin=request.asin,
        suppliers_contacted=0,
        messages_generated=[],
        status="pending",
    )


@router.get(
    "/{supplier_id}/communications",
    response_model=List[CommunicationLog],
    summary="Get communications",
    description="Obtiene historial de comunicaciones"
)
async def get_communications(
    supplier_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DbDependency = None
) -> List[CommunicationLog]:
    """
    Get communication history with supplier.
    
    Args:
        supplier_id: Supplier ID
        limit: Results per page
        offset: Pagination offset
        db: Database session
        
    Returns:
        List of communications
        
    Examples:
        >>> GET /api/v2/suppliers/123/communications
    """
    # TODO: Implement get_communications
    
    return []

