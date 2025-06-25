import argparse
import os
import csv
import re
import time
from typing import List, Optional, Set

LOG_FILE = "log.txt"
ASIN_LOG = os.path.join("logs", "asin_mismatch.log")
UNPROFITABLE_LOG = os.path.join("logs", "unprofitable_products.log")


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


def log_unprofitable(module: str, rows: List[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(UNPROFITABLE_LOG), exist_ok=True)
    try:
        with open(UNPROFITABLE_LOG, "a", encoding="utf-8") as f:
            for r in rows:
                asin = r.get("asin", "")
                roi = r.get("roi", 0)
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {module}: {asin},{roi}\n")
    except Exception:
        pass

PRODUCT_CSV = os.path.join("data", "product_results.csv")

INPUT_CSV = os.path.join("data", "market_analysis_results.csv")
SUPPLIER_CSV = os.path.join("data", "supplier_data.csv")
OUTPUT_CSV = os.path.join("data", "profitability_estimation_results.csv")
SHIPPING_COST = 2.50


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


def parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+\.\d+|\d+", str(value))
    return float(match.group()) if match else None


def load_supplier_costs(path: str) -> dict:
    costs = {}
    if not os.path.exists(path):
        return costs
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = (row.get("asin") or "").strip()
            cost = parse_float(row.get("cost"))
            if asin and cost is not None:
                costs[asin] = round(cost, 2)
    return costs


def estimate_profit(rows, supplier_costs):
    results = []
    unprofitable: List[dict] = []
    for row in rows:
        price = parse_float(row.get("price"))
        if price is None:
            continue
        asin = row.get("asin") or ""
        cost = supplier_costs.get(asin, round(price * 0.3, 2))
        fba_fees = round(price * 0.15 + 3.0, 2)
        profit = round(price - cost - SHIPPING_COST - fba_fees, 2)
        total_cost = cost + SHIPPING_COST + fba_fees
        roi = round(profit / total_cost, 2) if total_cost else 0.0
        viable = "YES" if roi > 0 else "NO"
        if roi <= 0:
            unprofitable.append({"asin": asin, "roi": roi})
            continue
        results.append(
            {
                "asin": asin,
                "title": row.get("title", ""),
                "price": round(price, 2),
                "cost": cost,
                "fba_fees": fba_fees,
                "shipping": SHIPPING_COST,
                "profit": profit,
                "roi": roi,
                "score": row.get("score", ""),
                "Viable": viable,
            }
        )
    if unprofitable:
        print(
            f"Skipping {len(unprofitable)} unprofitable products (ROI ≤ 0). See {UNPROFITABLE_LOG}"
        )
        log_unprofitable("profitability_estimation", unprofitable)
    return results


def load_market_data(path: str):
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
            log_asin_mismatch("profitability_estimation", unknown)
            log(f"profitability_estimation: ASIN mismatch {','.join(sorted(unknown))}")
            if not filtered:
                return []
        return filtered
    return rows


def save_results(rows, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "asin",
            "title",
            "price",
            "cost",
            "fba_fees",
            "shipping",
            "profit",
            "roi",
            "score",
            "Viable",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_top_products(rows, count=5):
    rows = [r for r in rows if (r.get("roi") or 0) > 0]
    rows = sorted(rows, key=lambda x: x["roi"], reverse=True)[:count]
    header = f"{'ASIN':12} | {'Price':>6} | {'Cost':>6} | {'Profit':>7} | {'ROI':>5}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | "
            f"${r['price']:>6.2f} | "
            f"${r['cost']:>6.2f} | "
            f"${r['profit']:>7.2f} | "
            f"{r['roi']:>5.2f}"
        )


def main(argv: Optional[List[str]] = None) -> None:
    global INPUT_CSV, SUPPLIER_CSV, OUTPUT_CSV

    parser = argparse.ArgumentParser(
        description="Estimate profitability of products"
    )
    parser.add_argument(
        "--input",
        default=INPUT_CSV,
        help="Path to market analysis CSV",
    )
    parser.add_argument(
        "--supplier-costs",
        default=SUPPLIER_CSV,
        help="CSV file with supplier costs",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_CSV,
        help="Where to save profitability results",
    )
    args = parser.parse_args(argv)

    INPUT_CSV = args.input
    SUPPLIER_CSV = args.supplier_costs
    OUTPUT_CSV = args.output

    market_data = load_market_data(INPUT_CSV)
    if not market_data:
        return
    supplier_costs = load_supplier_costs(SUPPLIER_CSV)
    results = estimate_profit(market_data, supplier_costs)
    save_results(results, OUTPUT_CSV)
    print_top_products(results, 5)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
