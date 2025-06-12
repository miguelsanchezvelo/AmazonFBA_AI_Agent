import os
import csv
import re
import argparse
from math import floor
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()
API_KEY = os.getenv("SERPAPI_API_KEY")
if not API_KEY:
    raise SystemExit("Fatal: SERPAPI_API_KEY not set in environment")

CATEGORIES = ["kitchen", "fitness", "pets", "baby", "home"]
DATA_PATH = os.path.join("data", "product_results.csv")
FIXED_COST = 200.0
COST_RATE = 0.5


def parse_price(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, dict):
        val = val.get("raw") or val.get("value")
    m = re.search(r"\d+\.\d+|\d+", str(val))
    return float(m.group()) if m else None


def parse_float(val) -> Optional[float]:
    if val is None:
        return None
    m = re.search(r"\d+\.\d+|\d+", str(val))
    return float(m.group()) if m else None


def extract_asin_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    return m.group(1) if m else None


def is_asin_format(asin: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{10}", asin or ""))


def log_skipped(reason: str, item: Dict):
    title = (item.get("title") or "")[:40]
    print(f"SKIPPED ({reason}): {title}")


def search_category(keyword: str, pages: int = 3, debug: bool = False) -> List[Dict]:
    results = []
    for page in range(1, pages + 1):
        params = {
            "engine": "amazon",
            "type": "search",
            "amazon_domain": "amazon.com",
            "k": keyword,
            "page": page,
            "api_key": API_KEY,
        }
        search = GoogleSearch(params)
        data = search.get_dict()
        raw_items = data.get("organic_results", []) or []
        if debug:
            print(f"DEBUG page {page} results for '{keyword}': {raw_items}")
        results.extend(raw_items)
    return results


def similar_item(title: str, valid: List[Dict]) -> Optional[Dict]:
    best = None
    ratio = 0.0
    for v in valid:
        r = SequenceMatcher(None, title.lower(), v["title"].lower()).ratio()
        if r > ratio:
            ratio = r
            best = v
    if ratio >= 0.5:
        return best
    return None


def compute_metrics(price: float, budget: float) -> Tuple[float, float, int, float]:
    est_cost = price * COST_RATE
    margin = price - est_cost
    units = floor(budget / est_cost)
    total_profit = units * margin
    return est_cost, margin, units, total_profit


def discover_products(variable_budget: float, debug: bool = False) -> Tuple[List[Dict[str, object]], List[Dict[str, int]]]:
    results: List[Dict[str, object]] = []
    summary: List[Dict[str, int]] = []
    for cat in CATEGORIES:
        raw_items = search_category(cat, pages=3, debug=debug)
        valid_items: List[Dict] = []
        valid = estimated = skipped = 0
        for item in raw_items:
            if debug:
                print("RAW", item)
            title = (item.get("title") or "").strip()
            if not title:
                log_skipped("missing title", item)
                skipped += 1
                continue
            price = parse_price(item.get("price"))
            if price is None or price <= 0:
                log_skipped("missing/invalid price", item)
                skipped += 1
                continue
            link = item.get("link") or item.get("url")
            asin = item.get("asin") or extract_asin_from_url(link)
            rating = parse_float(item.get("rating"))
            reviews = parse_float(item.get("reviews"))
            if asin and is_asin_format(asin):
                est_cost, margin, units, total_profit = compute_metrics(price, variable_budget)
                if units <= 0:
                    log_skipped("no units", item)
                    skipped += 1
                    continue
                entry = {
                    "title": title,
                    "asin": asin,
                    "estimated": False,
                    "price": price,
                    "rating": rating,
                    "reviews": reviews,
                    "est_cost": est_cost,
                    "margin": margin,
                    "units_possible": units,
                    "estimated_total_profit": total_profit,
                    "link": link,
                }
                results.append(entry)
                valid_items.append(entry)
                valid += 1
            else:
                match = similar_item(title, valid_items)
                if not match:
                    log_skipped("missing ASIN", item)
                    skipped += 1
                    continue
                est_cost, margin, units, total_profit = compute_metrics(price, variable_budget)
                if units <= 0:
                    log_skipped("no units", item)
                    skipped += 1
                    continue
                entry = {
                    "title": title,
                    "asin": match["asin"],
                    "estimated": True,
                    "price": price,
                    "rating": match.get("rating"),
                    "reviews": match.get("reviews"),
                    "est_cost": est_cost,
                    "margin": margin,
                    "units_possible": units,
                    "estimated_total_profit": total_profit,
                    "link": link,
                }
                results.append(entry)
                estimated += 1
        summary.append({"category": cat, "valid": valid, "estimated": estimated, "skipped": skipped})
    return results, summary


def save_to_csv(products: List[Dict[str, object]]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "asin",
                "estimated",
                "price",
                "rating",
                "reviews",
                "est_cost",
                "margin",
                "units_possible",
                "estimated_total_profit",
                "link",
            ],
        )
        writer.writeheader()
        for row in products:
            writer.writerow(row)


def print_report(products: List[Dict[str, object]]):
    header = f"{'Title':40} | {'Price':>6} | {'Margin':>6} | {'Units':>5} | {'Total Profit':>12}"
    print(header)
    print("-" * len(header))
    for p in products:
        title = (p.get('title') or '')[:40]
        print(
            f"{title:40} | "
            f"${p['price']:>6.2f} | "
            f"${p['margin']:>6.2f} | "
            f"{p['units_possible']:>5} | "
            f"${p['estimated_total_profit']:>11.2f}"
        )


def main():
    parser = argparse.ArgumentParser(description="Discover Amazon products")
    parser.add_argument("--debug", action="store_true", help="print raw entries")
    args = parser.parse_args()

    try:
        budget = float(input("Enter your total startup budget in USD: "))
    except ValueError:
        raise SystemExit("Invalid budget amount")

    variable_budget = budget - FIXED_COST
    if variable_budget <= 0:
        raise SystemExit("Budget too low after reserving fixed costs")

    products, summary = discover_products(variable_budget, debug=args.debug)
    if not products:
        raise SystemExit("No products found")

    products.sort(key=lambda x: x["estimated_total_profit"], reverse=True)
    top = products[:20]

    for s in summary:
        print(
            f"Category '{s['category']}': valid={s['valid']} "
            f"estimated={s['estimated']} skipped={s['skipped']}"
        )

    print_report(top)
    save_to_csv(top)
    print(f"Saved {len(top)} products to {DATA_PATH}")
    print(f"Total products saved: {len(top)}")


if __name__ == "__main__":
    main()
