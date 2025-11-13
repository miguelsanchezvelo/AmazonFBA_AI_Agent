# 📡 Amazon FBA AI Agent V2 - API Documentation

**Version:** 2.0.0  
**Base URL:** `http://localhost:8000/api/v2`  
**Protocol:** REST + WebSocket

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Error Handling](#error-handling)
4. [Endpoints](#endpoints)
   - [Products](#products-endpoints)
   - [Analysis](#analysis-endpoints)
   - [Suppliers](#suppliers-endpoints)
   - [Inventory](#inventory-endpoints)
   - [WebSocket](#websocket-endpoints)
5. [Data Models](#data-models)
6. [Examples](#examples)

---

## 🔐 Authentication

Amazon FBA AI Agent V2 uses JWT (JSON Web Tokens) for authentication.

### Getting a Token

```http
POST /api/v2/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Using the Token

Include the token in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

```http
POST /api/v2/auth/refresh
Authorization: Bearer <refresh_token>
```

---

## ⚡ Rate Limiting

Rate limiting is enabled by default to protect the API from abuse.

- **Default Limits:** 100 requests per minute per IP
- **Headers:** Rate limit information is included in response headers:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

**Rate Limit Error Response:**
```json
{
  "error": {
    "type": "rate_limit_error",
    "code": 429,
    "message": "Rate limit exceeded. Please try again later.",
    "retry_after": 60
  }
}
```

---

## ❌ Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "type": "error_type",
    "code": 400,
    "message": "Human-readable error message",
    "details": {},
    "path": "/api/v2/products/invalid"
  }
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `202` - Accepted (async operation started)
- `204` - No Content (successful delete)
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict (duplicate resource)
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## 📦 Endpoints

### Products Endpoints

#### List Products

```http
GET /api/v2/products
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `keyword` | string | Search keyword | - |
| `category` | string | Filter by category | - |
| `min_price` | float | Minimum price | - |
| `max_price` | float | Maximum price | - |
| `min_rating` | float | Minimum rating (0-5) | - |
| `max_bsr` | integer | Maximum Best Seller Rank | - |
| `limit` | integer | Results per page (1-100) | 20 |
| `offset` | integer | Pagination offset | 0 |

**Response:**
```json
{
  "products": [
    {
      "asin": "B08N5WRWNW",
      "title": "Premium Yoga Mat",
      "price": 34.99,
      "rating": 4.6,
      "reviews_count": 2340,
      "bsr": 280,
      "category": "Sports & Outdoors",
      "image_url": "https://...",
      "url": "https://amazon.com/...",
      "status": "discovered",
      "created_at": "2025-10-29T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "pages": 8
}
```

**Example - curl:**
```bash
curl -X GET "http://localhost:8000/api/v2/products?keyword=yoga&min_rating=4.0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example - Python:**
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
params = {"keyword": "yoga", "min_rating": 4.0, "limit": 10}
response = requests.get("http://localhost:8000/api/v2/products", 
                       headers=headers, params=params)
products = response.json()
```

---

#### Get Product by ASIN

```http
GET /api/v2/products/{asin}
```

**Path Parameters:**
- `asin` (string, required): Amazon Standard Identification Number

**Response:**
```json
{
  "asin": "B08N5WRWNW",
  "title": "Premium Yoga Mat",
  "price": 34.99,
  "rating": 4.6,
  "reviews_count": 2340,
  "bsr": 280,
  "category": "Sports & Outdoors",
  "image_url": "https://...",
  "url": "https://amazon.com/...",
  "status": "discovered",
  "estimated_profit": 12.50,
  "viability_score": 75,
  "created_at": "2025-10-29T10:00:00Z",
  "updated_at": "2025-10-29T10:00:00Z"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v2/products/B08N5WRWNW" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### Create Product

```http
POST /api/v2/products
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "asin": "B08N5WRWNW",
  "title": "Premium Yoga Mat",
  "price": 34.99,
  "rating": 4.6,
  "reviews_count": 2340,
  "bsr": 280,
  "category": "Sports & Outdoors",
  "image_url": "https://...",
  "url": "https://amazon.com/..."
}
```

**Response:** `201 Created`
```json
{
  "asin": "B08N5WRWNW",
  "title": "Premium Yoga Mat",
  "price": 34.99,
  "rating": 4.6,
  "reviews_count": 2340,
  "bsr": 280,
  "category": "Sports & Outdoors",
  "image_url": "https://...",
  "url": "https://amazon.com/...",
  "status": "discovered",
  "created_at": "2025-10-29T10:00:00Z"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v2/products" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B08N5WRWNW",
    "title": "Premium Yoga Mat",
    "price": 34.99,
    "rating": 4.6,
    "reviews_count": 2340
  }'
```

---

#### Update Product

```http
PUT /api/v2/products/{asin}
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "price": 32.99,
  "rating": 4.7,
  "reviews_count": 2500
}
```

**Response:** `200 OK`
```json
{
  "asin": "B08N5WRWNW",
  "title": "Premium Yoga Mat",
  "price": 32.99,
  "rating": 4.7,
  "reviews_count": 2500,
  "updated_at": "2025-10-29T10:30:00Z"
}
```

---

#### Delete Product

```http
DELETE /api/v2/products/{asin}
Authorization: Bearer YOUR_TOKEN
```

**Response:** `204 No Content`

---

#### Discover Products

```http
POST /api/v2/products/discover
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "budget": 3000,
  "categories": ["Sports", "Home"],
  "min_demand_score": 70,
  "max_results": 20,
  "auto_analyze": true,
  "keywords": ["yoga mat", "fitness equipment"]
}
```

**Response:** `202 Accepted`
```json
{
  "task_id": "abc-123-def-456",
  "status": "pending",
  "products_found": 0,
  "estimated_time": 30,
  "message": "Product discovery started. Check status using task_id."
}
```

**Example:**
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
payload = {
    "budget": 3000,
    "categories": ["Sports"],
    "min_demand_score": 70,
    "auto_analyze": True
}
response = requests.post("http://localhost:8000/api/v2/products/discover",
                        headers=headers, json=payload)
task = response.json()

# Check status
task_id = task["task_id"]
status_response = requests.get(
    f"http://localhost:8000/api/v2/products/discover/{task_id}",
    headers=headers
)
```

---

#### Get Discovery Status

```http
GET /api/v2/products/discover/{task_id}
```

**Response:**
```json
{
  "task_id": "abc-123-def-456",
  "status": "completed",
  "products_found": 15,
  "products": [
    {
      "asin": "B08N5WRWNW",
      "title": "Premium Yoga Mat",
      "opportunity_score": 85.5
    }
  ],
  "estimated_time": 30,
  "elapsed_time": 28
}
```

---

#### Get Trending Keywords

```http
GET /api/v2/products/trending/keywords
```

**Query Parameters:**
- `category` (string, optional): Filter by category
- `limit` (integer, 1-50): Number of keywords | Default: 10

**Response:**
```json
[
  {
    "keyword": "yoga mat",
    "score": 95,
    "trend": "up",
    "growth_rate": 15.5
  },
  {
    "keyword": "resistance bands",
    "score": 88,
    "trend": "up",
    "growth_rate": 12.3
  }
]
```

---

### Analysis Endpoints

#### Request Product Analysis

```http
POST /api/v2/analysis
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "asin": "B08N5WRWNW",
  "analysis_types": ["full"],
  "force_refresh": false
}
```

**Response:** `202 Accepted`
```json
{
  "task_id": "analysis-abc-123",
  "asin": "B08N5WRWNW",
  "status": "processing",
  "estimated_time": 45,
  "message": "Analysis started. Check status using task_id."
}
```

---

#### Get Product Analysis

```http
GET /api/v2/analysis/{asin}
```

**Query Parameters:**
- `force_refresh` (boolean): Force new analysis | Default: false

**Response:**
```json
{
  "asin": "B08N5WRWNW",
  "status": "completed",
  "profitability": {
    "roi": 0.65,
    "profit_per_unit": 12.50,
    "monthly_profit": 1875.00,
    "fba_fees": 8.50,
    "shipping_cost": 3.50,
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
    "avg_price": 34.99,
    "price_range": [25.99, 44.99]
  },
  "recommendation": "BUY",
  "confidence": 82.3,
  "analyzed_at": "2025-10-29T10:15:00Z"
}
```

---

#### Get Quick Analysis

```http
GET /api/v2/analysis/quick/{asin}
```

**Response:**
```json
{
  "asin": "B08N5WRWNW",
  "viability_score": 75,
  "risk_level": "medium",
  "recommended_action": "buy",
  "profit_margin": 35.5,
  "roi": 42.3,
  "demand_score": 80
}
```

---

#### Get Analysis Task Status

```http
GET /api/v2/analysis/task/{task_id}
```

**Response:**
```json
{
  "task_id": "analysis-abc-123",
  "asin": "B08N5WRWNW",
  "status": "completed",
  "estimated_time": 45,
  "elapsed_time": 42
}
```

---

#### Batch Quick Analysis

```http
GET /api/v2/analysis/batch?asins=B08N5WRWNW&asins=B09ABC123
```

**Response:**
```json
[
  {
    "asin": "B08N5WRWNW",
    "viability_score": 75,
    "risk_level": "medium",
    "recommended_action": "buy"
  },
  {
    "asin": "B09ABC123",
    "viability_score": 60,
    "risk_level": "high",
    "recommended_action": "monitor"
  }
]
```

---

### Suppliers Endpoints

#### List Suppliers

```http
GET /api/v2/suppliers
```

**Query Parameters:**
- `country` (string): Filter by country
- `rating` (string): Filter by rating
- `limit` (integer): Results per page | Default: 20
- `offset` (integer): Pagination offset | Default: 0

**Response:**
```json
{
  "suppliers": [
    {
      "id": 1,
      "name": "ABC Manufacturing Co.",
      "country": "China",
      "email": "sales@abc.com",
      "rating": "4.5",
      "status": "contacted",
      "min_order_quantity": 100,
      "products_count": 5,
      "total_orders": 12
    }
  ],
  "total": 50,
  "page": 1
}
```

---

#### Generate Supplier Contact Message

```http
POST /api/v2/suppliers/contact
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "asin": "B08N5WRWNW",
  "quantity": 100,
  "custom_message": "Interested in custom branding"
}
```

**Response:**
```json
{
  "message": "Dear Supplier,\n\nWe are interested in purchasing...",
  "suppliers_contacted": 3,
  "estimated_moq": 100,
  "estimated_unit_cost": 12.50,
  "cached": false
}
```

---

### Inventory Endpoints

#### Get Inventory Status

```http
GET /api/v2/inventory
```

**Query Parameters:**
- `asin` (string): Filter by ASIN
- `status` (string): Filter by status (in_stock, low_stock, out_of_stock)
- `alert_level` (string): Filter by alert level

**Response:**
```json
{
  "inventory": [
    {
      "asin": "B08N5WRWNW",
      "quantity": 45,
      "reorder_point": 50,
      "reorder_quantity": 100,
      "unit_cost": 12.50,
      "status": "low_stock",
      "alert_level": "high",
      "days_until_stockout": 5,
      "avg_daily_sales": 9.0
    }
  ],
  "total": 120
}
```

---

#### Get Inventory Alerts

```http
GET /api/v2/inventory/alerts
```

**Response:**
```json
{
  "alerts": [
    {
      "asin": "B08N5WRWNW",
      "alert_type": "LOW_STOCK",
      "current_quantity": 15,
      "recommended_reorder": 100,
      "days_until_stockout": 3,
      "urgency": "high"
    }
  ],
  "total_alerts": 5
}
```

---

#### Trigger Reorder

```http
POST /api/v2/inventory/reorder
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "asin": "B08N5WRWNW",
  "quantity": 100
}
```

**Response:**
```json
{
  "success": true,
  "asin": "B08N5WRWNW",
  "quantity_ordered": 100,
  "estimated_delivery": "2025-11-15T00:00:00Z"
}
```

---

### WebSocket Endpoints

#### WebSocket Connection

```http
WS /api/v2/ws/updates?token=YOUR_TOKEN
```

**Connection Flow:**

1. **Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws/updates?token=YOUR_TOKEN');
```

2. **Receive Welcome:**
```json
{
  "type": "connection",
  "status": "connected",
  "timestamp": "2025-10-29T10:00:00Z",
  "message": "Connected to Amazon FBA AI Agent V2"
}
```

3. **Subscribe to Events:**
```json
{
  "type": "subscribe",
  "filters": {
    "event_types": ["product_discovered", "analysis_complete"],
    "asins": ["B08N5WRWNW"],
    "min_priority": "normal"
  }
}
```

4. **Receive Events:**
```json
{
  "event_type": "product_discovered",
  "timestamp": "2025-10-29T10:01:30Z",
  "payload": {
    "asin": "B08N5WRWNW",
    "title": "Premium Yoga Mat",
    "opportunity_score": 85.5
  }
}
```

**Event Types:**
- `product_discovered` - New product found
- `analysis_complete` - Analysis finished
- `price_optimized` - Price optimization suggested
- `inventory_alert` - Inventory alert triggered
- `supplier_contacted` - Supplier message sent

**Client Messages:**
- `ping` - Heartbeat (server responds with `pong`)
- `subscribe` - Update subscription filters
- `unsubscribe` - Remove subscription filters

**Example JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws/updates?token=YOUR_TOKEN');

ws.onopen = () => {
  // Subscribe to events
  ws.send(JSON.stringify({
    type: 'subscribe',
    filters: {
      event_types: ['product_discovered', 'analysis_complete']
    }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event received:', data);
  
  if (data.event_type === 'product_discovered') {
    // Handle new product
    updateUI(data.payload);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

---

## 📊 Data Models

### Product

```typescript
interface Product {
  asin: string;              // Required, unique, 10 chars
  title: string;             // Required, max 500 chars
  price: number;             // Required, > 0
  rating?: number;           // 0-5
  reviews_count?: number;     // >= 0
  bsr?: number;              // Best Seller Rank
  category?: string;          // Max 200 chars
  image_url?: string;         // URL
  url?: string;               // Amazon URL
  status: "discovered" | "analyzing" | "analyzed" | "approved" | "rejected";
  estimated_profit?: number;
  viability_score?: number;  // 0-100
  created_at: string;        // ISO 8601
  updated_at: string;         // ISO 8601
}
```

### Analysis

```typescript
interface FullAnalysis {
  asin: string;
  status: "pending" | "processing" | "completed" | "failed";
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
  confidence: number;         // 0-100
  analyzed_at: string;        // ISO 8601
}
```

### Inventory

```typescript
interface InventoryStatus {
  asin: string;
  quantity: number;
  reorder_point: number;
  reorder_quantity: number;
  unit_cost: number;
  location: string;
  status: "in_stock" | "low_stock" | "out_of_stock" | "reordering";
  alert_level: "none" | "low" | "medium" | "high";
  days_until_stockout?: number;
  avg_daily_sales?: number;
}
```

---

## 💡 Examples

### Complete Workflow Example

**1. Discover Products:**
```bash
curl -X POST "http://localhost:8000/api/v2/products/discover" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 3000,
    "categories": ["Sports"],
    "min_demand_score": 70
  }'
```

**2. Check Discovery Status:**
```bash
curl -X GET "http://localhost:8000/api/v2/products/discover/{task_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**3. Request Analysis:**
```bash
curl -X POST "http://localhost:8000/api/v2/analysis" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B08N5WRWNW",
    "analysis_types": ["full"]
  }'
```

**4. Get Analysis Results:**
```bash
curl -X GET "http://localhost:8000/api/v2/analysis/B08N5WRWNW" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**5. Check Inventory:**
```bash
curl -X GET "http://localhost:8000/api/v2/inventory?asin=B08N5WRWNW" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔗 Related Documentation

- [AGENTS.md](./AGENTS.md) - Agent system documentation
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md) - System architecture

---

## 📝 Version History

- **v2.0.0** (2025-10-29) - Initial release with REST API and WebSocket support

---

## 🆘 Support

For issues or questions:
- GitHub Issues: [Link]
- Documentation: [Link]
- Email: support@example.com

