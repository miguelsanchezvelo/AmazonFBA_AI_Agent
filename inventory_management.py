import argparse
import csv
import os
import time
from typing import List, Dict, Optional, Set
from mock_data import get_mock_asins

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

PRODUCT_CSV = os.path.join("data", "product_results.csv")

INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_CSV = os.path.join("data", "inventory_management_results.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate inventory recommendations based on supplier selections")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--input', default=INPUT_CSV, help='CSV with supplier selections')
    parser.add_argument('--output', default=OUTPUT_CSV, help='Where to save inventory recommendations')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    return parser.parse_args()


args = parse_args()


def load_valid_asins() -> Set[str]:
    if not os.path.exists(PRODUCT_CSV):
        return set()
    with open(PRODUCT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            row.get("asin") or row.get("estimated_asin")
            for row in reader
            if row.get("asin") or row.get("estimated_asin")
        }


def parse_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).replace("$", "")
    try:
        return float(val)
    except ValueError:
        digits = "".join(ch for ch in val if ch.isdigit() or ch == ".")
        try:
            return float(digits)
        except ValueError:
            return None


def parse_int(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(float(val))
    except ValueError:
        digits = "".join(ch for ch in str(val) if ch.isdigit())
        return int(digits) if digits else None


def is_viable(row: Dict[str, str]) -> bool:
    roi = parse_float(row.get("roi"))
    viable_flag = str(row.get("Viable", "YES")).strip().upper()
    return (roi is not None and roi > 0) or viable_flag == "YES"


def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        print(f"Input file '{path}' not found")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    valid = load_valid_asins()
    if valid:
        filtered = []
        unknown: Set[str] = set()
        for r in rows:
            asin = (r.get("asin") or "").strip()
            if asin and asin not in valid:
                unknown.add(asin)
                continue
            filtered.append(r)
        if unknown:
            print(
                "Warning: Skipping "
                f"{len(unknown)} products not found in product_results.csv: "
                + ", ".join(sorted(unknown))
            )
            log_asin_mismatch("inventory_management", unknown)
            log(f"inventory_management: ASIN mismatch {','.join(sorted(unknown))}")
            if not filtered:
                return []
        rows = filtered
    return [r for r in rows if is_viable(r)]


def save_rows(rows: List[Dict[str, object]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "asin",
                "title",
                "recommended_stock",
                "stock_cost",
                "projected_value",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def process(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for r in rows:
        units = parse_int(r.get("units_to_order")) or 0
        if units <= 0:
            continue
        cost = parse_float(r.get("cost")) or 0.0
        price = parse_float(r.get("price")) or 0.0
        recommended = int(units * 1.25)
        stock_cost = round(recommended * cost, 2)
        proj_value = round(recommended * price, 2)
        results.append(
            {
                "asin": r.get("asin", ""),
                "title": r.get("title", ""),
                "recommended_stock": recommended,
                "stock_cost": stock_cost,
                "projected_value": proj_value,
            }
        )
    return results


def print_table(rows: List[Dict[str, object]]) -> None:
    header = (
        f"{'ASIN':12} | {'Title':30} | {'Rec Stock':>9} | {'Stock Cost':>10} | {'Proj Value':>10}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | {(r['title'] or '')[:30]:30} | {r['recommended_stock']:>9} | "
            f"${r['stock_cost']:>10.2f} | ${r['projected_value']:>10.2f}"
        )


def main() -> None:
    global INPUT_CSV, OUTPUT_CSV

    INPUT_CSV = args.input
    OUTPUT_CSV = args.output

    use_mock = args.mock
    if use_mock:
        mock_inventory = [dict(row, **{"units_to_order": 100, "stock": 100, "restock_needed": "NO"}) for row in get_mock_asins()]
        save_rows(mock_inventory, OUTPUT_CSV)
        print(f"[MOCK] Saved {len(mock_inventory)} inventory management rows to {OUTPUT_CSV}")
        return

    rows = load_rows(INPUT_CSV)
    if not rows:
        print("No viable supplier selections found.")
        save_rows([], OUTPUT_CSV)
        print(f"Results saved to {OUTPUT_CSV}")
        return
    results = process(rows)
    if results:
        print_table(results)
    else:
        print("No products with units to order found.")
    save_rows(results, OUTPUT_CSV)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
