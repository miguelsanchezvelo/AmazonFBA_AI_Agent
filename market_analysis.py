import os
import csv
import re
import argparse
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()
API_KEY = os.getenv("SERPAPI_API_KEY")
if not API_KEY:
    raise EnvironmentError("SERPAPI_API_KEY not set in environment")

DATA_PATH = os.path.join("data", "market_analysis_results.csv")
# Default CSV produced by product_discovery.py
DISCOVERY_CSV = os.path.join("data", "product_results.csv")


def parse_float(value: str) -> Optional[float]:
    """Return float from string like '4.5 out of 5' or '$12.34'."""
    if value is None:
        return None
    match = re.search(r"\d+\.\d+|\d+", value)
    return float(match.group()) if match else None


def is_valid_asin(asin: str) -> bool:
    """Return True if the string looks like a valid 10-character ASIN."""
    return bool(re.fullmatch(r"[A-Z0-9]{10}", asin.upper()))


def evaluate_potential(product: Dict[str, Optional[float]]) -> str:
    """Return HIGH/MEDIUM/LOW score based on rating and review count."""
    rating = product.get("rating") or 0
    reviews = product.get("reviews") or 0
    bsr = product.get("bsr")
    if rating >= 4.3 and reviews >= 300 and bsr:
        return "HIGH"
    if rating >= 4.0:
        return "MEDIUM"
    return "LOW"


def fetch_product_info(asin: str) -> Optional[Dict[str, str]]:
    """Fetch product information from SerpAPI for a single ASIN."""
    params = {
        "engine": "amazon",
        "api_key": API_KEY,
        "amazon_domain": "amazon.com",
        "type": "product",
        "asin": asin,
    }
    try:
        search = GoogleSearch(params)
        result = search.get_dict()
    except Exception as exc:
        print(f"Error fetching {asin}: {exc}")
        return None

    product = result.get("product_results") or {}
    if not product:
        print(f"No data for ASIN {asin}")
        return None

    title = product.get("title")
    price_raw = product.get("price", {}).get("raw") if isinstance(product.get("price"), dict) else product.get("price")
    price = parse_float(price_raw)
    rating = parse_float(str(product.get("rating")))
    reviews = parse_float(str(product.get("reviews")))
    link = product.get("url") or product.get("link")

    bsr = None
    info = result.get("product_information", [])
    for item in info:
        if "Best Sellers Rank" in item.get("title", ""):
            bsr = item.get("value")
            break
    if not bsr:
        bsr = product.get("best_sellers_rank")

    return {
        "asin": asin,
        "title": title,
        "price": price,
        "rating": rating,
        "reviews": reviews,
        "bsr": bsr,
        "link": link,
    }


def process_asins(asins: List[str]) -> List[Dict[str, str]]:
    results = []
    for asin in asins:
        asin = asin.strip()
        if not asin:
            continue
        if not is_valid_asin(asin):
            print(f"Invalid ASIN {asin}, skipping")
            continue
        data = fetch_product_info(asin)
        if data:
            data["score"] = evaluate_potential(data)
            results.append(data)
        else:
            print(f"Skipping ASIN {asin}")
        time.sleep(1)  # small delay for rate limits
    return results


def load_asins_from_csv(path: str) -> List[str]:
    """Return list of ASINs from a CSV file column named 'asin'."""
    asins = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "asin" not in reader.fieldnames:
                print(f"CSV {path} is missing an 'asin' column")
                return []
            for row in reader:
                val = row.get("asin")
                if val:
                    asins.append(val.strip())
    except FileNotFoundError:
        print(f"File not found: {path}")
        return []
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return []
    return asins


def save_to_csv(products: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["asin", "title", "price", "rating", "reviews", "bsr", "link", "score"],
        )
        writer.writeheader()
        for item in products:
            writer.writerow(item)


def print_report(products: List[Dict[str, str]]):
    for p in products:
        print(f"ASIN: {p['asin']}")
        print(f"Title: {p.get('title')}")
        print(f"Price: {p.get('price')}")
        print(f"Rating: {p.get('rating')} ({p.get('reviews')} reviews)")
        print(f"BSR: {p.get('bsr')}")
        print(f"Score: {p.get('score')}")
        print(f"Link: {p.get('link')}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze Amazon ASINs")
    parser.add_argument("--csv", help="optional CSV file with asin column")
    args = parser.parse_args()

    if args.csv:
        asins = load_asins_from_csv(args.csv)
        if not asins:
            print(f"No ASINs found in {args.csv}")
            return
    else:
        prompt = (
            "Enter ASIN(s) separated by comma "
            f"(press Enter to load from {DISCOVERY_CSV}): "
        )
        asin_input = input(prompt).strip()
        if asin_input:
            asins = [a.strip() for a in asin_input.split(",") if a.strip()]
        else:
            asins = load_asins_from_csv(DISCOVERY_CSV)
            if not asins:
                print(
                    f"Could not load ASINs from {DISCOVERY_CSV}. "
                    "Ensure the file exists and has an 'asin' column."
                )
                return
            print(f"Loaded {len(asins)} ASINs from {DISCOVERY_CSV}")

    if not asins:
        print("No ASINs provided")
        return
    products = process_asins(asins)
    print_report(products)
    save_to_csv(products)
    print(f"Saved {len(products)} results to {DATA_PATH}")


if __name__ == "__main__":
    main()
