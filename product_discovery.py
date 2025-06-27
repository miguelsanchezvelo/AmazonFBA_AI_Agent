import os
import csv
import re
import argparse
from math import floor
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover Amazon products")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--budget', type=float, help='Total startup budget in USD')
    return parser.parse_args()


args = parse_args()

LOG_FILE = "log.txt"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

API_KEY = None

def get_api_key() -> Optional[str]:
    global API_KEY
    if API_KEY is not None:
        return API_KEY
    load_dotenv()
    API_KEY = os.getenv("SERPAPI_API_KEY")
    return API_KEY

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


ASIN_PATTERN = r"^B0[A-Z0-9]{8}$"


def is_asin_format(asin: str) -> bool:
    """Return True if asin matches Amazon's B0-prefixed pattern."""
    return bool(re.fullmatch(ASIN_PATTERN, asin or ""))


def search_similar_asin(title: str, verbose: bool = False) -> Optional[str]:
    """Search Amazon for the given title and return first valid ASIN."""
    key = get_api_key()
    if not key:
        if verbose:
            print("SERPAPI_API_KEY not configured")
        return None
    try:
        from serpapi import GoogleSearch
    except Exception as exc:  # pragma: no cover - optional dependency
        if verbose:
            print(f"SerpAPI import error: {exc}")
        return None

    params = {
        "engine": "amazon",
        "type": "search",
        "amazon_domain": "amazon.com",
        "k": title,
        "api_key": key,
    }
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
    except Exception as exc:
        if verbose:
            print(f"Error estimating ASIN for '{title}': {exc}")
        return None
    for item in data.get("organic_results", []) or []:
        asin = item.get("asin") or extract_asin_from_url(item.get("link") or item.get("url"))
        if asin and is_asin_format(asin):
            if verbose:
                print(f"Estimated ASIN {asin} for '{title}'")
            return asin
    return None


def log_skipped(reason: str, item: Dict):
    title = (item.get("title") or "")[:40]
    print(f"SKIPPED ({reason}): {title}")


def search_category(keyword: str, pages: int = 3, debug: bool = False) -> List[Dict]:
    key = get_api_key()
    if not key:
        raise RuntimeError("SERPAPI_API_KEY not configured")
    from serpapi import GoogleSearch

    results = []
    for page in range(1, pages + 1):
        params = {
            "engine": "amazon",
            "type": "search",
            "amazon_domain": "amazon.com",
            "k": keyword,
            "page": page,
            "api_key": key,
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


def discover_products(
    variable_budget: float,
    debug: bool = False,
    verbose: bool = False,
    max_products: int = 0,
) -> Tuple[List[Dict[str, object]], List[Dict[str, int]]]:
    """Return discovered products and per-category summary."""
    results: List[Dict[str, object]] = []
    summary: List[Dict[str, int]] = []
    seen: set = set()

    for cat in CATEGORIES:
        raw_items = search_category(cat, pages=3, debug=debug)
        valid = estimated = skipped = 0
        count = 0

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
            est_asin = None

            if not (asin and is_asin_format(asin)):
                asin = None
                est_asin = search_similar_asin(title, verbose=verbose)
                if not est_asin:
                    log_skipped("no valid ASIN found", item)
                    skipped += 1
                    continue

            chosen = asin or est_asin
            if chosen in seen:
                log_skipped("duplicate", item)
                skipped += 1
                continue

            est_cost, margin, units, total_profit = compute_metrics(price, variable_budget)
            if units <= 0:
                log_skipped("no units", item)
                skipped += 1
                continue

            entry = {
                "title": title,
                "asin": asin or "",
                "estimated_asin": est_asin or "",
                "price": price,
                "margin": margin,
                "units": units,
                "total_profit": total_profit,
            }

            results.append(entry)
            seen.add(chosen)
            if asin:
                valid += 1
            else:
                estimated += 1

            count += 1
            if max_products and count >= max_products:
                break

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
                "estimated_asin",
                "price",
                "margin",
                "units",
                "total_profit",
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
            f"{p['units']:>5} | "
            f"${p['total_profit']:>11.2f}"
        )


def main() -> None:
    try:
        if args.budget is not None:
            budget = args.budget
        elif args.auto:
            budget = 1000.0
        else:
            budget = float(input("Enter your total startup budget in USD: "))
    except ValueError:
        raise SystemExit("Invalid budget amount")

    variable_budget = budget - FIXED_COST
    if variable_budget <= 0:
        raise SystemExit("Budget too low after reserving fixed costs")

    fallback_csv = os.path.join("data", "mock_product_results.csv")
    try:
        products, summary = discover_products(
            variable_budget,
            debug=args.debug,
            verbose=args.verbose,
            max_products=args.max_products,
        )
    except Exception as exc:
        products = []
        summary = []
        msg = f"product_discovery error: {exc}"
        print(msg)
        log(msg)

    if not products:
        if os.path.exists(fallback_csv):
            msg = f"No products found. Using mock data from {fallback_csv}"
            print(msg)
            log(msg)
            with open(fallback_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                products = []
                for row in reader:
                    row["price"] = parse_float(row.get("price")) or 0.0
                    row["margin"] = parse_float(row.get("margin")) or 0.0
                    row["units"] = int(row.get("units") or 0)
                    row["total_profit"] = parse_float(row.get("total_profit")) or 0.0
                    products.append(row)
            summary = []
        else:
            raise SystemExit("No products found")

    products.sort(key=lambda x: x["total_profit"], reverse=True)
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
