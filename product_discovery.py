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


def discover_products(budget: float) -> List[Dict]:
    found = []
    for keyword in KEYWORDS:
        items = search_products(keyword)
        count = 0
        for item in items:
            price = item.get("extracted_price")
            if price is None:
                price = parse_price(item.get("price"))
            if price is None or price > budget:
                continue
            found.append({
                "category": keyword,
                "title": item.get("title"),
                "price": price,
                "product_id": item.get("product_id") or item.get("asin"),
                "link": item.get("link"),
            })
            count += 1
            if len(found) >= MAX_RESULTS:
                return found
        print(f"{keyword}: {count} valid products found")
    return found


def save_to_csv(products: List[Dict]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["category", "title", "price", "product_id", "link"],
        )
        writer.writeheader()
        for item in products:
            writer.writerow(item)


def main():
    try:
        budget = float(input("Enter your maximum unit price in USD: "))
    except ValueError:
        print("Invalid budget")
        return

    products = discover_products(budget)
    products.sort(key=lambda x: x["price"])  # sort by price ascending
    save_to_csv(products)
    print(f"Saved {len(products)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
