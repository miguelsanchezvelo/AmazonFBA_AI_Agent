import os
import csv
import re
import argparse
from math import floor
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import time
import sys
import io
from mock_data import get_mock_asins
from utils import save_rows  # o definir save_rows localmente si no existe utils

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover Amazon products")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--budget', type=float, help='Total startup budget in USD')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--keywords', type=str, help='Keywords for product discovery')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    parser.add_argument('--real', action='store_true', help='Usar datos reales (por defecto: mock)')
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
        import serpapi
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
        client = serpapi.Client(api_key=key)
        data = client.search(params).as_dict()
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
    import serpapi

    results = []
    client = serpapi.Client(api_key=key)
    for page in range(1, pages + 1):
        params = {
            "engine": "amazon",
            "type": "search",
            "amazon_domain": "amazon.com",
            "k": keyword,
            "page": page,
            "api_key": key,
        }
        data = client.search(params).as_dict()
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
    global OUTPUT_CSV
    parser = argparse.ArgumentParser(description="Product discovery")
    parser.add_argument('--output', default='data/discovery_results.csv', help='Output CSV file')
    parser.add_argument('--keywords', default=None, help='Keywords for product discovery')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    parser.add_argument('--real', action='store_true', help='Usar datos reales (por defecto: mock)')
    args = parser.parse_args()
    OUTPUT_CSV = args.output
    use_mock = not args.real
    if use_mock:
        mock_products = get_mock_asins()
        save_rows(mock_products, OUTPUT_CSV)
        print(f"[MOCK] Saved {len(mock_products)} products to {OUTPUT_CSV}")
        return
    keywords = args.keywords.split(',') if args.keywords else []
    if not keywords:
        msg = "No se encontraron palabras clave para el descubrimiento de productos. El archivo de entrada está vacío."
        print(msg)
        log(msg)
        save_rows([], OUTPUT_CSV)
        print(f"Results saved to {OUTPUT_CSV}")
        return
    keyword_invalid = 0
    no_results = 0
    total = 0
    results = []
    for kw in keywords:
        total += 1
        if not kw:
            keyword_invalid += 1
            continue
        # Simulación: si no hay resultados para la keyword, descartar
        found = True  # Aquí iría la lógica real
        if not found:
            no_results += 1
            continue
        # Simulación de producto encontrado
        results.append({"asin": f"ASIN{total}", "title": f"Producto {total}", "price": 10.0 + total})
    if not results:
        msg = (
            f"No se encontraron productos en el descubrimiento.\n"
            f"Total palabras clave analizadas: {total}.\n"
            f"Descartadas por palabra clave inválida: {keyword_invalid}.\n"
            f"Descartadas por no encontrar resultados: {no_results}.\n"
        )
        print(msg)
        log(msg)
        save_rows([], OUTPUT_CSV)
        print(f"Results saved to {OUTPUT_CSV}")
        return
    save_rows(results, OUTPUT_CSV)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
