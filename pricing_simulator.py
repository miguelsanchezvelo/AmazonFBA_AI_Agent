"""Simulate how selling price changes impact ROI and total profit."""

import csv
import os
import re
from typing import Dict, List, Optional

INPUT_CSV = os.path.join("data", "profitability_estimation_results.csv")
OUTPUT_CSV = os.path.join("data", "pricing_simulation_results.csv")
VARIATIONS = [-0.2, -0.1, 0.0, 0.1, 0.2]
DEFAULT_SALES = 100  # units used if no sales info available


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


# Simulation --------------------------------------------------------------

def simulate(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for row in rows:
        price = parse_float(row.get("price"))
        cost = parse_float(row.get("cost")) or 0.0
        shipping = parse_float(row.get("shipping")) or 0.0
        base_sales = parse_int(row.get("est_monthly_sales")) or DEFAULT_SALES
        if price is None or cost is None:
            continue
        for pct in VARIATIONS:
            new_price = round(price * (1 + pct), 2)
            fba_fees = round(new_price * 0.15 + 3.0, 2)
            margin = new_price - cost - shipping - fba_fees
            total_cost = cost + shipping + fba_fees
            roi = round(margin / total_cost, 2) if total_cost else 0.0
            total_profit = round(margin * base_sales, 2)
            results.append(
                {
                    "asin": row.get("asin", ""),
                    "title": row.get("title", ""),
                    "variation": f"{pct:+.0%}",
                    "new_price": new_price,
                    "margin_per_unit": round(margin, 2),
                    "roi": roi,
                    "total_profit": total_profit,
                }
            )
    return results


# Saving -----------------------------------------------------------------

def save_results(rows: List[Dict[str, object]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "asin",
                "title",
                "variation",
                "new_price",
                "margin_per_unit",
                "roi",
                "total_profit",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


# Printing ----------------------------------------------------------------

def print_table(rows: List[Dict[str, object]]) -> None:
    header = (
        f"{'ASIN':12} | {'Var':>5} | {'Price':>8} | {'Margin':>8} | {'ROI':>5} | {'Tot Profit':>11}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | {r['variation']:>5} | ${r['new_price']:>8.2f} | "
            f"${r['margin_per_unit']:>8.2f} | {r['roi']:>5.2f} | ${r['total_profit']:>11.2f}"
        )


# Main --------------------------------------------------------------------

def main() -> None:
    rows = load_rows(INPUT_CSV)
    if not rows:
        print(
            f"Input file '{INPUT_CSV}' not found. Run profitability_estimation.py first."
        )
        return
    sims = simulate(rows)
    if not sims:
        print("No valid rows found for simulation.")
        return
    print_table(sims)
    save_results(sims, OUTPUT_CSV)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
