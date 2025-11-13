#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Wrappers con Cache Automatico
Wrappers para todas las APIs externas con cache integrado
"""

import json
import sys
import os
import asyncio
from typing import Dict, List, Optional, Any

# Agregar directorio raiz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache_manager import cache

DEFAULT_TREND_KEYWORDS = [
    "trending",
    "best seller",
    "popular",
    "new arrival",
    "top rated",
]

# ============================================================================
# SERPAPI WRAPPER
# ============================================================================

def load_config() -> Dict:
    """Carga configuracion del proyecto."""
    config = {}
    
    # Primero intentar cargar desde config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        pass
    
    # Sobrescribir con variables de entorno si existen
    import os
    if os.getenv('SERPAPI_KEY'):
        config['serpapi_key'] = os.getenv('SERPAPI_KEY')
    if os.getenv('OPENAI_API_KEY'):
        config['openai_api_key'] = os.getenv('OPENAI_API_KEY')
    
    return config


@cache.cached(ttl=3600, key_prefix="serpapi_amazon")
def search_amazon_cached(keyword: str, max_results: int = 10, page: int = 1) -> List[Dict]:
    """
    Busca productos en Amazon con SerpAPI - CACHEADO.
    
    Cache TTL: 1 hora (resultados cambian poco en 1 hora)
    Ahorro: ~90% de llamadas a API
    
    Args:
        keyword: Palabra clave de busqueda
        max_results: Maximo numero de resultados
        page: Numero de pagina
        
    Returns:
        Lista de productos encontrados
    """
    try:
        from serpapi.google_search import GoogleSearch
    except ImportError:
        print("ERROR: serpapi no instalado. pip install google-search-results")
        return []
    
    config = load_config()
    serpapi_key = config.get("serpapi_key", "")
    
    if not serpapi_key:
        print("ERROR: serpapi_key no configurada en config.json")
        return []
    
    params = {
        "api_key": serpapi_key,
        "engine": "amazon",
        "amazon_domain": "amazon.com",
        "k": keyword,  # Amazon usa 'k' no 'q' para el query
        "page": str(page)
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # DEBUG: Print response keys and error if present
        print(f"SerpAPI Response Keys: {list(results.keys())}")
        if 'error' in results:
            print(f"SerpAPI ERROR: {results['error']}")
            return []
        
        products = []
        if "organic_results" in results:
            print(f"SerpAPI: Found {len(results['organic_results'])} organic results")
            for item in results["organic_results"][:max_results]:
                # DEBUG: Print first product structure
                if len(products) == 0:
                    print(f"DEBUG First product keys: {list(item.keys())}")
                    print(f"DEBUG First product sample: title={item.get('title','N/A')[:50]}, price={item.get('price')}, rating={item.get('rating')}")
                
                products.append({
                    'title': item.get('title', ''),
                    'asin': item.get('asin', ''),
                    'link': item.get('link', ''),
                    'price': item.get('price', ''),
                    'rating': item.get('rating', 0),
                    'reviews': item.get('reviews', 0),
                    'reviews_count': item.get('reviews_count', item.get('reviews', 0)),
                    'position': item.get('position', 0),
                })
        elif "shopping_results" in results:
            print(f"SerpAPI: Found {len(results['shopping_results'])} shopping results")
            for item in results["shopping_results"][:max_results]:
                products.append({
                    'title': item.get('title', ''),
                    'asin': item.get('asin', ''),
                    'link': item.get('link', ''),
                    'price': item.get('price', ''),
                    'rating': item.get('rating', 0),
                    'reviews': item.get('reviews', 0),
                    'position': item.get('position', 0),
                })
        else:
            print(f"SerpAPI: No products found in response")
        
        print(f"SerpAPI: Encontrados {len(products)} productos para '{keyword}'")
        return products
        
    except Exception as e:
        import traceback
        print(f"ERROR en SerpAPI: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return []


@cache.cached(ttl=3600, key_prefix="serpapi_asin")
def get_amazon_product_by_asin_cached(asin: str) -> Optional[Dict]:
    """
    Obtiene informacion de producto Amazon por ASIN - CACHEADO.
    
    Cache TTL: 1 hora
    
    Args:
        asin: ASIN del producto
        
    Returns:
        Dict con informacion del producto o None
    """
    try:
        from serpapi import GoogleSearch
    except ImportError:
        return None
    
    config = load_config()
    serpapi_key = config.get("serpapi_key", "")
    
    if not serpapi_key:
        return None
    
    params = {
        "api_key": serpapi_key,
        "engine": "amazon_product",
        "amazon_domain": "amazon.com",
        "asin": asin
    }
    
    try:
        search = GoogleSearch(params)
        result = search.get_dict()
        
        if "product_results" in result:
            return result["product_results"]
        
        return None
        
    except Exception as e:
        print(f"ERROR obteniendo ASIN {asin}: {e}")
        return None


# ============================================================================
# OPENAI WRAPPER
# ============================================================================

@cache.cached(ttl=86400, key_prefix="openai_message")  # 24 horas
def generate_supplier_message_cached(product_title: str, asin: str, units: int) -> str:
    """
    Genera mensaje para proveedor con OpenAI - CACHEADO.
    
    Cache TTL: 24 horas (mensajes similares no necesitan regenerarse)
    Ahorro: ~95% de llamadas a API
    
    Args:
        product_title: Titulo del producto
        asin: ASIN del producto
        units: Cantidad de unidades
        
    Returns:
        Mensaje generado
    """
    try:
        import openai
    except ImportError:
        return f"Dear Supplier,\n\nWe are interested in {units} units of {product_title}.\n\nBest regards"
    
    config = load_config()
    openai_key = config.get("openai_key", "")
    
    if not openai_key:
        return f"Dear Supplier,\n\nWe are interested in {units} units of {product_title}.\n\nBest regards"
    
    openai.api_key = openai_key
    
    prompt = f"""Generate a professional message in English to request a quote from a supplier.

Product: {product_title}
ASIN: {asin}
Quantity: {units} units

The message should include:
- Professional greeting
- Interest in the product
- Request for MOQ, unit price, and delivery time
- Polite closing
"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"ERROR en OpenAI: {e}")
        return f"Dear Supplier,\n\nWe are interested in {units} units of {product_title} (ASIN: {asin}).\n\nPlease provide your best quote including MOQ, unit price, and delivery time.\n\nBest regards"


# ============================================================================
# GOOGLE TRENDS WRAPPER
# ============================================================================

@cache.cached(ttl=21600, key_prefix="google_trends")  # 6 horas
def get_trend_data_cached(keyword: str, timeframe: str = "today 3-m", geo: str = "US") -> Optional[Dict]:
    """
    Obtiene datos de Google Trends - CACHEADO.
    
    Cache TTL: 6 horas (tendencias cambian lento)
    Ahorro: ~80% de llamadas
    
    Args:
        keyword: Palabra clave
        timeframe: Periodo de tiempo
        geo: Pais
        
    Returns:
        Datos de tendencias o None
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return None
    
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo)
        
        interest_over_time = pytrends.interest_over_time()
        
        if not interest_over_time.empty:
            return {
                'keyword': keyword,
                'max_interest': int(interest_over_time[keyword].max()),
                'avg_interest': float(interest_over_time[keyword].mean()),
                'current_interest': int(interest_over_time[keyword].iloc[-1]),
                'data': interest_over_time[keyword].tolist(),
                'timeframe': timeframe,
                'geo': geo
            }
        
        return None
        
    except Exception as e:
        print(f"ERROR en Google Trends: {e}")
        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def invalidate_cache_for_keyword(keyword: str):
    """Invalida cache para un keyword especifico."""
    cache.clear(f"serpapi_amazon:*{keyword}*")
    cache.clear(f"google_trends:*{keyword}*")
    print(f"Cache invalidado para keyword: {keyword}")


def get_cache_statistics() -> Dict[str, Any]:
    """Obtiene estadisticas del cache."""
    return cache.get_stats()


def clear_all_api_cache():
    """Limpia todo el cache de APIs."""
    cache.clear("serpapi*")
    cache.clear("openai*")
    cache.clear("google_trends*")
    print("Todo el cache de APIs limpiado")


# ============================================================================
# WRAPPER CLASSES (for compatibility with agents)
# ============================================================================

class SerpAPIWrapper:
    """Wrapper class for SerpAPI functionality."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SerpAPI wrapper.
        
        Args:
            api_key: Optional API key (if None, uses config.json)
        """
        self.api_key = api_key
    
    async def search_amazon(
        self,
        keyword: Optional[str] = None,
        *,
        query: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search Amazon products accepting ``keyword`` or ``query`` aliases."""

        search_term = keyword or query
        if not search_term:
            raise ValueError("A search term must be provided via 'keyword' or 'query'.")

        return await asyncio.to_thread(
            search_amazon_cached,
            search_term,
            max_results,
        )
    
    async def get_product_by_asin(self, asin: str) -> Optional[Dict]:
        """
        Get product by ASIN.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Product data or None
        """
        return await asyncio.to_thread(get_amazon_product_by_asin_cached, asin)


class GoogleTrendsWrapper:
    """Wrapper class for Google Trends functionality."""
    
    def __init__(self):
        """Initialize Google Trends wrapper."""
        pass
    
    async def get_trend_data(self, keyword: str, timeframe: str = "today 3-m", geo: str = "US") -> Optional[Dict]:
        """
        Get trend data for keyword.
        
        Args:
            keyword: Search keyword
            timeframe: Time period
            geo: Country code
            
        Returns:
            Trend data or None
        """
        return await asyncio.to_thread(
            get_trend_data_cached,
            keyword,
            timeframe,
            geo,
        )

    async def get_trending_searches(self, region: str = "US", limit: int = 10) -> List[str]:
        """Return trending search keywords for the given region."""

        try:
            from pytrends.request import TrendReq
        except ImportError:
            return DEFAULT_TREND_KEYWORDS[:limit]

        try:
            def _fetch_trending() -> List[str]:
                pytrends = TrendReq(hl="en-US", tz=360)
                trending = pytrends.trending_searches(pn=region)
                if trending is None or trending.empty:
                    return []
                return trending.iloc[:, 0].tolist()

            keywords = await asyncio.to_thread(_fetch_trending)
        except Exception:
            keywords = []

        if not keywords:
            keywords = DEFAULT_TREND_KEYWORDS

        return keywords[:limit]


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DEMO: API Wrappers con Cache")
    print("=" * 60)
    
    # Test SerpAPI
    print("\n1. Busqueda en Amazon (primera vez - llamada real):")
    import time
    start = time.time()
    products1 = search_amazon_cached("yoga mat", max_results=5)
    elapsed1 = time.time() - start
    print(f"   Tiempo: {elapsed1:.2f}s")
    print(f"   Productos: {len(products1)}")
    
    print("\n2. Misma busqueda (cache hit - instantaneo):")
    start = time.time()
    products2 = search_amazon_cached("yoga mat", max_results=5)
    elapsed2 = time.time() - start
    print(f"   Tiempo: {elapsed2:.2f}s")
    print(f"   Productos: {len(products2)}")
    
    # Stats
    print("\n3. Estadisticas del cache:")
    stats = get_cache_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\nDemo completado!")

