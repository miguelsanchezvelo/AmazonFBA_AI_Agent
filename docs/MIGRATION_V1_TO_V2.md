# 🔄 Amazon FBA AI Agent - Migration Guide V1 to V2

**Version:** 2.0.0  
**Last Updated:** 2025-10-29

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Migration Timeline](#migration-timeline)
3. [Backward Compatibility](#backward-compatibility)
4. [Data Migration](#data-migration)
5. [Code Migration](#code-migration)
6. [Migration Checklist](#migration-checklist)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### What Changed in V2?

**V1 Architecture:**
- Sequential pipeline (blocking)
- Scripts-based (Python scripts)
- CSV file storage
- Streamlit dashboards
- Synchronous processing

**V2 Architecture:**
- Event-driven multi-agent system
- REST API + WebSocket
- PostgreSQL database
- React frontend
- Asynchronous processing

### Key Benefits

- ✅ **3x faster** processing (parallel agents)
- ✅ **Real-time updates** via WebSocket
- ✅ **Better scalability** (horizontal scaling)
- ✅ **API-first** design
- ✅ **Database persistence** (no CSV files)

---

## 📅 Migration Timeline

### Recommended Timeline: 4 Weeks

**Week 1: Preparation**
- Review V2 architecture
- Set up V2 environment
- Test V2 with sample data
- Train team on new system

**Week 2: Data Migration**
- Migrate CSV data to PostgreSQL
- Verify data integrity
- Set up V2 in staging

**Week 3: Gradual Migration**
- Run V1 and V2 in parallel
- Redirect 25% traffic to V2
- Monitor and compare results
- Fix issues

**Week 4: Complete Migration**
- 100% traffic to V2
- V1 in read-only mode
- Final verification
- Deprecate V1

---

## 🔄 Backward Compatibility

### What Still Works

✅ **V1 Scripts** - Can call V2 API internally:
```python
# V1 script (product_discovery.py)
import requests

def discover_products(budget):
    # Calls V2 API internally
    response = requests.post(
        "http://localhost:8000/api/v2/products/discover",
        json={"budget": budget}
    )
    # Still saves CSV for compatibility
    save_to_csv(response.json())
```

✅ **CSV Export** - V2 can export to CSV:
```http
GET /api/v2/products/export?format=csv
```

✅ **Streamlit Dashboards** - Can be adapted to use V2 API:
```python
# streamlit_dashboard.py
import requests
import streamlit as st

response = requests.get("http://localhost:8000/api/v2/products")
products = response.json()["products"]
st.dataframe(products)
```

### What Changed

❌ **Direct CSV access** - Data is now in PostgreSQL  
❌ **Script execution order** - Events drive processing  
❌ **Synchronous waiting** - Use async/tasks instead  

---

## 💾 Data Migration

### Step 1: Export V1 Data

```bash
# Export all CSV files
python scripts/export_v1_data.py

# This creates:
# - data/products_backup.csv
# - data/analysis_backup.csv
# - data/inventory_backup.csv
# - data/suppliers_backup.csv
```

### Step 2: Transform Data

```python
# scripts/migrate_data.py
import pandas as pd
from backend.database.session import Session
from backend.database.models import Product

def migrate_products():
    """Migrate products from CSV to PostgreSQL."""
    # Read CSV
    df = pd.read_csv("data/products_backup.csv")
    
    # Transform and insert
    db = Session()
    try:
        for _, row in df.iterrows():
            product = Product(
                asin=row["asin"],
                title=row["title"],
                price=float(row["price"]),
                rating=float(row.get("rating", 0)),
                reviews_count=int(row.get("reviews_count", 0)),
                bsr=int(row.get("bsr", 0)) if pd.notna(row.get("bsr")) else None,
                category=row.get("category"),
                status="discovered"
            )
            db.add(product)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_products()
```

### Step 3: Verify Migration

```python
# scripts/verify_migration.py
from backend.database.session import Session
from backend.database.models import Product
import pandas as pd

def verify():
    """Verify data migration."""
    db = Session()
    
    # Count products
    v2_count = db.query(Product).count()
    
    # Count CSV
    df = pd.read_csv("data/products_backup.csv")
    v1_count = len(df)
    
    print(f"V1 products: {v1_count}")
    print(f"V2 products: {v2_count}")
    
    assert v2_count == v1_count, "Count mismatch!"
    
    # Verify sample data
    sample = db.query(Product).first()
    print(f"Sample: {sample.asin} - {sample.title}")
    
    db.close()

if __name__ == "__main__":
    verify()
```

### Step 4: Migrate Other Data

```bash
# Run migration scripts
python scripts/migrate_analysis.py
python scripts/migrate_inventory.py
python scripts/migrate_suppliers.py
```

### Migration Script Template

```python
#!/usr/bin/env python3
"""Migration script template."""

import pandas as pd
from backend.database.session import Session
from backend.database.models import YourModel

def migrate():
    """Migrate data from CSV to database."""
    # Read CSV
    df = pd.read_csv("data/your_backup.csv")
    
    # Transform
    db = Session()
    try:
        for _, row in df.iterrows():
            # Create model instance
            instance = YourModel(
                field1=row["field1"],
                field2=row.get("field2"),
                # ... map all fields
            )
            db.add(instance)
        
        db.commit()
        print(f"Migrated {len(df)} records")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
```

---

## 💻 Code Migration

### V1 → V2 API Mapping

#### Product Discovery

**V1:**
```python
# product_discovery.py
def discover_products(budget):
    # ... SerpAPI calls ...
    save_to_csv(products)
```

**V2:**
```python
import requests

def discover_products(budget):
    response = requests.post(
        "http://localhost:8000/api/v2/products/discover",
        json={"budget": budget}
    )
    task = response.json()
    
    # Poll for completion
    while True:
        status = requests.get(
            f"http://localhost:8000/api/v2/products/discover/{task['task_id']}"
        ).json()
        if status["status"] == "completed":
            return status["products"]
        time.sleep(2)
```

#### Market Analysis

**V1:**
```python
# market_analysis.py
def analyze_product(asin):
    # ... analysis ...
    save_to_csv(result)
```

**V2:**
```python
# Request analysis
response = requests.post(
    "http://localhost:8000/api/v2/analysis",
    json={"asin": asin, "analysis_types": ["full"]}
)
task = response.json()

# Get results
analysis = requests.get(
    f"http://localhost:8000/api/v2/analysis/{asin}"
).json()
```

#### Inventory Management

**V1:**
```python
# inventory_management.py
def check_inventory():
    df = pd.read_csv("data/inventory.csv")
    # ... process ...
```

**V2:**
```python
# Get inventory
response = requests.get(
    "http://localhost:8000/api/v2/inventory"
)
inventory = response.json()["inventory"]

# Get alerts
alerts = requests.get(
    "http://localhost:8000/api/v2/inventory/alerts"
).json()
```

### WebSocket Migration

**V1:** Polling for updates
```python
while True:
    data = check_for_updates()
    if data:
        process(data)
    time.sleep(5)
```

**V2:** WebSocket real-time updates
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data["event_type"] == "product_discovered":
        process_product(data["payload"])

ws = websocket.WebSocketApp(
    "ws://localhost:8000/api/v2/ws/updates?token=YOUR_TOKEN",
    on_message=on_message
)
ws.run_forever()
```

---

## ✅ Migration Checklist

### Pre-Migration

- [ ] Backup all V1 data (CSV files)
- [ ] Review V2 architecture documentation
- [ ] Set up V2 development environment
- [ ] Test V2 with sample data
- [ ] Train team on V2

### Data Migration

- [ ] Export V1 CSV files
- [ ] Create migration scripts
- [ ] Run product migration
- [ ] Run analysis migration
- [ ] Run inventory migration
- [ ] Run supplier migration
- [ ] Verify all data migrated
- [ ] Verify data integrity

### Code Migration

- [ ] Update scripts to use V2 API
- [ ] Migrate Streamlit dashboards
- [ ] Update automation scripts
- [ ] Test all integrations
- [ ] Update documentation

### Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] End-to-end tests pass
- [ ] Performance tests pass
- [ ] Security tests pass

### Deployment

- [ ] Deploy V2 to staging
- [ ] Run V1 and V2 in parallel
- [ ] Gradual traffic migration (25%, 50%, 75%, 100%)
- [ ] Monitor metrics
- [ ] Fix issues

### Completion

- [ ] 100% traffic on V2
- [ ] V1 in read-only mode
- [ ] Archive V1 data
- [ ] Update documentation
- [ ] Communicate changes to users

---

## 🔧 Troubleshooting

### Data Migration Issues

**Problem:** Missing fields in V2  
**Solution:**
- Add default values for missing fields
- Map old fields to new schema
- Handle NULL values

**Problem:** Data type mismatches  
**Solution:**
- Convert types during migration
- Validate data before insert
- Use try/except for bad data

### API Migration Issues

**Problem:** V1 scripts failing  
**Solution:**
- Check API endpoint URLs
- Verify authentication tokens
- Handle async responses properly

**Problem:** Performance regression  
**Solution:**
- Use caching
- Optimize database queries
- Enable connection pooling

### Rollback Procedure

If migration fails:

```bash
# 1. Stop V2
docker-compose down

# 2. Restore V1 data
cp data/products_backup.csv data/products.csv

# 3. Restart V1
python fba_agent.py

# 4. Restore V1 database (if needed)
# Restore from backup
```

---

## 📚 Related Documentation

- [API.md](./API.md) - V2 API documentation
- [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md) - V2 architecture
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide

---

## 🆘 Support

For migration issues:
- GitHub Issues: [Link]
- Email: support@example.com

