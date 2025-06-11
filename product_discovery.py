import os
import csv
import re
import argparse
from typing import List, Dict, Optional

from dotenv import load_dotenv
from serpapi import GoogleSearch

# Load SERPAPI_API_KEY from .env
load_dotenv()
API_KEY = os.getenv("SERPAPI_API_KEY")
if not API_KEY:
    raise EnvironmentError("SERPAPI_API_KEY not set in environment")

# Predefined product keywords/categories
DEFAULT_KEYWORDS = ["kitchen", "pets", "fitness", "baby", "home"]


def get_keywords() -> List[str]:
    """Return list of keywords from env or fall back to defaults."""
    env_val = os.getenv("SEARCH_KEYWORDS")
    if env_val:
        kws = [k.strip() for k in env_val.split(",") if k.strip()]
        return kws if kws else DEFAULT_KEYWORDS
    return DEFAULT_KEYWORDS


KEYWORDS = get_keywords()

MAX_RESULTS = 20
DATA_PATH = os.path.join("data", "product_results.csv")

# Reserve this amount from the startup budget for tools/subscriptions
FIXED_COST = float(os.getenv("FIXED_COST", "200"))

# Portion of the sale price taken by FBA fees
FBA_FEE_RATE = 0.2

# Estimated manufacturing cost as a portion of sale price
COST_RATE = 0.5


def parse_price(value) -> Optional[float]:
    """Return float price from a string or dict such as {'raw': '$12.34'}."""
    if value is None:
        return None
    if isinstance(value, dict):
        if "value" in value:
            try:
                return float(value["value"])
            except (TypeError, ValueError):
                pass
        value = value.get("raw")
    numbers = re.findall(r"\d+\.\d+|\d+", str(value))
    if not numbers:
        return None
    return float(numbers[0])


def extract_asin_from_url(url: str) -> Optional[str]:
    """Return ASIN if URL contains '/dp/ASIN' pattern."""
    if not url:
        return None
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not match:
        return None
    return match.group(1)


def search_products(keyword: str) -> List[Dict]:
    """Search Amazon for the given keyword and return organic results."""
    params = {
        "engine": "amazon",
        "amazon_domain": "amazon.com",
        "type": "search",
        "keyword": keyword,
        "page": 1,
        "api_key": API_KEY,
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("organic_results", []) or []


def discover_products(variable_budget: float) -> List[Dict]:
    """Search for products and calculate potential margins."""
    found = []
    for keyword in KEYWORDS:
        items = search_products(keyword)
        if not items:
            print(f"Warning: no products returned for keyword '{keyword}'")
            continue
        valid_asin_found = False
        for item in items:
            sale_price = parse_price(item.get("price"))
            if sale_price is None:
                continue
            if sale_price > variable_budget:
                continue

            link = item.get("link") or item.get("url")
            asin = extract_asin_from_url(link)
            if asin is None:
                continue
            valid_asin_found = True

            unit_cost = sale_price * COST_RATE
            fba_fee = sale_price * FBA_FEE_RATE
            unit_margin = sale_price - unit_cost - fba_fee
            quantity = int(variable_budget // unit_cost)
            if quantity <= 0:
                continue
            total_est_profit = unit_margin * quantity

            found.append({
                "title": item.get("title"),
                "price": sale_price,
                "est_cost": unit_cost,
                "fba_fees": fba_fee,
                "unit_margin": unit_margin,
                "units_possible": quantity,
                "total_est_profit": total_est_profit,
                "asin": asin,
                "link": link,
            })
            if len(found) >= MAX_RESULTS:
                return found
        if not valid_asin_found:
            print(f"Warning: no valid ASINs found for keyword '{keyword}'")
        # silently continue if no products found
    if not found:
        print("No products found that meet the criteria")
    return found


def save_to_csv(products: List[Dict]):
    """Save ranked product results to CSV."""
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
        for item in products:
            writer.writerow(item)


def print_report(products: List[Dict]):
    if not products:
        print("No results to display")
        return
    header = (
        f"{'Title':40} | {'Price':>6} | {'Margin':>6} | "
        f"{'Units':>5} | {'Total Profit':>12}"
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
    parser = argparse.ArgumentParser(description="Discover Amazon FBA opportunities")
    parser.add_argument("--reserve", type=float, help="override fixed cost reserve")
    args = parser.parse_args()

    reserve = args.reserve if args.reserve is not None else FIXED_COST

    try:
        budget = float(input("Enter your total startup budget in USD: "))
    except ValueError:
        print("Invalid budget")
        return

    variable_budget = budget - reserve
    if variable_budget <= 0:
        print("Budget is too low after reserving fixed costs")
        return

    products = discover_products(variable_budget)
    if not products:
        return
    products.sort(key=lambda x: x["total_est_profit"], reverse=True)
    top_products = products[:10]
    print_report(top_products)
    save_to_csv(top_products)
    print(f"Saved {len(top_products)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
