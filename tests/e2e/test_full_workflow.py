#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E smoke tests for Amazon FBA AI Agent V2."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

from backend.api.config import settings
from backend.api.dependencies import create_access_token
from backend.api.main import app
from backend.database import session as db_session
from backend.models.product import ProductCreate


def test_full_workflow_end_to_end(tmp_path: Path) -> None:
    """Run a smoke scenario covering core API endpoints and async orchestration.

    Args:
        tmp_path: Temporary path provided by pytest.
    """
    # Configure isolated SQLite database for this E2E run.
    db_path: Path = tmp_path / "e2e_workflow.db"
    settings.database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    db_session.async_engine = None
    db_session.AsyncSessionLocal = None

    # Ensure database schema exists before hitting the API.
    asyncio.run(db_session.init_db())

    # Prepare authentication headers and rate-limit identifiers.
    token: str = create_access_token("e2e-user@example.com")
    auth_headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "X-Client-ID": "e2e-suite"
    }

    # Instantiate HTTP client that respects FastAPI lifespan events.
    with TestClient(app) as client:
        # Hit health endpoint to verify application startup.
        health_response = client.get(f"{settings.api_prefix}/health")
        assert health_response.status_code == 200

        # Create a mock product through the API to exercise DB + cache layers.
        product_payload = ProductCreate(
            asin="B08E2ETEST",
            title="E2E Test Product",
            price=29.99,
            rating=4.6,
            reviews_count=250,
            category="fitness"
        )
        product_payload_dict = product_payload.model_dump()
        product_payload_dict["price"] = float(product_payload_dict["price"])
        create_response = client.post(
            f"{settings.api_prefix}/products/",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=product_payload_dict
        )
        assert create_response.status_code == 201
        created_product = create_response.json()
        assert created_product["asin"] == product_payload.asin

        # Fetch collection endpoint to confirm listing works and includes the product.
        list_response = client.get(f"{settings.api_prefix}/products/")
        assert list_response.status_code == 200
        products_data = list_response.json()
        assert any(item["asin"] == product_payload.asin for item in products_data["products"])

        # Retrieve product details by ASIN.
        detail_response = client.get(
            f"{settings.api_prefix}/products/{product_payload.asin}"
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["title"] == product_payload.title

        # Kick off discovery pipeline to ensure event bus + cache path works.
        discovery_response = client.post(
            f"{settings.api_prefix}/products/discover",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "budget": 5000,
                "categories": ["fitness"],
                "min_demand_score": 70,
                "auto_analyze": True
            }
        )
        assert discovery_response.status_code == 202
        discovery_payload = discovery_response.json()
        assert discovery_payload["status"] == "pending"

        # Poll discovery status to verify task persistence through cache manager.
        status_response = client.get(
            f"{settings.api_prefix}/products/discover/{discovery_payload['task_id']}"
        )
        assert status_response.status_code == 200
        assert status_response.json()["task_id"] == discovery_payload["task_id"]

    # Close database connections and cleanup temporary SQLite file.
    asyncio.run(db_session.close_db_connections())
    if db_path.exists():
        db_path.unlink()
