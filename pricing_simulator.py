import os
import csv
import re
from typing import Dict, List, Optional

INVENTORY_CSV = os.path.join("data", "inventory_management_results.csv")
PROFIT_CSV = os.path.join("data", "profitability_estimation_results.csv")
OUTPUT_CSV = os.path.join("data", "pricing_simulation_results.csv")


def parse_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"\d+\.\d+|\d+", str(val))
    return float(m.group()) if m else None


def parse_int(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    m = re.search(r"\d+", str(val))
    return int(m.group()) if m else None


def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def join_data(inv_rows: List[Dict[str, str]], profit_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    inv_map = {r.get("asin", ""): r for r in inv_rows}
    combined: List[Dict[str, object]] = []
    for p in profit_rows:
        asin = p.get("asin") or ""
        inv = inv_map.get(asin)
        if not inv:
            continue
        price = parse_float(p.get("price"))
        cost = parse_float(p.get("cost"))
        stock = parse_int(inv.get("recommended_stock"))
        if price is None or cost is None or stock is None:
            continue
        combined.append(
            {
                "asin": asin,
                "title": p.get("title", ""),
                "price": price,
                "cost": cost,
                "stock": stock,
            }
        )
    return combined


def simulate(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for row in rows:
        price = row["price"]
        cost = row["cost"]
        stock = row["stock"]
        for pct in (-0.2, -0.1, 0.0, 0.1, 0.2):
            new_price = round(price * (1 + pct), 2)
            profit_unit = round(new_price - cost, 2)
            roi = round(profit_unit / cost, 2) if cost else 0.0
            proj_profit = round(profit_unit * stock, 2)
            results.append(
                {
                    "asin": row["asin"],
                    "original_price": price,
                    "simulated_price": new_price,
                    "profit_per_unit": profit_unit,
                    "roi": roi,
                    "projected_profit": proj_profit,
                }
            )
    return results


def save_results(rows: List[Dict[str, object]]):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "asin",
                "original_price",
                "simulated_price",
                "profit_per_unit",
                "roi",
                "projected_profit",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def print_table(rows: List[Dict[str, object]]):
    header = (
        f"{'ASIN':12} | {'Orig Price':>10} | {'Sim Price':>9} | "
        f"{'Profit/U':>8} | {'ROI':>5} | {'Proj Profit':>12}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | "
            f"${r['original_price']:>10.2f} | "
            f"${r['simulated_price']:>9.2f} | "
            f"${r['profit_per_unit']:>8.2f} | "
            f"{r['roi']:>5.2f} | "
            f"${r['projected_profit']:>12.2f}"
        )


def main() -> None:
    inv_rows = load_rows(INVENTORY_CSV)
    prof_rows = load_rows(PROFIT_CSV)
    if not inv_rows:
        print(f"Input file '{INVENTORY_CSV}' not found. Exiting.")
        return
    if not prof_rows:
        print(f"Input file '{PROFIT_CSV}' not found. Exiting.")
        return
    combined = join_data(inv_rows, prof_rows)
    if not combined:
        print("No matching products found.")
        return
    sims = simulate(combined)
    print_table(sims)
    save_results(sims)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
