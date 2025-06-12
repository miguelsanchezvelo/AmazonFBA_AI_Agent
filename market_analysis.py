import os
import csv
import re
import argparse
import time
from typing import List, Dict, Optional, Tuple

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


def fetch_product_by_title(title: str) -> Optional[Dict[str, str]]:
    """Search Amazon by title and return info from the most relevant result."""
    params = {
        "engine": "amazon",
        "api_key": API_KEY,
        "amazon_domain": "amazon.com",
        "type": "search",
        "search_term": title,
    }
    try:
        search = GoogleSearch(params)
        result = search.get_dict()
    except Exception as exc:
        print(f"Error searching for '{title}': {exc}")
        return None

    items = result.get("organic_results", []) or []
    if not items:
        print(f"No search results for '{title}'")
        return None

    # Pick item with position==1, otherwise highest rating * reviews
    best = None
    best_score = -1.0
    for item in items:
        if item.get("position") == 1:
            best = item
            break
        rating = parse_float(str(item.get("rating"))) or 0
        reviews = parse_float(str(item.get("reviews"))) or 0
        score = rating * reviews
        if score > best_score:
            best_score = score
            best = item

    if not best:
        return None

    asin = best.get("asin")
    link = best.get("link") or best.get("url")
    if not asin and link:
        m = re.search(r"/dp/([A-Z0-9]{10})", link)
        asin = m.group(1) if m else None

    price = parse_float(
        best.get("price", {}).get("raw") if isinstance(best.get("price"), dict) else best.get("price")
    )
    rating = parse_float(str(best.get("rating")))
    reviews = parse_float(str(best.get("reviews")))

    bsr = None
    if asin and is_valid_asin(asin):
        detail = fetch_product_info(asin)
        if detail:
            bsr = detail.get("bsr")

    return {
        "asin": asin,
        "title": best.get("title"),
        "price": price,
        "rating": rating,
        "reviews": reviews,
        "bsr": bsr,
        "link": link,
    }


def process_products(products: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], int, int, int]:
    """Process a list of entries containing asin and optional title."""
    results = []
    real = estimated = failed = 0
    for item in products:
        asin = (item.get("asin") or "").strip()
        title = (item.get("title") or "").strip()

        data = None
        if is_valid_asin(asin):
            data = fetch_product_info(asin)
            if data:
                data["estimated"] = False
                real += 1
        if not data and title:
            data = fetch_product_by_title(title)
            if data:
                data["estimated"] = True
                estimated += 1

        if not data:
            print(f"Failed to fetch data for entry: ASIN='{asin}' Title='{title[:40]}'")
            failed += 1
            continue

        data["score"] = evaluate_potential(data)
        results.append(data)
        time.sleep(1)  # small delay for rate limits

    return results, real, estimated, failed


def load_asins_from_csv(path: str) -> List[str]:
    """Return list of valid ASINs from a CSV file column named 'asin'."""
    asins = []
    invalid = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "asin" not in reader.fieldnames:
                print(f"CSV {path} is missing an 'asin' column")
                return []
            for row in reader:
                val = (row.get("asin") or "").strip()
                if not val:
                    continue
                if is_valid_asin(val):
                    asins.append(val)
                else:
                    invalid += 1
    except FileNotFoundError:
        print(f"File not found: {path}")
        return []
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return []
    if invalid:
        print(f"Skipped {invalid} invalid ASIN(s) in {path}")
    return asins


def load_products_from_csv(path: str) -> List[Dict[str, str]]:
    """Return list of entries with asin and title from a CSV file."""
    products = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "asin" not in reader.fieldnames:
                print(f"CSV {path} is missing an 'asin' column")
                return []
            for row in reader:
                asin = (row.get("asin") or "").strip()
                title = (row.get("title") or "").strip()
                products.append({"asin": asin, "title": title})
    except FileNotFoundError:
        print(f"File not found: {path}")
        return []
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return []
    return products


def save_to_csv(products: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "asin",
                "title",
                "price",
                "rating",
                "reviews",
                "bsr",
                "link",
                "score",
                "estimated",
            ],
        )
        writer.writeheader()
        for item in products:
            writer.writerow(item)


def print_report(products: List[Dict[str, str]]):
    for p in products:
        print(f"ASIN: {p.get('asin')}")
        print(f"Title: {p.get('title')}")
        print(f"Price: {p.get('price')}")
        print(f"Rating: {p.get('rating')} ({p.get('reviews')} reviews)")
        print(f"BSR: {p.get('bsr')}")
        print(f"Score: {p.get('score')} (estimated: {p.get('estimated')})")
        print(f"Link: {p.get('link')}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze Amazon ASINs")
    parser.add_argument("--csv", help="optional CSV file with asin column")
    args = parser.parse_args()

    if args.csv:
        entries = load_products_from_csv(args.csv)
        if not entries:
            print(f"No products found in {args.csv}")
            return
    else:
        prompt = (
            "Enter ASIN(s) separated by comma "
            f"(press Enter to load from {DISCOVERY_CSV}): "
        )
        asin_input = input(prompt).strip()
        if asin_input:
            entered = [a.strip() for a in asin_input.split(",") if a.strip()]
            valid = [a for a in entered if is_valid_asin(a)]
            if not valid:
                print("No valid ASINs provided")
                return
            if len(valid) < len(entered):
                print(f"Skipped {len(entered) - len(valid)} invalid ASIN(s)")
            entries = [{"asin": a, "title": ""} for a in valid]
        else:
            entries = load_products_from_csv(DISCOVERY_CSV)
            if not entries:
                print(
                    f"Could not load products from {DISCOVERY_CSV}. "
                    "Ensure the file exists and has 'asin' and 'title' columns."
                )
                return
            print(f"Loaded {len(entries)} products from {DISCOVERY_CSV}")

    if not entries:
        print("No products provided")
        return
    products, real, estimated, failed = process_products(entries)
    if not products:
        print("No product data retrieved")
        return
    print_report(products)
    save_to_csv(products)
    print(f"Saved {len(products)} results to {DATA_PATH}")
    print(
        f"Analyzed with ASIN data: {real} | Estimated by title: {estimated} | Failed: {failed}"
    )


if __name__ == "__main__":
    main()
