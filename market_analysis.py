# market_analysis.py - Cleaned up version with dual API fallback
import os
import csv
import re
import argparse
import time
import json
from typing import List, Dict, Optional, Tuple, Set
import sys
import io
from mock_data import get_mock_asins

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

try:
    import serpapi
except Exception:  # pragma: no cover - optional dependency
    serpapi = None  # type: ignore

load_dotenv()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

def safe_strip(val):
    return val.strip() if isinstance(val, str) else ''

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Amazon market data")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--csv', help='CSV with ASINs (API mode) or mock data (manual mode)')
    parser.add_argument('--no-fallback', action='store_true', help='disable API fallback searches')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    parser.add_argument('--real', action='store_true', help='Usar datos reales (por defecto: mock)')
    return parser.parse_args()


args = parse_args()

LOG_FILE = "log.txt"
ASIN_LOG = os.path.join("logs", "asin_mismatch.log")


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def log_asin_mismatch(module: str, asins: Set[str]) -> None:
    if not asins:
        return
    os.makedirs(os.path.dirname(ASIN_LOG), exist_ok=True)
    try:
        with open(ASIN_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} {module}: {','.join(sorted(asins))}\n"
            )
    except Exception:
        pass

CONFIG_PATH = "config.json"
DATA_PATH = os.path.join("data", "market_analysis_results.csv")
DISCOVERY_CSV = os.path.join("data", "product_results.csv")
MOCK_DATA_CSV = os.path.join("data", "mock_market_data.csv")

SERPAPI_KEY: Optional[str] = None
KEEPA_KEY: Optional[str] = None


def load_valid_asins() -> Set[str]:
    if not os.path.exists(DISCOVERY_CSV):
        return set()
    with open(DISCOVERY_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            row.get("asin") or row.get("estimated_asin")
            for row in reader
            if row.get("asin") or row.get("estimated_asin")
        }


def load_keys(prompt: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Load API keys from environment or config file.

    If ``prompt`` is ``True`` y hay una clave faltante, se le pedirá al usuario.
    Si stdin no es interactivo, asignar None directamente para evitar errores.
    """

    global SERPAPI_KEY, KEEPA_KEY

    if SERPAPI_KEY is not None or KEEPA_KEY is not None:
        # Keys already loaded
        return SERPAPI_KEY, KEEPA_KEY

    config: Dict[str, str] = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            print(f"Warning: could not read {CONFIG_PATH}: {exc}")

    SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or config.get("serpapi_key")
    KEEPA_KEY = os.getenv("KEEPA_API_KEY") or config.get("keepa_key")

    if prompt:
        if not SERPAPI_KEY:
            if sys.stdin.isatty():
                inp = input("Enter your SerpAPI key (or leave blank): ")
                SERPAPI_KEY = safe_strip(inp)
            else:
                SERPAPI_KEY = None
        if not KEEPA_KEY:
            if sys.stdin.isatty():
                inp = input("Enter your Keepa API key (or leave blank): ")
                KEEPA_KEY = safe_strip(inp)
            else:
                KEEPA_KEY = None

    return SERPAPI_KEY, KEEPA_KEY


def is_api_available() -> bool:
    """Return ``True`` if at least one API key is configured."""

    load_keys(prompt=False)
    return bool(SERPAPI_KEY) or bool(KEEPA_KEY)


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"\d+\.\d+|\d+", value)
    return float(match.group()) if match else None


ASIN_PATTERN = r"^B0[A-Z0-9]{8}$"


def is_valid_asin(asin: str) -> bool:
    return bool(re.fullmatch(ASIN_PATTERN, (asin or "").upper()))


def evaluate_potential(product: Dict[str, Optional[float]]) -> str:
    rating = product.get("rating") or 0
    reviews = product.get("reviews") or 0
    bsr = product.get("bsr")
    if rating >= 4.3 and reviews >= 300 and bsr:
        return "HIGH"
    if rating >= 4.0:
        return "MEDIUM"
    return "LOW"


def get_product_data_serpapi(asin: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, str]]:
    key, _ = load_keys()
    if serpapi is None or not key:
        return None
    client = serpapi.Client(api_key=key)
    if asin:
        params = {
            "engine": "amazon",
            "api_key": key,
            "amazon_domain": "amazon.com",
            "type": "product",
            "asin": asin,
        }
        try:
            result = client.search(params).as_dict()
            product = result.get("product_results") or {}
            if not product:
                return None
            title = product.get("title")
            price_raw = product.get("price", {}).get("raw") if isinstance(product.get("price"), dict) else product.get("price")
            price = parse_float(price_raw)
            rating = parse_float(str(product.get("rating")))
            reviews = parse_float(str(product.get("reviews")))
            link = product.get("url") or product.get("link")
            bsr = None
            for item in result.get("product_information", []):
                if "Best Sellers Rank" in item.get("title", ""):
                    bsr = item.get("value")
                    break
            return {
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "bsr": bsr,
                "link": link,
                "source": "serpapi",
                "estimated": False,
            }
        except Exception as e:
            print(f"SerpAPI error for ASIN {asin}: {e}")

    if title:
        params = {
            "engine": "amazon",
            "api_key": key,
            "amazon_domain": "amazon.com",
            "type": "search",
            "search_term": title,
        }
        try:
            result = client.search(params).as_dict()
            items = result.get("organic_results", [])
            if not items:
                return None
            best = items[0]
            asin = best.get("asin")
            link = best.get("link") or best.get("url")
            price = parse_float(best.get("price", {}).get("raw") if isinstance(best.get("price"), dict) else best.get("price"))
            rating = parse_float(str(best.get("rating")))
            reviews = parse_float(str(best.get("reviews")))
            return {
                "asin": asin,
                "title": best.get("title"),
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "bsr": None,
                "link": link,
                "source": "serpapi",
                "estimated": True,
            }
        except Exception as e:
            print(f"SerpAPI error for title '{title}': {e}")

    return None


def get_product_data_keepa(asin: Optional[str] = None, keywords: Optional[str] = None) -> Optional[Dict[str, str]]:
    _, key = load_keys()
    if asin:
        url = f"https://api.keepa.com/product?key={key}&domain=1&asin={asin}"
    elif keywords:
        url = f"https://api.keepa.com/search?key={key}&domain=1&term={requests.utils.quote(keywords)}"
    else:
        return None

    try:
        data = requests.get(url, timeout=20).json()
        products = data.get("products") or []
        if not products:
            return None
        item = products[0]
        asin = item.get("asin")
        return {
            "asin": asin,
            "title": item.get("title"),
            "price": parse_float(str(item.get("buyBoxSellerPrice") or item.get("buyBoxPrice"))),
            "rating": parse_float(str(item.get("rating"))),
            "reviews": parse_float(str(item.get("reviewCount"))),
            "bsr": item.get("salesRank"),
            "link": f"https://www.amazon.com/dp/{asin}",
            "source": "keepa",
            "estimated": keywords is not None and not asin,
        }
    except Exception as e:
        print(f"Keepa error: {e}")
    return None


def load_asins_from_csv(path: str) -> List[str]:
    """Load ASIN values from a CSV file containing an ``asin`` column."""
    asins: List[str] = []
    if not os.path.exists(path):
        print(f"Warning: CSV file '{path}' not found")
        return asins
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = safe_strip(row.get("asin"))
            if asin and is_valid_asin(asin):
                asins.append(asin)
    return asins


def prompt_asins() -> List[str]:
    """Prompt the user for ASIN values."""
    raw = input(
        "Enter ASINs separated by spaces (leave blank to load from discovery results): "
    )
    raw = safe_strip(raw)
    if not raw:
        return []
    return [safe_strip(a).upper() for a in raw.split() if is_valid_asin(a)]


def load_manual_csv(path: str) -> List[Dict[str, object]]:
    """Load mock product data from a CSV file for manual mode."""
    products: List[Dict[str, object]] = []
    if not os.path.exists(path):
        print(f"Warning: mock CSV '{path}' not found")
        return products
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = safe_strip(row.get("asin"))
            if asin and not is_valid_asin(asin):
                # Ignore invalid ASINs in mock data
                continue
            product = {
                "asin": asin,
                "title": safe_strip(row.get("title")),
                "price": parse_float(safe_strip(str(row.get("price")))),
                "rating": parse_float(safe_strip(str(row.get("rating")))),
                "reviews": parse_float(safe_strip(str(row.get("reviews")))),
                "bsr": safe_strip(row.get("bsr")),
                "link": safe_strip(row.get("link")) or "",
                "source": safe_strip(row.get("source")) or "manual",
                "estimated": True,
            }
            score = parse_float(safe_strip(str(row.get("score"))))
            if score is not None:
                product["score"] = score
            products.append(product)
    return products


def manual_input(asins: Optional[List[str]] = None) -> List[Dict[str, object]]:
    """Prompt the user to manually enter product data."""
    products: List[Dict[str, object]] = []
    print("Manual data entry mode. Leave ASIN blank to finish.")
    index = 0
    while True:
        if asins and index < len(asins):
            asin = asins[index]
            print(f"Provide data for ASIN {asin}")
        else:
            asin = input("ASIN: ")
            asin = safe_strip(asin)
            if not asin:
                break
        title = input("Title: ")
        title = safe_strip(title)
        price = parse_float(input("Price: "))
        rating = parse_float(input("Rating: "))
        reviews = parse_float(input("Reviews: "))
        bsr = input("Best Seller Rank: ")
        bsr = safe_strip(bsr) or None
        link = input("Link: ")
        link = safe_strip(link)
        products.append(
            {
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "bsr": bsr,
                "link": link,
                "source": "manual",
                "estimated": True,
            }
        )
        index += 1
        if asins and index >= len(asins):
            break
    return products


def save_results(products: List[Dict[str, object]]):
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
                "estimated",
                "potential",
                "selection_reason",
            ],
        )
        writer.writeheader()
        for row in products:
            row["selection_reason"] = "Passed market analysis filters"
            writer.writerow(row)


def save_to_csv(products: List[Dict[str, object]]):
    """Compatibility wrapper that saves results to ``DATA_PATH``."""
    save_results(products)


def print_report(products: List[Dict[str, object]]):
    """Print a simple text report of analyzed products."""
    header = (
        f"{'ASIN':12} | {'Title':40} | {'Price':>6} | {'Rating':>6} | "
        f"{'Reviews':>7} | {'BSR':>10} | {'Potential':>8}"
    )
    print(header)
    print("-" * len(header))
    for p in products:
        price = p.get('price')
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else 'N/A'
        rating = p.get('rating') or 0
        reviews = int(p.get('reviews') or 0)
        bsr = p.get('bsr') or ''
        print(
            f"{(p.get('asin') or ''):12} | "
            f"{(p.get('title') or '')[:40]:40} | "
            f"{price_str:>6} | "
            f"{rating:>6.1f} | "
            f"{reviews:>7} | "
            f"{str(bsr):>10} | "
            f"{p.get('potential', ''):>8}"
        )


def process_products(products: List[Dict[str, object]]):
    """Evaluate potential, print a report and save the results."""
    if not products:
        return
    for p in products:
        p["potential"] = evaluate_potential(p)
    print_report(products)
    save_to_csv(products)


def analyze(asins: List[str], use_serp: bool, use_keepa: bool, fallback: bool) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for asin in asins:
        product: Optional[Dict[str, object]] = None
        if use_serp:
            product = get_product_data_serpapi(asin=asin)
        if not product and use_keepa:
            product = get_product_data_keepa(asin=asin)
        if product and not product.get("bsr") and use_keepa and fallback:
            # try to supplement missing info with Keepa
            sup = get_product_data_keepa(asin=asin)
            if sup:
                for k in ["price", "rating", "reviews", "bsr", "link"]:
                    if not product.get(k):
                        product[k] = sup.get(k)
        if not product:
            print(f"No data found for {asin}")
            continue
        product["potential"] = evaluate_potential(product)
        product["selection_reason"] = "Passed market analysis filters"
        results.append(product)
    return results


def main() -> None:
    global INPUT_CSV, OUTPUT_CSV
    parser = argparse.ArgumentParser(description="Market analysis")
    parser.add_argument('--input', default='data/discovery_results.csv', help='Input CSV file')
    parser.add_argument('--output', default='data/market_analysis_results.csv', help='Output CSV file')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    parser.add_argument('--real', action='store_true', help='Usar datos reales (por defecto: mock)')
    args = parser.parse_args()
    INPUT_CSV = args.input
    OUTPUT_CSV = args.output
    use_mock = not args.real
    if use_mock:
        mock_market = [dict(row, **{"market_price": row["price"], "market_demand": row["demand"]}) for row in get_mock_asins()]
        save_rows(mock_market, OUTPUT_CSV)
        print(f"[MOCK] Saved {len(mock_market)} market analysis rows to {OUTPUT_CSV}")
        return
    # ... resto de la lógica real ...


def save_rows(rows, path, fieldnames=None):
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
