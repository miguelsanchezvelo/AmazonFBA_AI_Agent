#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discovery Agent - Descubre productos rentables usando tendencias y análisis de mercado.

Responsabilidades:
- Descubrir productos trending
- Analizar oportunidades en Amazon
- Filtrar por criterios de rentabilidad
- Publicar eventos ProductDiscovered
"""

from typing import Any, Dict, List, Optional, Set
from decimal import Decimal
import asyncio
from functools import wraps
import time

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService
from core.api_wrappers import SerpAPIWrapper, GoogleTrendsWrapper
from backend.database.session import get_db
from backend.database.repositories import ProductRepository
from backend.models.product import ProductCreate


def retry_with_backoff(retries: int = 3, backoff_factor: float = 2.0, initial_delay: float = 1.0):
    """
    Decorator para reintentar funciones async con exponential backoff.
    
    Args:
        retries: Número de reintentos
        backoff_factor: Factor de multiplicación para el delay
        initial_delay: Delay inicial en segundos
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries:
                        # Log warning y esperar antes de reintentar
                        if hasattr(args[0], 'logger'):
                            args[0].logger.warning(
                                f"Attempt {attempt + 1}/{retries + 1} failed for {func.__name__}: {e}. "
                                f"Retrying in {delay:.1f}s..."
                            )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        # Último intento falló, propagar excepción
                        if hasattr(args[0], 'logger'):
                            args[0].logger.error(
                                f"All {retries + 1} attempts failed for {func.__name__}: {e}"
                            )
                        raise last_exception
            
            raise last_exception
        
        return wrapper
    return decorator


class DiscoveryAgent(BaseAgent):
    """
    Agent especializado en descubrir productos rentables.
    
    Subscribe a:
    - TrendDiscoveryRequested: Solicitud para descubrir nuevos productos
    
    Publica:
    - ProductDiscovered: Producto rentable descubierto
    
    Usa:
    - SerpAPI para búsqueda en Amazon
    - Google Trends para análisis de tendencias
    - Caché de 1h para reducir costos
    
    Examples:
        >>> agent = DiscoveryAgent()
        >>> await agent.start()
        >>> 
        >>> # Procesar evento
        >>> event = {
        ...     "event_type": "TrendDiscoveryRequested",
        ...     "payload": {"budget": 3000, "category": "fitness"}
        ... }
        >>> result = await agent.process_event(event)
    """
    
    def __init__(
        self,
        serpapi_key: Optional[str] = None,
        cache_ttl: int = 3600,
        min_rating: float = 4.0,
        max_price: float = 5000
    ):
        """
        Inicializa el Discovery Agent.
        
        Args:
            serpapi_key: API key de SerpAPI (None = cargar de config)
            cache_ttl: TTL del caché en segundos (default: 1 hora)
            min_rating: Rating mínimo de productos (default: 4.0)
            max_price: Precio máximo de productos (default: 5000)
        """
        super().__init__(
            name="DiscoveryAgent",
            subscribed_events={"TrendDiscoveryRequested"}
        )
        
        self.serpapi_key = serpapi_key
        self.cache_ttl = cache_ttl
        self.min_rating = min_rating
        self.max_price = max_price
        
        # Servicios (se inicializan en initialize())
        self.cache: Optional[CacheService] = None
        self.serp_api: Optional[SerpAPIWrapper] = None
        self.trends_api: Optional[GoogleTrendsWrapper] = None
    
    async def initialize(self) -> None:
        """
        Inicializa el agent y sus dependencias.
        
        Configura:
        - Cache manager
        - SerpAPI wrapper
        - Google Trends wrapper
        """
        self.logger.info(f"Initializing {self.name}...")
        
        try:
            # Inicializar caché
            self.cache = CacheService()
            await self.cache.connect()
            self.logger.info("Cache connected")
            
            # Inicializar API wrappers
            self.serp_api = SerpAPIWrapper(api_key=self.serpapi_key)
            self.trends_api = GoogleTrendsWrapper()
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento de descubrimiento de productos.
        
        Args:
            event: Evento con:
                - payload.budget: Presupuesto máximo
                - payload.categories: Lista de categorías/keywords a buscar (opcional)
                - payload.category: Categoría única (opcional, legacy)
        
        Returns:
            Evento ProductDiscovered con productos encontrados
        """
        payload = event.get("payload", {})
        budget = payload.get("budget", self.max_price)
        
        # Soportar tanto 'categories' (nuevo) como 'category' (legacy)
        categories = payload.get("categories", [])
        if not categories:
            category = payload.get("category", "")
            categories = [category] if category else []
        
        self.logger.info(
            f"Discovering products (budget: ${budget}, categories: {categories})"
        )
        
        try:
            # 1. Si se proporcionan categorías específicas, usarlas directamente como keywords
            # Si no, obtener trending keywords
            if categories:
                search_keywords = categories
                self.logger.info(f"Using {len(search_keywords)} provided keywords/categories")
            else:
                search_keywords = await self._get_trending_keywords("")
                self.logger.info(f"Found {len(search_keywords)} trending keywords")
            
            # 2. Buscar productos para cada keyword
            all_products = []
            for keyword in search_keywords[:10]:  # Limitar a top 10 para no gastar mucho
                products = await self._search_products(keyword, budget)
                all_products.extend(products)
            
            # 4. Filtrar y rankear productos
            viable_products = self._filter_products(all_products)
            ranked_products = self._rank_products(viable_products)
            
            self.logger.info(f"Discovered {len(ranked_products)} viable products")
            
            # 5. Guardar productos en la base de datos
            saved_count = 0
            if ranked_products:
                try:
                    saved_count = await self._save_products_to_db(ranked_products[:20])
                    self.logger.info(f"Saved {saved_count} products to database")
                except Exception as e:
                    self.logger.error(f"Error saving products to DB: {e}")
            
            # 6. Actualizar task status en caché
            task_id = payload.get("task_id")
            if task_id and self.cache:
                try:
                    await self.cache.set(
                        f"discovery_task:{task_id}",
                        {
                            "task_id": task_id,
                            "status": "completed" if ranked_products else "completed_no_results",
                            "products_found": len(ranked_products),
                            "products_saved": saved_count,
                            "products": ranked_products[:20],  # Top 20
                            "message": f"Found {len(ranked_products)} products, saved {saved_count} to database"
                        },
                        ttl=3600
                    )
                    self.logger.info(f"Updated task status: {task_id}")
                except Exception as e:
                    self.logger.error(f"Error updating task status: {e}")
            
            # 6. Crear evento(s) para cada producto descubierto
            if ranked_products:
                # Retornar el mejor producto
                top_product = ranked_products[0]
                
                return Event(
                    event_type="ProductDiscovered",
                    payload={
                        "task_id": task_id,
                        "product": top_product,
                        "all_products": ranked_products[:10],  # Top 10
                        "discovery_metadata": {
                            "trending_keywords": search_keywords,
                            "total_found": len(all_products),
                            "viable_count": len(viable_products)
                        }
                    },
                    source_agent=self.name
                ).to_dict()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error discovering products: {e}", exc_info=True)
            raise
    
    async def _save_products_to_db(self, products: List[Dict[str, Any]]) -> int:
        """
        Guarda productos descubiertos en la base de datos.
        
        Args:
            products: Lista de productos a guardar
            
        Returns:
            Número de productos guardados exitosamente
        """
        saved_count = 0
        
        try:
            async for session in get_db():
                repo = ProductRepository(session)
                
                for product in products:
                    try:
                        # Verificar si el producto ya existe
                        asin = product.get("asin")
                        if not asin:
                            continue
                        
                        existing = await repo.get_by_asin(asin)
                        if existing:
                            self.logger.debug(f"Product {asin} already exists, skipping")
                            continue
                        
                        # Preparar datos para crear el producto
                        product_data = {
                            "asin": asin,
                            "title": product.get("title", ""),
                            "price": Decimal(str(product.get("price", 0))),
                            "rating": float(product.get("rating", 0)),
                            "reviews": int(product.get("reviews_count", 0) or product.get("reviews", 0)),  # ORM field is 'reviews'
                            "category": product.get("category", "fitness"),
                            "bsr": product.get("bsr"),
                            "image_url": product.get("thumbnail"),
                        }
                        
                        # Crear producto en la BD
                        await repo.create(product_data)
                        saved_count += 1
                        self.logger.debug(f"Saved product {asin} to database")
                        
                    except Exception as e:
                        self.logger.warning(f"Error saving product {product.get('asin', 'unknown')}: {e}")
                        continue
                
                # Commit the session
                await session.commit()
                
        except Exception as e:
            self.logger.error(f"Database error while saving products: {e}")
        
        return saved_count
    
    async def shutdown(self) -> None:
        """
        Apaga el agent limpiamente.
        
        Cierra:
        - Conexiones de caché
        - API wrappers
        """
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            if self.cache:
                await self.cache.disconnect()
                self.logger.info("Cache disconnected")
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def _get_trending_keywords(self, category: str = "") -> List[str]:
        """
        Obtiene keywords trending usando Google Trends.
        
        Args:
            category: Categoría para filtrar tendencias
        
        Returns:
            Lista de keywords trending
        """
        cache_key = f"trending_keywords:{category}"
        
        # Intentar obtener del caché
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                self.logger.debug(f"Cache hit for trending keywords: {category}")
                return cached
        
        try:
            # Obtener de Google Trends
            if self.trends_api:
                keywords = await self.trends_api.get_trending_searches(
                    region='US'
                )
            else:
                # Fallback a keywords genéricos
                keywords = self._get_default_keywords(category)
            
            # Guardar en caché
            if self.cache:
                await self.cache.set(cache_key, keywords, ttl=self.cache_ttl)
            
            return keywords[:10]  # Top 10
            
        except Exception as e:
            self.logger.warning(f"Error getting trends: {e}, using defaults")
            return self._get_default_keywords(category)
    
    def _get_default_keywords(self, category: str = "") -> List[str]:
        """
        Retorna keywords por defecto si Google Trends falla.
        
        Args:
            category: Categoría
        
        Returns:
            Lista de keywords por defecto
        """
        defaults = {
            "fitness": ["yoga mat", "resistance bands", "foam roller", "dumbbells"],
            "home": ["organizer", "storage", "kitchen gadget", "home decor"],
            "tech": ["phone case", "charger", "earbuds", "cable organizer"],
            "beauty": ["skincare", "makeup brush", "face mask", "hair care"],
            "": ["trending", "best seller", "popular", "new arrival"]
        }
        
        return defaults.get(category.lower(), defaults[""])
    
    @retry_with_backoff(retries=3, backoff_factor=2.0, initial_delay=1.0)
    async def _search_products(self, keyword: str, max_price: float) -> List[Dict[str, Any]]:
        """
        Busca productos en Amazon usando SerpAPI con retry logic.
        
        Args:
            keyword: Palabra clave a buscar
            max_price: Precio máximo
        
        Returns:
            Lista de productos encontrados
            
        Note:
            Decorated with @retry_with_backoff for automatic retries on API failures
        """
        cache_key = f"products:{keyword}:{max_price}"
        
        # Intentar obtener del caché
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                self.logger.debug(f"Cache hit for products: {keyword}")
                return cached
        
        try:
            if self.serp_api:
                # Buscar en Amazon
                products = await self.serp_api.search_amazon(
                    query=keyword,
                    max_results=20
                )
                # El wrapper ya retorna lista parseada, no necesitamos _parse_serp_results
            else:
                # Modo desarrollo sin API
                products = self._generate_mock_products(keyword, max_price)
            
            # Guardar en caché
            if self.cache:
                await self.cache.set(cache_key, products, ttl=self.cache_ttl)
            
            return products
            
        except Exception as e:
            self.logger.warning(f"Error searching products for '{keyword}': {e}")
            return []
    
    def _parse_serp_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea resultados de SerpAPI a formato interno.
        
        Args:
            results: Resultados crudos de SerpAPI
        
        Returns:
            Lista de productos parseados
        """
        products = []
        
        for item in results.get("organic_results", []):
            try:
                product = {
                    "asin": item.get("asin", ""),
                    "title": item.get("title", ""),
                    "price": float(item.get("price", {}).get("value", 0)),
                    "rating": float(item.get("rating", 0)),
                    "reviews_count": int(item.get("reviews", 0)),
                    "thumbnail": item.get("thumbnail", ""),
                    "link": item.get("link", "")
                }
                
                if product["asin"] and product["price"] > 0:
                    products.append(product)
                    
            except Exception as e:
                self.logger.debug(f"Error parsing product: {e}")
                continue
        
        return products
    
    def _generate_mock_products(self, keyword: str, max_price: float) -> List[Dict[str, Any]]:
        """
        Genera productos mock para desarrollo/testing.
        
        Args:
            keyword: Keyword
            max_price: Precio máximo
        
        Returns:
            Lista de productos mock
        """
        import random
        
        products = []
        for i in range(5):
            products.append({
                "asin": f"B08{random.randint(100000, 999999)}",
                "title": f"{keyword.title()} - Product {i+1}",
                "price": random.uniform(10, min(max_price, 100)),
                "rating": random.uniform(3.5, 5.0),
                "reviews_count": random.randint(10, 5000),
                "thumbnail": "",
                "link": ""
            })
        
        return products
    
    def _filter_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra productos por criterios de viabilidad.
        
        Args:
            products: Lista de productos
        
        Returns:
            Productos que cumplen criterios
        """
        viable = []
        self.logger.info(f"Filtering {len(products)} products...")
        
        for product in products:
            try:
                # Convertir price a float si es string
                price = product.get("price", 0)
                if isinstance(price, str):
                    # Eliminar símbolos de moneda y comas
                    price = price.replace("$", "").replace(",", "").strip()
                    price = float(price) if price else 0
                else:
                    price = float(price) if price else 0
                
                if len(viable) == 0:  # DEBUG: Log first product details
                    self.logger.info(f"DEBUG first product: price={price}, max={self.max_price}, rating={product.get('rating')}, min_rating={self.min_rating}")
                
                # Convertir rating a float si es string
                rating = product.get("rating", 0)
                if isinstance(rating, str):
                    rating = float(rating) if rating else 0
                else:
                    rating = float(rating) if rating else 0
                
                # Convertir reviews a int si es string (SerpAPI usa "reviews", no "reviews_count")
                reviews = product.get("reviews", 0)
                if isinstance(reviews, str):
                    reviews = reviews.replace(",", "").strip()
                    reviews = int(reviews) if reviews else 0
                else:
                    reviews = int(reviews) if reviews else 0
                
                # Actualizar el producto con valores convertidos
                product["price"] = price
                product["rating"] = rating
                product["reviews_count"] = reviews
                
                # Criterios de filtrado (relajados para debugging)
                asin = product.get("asin")
                if not asin:
                    self.logger.debug(f"Product without ASIN, skipping")
                    continue
                    
                if price <= 0:
                    self.logger.debug(f"Product {asin} has invalid price: {price}")
                    continue
                    
                if price > self.max_price:
                    self.logger.debug(f"Product {asin} price too high: {price} > {self.max_price}")
                    continue
                    
                if rating < self.min_rating:
                    self.logger.debug(f"Product {asin} rating too low: {rating} < {self.min_rating}")
                    continue
                
                # Requiere 10+ reviews para validar demanda real (no solo inicial)
                if reviews < 10:
                    self.logger.debug(f"Product {asin} has insufficient reviews: {reviews} (minimum 10 required)")
                    continue
                
                viable.append(product)
                self.logger.info(f"✓ Product {asin} is VIABLE: price=${price}, rating={rating}, reviews={reviews}")
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error filtering product {product.get('asin', 'unknown')}: {e}")
                continue
        
        return viable
    
    def _rank_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rankea productos por potencial de rentabilidad.
        
        Criterios:
        - Rating alto
        - Muchas reviews (demanda)
        - Precio medio (margen)
        
        Args:
            products: Lista de productos
        
        Returns:
            Productos ordenados por score
        """
        def calculate_score(product: Dict[str, Any]) -> float:
            """Calcula score de rentabilidad."""
            rating = product.get("rating", 0)
            reviews = product.get("reviews_count", 0)
            price = product.get("price", 0)
            
            # Score = rating * log(reviews) * price_factor
            import math
            score = (
                rating * 
                math.log10(max(reviews, 10)) *
                (1 if price < 50 else 0.5)  # Preferir precio medio
            )
            
            return score
        
        # Calcular scores y ordenar
        for product in products:
            product["opportunity_score"] = calculate_score(product)
        
        ranked = sorted(
            products,
            key=lambda p: p.get("opportunity_score", 0),
            reverse=True
        )
        
        return ranked

