import os
import csv
import re
from typing import List, Dict

from dotenv import load_dotenv
from serpapi import GoogleSearch

# Load SERPAPI_API_KEY from .env
load_dotenv()
API_KEY = os.getenv("SERPAPI_API_KEY")
if not API_KEY:
    raise EnvironmentError("SERPAPI_API_KEY not set in environment")

# Predefined product keywords/categories
KEYWORDS = ["kitchen", "fitness", "pets", "baby", "office", "gadgets"]

MAX_RESULTS = 20
DATA_PATH = os.path.join("data", "product_results.csv")

# Reserve this amount from the startup budget for tools/subscriptions
FIXED_COST = 200.0

# Portion of the sale price taken by FBA fees
FBA_FEE_RATE = 0.2

# Estimated manufacturing cost as a portion of sale price
COST_RATE = 0.5

# Estimated number of units used to derive a per-unit budget
ORDER_SIZE_ESTIMATE = 20


def parse_price(value: str) -> float:
    """Extract float price from a string like '$12.34'."""
    if value is None:
        return None
    numbers = re.findall(r"\d+\.\d+|\d+", value)
    if not numbers:
        return None
    return float(numbers[0])


def search_products(keyword: str) -> List[Dict]:
    """Search Google Shopping for the given keyword and return item list."""
    params = {
        "engine": "google_shopping",
        "q": keyword,
        "api_key": API_KEY,
        "hl": "en",
        "gl": "us",
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("shopping_results", []) or []


def discover_products(variable_budget: float) -> List[Dict]:
    """Search for products and calculate potential margins."""
    found = []
    per_unit_budget = variable_budget / ORDER_SIZE_ESTIMATE
    price_cap = per_unit_budget * 0.7
    for keyword in KEYWORDS:
        items = search_products(keyword)
        count = 0
        for item in items:
            sale_price = item.get("extracted_price")
            if sale_price is None:
                sale_price = parse_price(item.get("price"))
            if sale_price is None:
                continue
            if sale_price > price_cap:
                continue

            unit_cost = sale_price * COST_RATE
            fba_fee = sale_price * FBA_FEE_RATE
            unit_margin = sale_price - unit_cost - fba_fee
            quantity = int(variable_budget // unit_cost)
            if quantity <= 0:
                continue
            total_margin = unit_margin * quantity

            found.append({
                "category": keyword,
                "title": item.get("title"),
                "sale_price": sale_price,
                "unit_cost": unit_cost,
                "unit_margin": unit_margin,
                "quantity": quantity,
                "total_margin": total_margin,
                "product_id": item.get("product_id") or item.get("asin"),
                "link": item.get("link"),
            })
            count += 1
            if len(found) >= MAX_RESULTS:
                return found
        print(f"{keyword}: {count} opportunities found")
    return found


def save_to_csv(products: List[Dict]):
    """Save ranked product results to CSV."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "category",
                "title",
                "sale_price",
                "unit_cost",
                "unit_margin",
                "quantity",
                "total_margin",
                "product_id",
                "link",
            ],
        )
        writer.writeheader()
        for item in products:
            writer.writerow(item)


def print_report(products: List[Dict]):
    header = (
        f"{'Title':50} | {'Price':>6} | {'Est. Cost':>9} | "
        f"{'Est. Margin':>10} | {'Units':>5} | {'Total Profit':>12}"
    )
    print(header)
    print("-" * len(header))
    for p in products:
        title = (p["title"] or "")[:50]
        print(
            f"{title:50} | "
            f"${p['sale_price']:>6.2f} | "
            f"${p['unit_cost']:>8.2f} | "
            f"${p['unit_margin']:>9.2f} | "
            f"{p['quantity']:>5} | "
            f"${p['total_margin']:>11.2f}"
        )


def main():
    try:
        budget = float(input("Enter your total startup budget in USD: "))
    except ValueError:
        print("Invalid budget")
        return

    variable_budget = budget - FIXED_COST
    if variable_budget <= 0:
        print("Budget is too low after reserving fixed costs")
        return

    products = discover_products(variable_budget)
    products.sort(key=lambda x: x["total_margin"], reverse=True)
    top_products = products[:10]
    print_report(top_products)
    save_to_csv(top_products)
    print(f"Saved {len(top_products)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
