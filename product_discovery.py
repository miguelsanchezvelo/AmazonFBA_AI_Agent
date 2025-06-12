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

# Summary counters
total_products_considered = 0
skipped_invalid_asin = 0
skipped_missing_price = 0
total_valid_products_saved = 0


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


def is_valid_asin(asin: str) -> bool:
    """Check if an ASIN returns valid product data from SerpAPI."""
    params = {
        "engine": "amazon",
        "type": "product",
        "amazon_domain": "amazon.com",
        "asin": asin,
        "api_key": API_KEY,
    }
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
    except Exception:
        return False
    if not data or "error" in data:
        return False
    product = data.get("product_results") or {}
    if not product and not data.get("product_information"):
        return False
    title = product.get("title")
    price_val = product.get("price")
    if price_val is not None:
        price = parse_price(price_val)
    else:
        price = None
    if not title or price is None:
        return False
    return True


def log_skipped(reason: str, product: dict):
    """Print a concise message for a skipped product."""
    title = (product.get("title") or "")[:40]
    print(f"SKIPPED ({reason}): {title}")


def search_category(category: str) -> List[Dict]:
    params = {
        "engine": "amazon",
        "type": "search",
        # "k" is the search query parameter for Amazon results
        "k": category,
        "amazon_domain": "amazon.com",
        "gl": "us",
        "hl": "en",
        "page": 1,
        "api_key": API_KEY,
    }
    search = GoogleSearch(params)
    data = search.get_dict()
    if "error" in data:
        print("SERPAPI ERROR:", data["error"])
    return data.get("organic_results", []) or []


def discover_products(variable_budget: float) -> List[Dict[str, object]]:
    global total_products_considered, skipped_invalid_asin, skipped_missing_price, total_valid_products_saved
    results: List[Dict[str, object]] = []
    total_missing_price = 0
    total_zero_cost = 0
    total_missing_asin = 0
    for category in CATEGORIES:
        raw_items = search_category(category)
        print(f"Category '{category}' returned {len(raw_items)} results")
        skipped_missing_price_cat = 0
        skipped_zero_cost = 0
        skipped_missing_asin = 0
        skipped_other = 0
        for item in raw_items:
            total_products_considered += 1
            price = parse_price(item.get("price"))
            if price is None or not isinstance(price, (int, float)) or price <= 0:
                skipped_missing_price += 1
                skipped_missing_price_cat += 1
                log_skipped("missing/invalid price", item)
                continue

            url = item.get("link") or item.get("url")
            asin = extract_asin_from_url(url)
            if asin is None:
                skipped_missing_asin += 1
                log_skipped("missing ASIN", item)
                continue
            if not is_valid_asin(asin):
                skipped_invalid_asin += 1
                print(f"Invalid ASIN: {asin} → skipped")
                continue

            if price > variable_budget:
                skipped_other += 1
                log_skipped("over budget", item)
                continue

            est_cost = price * COST_RATE
            if est_cost <= 0:
                skipped_zero_cost += 1
                log_skipped("zero est cost", item)
                continue

            fba_fees = price * FBA_FEE_RATE
            unit_margin = price - est_cost - fba_fees
            units_possible = floor(variable_budget / est_cost)
            if units_possible <= 0:
                skipped_other += 1
                log_skipped("no units", item)
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
            total_valid_products_saved += 1
        total_missing_price += skipped_missing_price_cat
        total_zero_cost += skipped_zero_cost
        total_missing_asin += skipped_missing_asin
        total_skipped = (
            skipped_missing_price_cat
            + skipped_zero_cost
            + skipped_missing_asin
            + skipped_other
        )
        print(
            f"Skipped {total_skipped} products for '{category}' - "
            f"missing price: {skipped_missing_price_cat}, "
            f"zero cost: {skipped_zero_cost}, "
            f"missing ASIN: {skipped_missing_asin}, "
            f"other: {skipped_other}\n"
        )

    print(
        "Summary of skipped products - "
        f"missing price: {total_missing_price}, "
        f"zero cost: {total_zero_cost}, "
        f"missing ASIN: {total_missing_asin}"
    )
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
    print()
    valid_asins = total_products_considered - skipped_invalid_asin
    print(f"Total products fetched: {total_products_considered}")
    print(f"Valid ASINs: {valid_asins}")
    print(f"Skipped invalid ASINs: {skipped_invalid_asin}")
    print(f"Products saved: {total_valid_products_saved}")
    print(f"Output: {DATA_PATH}")


if __name__ == "__main__":
    main()
