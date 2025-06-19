import argparse
import os
import csv
import json
from typing import List, Optional

CONFIG_FILE = "config.json"
DATA_DIR = "data"
CSV_FILE = os.path.join(DATA_DIR, "mock_market_data.csv")
FIELDNAMES = [
    "asin",
    "title",
    "price",
    "rating",
    "reviews",
    "bsr",
    "link",
    "source",
    "score",
    "estimated",
]


def load_keys():
    """Return SerpAPI and Keepa keys from env or config."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
    serp = os.getenv("SERPAPI_API_KEY") or config.get("serpapi_key")
    keepa = os.getenv("KEEPA_API_KEY") or config.get("keepa_key")
    return serp, keepa


def create_mock_csv() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CSV_FILE):
        return

    products = [
        {
            "asin": "B0MOCK001",
            "title": "Wireless Bluetooth Earbuds",
            "price": 39.99,
            "rating": 4.5,
            "reviews": 2400,
            "bsr": 120,
            "link": "https://example.com/B0MOCK001",
            "source": "serpapi",
            "score": "HIGH",
            "estimated": False,
        },
        {
            "asin": "B0MOCK002",
            "title": "Organic Green Tea Bags, 100 Count",
            "price": 15.99,
            "rating": 4.4,
            "reviews": 1600,
            "bsr": 780,
            "link": "https://example.com/B0MOCK002",
            "source": "serpapi",
            "score": "HIGH",
            "estimated": False,
        },
        {
            "asin": "B0MOCK003",
            "title": "Non-Slip Yoga Mat 6mm",
            "price": 21.95,
            "rating": 4.2,
            "reviews": 540,
            "bsr": 1300,
            "link": "https://example.com/B0MOCK003",
            "source": "keepa",
            "score": "MEDIUM",
            "estimated": False,
        },
        {
            "asin": "B0MOCK004",
            "title": "USB-C Laptop Docking Station",
            "price": 84.5,
            "rating": 4.1,
            "reviews": 310,
            "bsr": 2500,
            "link": "https://example.com/B0MOCK004",
            "source": "keepa",
            "score": "MEDIUM",
            "estimated": False,
        },
        {
            "asin": "B0MOCK005",
            "title": "Stainless Steel Water Bottle 32oz",
            "price": 18.75,
            "rating": 4.6,
            "reviews": 2900,
            "bsr": 450,
            "link": "https://example.com/B0MOCK005",
            "source": "manual",
            "score": "HIGH",
            "estimated": False,
        },
        {
            "asin": "B0MOCK006",
            "title": "Smart Plug WiFi Outlet 2 Pack",
            "price": 25.99,
            "rating": 4.3,
            "reviews": 1500,
            "bsr": 900,
            "link": "https://example.com/B0MOCK006",
            "source": "manual",
            "score": "HIGH",
            "estimated": True,
        },
        {
            "asin": "B0MOCK007",
            "title": "Kids Art Supplies Set",
            "price": 29.5,
            "rating": 4.0,
            "reviews": 220,
            "bsr": 1750,
            "link": "https://example.com/B0MOCK007",
            "source": "serpapi",
            "score": "LOW",
            "estimated": False,
        },
    ]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(products)
    print(f"Mock data created at {CSV_FILE} for offline mode.")


def main(argv: Optional[List[str]] = None) -> None:
    global CONFIG_FILE, CSV_FILE

    parser = argparse.ArgumentParser(description="Generate local mock data if APIs are unavailable")
    parser.add_argument("--config", default=CONFIG_FILE, help="Path to optional config JSON")
    parser.add_argument("--output", default=CSV_FILE, help="Output CSV file")
    args = parser.parse_args(argv)
    CONFIG_FILE = args.config
    CSV_FILE = args.output

    serp, keepa = load_keys()
    if serp or keepa:
        print("APIs available — mock data generation skipped.")
        return

    create_mock_csv()


if __name__ == "__main__":
    main()
