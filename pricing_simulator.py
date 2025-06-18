"""Simulate pricing strategies based on profitability and demand data."""

import csv
import os
import re
from typing import Dict, List, Optional

PROFIT_CSV = os.path.join("data", "profitability_estimation_results.csv")
DEMAND_CSV = os.path.join("data", "demand_forecast_results.csv")


# Parsing helpers ---------------------------------------------------------

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


# Loading ----------------------------------------------------------------

def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def join_data(profit_rows: List[Dict[str, str]], demand_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    demand_map = {r.get("asin"): r for r in demand_rows}
    combined: List[Dict[str, object]] = []
    for p in profit_rows:
        asin = p.get("asin") or ""
        d = demand_map.get(asin)
        if not d:
            continue
        price = parse_float(p.get("price"))
        cost = parse_float(p.get("cost"))
        shipping = parse_float(p.get("shipping")) or 0.0
        fba_fees = parse_float(p.get("fba_fees")) or 0.0
        sales = parse_int(d.get("est_monthly_sales")) or 0
        if price is None or cost is None:
            continue
        combined.append(
            {
                "asin": asin,
                "title": p.get("title", ""),
                "price": price,
                "cost": cost,
                "shipping": shipping,
                "fba_fees": fba_fees,
                "base_sales": sales,
            }
        )
    return combined


# Simulation --------------------------------------------------------------

def simulate(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for row in rows:
        base_price = row["price"]
        cost = row["cost"]
        shipping = row["shipping"]
        base_fees = row["fba_fees"]
        base_sales = row["base_sales"]
        for step in range(0, 6):  # 0% to 50% in 10% increments
            pct = step * 0.1
            new_price = round(base_price * (1 + pct), 2)
            sales_factor = max(0.0, 1 - 1.5 * pct)  # +10% price => -15% sales
            est_sales = int(round(base_sales * sales_factor))
            fba_fees = new_price * 0.15 + 3.0 if base_fees else 0.0
            profit_unit = new_price - cost - shipping - fba_fees
            roi = (
                round(profit_unit / (cost + shipping + fba_fees), 2)
                if (cost + shipping + fba_fees)
                else 0.0
            )
            total_profit = round(profit_unit * est_sales, 2)
            results.append(
                {
                    "asin": row["asin"],
                    "original_price": base_price,
                    "new_price": new_price,
                    "estimated_sales": est_sales,
                    "new_profit": total_profit,
                    "roi": roi,
                }
            )
    return results


# Printing ----------------------------------------------------------------

def print_table(rows: List[Dict[str, object]]):
    header = (
        f"{'ASIN':12} | {'Orig Price':>10} | {'New Price':>9} | {'Sales':>6} | {'Profit':>10} | {'ROI':>5}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | "
            f"${r['original_price']:>10.2f} | "
            f"${r['new_price']:>9.2f} | "
            f"{r['estimated_sales']:>6} | "
            f"${r['new_profit']:>10.2f} | "
            f"{r['roi']:>5.2f}"
        )


# Main --------------------------------------------------------------------

def main() -> None:
    prof_rows = load_rows(PROFIT_CSV)
    demand_rows = load_rows(DEMAND_CSV)
    if not prof_rows:
        print(f"Input file '{PROFIT_CSV}' not found. Exiting.")
        return
    if not demand_rows:
        print(f"Input file '{DEMAND_CSV}' not found. Exiting.")
        return
    combined = join_data(prof_rows, demand_rows)
    if not combined:
        print("No matching products found.")
        return
    sims = simulate(combined)
    print_table(sims)


if __name__ == "__main__":
    main()
