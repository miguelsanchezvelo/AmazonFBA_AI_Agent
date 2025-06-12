import os
import csv
import re
import argparse
import time
import json
from typing import List, Dict, Optional, Tuple

from dotenv import load_dotenv
from serpapi import GoogleSearch
import requests

load_dotenv()

CONFIG_PATH = "config.json"


def load_api_keys() -> Tuple[str, str]:
    serpapi_key = None
    keepa_key = None
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                serpapi_key = cfg.get("serpapi_key")
                keepa_key = cfg.get("keepa_key")
        except Exception as exc:
            print(f"Error reading {CONFIG_PATH}: {exc}")

    serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
    keepa_key = keepa_key or os.getenv("KEEPA_API_KEY")

    if not serpapi_key:
        serpapi_key = input("Enter your SerpAPI key: ").strip()
    if not keepa_key:
        keepa_key = input("Enter your Keepa API key: ").strip()

    return serpapi_key, keepa_key


SERPAPI_KEY, KEEPA_KEY = load_api_keys()

DATA_PATH = os.path.join("data", "market_analysis_results.csv")
# Default CSV produced by product_discovery.py
DISCOVERY_CSV = os.path.join("data", "product_results.csv")


def parse_float(value: str) -> Optional[float]:
    """Return float from string like '4.5 out of 5' or '$12.34'."""
    if value is None:
        return None
    match = re.search(r"\d+\.\d+|\d+", value)
    return float(match.group()) if match else None


ASIN_PATTERN = r"^B0[A-Z0-9]{8}$"


def is_valid_asin(asin: str) -> bool:
    """Return True if asin matches Amazon's B0-prefixed pattern."""
    return bool(re.fullmatch(ASIN_PATTERN, (asin or "").upper()))


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
        "api_key": SERPAPI_KEY,
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
        "api_key": SERPAPI_KEY,
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


def get_product_data_serpapi(asin: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, object]]:
    """Try retrieving product info using SerpAPI by ASIN then title."""
    data = None
    estimated = False
    if asin and is_valid_asin(asin):
        data = fetch_product_info(asin)
    if not data and title:
        data = fetch_product_by_title(title)
        estimated = True if data else False
    if data:
        data["estimated"] = estimated
        data["source"] = "serpapi"
    return data


def get_product_data_keepa(asin: Optional[str] = None, keywords: Optional[str] = None, keepa_key: Optional[str] = None) -> Optional[Dict[str, object]]:
    """Retrieve product info from Keepa either by ASIN or search keywords."""
    if not keepa_key:
        return None
    base = "https://api.keepa.com"
    params = {"key": keepa_key, "domain": "US"}
    if asin:
        try:
            resp = requests.get(f"{base}/product", params={**params, "asin": asin})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("products"):
                    return {"source": "keepa", "estimated": False, "raw": data}
        except Exception as exc:
            print(f"Keepa ASIN error for {asin}: {exc}")
    if keywords:
        try:
            resp = requests.get(f"{base}/search", params={**params, "term": keywords})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("products"):
                    return {"source": "keepa", "estimated": True, "raw": data}
        except Exception as exc:
            print(f"Keepa search error for '{keywords}': {exc}")
    return None


def process_products(products: List[Dict[str, str]], verbose: bool = False) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """Process a list of entries with asin/estimated_asin/title."""
    results = []
    stats = {
        "analyzed": 0,
        "fallback_success": 0,
        "skipped_invalid": 0,
        "skipped_no_data": 0,
    }

    for item in products:
        asin = (item.get("asin") or "").strip()
        est_asin = (item.get("estimated_asin") or "").strip()
        title = (item.get("title") or "").strip()

        chosen = None
        if is_valid_asin(asin):
            chosen = asin
        elif is_valid_asin(est_asin):
            chosen = est_asin

        data = None
        if chosen or title:
            data = get_product_data_serpapi(asin=chosen, title=title)
            if data:
                if chosen and chosen != asin:
                    data["estimated"] = True
                if data.get("source") == "serpapi" and not data.get("estimated"):
                    stats["analyzed"] += 1
                elif data.get("source") == "serpapi" and data.get("estimated"):
                    stats["fallback_success"] += 1
        if not data:
            data = get_product_data_keepa(asin=chosen, keywords=title, keepa_key=KEEPA_KEY)
            if data:
                if chosen and chosen != asin:
                    data["estimated"] = True
                if data.get("estimated"):
                    stats["fallback_success"] += 1
                else:
                    stats["analyzed"] += 1

        if not data:
            if not (asin or est_asin):
                stats["skipped_invalid"] += 1
            else:
                stats["skipped_no_data"] += 1
            if verbose:
                print(f"Skipped entry ASIN='{asin}' EST='{est_asin}' Title='{title[:40]}'")
            continue

        data["score"] = evaluate_potential(data)
        results.append(data)
        time.sleep(1)

    return results, stats


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
    """Return list of entries with asin, estimated_asin and title from a CSV file."""
    products = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "asin" not in reader.fieldnames or "title" not in reader.fieldnames:
                print(f"CSV {path} is missing required columns")
                return []
            for row in reader:
                products.append(
                    {
                        "asin": (row.get("asin") or "").strip(),
                        "estimated_asin": (row.get("estimated_asin") or "").strip(),
                        "title": (row.get("title") or "").strip(),
                    }
                )
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
                "source",
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
        print(f"Source: {p.get('source')} | Estimated: {p.get('estimated')}")
        print(f"Score: {p.get('score')}")
        print(f"Link: {p.get('link')}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze Amazon ASINs")
    parser.add_argument("--csv", help="optional CSV file with asin column")
    parser.add_argument("--verbose", action="store_true", help="print verbose logs")
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
            entries = [{"asin": a, "estimated_asin": "", "title": ""} for a in valid]
        else:
            entries = load_products_from_csv(DISCOVERY_CSV)
            if not entries:
                print(
                    f"Could not load products from {DISCOVERY_CSV}. "
                    "Ensure the file exists and has 'asin', 'title', and optional 'estimated_asin' columns."
                )
                return
            print(f"Loaded {len(entries)} products from {DISCOVERY_CSV}")

    if not entries:
        print("No products provided")
        return
    products, stats = process_products(entries, verbose=args.verbose)
    if not products:
        print("No product data retrieved")
        return
    print_report(products)
    save_to_csv(products)
    print(f"Saved {len(products)} results to {DATA_PATH}")
    print(
        f"Analyzed: {stats['analyzed']} | Fallback success: {stats['fallback_success']} | "
        f"Skipped invalid: {stats['skipped_invalid']} | Skipped no data: {stats['skipped_no_data']}"
    )


if __name__ == "__main__":
    main()
