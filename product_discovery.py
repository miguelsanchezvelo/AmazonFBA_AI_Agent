import os
import csv
import re
from math import floor
from typing import List, Dict, Optional

from dotenv import load_dotenv
from serpapi import GoogleSearch

# Load environment and validate API key
load_dotenv()
API_KEY = os.getenv("SERPAPI_API_KEY")
if not API_KEY:
    raise SystemExit("Fatal: SERPAPI_API_KEY not set in environment")

# Constants
CATEGORIES = ["kitchen", "pets", "fitness", "baby", "home"]
DATA_PATH = os.path.join("data", "product_results.csv")
FIXED_COST = 200.0
FBA_FEE_RATE = 0.2
COST_RATE = 0.5


def parse_price(value) -> Optional[float]:
    """Extract a float price from a raw SerpAPI value."""
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("raw") or value.get("value")
    match = re.search(r"\d+\.\d+|\d+", str(value))
    return float(match.group()) if match else None


def extract_asin_from_url(url: str) -> Optional[str]:
    """Return ASIN if present in the URL."""
    if not url:
        return None
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None


def search_category(category: str) -> List[Dict]:
    params = {
        "engine": "amazon",
        "type": "search",
        "search_term": category,
        "amazon_domain": "amazon.com",
        "page": 1,
        "api_key": API_KEY,
    }
    search = GoogleSearch(params)
    data = search.get_dict()
    return data.get("organic_results", []) or []


def discover_products(variable_budget: float) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for category in CATEGORIES:
        raw_items = search_category(category)
        print(f"Category '{category}' returned {len(raw_items)} results")
        skipped = 0
        for item in raw_items:
            price = parse_price(item.get("price"))
            url = item.get("link") or item.get("url")
            asin = extract_asin_from_url(url)

            if price is None or asin is None or price > variable_budget:
                skipped += 1
                continue

            est_cost = price * COST_RATE
            fba_fees = price * FBA_FEE_RATE
            unit_margin = price - est_cost - fba_fees
            units_possible = floor(variable_budget / est_cost)
            if units_possible <= 0:
                skipped += 1
                continue
            total_est_profit = unit_margin * units_possible

            results.append({
                "title": item.get("title"),
                "price": price,
                "est_cost": est_cost,
                "fba_fees": fba_fees,
                "unit_margin": unit_margin,
                "units_possible": units_possible,
                "total_est_profit": total_est_profit,
                "asin": asin,
                "link": url,
            })
        print(f"Skipped {skipped} products for '{category}'\n")
    return results


def save_to_csv(products: List[Dict[str, object]]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "price",
                "est_cost",
                "fba_fees",
                "unit_margin",
                "units_possible",
                "total_est_profit",
                "asin",
                "link",
            ],
        )
        writer.writeheader()
        for row in products:
            writer.writerow(row)


def print_report(products: List[Dict[str, object]]):
    header = (
        f"{'Title':40} | {'Price':>6} | {'Margin':>6} | {'Units':>5} | {'Total Profit':>12}"
    )
    print(header)
    print("-" * len(header))
    for p in products:
        title = (p.get("title") or "")[:40]
        print(
            f"{title:40} | "
            f"${p['price']:>6.2f} | "
            f"${p['unit_margin']:>6.2f} | "
            f"{p['units_possible']:>5} | "
            f"${p['total_est_profit']:>11.2f}"
        )


def main():
    try:
        budget = float(input("Enter your total startup budget in USD: "))
    except ValueError:
        raise SystemExit("Invalid budget amount")

    variable_budget = budget - FIXED_COST
    if variable_budget <= 0:
        raise SystemExit("Budget too low after reserving fixed costs")

    products = discover_products(variable_budget)
    if not products:
        raise SystemExit("No valid products found")

    products.sort(key=lambda x: x["total_est_profit"], reverse=True)
    top_products = products[:10]

    print_report(top_products)
    save_to_csv(top_products)
    print(f"Saved {len(top_products)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
