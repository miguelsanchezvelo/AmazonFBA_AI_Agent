#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supplier Agent - Gestiona búsqueda y contacto con proveedores.

Responsabilidades:
- Buscar proveedores potenciales
- Generar mensajes de contacto personalizados
- Trackear comunicaciones
- Comparar cotizaciones
- Publicar eventos SupplierContactGenerated
"""

from typing import Any, Dict, List, Optional, Set
import asyncio
from datetime import datetime
import json

from backend.agents.base_agent import BaseAgent
from backend.core.event_bus import Event
from backend.services.cache_service import CacheService

# Claude Skills (preferred for AI generation)
try:
    from backend.services.claude_service import ClaudeService, get_skill_manager
    from backend.services.claude_skills import SupplierMessageSkill, SupplierEvaluationSkill
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude service no disponible.")

# OpenAI (fallback - being deprecated)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI no disponible. Instalar con: pip install openai")

try:
    from serpapi.google_search import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    print("⚠️  SerpAPI no disponible. Instalar con: pip install google-search-results")


class SupplierAgent(BaseAgent):
    """
    Agent especializado en gestión de proveedores.
    
    Subscribe a:
    - AnalysisComplete: Análisis completado (si GO, buscar proveedores)
    
    Publica:
    - SupplierContactGenerated: Contactos de proveedores generados
    
    Usa:
    - Claude Skills para generar mensajes personalizados (preferred)
    - OpenAI como fallback (deprecated)
    - SerpAPI para búsqueda de proveedores reales
    - Templates de mensajes como último recurso
    
    Examples:
        >>> agent = SupplierAgent()
        >>> await agent.start()
        >>> 
        >>> event = {
        ...     "event_type": "AnalysisComplete",
        ...     "payload": {"recommendation": {"decision": "GO"}, "product": {...}}
        ... }
        >>> result = await agent.process_event(event)
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        serpapi_key: Optional[str] = None,
        cache_ttl: int = 86400,  # 24 horas
        max_suppliers: int = 5
    ):
        """
        Inicializa el Supplier Agent.
        
        Args:
            openai_api_key: API key de OpenAI (deprecated, use Claude)
            serpapi_key: API key de SerpAPI para búsqueda de proveedores
            cache_ttl: TTL del caché en segundos
            max_suppliers: Número máximo de proveedores a contactar
        """
        super().__init__(
            name="SupplierAgent",
            subscribed_events={"AnalysisComplete"}
        )
        
        self.openai_api_key = openai_api_key
        self.serpapi_key = serpapi_key
        self.cache_ttl = cache_ttl
        self.max_suppliers = max_suppliers
        
        # Servicios
        self.cache: Optional[CacheService] = None
        self.claude_service: Optional[ClaudeService] = None
        self.supplier_message_skill: Optional[SupplierMessageSkill] = None
        self.supplier_evaluation_skill: Optional[SupplierEvaluationSkill] = None
        self.openai_client = None  # Deprecated fallback
    
    async def initialize(self) -> None:
        """Inicializa el agent y sus dependencias."""
        self.logger.info(f"Initializing {self.name}...")
        
        try:
            # Inicializar caché
            self.cache = CacheService()
            await self.cache.connect()
            self.logger.info("Cache connected")
            
            # Inicializar Claude Skills (preferred)
            if CLAUDE_AVAILABLE:
                try:
                    self.claude_service = ClaudeService()
                    self.supplier_message_skill = SupplierMessageSkill()
                    self.supplier_evaluation_skill = SupplierEvaluationSkill()
                    self.logger.info("✅ Claude service initialized with SupplierMessageSkill and SupplierEvaluationSkill")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Claude service: {e}, will use fallback")
                    self.claude_service = None
            else:
                self.logger.warning("Claude not available")
            
            # Inicializar OpenAI como fallback (deprecated)
            if OPENAI_AVAILABLE and self.openai_api_key and not self.claude_service:
                openai.api_key = self.openai_api_key
                self.openai_client = openai
                self.logger.info("⚠️  OpenAI client initialized (fallback - deprecated)")
            elif not self.claude_service:
                self.logger.warning("⚠️  No AI service available, using templates only")
            
            self.logger.info(f"{self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento de análisis completado.
        
        Solo procesa si la recomendación es GO.
        
        Args:
            event: Evento con análisis del producto
        
        Returns:
            Evento SupplierContactGenerated con contactos
        """
        payload = event.get("payload", {})
        recommendation = payload.get("recommendation", {})
        product = payload.get("product", {})
        
        # Solo procesar si la recomendación es GO
        decision = recommendation.get("decision", "")
        if decision != "GO":
            self.logger.info(f"Product decision is {decision}, skipping supplier search")
            return None
        
        asin = product.get("asin", "unknown")
        self.logger.info(f"Searching suppliers for product: {asin}")
        
        try:
            # 1. Buscar proveedores potenciales
            suppliers = await self._find_suppliers(product)
            self.logger.info(f"Found {len(suppliers)} potential suppliers")
            
            # 2. Generar mensajes personalizados para cada proveedor
            contacts = []
            for supplier in suppliers[:self.max_suppliers]:
                message = await self._generate_contact_message(product, supplier)
                contact = {
                    "supplier": supplier,
                    "message": message,
                    "generated_at": datetime.now().isoformat()
                }
                contacts.append(contact)
            
            self.logger.info(f"Generated {len(contacts)} supplier contacts")
            
            # 3. Crear evento con contactos
            return Event(
                event_type="SupplierContactGenerated",
                payload={
                    "product": product,
                    "asin": asin,
                    "contacts": contacts,
                    "total_suppliers_found": len(suppliers)
                },
                source_agent=self.name
            ).to_dict()
            
        except Exception as e:
            self.logger.error(f"Error processing suppliers for {asin}: {e}", exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """Apaga el agent limpiamente."""
        self.logger.info(f"Shutting down {self.name}...")
        
        try:
            if self.cache:
                await self.cache.disconnect()
            
            self.logger.info(f"{self.name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down {self.name}: {e}")
            raise
    
    async def _find_suppliers(
        self, 
        product: Dict[str, Any],
        countries: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca proveedores potenciales para el producto usando SerpAPI.
        
        Busca proveedores reales en:
        - Alibaba.com
        - Global Sources
        - Made-in-China
        
        Args:
            product: Datos del producto
            countries: Lista de países preferidos (ej: ["China", "Vietnam"])
            min_rating: Rating mínimo requerido
            max_results: Número máximo de resultados
        
        Returns:
            Lista de proveedores encontrados
        """
        title = product.get("title", "")
        product_name = title.split("-")[0].strip() if "-" in title else title[:50]
        
        cache_key = f"suppliers:{product_name}:{countries}:{min_rating}"
        
        # Intentar caché
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                self.logger.debug("Cache hit for suppliers")
                return cached
        
        # Buscar proveedores reales usando SerpAPI
        suppliers = []
        
        if SERPAPI_AVAILABLE and self.serpapi_key:
            try:
                suppliers = await self._search_real_suppliers(
                    product_name, 
                    countries=countries,
                    min_rating=min_rating,
                    max_results=max_results
                )
                self.logger.info(f"Found {len(suppliers)} real suppliers using SerpAPI")
            except Exception as e:
                self.logger.warning(f"Error searching real suppliers: {e}, falling back to mock")
                suppliers = self._generate_mock_suppliers(product)
        else:
            # Fallback a mock si no hay SerpAPI
            self.logger.info("SerpAPI not available, using mock suppliers")
            suppliers = self._generate_mock_suppliers(product)
        
        # Guardar en caché
        if self.cache and suppliers:
            await self.cache.set(cache_key, suppliers, ttl=self.cache_ttl)
        
        # Evaluar proveedores encontrados si Claude está disponible
        if suppliers and self.claude_service and self.supplier_evaluation_skill:
            evaluated_suppliers = []
            for supplier in suppliers[:self.max_suppliers]:  # Evaluar solo los primeros
                try:
                    evaluation = await self._evaluate_supplier(supplier, product)
                    supplier["evaluation"] = evaluation
                    evaluated_suppliers.append(supplier)
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate supplier {supplier.get('name', 'unknown')}: {e}")
                    evaluated_suppliers.append(supplier)
            suppliers = evaluated_suppliers
        
        return suppliers
    
    async def _evaluate_supplier(
        self,
        supplier: Dict[str, Any],
        product: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalúa un proveedor usando Claude SupplierEvaluationSkill.
        
        Args:
            supplier: Datos del proveedor
            product: Datos del producto
        
        Returns:
            Diccionario con evaluación del proveedor
        """
        if not self.claude_service or not self.supplier_evaluation_skill:
            return {"trust_score": 50, "status": "not_evaluated"}
        
        try:
            # Preparar datos para la skill
            input_data = {
                "supplier": {
                    "name": supplier.get("name", "Unknown"),
                    "country": supplier.get("country", "Unknown"),
                    "rating": supplier.get("rating", 0),
                    "contact_email": supplier.get("contact_email", ""),
                    "website": supplier.get("website", ""),
                    "years_in_business": supplier.get("years_in_business", 0),
                    "certifications": supplier.get("certifications", []),
                    "moq": supplier.get("min_order_quantity", 0),
                    "price_per_unit": supplier.get("price_per_unit", 0),
                    "lead_time_days": supplier.get("lead_time_days", 0)
                },
                "product_context": {
                    "name": product.get("title", "Product"),
                    "complexity": "medium",  # Could be enhanced later
                    "quality_requirements": "Amazon FBA standard"
                }
            }
            
            # Ejecutar skill
            self.logger.info(f"Evaluating supplier {supplier.get('name', 'unknown')}")
            result = await self.supplier_evaluation_skill.execute(
                input_data,
                self.claude_service
            )
            
            if result.success:
                self.logger.info(f"Supplier {supplier.get('name', 'unknown')} evaluated: trust_score={result.data.get('trust_score', 'N/A')}")
                return result.data
            else:
                self.logger.warning(f"Supplier evaluation failed: {result.error}")
                return {"trust_score": 50, "status": "evaluation_failed", "error": result.error}
                
        except Exception as e:
            self.logger.error(f"Error evaluating supplier: {e}", exc_info=True)
            return {"trust_score": 50, "status": "evaluation_error"}
    
    async def _search_real_suppliers(
        self,
        product_name: str,
        countries: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca proveedores reales usando SerpAPI Google Search.
        
        Realiza búsquedas en Google para encontrar proveedores en:
        - Alibaba.com
        - Global Sources
        - Made-in-China
        
        Args:
            product_name: Nombre del producto
            countries: Países preferidos
            min_rating: Rating mínimo
            max_results: Máximo de resultados
        
        Returns:
            Lista de proveedores parseados
        """
        import asyncio
        import re
        
        suppliers = []
        search_queries = []
        
        # Construir queries de búsqueda
        country_filter = ""
        if countries:
            country_filter = f" {countries[0]}"  # Usar primer país como filtro
        
        # Búsquedas estratégicas
        search_queries.append(f"Alibaba {product_name} supplier{country_filter}")
        search_queries.append(f"wholesale {product_name} manufacturer{country_filter}")
        
        if not countries or "China" in countries:
            search_queries.append(f"Made in China {product_name} factory")
        
        for query in search_queries[:2]:  # Limitar a 2 búsquedas para no exceder límites
            try:
                # Buscar en Google usando SerpAPI
                params = {
                    "api_key": self.serpapi_key,
                    "engine": "google",
                    "q": query,
                    "num": 10,
                    "gl": "us",
                    "hl": "en"
                }
                
                # Ejecutar búsqueda de forma asíncrona
                search = GoogleSearch(params)
                results = await asyncio.to_thread(lambda: search.get_dict())
                
                # Parsear resultados
                parsed = self._parse_google_supplier_results(results, product_name)
                suppliers.extend(parsed)
                
                # Limitar resultados totales
                if len(suppliers) >= max_results:
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error searching suppliers with query '{query}': {e}")
                continue
        
        # Filtrar por rating si se especifica
        if min_rating:
            suppliers = [s for s in suppliers if s.get("rating", 0) >= min_rating]
        
        # Ordenar por rating y limitar
        suppliers.sort(key=lambda s: s.get("rating", 0), reverse=True)
        return suppliers[:max_results]
    
    def _parse_google_supplier_results(
        self, 
        results: Dict[str, Any],
        product_name: str
    ) -> List[Dict[str, Any]]:
        """
        Parsea resultados de Google Search para extraer información de proveedores.
        
        Args:
            results: Resultados de SerpAPI Google Search
            product_name: Nombre del producto buscado
        
        Returns:
            Lista de proveedores parseados
        """
        import re
        import random
        
        suppliers = []
        
        # Extraer resultados orgánicos
        organic_results = results.get("organic_results", [])
        
        for result in organic_results:
            try:
                title = result.get("title", "")
                link = result.get("link", "")
                snippet = result.get("snippet", "")
                
                # Filtrar solo resultados de sitios de proveedores
                supplier_domains = [
                    "alibaba.com", 
                    "made-in-china.com",
                    "globalsources.com",
                    "dhgate.com",
                    "tradekey.com"
                ]
                
                if not any(domain in link.lower() for domain in supplier_domains):
                    continue
                
                # Extraer nombre de la empresa del título
                company_name = self._extract_company_name(title, snippet)
                
                # Extraer país del snippet o título
                country = self._extract_country(title, snippet, link)
                
                # Generar rating estimado basado en palabras clave
                rating = self._estimate_rating(title, snippet)
                
                # Estimar MOQ basado en el tipo de producto
                moq = self._estimate_moq(product_name)
                
                # Generar email de contacto
                email = self._generate_contact_email(company_name)
                
                supplier = {
                    "id": f"SUP{random.randint(10000, 99999)}",
                    "name": company_name,
                    "country": country,
                    "rating": rating,
                    "years_in_business": random.randint(2, 20),
                    "min_order_quantity": moq,
                    "estimated_price": 0,  # Se calculará después con cotización
                    "lead_time_days": random.randint(15, 45),
                    "verified": "verified" in snippet.lower() or "gold" in snippet.lower(),
                    "contact_email": email,
                    "website": link,
                    "source": "serpapi_google",
                    "specialties": [product_name.lower()]
                }
                
                suppliers.append(supplier)
                
            except Exception as e:
                self.logger.debug(f"Error parsing supplier result: {e}")
                continue
        
        return suppliers
    
    def _extract_company_name(self, title: str, snippet: str) -> str:
        """Extrae nombre de empresa del título o snippet."""
        # Intentar extraer del título antes de " - " o " | "
        for separator in [" - ", " | ", " – "]:
            if separator in title:
                return title.split(separator)[0].strip()
        
        # Si no hay separador, usar primeras palabras del título
        words = title.split()[:4]  # Primeras 4 palabras
        return " ".join(words)
    
    def _extract_country(self, title: str, snippet: str, link: str) -> str:
        """Extrae país del título, snippet o link."""
        import re
        
        # Países comunes en manufactura
        countries = [
            "China", "Vietnam", "India", "Thailand", "Bangladesh",
            "Indonesia", "Malaysia", "Philippines", "Taiwan", "Hong Kong"
        ]
        
        text = f"{title} {snippet}".lower()
        
        for country in countries:
            if country.lower() in text:
                return country
        
        # Si no se encuentra, inferir del dominio
        if "alibaba.com" in link.lower() or "made-in-china.com" in link.lower():
            return "China"
        
        return "Unknown"
    
    def _estimate_rating(self, title: str, snippet: str) -> float:
        """Estima rating basado en palabras clave positivas."""
        import random
        
        text = f"{title} {snippet}".lower()
        
        # Palabras clave positivas aumentan rating
        positive_keywords = [
            "verified", "gold supplier", "trade assurance", 
            "certified", "award", "leading", "top"
        ]
        
        rating = 3.5  # Base
        for keyword in positive_keywords:
            if keyword in text:
                rating += 0.3
        
        # Limitar entre 3.0 y 5.0
        rating = min(max(rating, 3.0), 5.0)
        
        # Agregar pequeña variación aleatoria
        rating += random.uniform(-0.2, 0.2)
        return round(rating, 1)
    
    def _estimate_moq(self, product_name: str) -> int:
        """Estima MOQ basado en el tipo de producto."""
        import random
        
        product_lower = product_name.lower()
        
        # Productos pequeños/cosmetics tienen MOQ más bajo
        if any(word in product_lower for word in ["cosmetic", "jewelry", "accessory", "small"]):
            return random.choice([100, 200, 500])
        
        # Productos medianos
        elif any(word in product_lower for word in ["home", "kitchen", "fitness"]):
            return random.choice([500, 1000, 2000])
        
        # Productos grandes/electrónicos tienen MOQ más alto
        else:
            return random.choice([1000, 2000, 5000])
    
    def _generate_contact_email(self, company_name: str) -> str:
        """Genera email de contacto basado en nombre de empresa."""
        # Simplificar nombre de empresa
        name_parts = company_name.lower().split()
        
        # Remover palabras comunes
        skip_words = ["co", "ltd", "limited", "inc", "corp", "group", "international", "global"]
        clean_parts = [p for p in name_parts if p not in skip_words]
        
        if clean_parts:
            domain = "".join(clean_parts[:2]) if len(clean_parts) >= 2 else clean_parts[0]
        else:
            domain = "supplier"
        
        return f"sales@{domain}.com"
    
    def _generate_mock_suppliers(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Genera proveedores mock para desarrollo/testing.
        
        Args:
            product: Datos del producto
        
        Returns:
            Lista de proveedores mock
        """
        import random
        
        # Templates de nombres de proveedores
        prefixes = ["Global", "International", "China", "Elite", "Premier"]
        middles = ["Trading", "Manufacturing", "Import", "Export", "Supply"]
        suffixes = ["Co Ltd", "Group", "Corp", "Company", "Industries"]
        
        suppliers = []
        for i in range(8):
            name = f"{random.choice(prefixes)} {random.choice(middles)} {random.choice(suffixes)}"
            
            supplier = {
                "id": f"SUP{random.randint(10000, 99999)}",
                "name": name,
                "country": random.choice(["China", "India", "Vietnam", "Thailand"]),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "years_in_business": random.randint(2, 15),
                "min_order_quantity": random.choice([100, 500, 1000, 2000]),
                "estimated_price": round(product.get("price", 0) * 0.4, 2),
                "lead_time_days": random.randint(15, 45),
                "verified": random.choice([True, False]),
                "contact_email": f"sales@{name.lower().replace(' ', '')}.com",
                "specialties": random.sample([
                    "electronics", "home goods", "sports", "beauty", "toys"
                ], k=2)
            }
            suppliers.append(supplier)
        
        # Ordenar por rating
        suppliers.sort(key=lambda s: s["rating"], reverse=True)
        
        return suppliers
    
    async def _generate_contact_message(
        self,
        product: Dict[str, Any],
        supplier: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera mensaje de contacto personalizado.
        
        Usa Claude Skills (preferred) > OpenAI (deprecated) > Template.
        
        Args:
            product: Datos del producto
            supplier: Datos del proveedor
        
        Returns:
            Diccionario con mensaje (subject, body)
        """
        # Preferir Claude Skills
        if self.claude_service and self.supplier_message_skill:
            try:
                message = await self._generate_with_claude(product, supplier)
                return message
            except Exception as e:
                self.logger.warning(f"Claude generation failed: {e}, trying fallback")
        
        # Fallback a OpenAI (deprecated)
        if self.openai_client and OPENAI_AVAILABLE:
            try:
                message = await self._generate_with_openai(product, supplier)
                return message
            except Exception as e:
                self.logger.warning(f"OpenAI generation failed: {e}, using template")
        
        # Último recurso: template
        message = self._generate_with_template(product, supplier)
        return message
    
    async def _generate_with_claude(
        self,
        product: Dict[str, Any],
        supplier: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera mensaje usando Claude Skills.
        
        Args:
            product: Datos del producto
            supplier: Datos del proveedor
        
        Returns:
            Mensaje generado
        """
        try:
            # Preparar datos para la skill
            input_data = {
                "product_name": product.get('title', 'Product'),
                "supplier_name": supplier.get('name', 'Supplier'),
                "message_type": "initial_inquiry",
                "quantity": 500,  # Default quantity
                "context": {
                    "product_price": product.get('price', 0),
                    "supplier_country": supplier.get('country', 'Unknown'),
                    "moq": supplier.get('min_order_quantity', 'Unknown')
                }
            }
            
            # Invocar skill
            result = await self.supplier_message_skill.execute(
                input_data,
                self.claude_service
            )
            
            if result.success:
                data = result.data
                return {
                    "subject": data.get("subject", f"Inquiry about {product.get('title', 'Product')}"),
                    "body": data.get("message", ""),
                    "generated_by": "claude",
                    "tone": data.get("tone", "professional"),
                    "follow_up_days": data.get("follow_up_days", 7)
                }
            else:
                raise Exception(f"Skill execution failed: {result.error}")
            
        except Exception as e:
            self.logger.error(f"Error generating with Claude: {e}", exc_info=True)
            raise
    
    async def _generate_with_openai(
        self,
        product: Dict[str, Any],
        supplier: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera mensaje usando OpenAI GPT.
        
        Args:
            product: Datos del producto
            supplier: Datos del proveedor
        
        Returns:
            Mensaje generado
        """
        prompt = f"""
Generate a professional supplier inquiry email for the following:

Product: {product.get('title', 'N/A')}
Product Price: ${product.get('price', 0):.2f}

Supplier: {supplier.get('name', 'N/A')}
Country: {supplier.get('country', 'N/A')}
Minimum Order: {supplier.get('min_order_quantity', 0)} units

Requirements:
- Professional and polite tone
- Request for quotation
- Ask about MOQ, pricing, lead time
- Mention quality standards (if applicable)
- Request samples
- Keep it concise (max 150 words)

Generate:
1. Subject line
2. Email body
"""
        
        try:
            # Llamar a OpenAI (async)
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional procurement assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            
            # Parsear respuesta (asumir formato Subject: / Body:)
            lines = content.split('\n')
            subject = ""
            body = []
            
            in_body = False
            for line in lines:
                if line.startswith("Subject:"):
                    subject = line.replace("Subject:", "").strip()
                elif line.startswith("Body:") or in_body:
                    in_body = True
                    if not line.startswith("Body:"):
                        body.append(line)
            
            return {
                "subject": subject or "Inquiry about product sourcing",
                "body": "\n".join(body).strip(),
                "generated_by": "openai"
            }
            
        except Exception as e:
            self.logger.warning(f"Error with OpenAI, using template: {e}")
            return self._generate_with_template(product, supplier)
    
    def _generate_with_template(
        self,
        product: Dict[str, Any],
        supplier: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera mensaje usando template predefinido.
        
        Args:
            product: Datos del producto
            supplier: Datos del proveedor
        
        Returns:
            Mensaje generado
        """
        product_title = product.get("title", "product")
        supplier_name = supplier.get("name", "supplier")
        moq = supplier.get("min_order_quantity", 1000)
        
        subject = f"Inquiry: {product_title[:50]}"
        
        body = f"""Dear {supplier_name} Team,

I hope this message finds you well.

I am interested in sourcing products similar to: {product_title}

Could you please provide the following information:

1. Best pricing for MOQ of {moq} units
2. Lead time for production and shipping
3. Available customization options
4. Sample availability and cost
5. Quality certifications (if any)

I am looking for a reliable long-term supplier and would appreciate your quotation at your earliest convenience.

Thank you for your time and consideration.

Best regards,
Amazon FBA Seller
"""
        
        return {
            "subject": subject,
            "body": body,
            "generated_by": "template"
        }
    
    async def compare_quotes(
        self,
        quotes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compara cotizaciones de diferentes proveedores.
        
        Args:
            quotes: Lista de cotizaciones
        
        Returns:
            Análisis comparativo
        """
        if not quotes:
            return {"message": "No quotes to compare"}
        
        # Ordenar por precio
        sorted_by_price = sorted(
            quotes,
            key=lambda q: q.get("price_per_unit", float('inf'))
        )
        
        # Ordenar por rating
        sorted_by_rating = sorted(
            quotes,
            key=lambda q: q.get("supplier_rating", 0),
            reverse=True
        )
        
        # Best value (precio/calidad)
        def value_score(quote):
            price = quote.get("price_per_unit", 100)
            rating = quote.get("supplier_rating", 0)
            # Score = rating / normalized_price
            return (rating / 5.0) / (price / 100) if price > 0 else 0
        
        sorted_by_value = sorted(
            quotes,
            key=value_score,
            reverse=True
        )
        
        return {
            "total_quotes": len(quotes),
            "cheapest": sorted_by_price[0] if sorted_by_price else None,
            "best_rated": sorted_by_rating[0] if sorted_by_rating else None,
            "best_value": sorted_by_value[0] if sorted_by_value else None,
            "avg_price": sum(q.get("price_per_unit", 0) for q in quotes) / len(quotes),
            "price_range": {
                "min": sorted_by_price[0].get("price_per_unit") if sorted_by_price else 0,
                "max": sorted_by_price[-1].get("price_per_unit") if sorted_by_price else 0
            }
        }

