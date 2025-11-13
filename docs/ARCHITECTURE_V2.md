# 🏗️ Amazon FBA AI Agent - Arquitectura V2

**Versión:** 2.0  
**Fecha:** Octubre 29, 2025  
**Status:** 🎯 Diseño Completo - Listo para Implementación

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Diagrama de Componentes](#diagrama-de-componentes)
3. [Event Schema](#event-schema)
4. [API Contracts](#api-contracts)
5. [Database Schema](#database-schema)
6. [Deployment Strategy](#deployment-strategy)
7. [Decisiones de Diseño](#decisiones-de-diseño)
8. [Plan de Migración](#plan-de-migración)

---

## 🎯 Visión General

### Cambio Fundamental: Pipeline Secuencial → Event-Driven Multi-Agent

**V1 (Actual):**
```
product_discovery → market_analysis → profitability → demand → supplier → pricing → inventory
(bloqueante, 120s, monolítico)
```

**V2 (Nueva):**
```
Event: TrendDiscoveryRequested
  ↓
[Discovery Agent] → ProductDiscovered event
  ↓
[Analysis Agent] → AnalysisComplete event
  ↓
[Supplier Agent] + [Pricing Agent] (paralelo) → Multiple events
  ↓
[Inventory Agent] → InventoryUpdated event

(no-bloqueante, 40s, distribuido)
```

### Principios de Diseño

1. **Event-Driven** - Comunicación asíncrona entre componentes
2. **Microservices-oriented** - Agents independientes y escalables
3. **API-First** - Backend expone REST + WebSockets
4. **Real-time** - Updates instantáneos sin polling
5. **Testable** - Cada componente testeado independientemente
6. **Observable** - Metrics, logs, tracing
7. **Scalable** - Horizontal scaling de agents
8. **Resilient** - Retry, circuit breakers, graceful degradation

---

## 🏛️ Diagrama de Componentes

### High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Dashboard]
        WS[WebSocket Client]
    end
    
    subgraph "API Layer"
        NGINX[Nginx Reverse Proxy]
        API[FastAPI Gateway]
        WSS[WebSocket Server]
    end
    
    subgraph "Agent Layer"
        DA[Discovery Agent]
        AA[Analysis Agent]
        SA[Supplier Agent]
        PA[Pricing Agent]
        IA[Inventory Agent]
    end
    
    subgraph "Core Services"
        EB[Event Bus]
        ORCH[Orchestrator]
        CACHE[(Redis Cache)]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        S3[(S3 Storage)]
    end
    
    subgraph "External APIs"
        SERP[SerpAPI]
        OAI[OpenAI]
        TRENDS[Google Trends]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
    end
    
    UI --> NGINX
    NGINX --> API
    NGINX --> WSS
    API --> EB
    WSS --> EB
    
    EB --> DA
    EB --> AA
    EB --> SA
    EB --> PA
    EB --> IA
    
    DA --> ORCH
    AA --> ORCH
    SA --> ORCH
    PA --> ORCH
    IA --> ORCH
    
    ORCH --> EB
    
    DA -.->|uses| CACHE
    AA -.->|uses| CACHE
    SA -.->|uses| CACHE
    
    DA --> SERP
    SA --> OAI
    PA --> OAI
    AA --> TRENDS
    
    DA --> DB
    AA --> DB
    SA --> DB
    PA --> DB
    IA --> DB
    
    API --> PROM
    DA --> PROM
    AA --> PROM
    
    PROM --> GRAF
```

### Component Details

#### Frontend Layer
- **React Dashboard** - SPA moderna con TypeScript
- **WebSocket Client** - Real-time updates
- **State Management** - Zustand para state global
- **API Client** - Axios con retry logic

#### API Layer
- **Nginx** - Reverse proxy, SSL, load balancing
- **FastAPI Gateway** - REST API + OpenAPI docs
- **WebSocket Server** - Bidirectional communication
- **Authentication** - JWT tokens

#### Agent Layer (Microservices Pattern)
- **Discovery Agent** - Descubre productos trending
- **Analysis Agent** - Analiza mercado y rentabilidad
- **Supplier Agent** - Gestiona comunicación con proveedores
- **Pricing Agent** - Optimiza precios dinámicamente
- **Inventory Agent** - Tracking de stock y alertas

#### Core Services
- **Event Bus** - Message broker (Redis Streams)
- **Orchestrator** - Coordina lifecycle de agents
- **Redis Cache** - Ya implementado ✅

#### Data Layer
- **PostgreSQL** - RDBMS principal
- **S3** - Storage de archivos (CSVs, reportes)

---

## 📡 Event Schema

### Base Event Structure

```typescript
interface BaseEvent {
  event_id: string;          // UUID único
  event_type: string;        // Tipo de evento
  timestamp: string;         // ISO 8601
  source_agent: string;      // Agente que lo generó
  correlation_id: string;    // Para tracking de flujos
  version: string;           // Schema version
  payload: object;           // Datos específicos del evento
  metadata?: {
    retry_count?: number;
    priority?: 'high' | 'medium' | 'low';
    ttl?: number;           // Time to live en segundos
  };
}
```

### Event Types

#### 1. TrendDiscoveryRequested

```json
{
  "event_type": "TrendDiscoveryRequested",
  "timestamp": "2025-10-29T10:00:00Z",
  "source_agent": "api_gateway",
  "correlation_id": "req-123-456",
  "payload": {
    "budget": 3000,
    "categories": ["electronics", "home"],
    "min_rating": 4.0,
    "max_results": 20,
    "user_id": "user_123"
  }
}
```

#### 2. ProductDiscovered

```json
{
  "event_type": "ProductDiscovered",
  "timestamp": "2025-10-29T10:01:30Z",
  "source_agent": "discovery_agent",
  "correlation_id": "req-123-456",
  "payload": {
    "products": [
      {
        "asin": "B08EXAMPLE",
        "title": "Eco Yoga Mat Premium",
        "price": 34.99,
        "rating": 4.6,
        "reviews": 2340,
        "bsr": 280,
        "category": "Sports & Outdoors",
        "discovery_method": "trending_keywords",
        "confidence": 85.5
      }
    ],
    "total_found": 15,
    "keywords_used": ["yoga mat", "eco friendly"],
    "api_calls_made": 3
  }
}
```

#### 3. AnalysisComplete

```json
{
  "event_type": "AnalysisComplete",
  "timestamp": "2025-10-29T10:03:00Z",
  "source_agent": "analysis_agent",
  "correlation_id": "req-123-456",
  "payload": {
    "asin": "B08EXAMPLE",
    "analysis": {
      "profitability": {
        "roi": 0.65,
        "profit_per_unit": 12.50,
        "monthly_profit": 1875.00,
        "viable": true
      },
      "demand": {
        "est_monthly_sales": 150,
        "demand_level": "HIGH",
        "trend_direction": "growing"
      },
      "competition": {
        "level": "medium",
        "num_sellers": 24,
        "price_range": [25.99, 44.99]
      }
    },
    "recommendation": "BUY",
    "confidence": 82.3
  }
}
```

#### 4. SupplierContactGenerated

```json
{
  "event_type": "SupplierContactGenerated",
  "timestamp": "2025-10-29T10:05:00Z",
  "source_agent": "supplier_agent",
  "correlation_id": "req-123-456",
  "payload": {
    "asin": "B08EXAMPLE",
    "message": "Dear Supplier,\n\nWe are interested...",
    "suppliers_contacted": 3,
    "estimated_moq": 100,
    "estimated_unit_cost": 12.50,
    "message_cached": false
  }
}
```

#### 5. PriceOptimized

```json
{
  "event_type": "PriceOptimized",
  "timestamp": "2025-10-29T10:06:00Z",
  "source_agent": "pricing_agent",
  "payload": {
    "asin": "B08EXAMPLE",
    "current_price": 34.99,
    "suggested_price": 36.99,
    "expected_roi_improvement": 0.08,
    "reasoning": "Competitors increased prices, demand stable",
    "confidence": 78.5
  }
}
```

#### 6. InventoryAlert

```json
{
  "event_type": "InventoryAlert",
  "timestamp": "2025-10-29T10:10:00Z",
  "source_agent": "inventory_agent",
  "payload": {
    "asin": "B08EXAMPLE",
    "alert_type": "LOW_STOCK",
    "current_quantity": 15,
    "recommended_reorder": 100,
    "days_until_stockout": 5,
    "urgency": "high"
  }
}
```

### Event Flow Example

```mermaid
sequenceDiagram
    participant User
    participant API
    participant EventBus
    participant DiscoveryAgent
    participant AnalysisAgent
    participant SupplierAgent
    participant PricingAgent
    
    User->>API: POST /discover (budget: 3000)
    API->>EventBus: TrendDiscoveryRequested
    EventBus->>DiscoveryAgent: deliver event
    
    DiscoveryAgent->>DiscoveryAgent: Search trending products
    DiscoveryAgent->>EventBus: ProductDiscovered (15 products)
    
    EventBus->>AnalysisAgent: deliver event
    AnalysisAgent->>AnalysisAgent: Analyze profitability
    
    par Parallel Processing
        AnalysisAgent->>EventBus: AnalysisComplete
        EventBus->>SupplierAgent: deliver event
        EventBus->>PricingAgent: deliver event
    end
    
    SupplierAgent->>EventBus: SupplierContactGenerated
    PricingAgent->>EventBus: PriceOptimized
    
    EventBus->>API: aggregate results
    API->>User: WebSocket update (real-time)
```

---

## 🔌 API Contracts

### REST API Endpoints

#### Products

```yaml
GET /api/v1/products:
  summary: List all products
  parameters:
    - name: page
      type: integer
      default: 1
    - name: limit
      type: integer
      default: 20
    - name: category
      type: string
      enum: [electronics, home, sports, baby]
    - name: min_roi
      type: float
      minimum: 0
  responses:
    200:
      schema:
        type: object
        properties:
          products:
            type: array
            items: Product
          total: integer
          page: integer
          pages: integer

POST /api/v1/products/discover:
  summary: Discover trending products
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          properties:
            budget: 
              type: number
              minimum: 500
            categories:
              type: array
              items:
                type: string
            min_rating:
              type: number
              minimum: 0
              maximum: 5
  responses:
    202:
      description: Discovery initiated (async)
      schema:
        job_id: string
        status: "processing"
    200:
      description: Discovery complete
      schema:
        products: array<Product>

GET /api/v1/products/{asin}:
  summary: Get product details
  parameters:
    - name: asin
      in: path
      required: true
  responses:
    200:
      schema: Product
    404:
      schema: Error

GET /api/v1/products/{asin}/analysis:
  summary: Get product analysis
  responses:
    200:
      schema: ProductAnalysis
```

#### Analysis

```yaml
POST /api/v1/analysis/market:
  summary: Analyze market for products
  requestBody:
    asins: array<string>
  responses:
    202:
      job_id: string
      
GET /api/v1/analysis/trends:
  summary: Get trending keywords
  responses:
    200:
      trends: array<TrendData>
```

#### Suppliers

```yaml
GET /api/v1/suppliers:
  summary: List suppliers
  
POST /api/v1/suppliers/contact:
  summary: Generate contact message
  requestBody:
    asin: string
    quantity: number
  responses:
    200:
      message: string
      cached: boolean
```

#### Inventory

```yaml
GET /api/v1/inventory:
  summary: Get inventory status
  
GET /api/v1/inventory/alerts:
  summary: Get low stock alerts
  
POST /api/v1/inventory/reorder:
  summary: Trigger reorder
```

### WebSocket Protocol

```yaml
WS /ws/updates:
  description: Real-time updates
  
  # Client → Server
  subscribe:
    type: "subscribe"
    channels: ["products", "analysis", "inventory"]
  
  # Server → Client
  update:
    type: "product_discovered"
    data: Product
  
  update:
    type: "analysis_complete"
    data: Analysis
  
  update:
    type: "inventory_alert"
    data: Alert
```

### Data Schemas

```typescript
interface Product {
  asin: string;
  title: string;
  price: number;
  rating: number;
  reviews: number;
  bsr?: number;
  category: string;
  image_url?: string;
  discovered_at: string;
  data_sources: string[];
  confidence: number;
}

interface ProductAnalysis {
  asin: string;
  profitability: {
    roi: number;
    profit_per_unit: number;
    monthly_profit: number;
    fba_fees: number;
    shipping_cost: number;
    viable: boolean;
  };
  demand: {
    est_monthly_sales: number;
    demand_level: "LOW" | "MEDIUM" | "HIGH";
    trend_direction: "declining" | "stable" | "growing";
  };
  competition: {
    level: "low" | "medium" | "high";
    num_sellers: number;
    avg_price: number;
    price_range: [number, number];
  };
  recommendation: "BUY" | "MONITOR" | "SKIP";
  confidence: number;
  analyzed_at: string;
}

interface Supplier {
  id: string;
  name: string;
  email: string;
  country: string;
  rating: number;
  min_order_quantity: number;
  products: string[];  // ASINs
  communication_history: Communication[];
}

interface InventoryStatus {
  asin: string;
  quantity: number;
  location: string;
  last_updated: string;
  reorder_point: number;
  days_until_stockout: number;
  alerts: Alert[];
}
```

---

## 💾 Database Schema

### PostgreSQL Tables

```sql
-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(10) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    price DECIMAL(10, 2),
    rating DECIMAL(3, 2),
    review_count INTEGER,
    best_seller_rank INTEGER,
    category VARCHAR(100),
    image_url TEXT,
    data_sources JSONB,  -- ['serpapi', 'trends']
    confidence DECIMAL(5, 2),
    discovered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_asin (asin),
    INDEX idx_category (category),
    INDEX idx_discovered_at (discovered_at DESC)
);

-- Analysis table (historical analysis data)
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    asin VARCHAR(10) NOT NULL,
    
    -- Profitability
    roi DECIMAL(5, 4),
    profit_per_unit DECIMAL(10, 2),
    monthly_profit DECIMAL(10, 2),
    fba_fees DECIMAL(10, 2),
    shipping_cost DECIMAL(10, 2),
    viable BOOLEAN,
    
    -- Demand
    est_monthly_sales INTEGER,
    demand_level VARCHAR(20),
    trend_direction VARCHAR(20),
    
    -- Competition
    competition_level VARCHAR(20),
    num_sellers INTEGER,
    avg_competitor_price DECIMAL(10, 2),
    
    -- Meta
    recommendation VARCHAR(20),  -- BUY, MONITOR, SKIP
    confidence DECIMAL(5, 2),
    analyzed_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_asin (asin),
    INDEX idx_recommendation (recommendation),
    INDEX idx_analyzed_at (analyzed_at DESC)
);

-- Suppliers table
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    country VARCHAR(100),
    rating DECIMAL(3, 2),
    verified BOOLEAN DEFAULT FALSE,
    min_order_quantity INTEGER,
    lead_time_days INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_country (country),
    INDEX idx_rating (rating DESC)
);

-- Product-Supplier relationship (many-to-many)
CREATE TABLE product_suppliers (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    unit_cost DECIMAL(10, 2),
    last_quote_date TIMESTAMP,
    quote_valid_until TIMESTAMP,
    
    UNIQUE(product_id, supplier_id)
);

-- Communications table
CREATE TABLE communications (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER REFERENCES suppliers(id),
    product_id INTEGER REFERENCES products(id),
    message_type VARCHAR(50),  -- inquiry, quote, order
    subject VARCHAR(200),
    body TEXT,
    sent_at TIMESTAMP,
    replied_at TIMESTAMP,
    status VARCHAR(50),  -- sent, replied, no_reply
    
    INDEX idx_supplier_id (supplier_id),
    INDEX idx_status (status)
);

-- Inventory table
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    asin VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    location VARCHAR(100),
    reorder_point INTEGER,
    reorder_quantity INTEGER,
    last_restocked_at TIMESTAMP,
    next_restock_date DATE,
    
    INDEX idx_asin (asin),
    INDEX idx_quantity (quantity)
);

-- Inventory movements (ledger)
CREATE TABLE inventory_movements (
    id SERIAL PRIMARY KEY,
    inventory_id INTEGER REFERENCES inventory(id),
    asin VARCHAR(10) NOT NULL,
    movement_type VARCHAR(20),  -- IN, OUT, ADJUSTMENT
    quantity INTEGER NOT NULL,
    reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    INDEX idx_asin (asin),
    INDEX idx_created_at (created_at DESC)
);

-- Events log (event sourcing)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source_agent VARCHAR(100),
    correlation_id VARCHAR(100),
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status VARCHAR(50),  -- pending, processed, failed, retry
    error_message TEXT,
    
    INDEX idx_event_type (event_type),
    INDEX idx_correlation_id (correlation_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);

-- Cache table (opcional, Redis es preferido)
CREATE TABLE api_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    ttl INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    INDEX idx_expires_at (expires_at)
);

-- Users table (para autenticación)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(200),
    role VARCHAR(50),  -- admin, user
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Metrics table (para analytics)
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    metric_type VARCHAR(100),  -- api_call, cache_hit, agent_processing_time
    metric_value DECIMAL(10, 2),
    labels JSONB,  -- {agent: "discovery", endpoint: "/products"}
    timestamp TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_metric_type (metric_type),
    INDEX idx_timestamp (timestamp DESC)
);
```

---

## 🚀 Deployment Strategy

### Architecture Layers

```mermaid
graph TB
    subgraph "Public Internet"
        USER[Users/Browsers]
    end
    
    subgraph "Edge Layer"
        CF[Cloudflare CDN]
        LB[Load Balancer]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            NGINX[Nginx Ingress]
        end
        
        subgraph "Application Pods"
            API1[FastAPI Pod 1]
            API2[FastAPI Pod 2]
            API3[FastAPI Pod 3]
            
            AGENT1[Agent Pod 1]
            AGENT2[Agent Pod 2]
            AGENT3[Agent Pod 3]
        end
        
        subgraph "Data Services"
            REDIS[(Redis Cluster)]
            PG[(PostgreSQL)]
            RABBIT[(RabbitMQ)]
        end
        
        subgraph "Monitoring"
            PROM[Prometheus]
            GRAF[Grafana]
            LOKI[Loki Logs]
        end
    end
    
    subgraph "External Services"
        S3[(AWS S3)]
        APIS[External APIs]
    end
    
    USER --> CF
    CF --> LB
    LB --> NGINX
    
    NGINX --> API1
    NGINX --> API2
    NGINX --> API3
    
    API1 --> REDIS
    API2 --> REDIS
    API3 --> REDIS
    
    API1 --> RABBIT
    API2 --> RABBIT
    API3 --> RABBIT
    
    AGENT1 --> RABBIT
    AGENT2 --> RABBIT
    AGENT3 --> RABBIT
    
    API1 --> PG
    AGENT1 --> PG
    
    AGENT1 --> APIS
    
    API1 --> S3
    
    API1 --> PROM
    AGENT1 --> PROM
    PROM --> GRAF
    PROM --> LOKI
```

### Deployment Environments

#### Development (Local)

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: fba_dev
      POSTGRES_USER: fba_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"  # Management UI
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fba_user:dev_password@postgres/fba_dev
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
  
  agents:
    build: ./backend
    command: python -m agents.orchestrator
    environment:
      DATABASE_URL: postgresql://fba_user:dev_password@postgres/fba_dev
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

**Comando:** `docker-compose up`

#### Staging (Kubernetes)

```yaml
# k8s/staging/kustomization.yaml
namespace: fba-staging

resources:
  - ../base
  
replicas:
  - name: backend
    count: 2
  - name: agents
    count: 2

configMapGenerator:
  - name: app-config
    literals:
      - ENV=staging
      - LOG_LEVEL=debug
```

#### Production (Kubernetes)

```yaml
# k8s/production/kustomization.yaml
namespace: fba-production

resources:
  - ../base

replicas:
  - name: backend
    count: 5
  - name: agents
    count: 10  # Escala según carga

resources:
  backend:
    cpu: "1000m"
    memory: "2Gi"
  agents:
    cpu: "500m"
    memory: "1Gi"

hpa:
  backend:
    minReplicas: 3
    maxReplicas: 20
    targetCPU: 70
  agents:
    minReplicas: 5
    maxReplicas: 50
    targetCPU: 80
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Lint Backend
        run: |
          pip install flake8 mypy
          flake8 backend/
          mypy backend/ --strict
      
      - name: Test Backend
        run: |
          pytest backend/tests/ --cov=backend --cov-report=xml
      
      - name: Lint Frontend
        run: |
          cd frontend
          npm run lint
      
      - name: Test Frontend
        run: |
          cd frontend
          npm test -- --coverage
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  build-and-push:
    needs: lint-and-test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Build Docker Images
        run: |
          docker build -t fba-backend:${{ github.sha }} backend/
          docker build -t fba-frontend:${{ github.sha }} frontend/
      
      - name: Push to Registry
        run: |
          docker push fba-backend:${{ github.sha }}
          docker push fba-frontend:${{ github.sha }}

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: |
          kubectl apply -k k8s/staging/
          kubectl rollout status deployment/backend -n fba-staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://fba.yourdomain.com
    steps:
      - name: Deploy to Production
        run: |
          kubectl apply -k k8s/production/
          kubectl rollout status deployment/backend -n fba-production
```

---

## 🎯 Decisiones de Diseño

### 1. Event-Driven vs Request-Response

**Decisión:** Event-Driven con Event Bus

**Razones:**
- ✅ Desacoplamiento total entre agents
- ✅ Escalabilidad horizontal fácil
- ✅ Retry automático
- ✅ Procesamiento asíncrono
- ✅ Auditoría completa (event log)

**Trade-offs:**
- ❌ Más complejidad inicial
- ❌ Eventual consistency (no immediate)
- ✅ Pero: Mejor para sistema en crecimiento

### 2. PostgreSQL vs MongoDB

**Decisión:** PostgreSQL

**Razones:**
- ✅ ACID transactions (crítico para inventario)
- ✅ Relaciones claras (productos-proveedores)
- ✅ Mejor para análisis histórico
- ✅ JSONB para flexibilidad donde se necesita

### 3. Redis Streams vs RabbitMQ

**Decisión:** Redis Streams (fase 1), migrar a RabbitMQ si escala

**Razones:**
- ✅ Redis ya está (caché)
- ✅ Más simple para empezar
- ✅ Suficiente para <100K events/día
- ⏭️ RabbitMQ cuando > 100K events/día

### 4. Monorepo vs Multi-repo

**Decisión:** Monorepo

**Razones:**
- ✅ Desarrollo más fácil (cambios atómicos)
- ✅ Versionado consistente
- ✅ Shared types (TypeScript)
- ✅ Mejor para equipos pequeños

### 5. REST + WebSocket vs GraphQL

**Decisión:** REST + WebSocket

**Razones:**
- ✅ Más simple
- ✅ OpenAPI docs gratis
- ✅ WebSocket para real-time
- ✅ No necesitamos complejidad de GraphQL

### 6. Synchronous vs Asynchronous Agents

**Decisión:** Asynchronous (async/await)

**Razones:**
- ✅ Paralelización natural
- ✅ Mejor uso de recursos
- ✅ Non-blocking I/O
- ✅ FastAPI es async-native

---

## 🔄 Plan de Migración V1 → V2

### Fase 1: Coexistencia (Semana 1)

```
V1 (Actual)                    V2 (Nueva)
├─ Scripts Python              ├─ Backend FastAPI
├─ Streamlit Dashboards  →     ├─ React Dashboard  
├─ CSV files                   └─ PostgreSQL
└─ (Sigue funcionando)         (Development en paralelo)

Usuario puede usar ambas versiones
```

### Fase 2: Migración Gradual (Semana 2-3)

```
1. Migrar datos CSV → PostgreSQL
2. Redirigir tráfico gradualmente a V2
3. Validar en staging
4. A/B testing
5. Monitoring comparativo
```

### Fase 3: Deprecation V1 (Semana 4)

```
1. Todos los usuarios en V2
2. V1 en read-only mode
3. Backup de V1
4. Documentar diferencias
5. Cleanup final
```

### Backward Compatibility

**Mantener:**
- ✅ APIs de V1 disponibles en `/api/v1/legacy/`
- ✅ CSVs se siguen generando (export feature)
- ✅ Scripts Python siguen funcionando (conectan a API V2)

**Estrategia:**
```python
# V1 scripts pueden seguir usándose
# Internamente llamarán a API V2

# product_discovery.py (V1)
def discover_products(budget):
    # Ahora internamente llama a API V2
    response = requests.post("http://localhost:8000/api/v1/products/discover", json={
        "budget": budget
    })
    # Guarda resultado en CSV (compatible V1)
    save_to_csv(response.json())
```

---

## 📊 Estructura de Directorios Final

```
amazon-fba-v2/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── config.py
│   │   └── routes/
│   │       ├── products.py
│   │       ├── analysis.py
│   │       ├── suppliers.py
│   │       ├── inventory.py
│   │       └── websockets.py
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── discovery_agent.py
│   │   ├── analysis_agent.py
│   │   ├── supplier_agent.py
│   │   ├── pricing_agent.py
│   │   └── inventory_agent.py
│   ├── core/
│   │   ├── event_bus.py
│   │   ├── orchestrator.py
│   │   └── cache_manager.py (ya existe)
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   ├── repository.py
│   │   └── migrations/
│   ├── models/
│   │   ├── product.py
│   │   ├── analysis.py
│   │   └── events.py
│   ├── services/
│   │   ├── product_service.py
│   │   ├── analysis_service.py
│   │   └── cache_service.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── state/
│   │   ├── api/
│   │   └── types/
│   ├── public/
│   └── package.json
├── infrastructure/
│   ├── docker/
│   ├── k8s/
│   ├── monitoring/
│   └── nginx/
├── docs/
│   ├── ARCHITECTURE_V2.md (este archivo)
│   ├── API.md
│   ├── AGENTS.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPMENT.md
│   └── MIGRATION_V1_TO_V2.md
├── scripts/
│   ├── setup_dev.sh
│   ├── run_migrations.py
│   └── seed_data.py
├── docker-compose.yml
├── docker-compose.prod.yml
└── README_V2.md
```

---

## 🔐 Security Considerations

### Authentication & Authorization
- JWT tokens para API
- API keys para external integrations
- Role-based access control (RBAC)
- Rate limiting per user

### Data Security
- Secrets in Kubernetes secrets (no env vars)
- Encrypted database connections
- SSL/TLS everywhere
- API key rotation

### Input Validation
- Pydantic models en FastAPI
- SQL injection prevention (ORM)
- XSS prevention en frontend
- CSRF tokens

---

## 📈 Scaling Strategy

### Horizontal Scaling

**Auto-scaling rules:**
```yaml
Backend API:
  - CPU > 70% → +1 pod
  - Requests > 1000/min → +1 pod
  - Max: 20 pods

Agents:
  - Queue depth > 100 → +2 pods
  - CPU > 80% → +1 pod  
  - Max: 50 pods (10 de cada tipo)
```

### Database Scaling

**Phase 1 (0-10K products):**
- Single PostgreSQL instance
- Periodic backups

**Phase 2 (10K-100K products):**
- PostgreSQL read replicas
- Connection pooling (PgBouncer)

**Phase 3 (100K+ products):**
- PostgreSQL sharding por categoría
- Caching layer más agresivo
- Consider moving to TimescaleDB para time-series

---

## 🎯 Success Criteria

### Technical
- ✅ 99.9% uptime
- ✅ <200ms API latency (p95)
- ✅ >75% test coverage
- ✅ 0 critical security vulnerabilities
- ✅ <$25/mes infrastructure cost

### Business
- ✅ Process 1000+ products/day
- ✅ Real-time updates <100ms
- ✅ $400+/year API cost savings
- ✅ Support 10+ concurrent users

### User Experience
- ✅ Dashboard loads <2s
- ✅ Product discovery <30s
- ✅ Mobile responsive
- ✅ Zero data loss

---

## 📝 ADRs (Architecture Decision Records)

### ADR-001: Event-Driven Architecture

**Status:** Approved  
**Date:** 2025-10-29

**Context:**
Sistema actual es pipeline secuencial bloqueante.

**Decision:**
Migrar a event-driven architecture con specialized agents.

**Consequences:**
- Agents pueden escalar independientemente
- Sistema más complejo pero más flexible
- Eventual consistency (acceptable para uso)

---

### ADR-002: FastAPI + React

**Status:** Approved

**Context:**
Streamlit es limitado para aplicaciones complejas.

**Decision:**
FastAPI backend + React frontend.

**Consequences:**
- Más control sobre UI/UX
- Mejor performance
- Real-time capabilities
- Mayor curva de aprendizaje

---

### ADR-003: PostgreSQL como RDBMS

**Status:** Approved

**Context:**
Actualmente usando CSVs.

**Decision:**
PostgreSQL para persistencia.

**Consequences:**
- ACID transactions
- Better querying
- Relational data modeling
- Requiere migrations

---

## ✅ CONCLUSIÓN

**Arquitectura V2 está diseñada y lista para implementación.**

**Próximos pasos:**
1. Review este documento
2. Ajustar si es necesario
3. Lanzar 6 agents en paralelo (Días 2-6)

**Estimated timeline:** 7 días  
**Estimated LOC:** ~15,000 líneas nuevas  
**Estimated value:** Sistema production-ready escalable

---

**READY TO BUILD?** 🚀

