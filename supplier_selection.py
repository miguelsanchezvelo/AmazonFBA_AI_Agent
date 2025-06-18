"""
Select the most profitable products to order from suppliers based on budget.

Combines profitability estimation with demand forecast and chooses the quantity
of each product to purchase, sorted by ROI and constrained by available budget.

Development mode: if input CSV files are missing, minimal mock data will be
created for testing purposes.
"""

import csv
import os
import re
from typing import Dict, List, Optional

PROFITABILITY_CSV = os.path.join("data", "profitability_estimation_results.csv")
DEMAND_CSV = os.path.join("data", "demand_forecast_results.csv")
OUTPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
TURNOVER_DAYS = 90  # average inventory turnover period in days


# Helpers ---------------------------------------------------------------

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


def save_csv(rows: List[Dict[str, object]], path: str, fieldnames: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# Mock data -------------------------------------------------------------

MOCK_PROFIT_ROWS = [
    {
        "asin": "B0TEST001",
        "title": "Mock Product A",
        "price": 25.0,
        "cost": 10.0,
        "fba_fees": 4.0,
        "shipping": 2.5,
        "profit": 8.5,
        "roi": 0.59,
        "score": "HIGH",
    },
    {
        "asin": "B0TEST002",
        "title": "Mock Product B",
        "price": 40.0,
        "cost": 20.0,
        "fba_fees": 5.0,
        "shipping": 2.5,
        "profit": 12.5,
        "roi": 0.5,
        "score": "MEDIUM",
    },
    {
        "asin": "B0TEST003",
        "title": "Mock Product C",
        "price": 15.0,
        "cost": 5.0,
        "fba_fees": 3.0,
        "shipping": 2.5,
        "profit": 4.5,
        "roi": 0.5,
        "score": "LOW",
    },
]

MOCK_DEMAND_ROWS = [
    {
        "asin": "B0TEST001",
        "title": "Mock Product A",
        "bsr": 300,
        "est_monthly_sales": 500,
        "demand_level": "HIGH",
    },
    {
        "asin": "B0TEST002",
        "title": "Mock Product B",
        "bsr": 1000,
        "est_monthly_sales": 300,
        "demand_level": "MEDIUM",
    },
    {
        "asin": "B0TEST003",
        "title": "Mock Product C",
        "bsr": 3000,
        "est_monthly_sales": 100,
        "demand_level": "LOW",
    },
]


def ensure_mock_data():
    if not os.path.exists(PROFITABILITY_CSV):
        save_csv(MOCK_PROFIT_ROWS, PROFITABILITY_CSV, list(MOCK_PROFIT_ROWS[0].keys()))
    if not os.path.exists(DEMAND_CSV):
        save_csv(MOCK_DEMAND_ROWS, DEMAND_CSV, list(MOCK_DEMAND_ROWS[0].keys()))


# Core logic ------------------------------------------------------------

def join_data(profit_rows: List[Dict[str, str]], demand_rows: List[Dict[str, str]]):
    demand_map = {r["asin"]: r for r in demand_rows}
    combined: List[Dict[str, object]] = []
    for p in profit_rows:
        asin = p.get("asin") or ""
        d = demand_map.get(asin)
        if not d:
            continue
        combined.append({**p, **d})
    return combined


def allocate_budget(rows: List[Dict[str, object]], budget: float):
    results: List[Dict[str, object]] = []
    remaining = budget
    total_profit = 0.0
    total_cost = 0.0
    for row in rows:
        cost = parse_float(row.get("cost")) or 0.0
        profit = parse_float(row.get("profit")) or 0.0
        demand = parse_int(row.get("est_monthly_sales")) or 0
        if cost <= 0:
            units = 0
        else:
            max_affordable = int(remaining // cost)
            units = min(max_affordable, demand)
        total_cost_row = round(units * cost, 2)
        est_profit_row = round(units * profit, 2)
        temporal_roi = (
            (est_profit_row / total_cost_row) * (365 / TURNOVER_DAYS)
            if total_cost_row
            else 0.0
        )
        row_result = {
            "asin": row.get("asin", ""),
            "title": row.get("title", ""),
            "price": parse_float(row.get("price")) or 0.0,
            "cost": cost,
            "roi": parse_float(row.get("roi")) or 0.0,
            "demand": row.get("demand_level", ""),
            "units_to_order": units,
            "total_cost": total_cost_row,
            "estimated_profit": est_profit_row,
            "temporal_roi": round(temporal_roi, 2),
        }
        results.append(row_result)
        remaining -= units * cost
        total_cost += units * cost
        total_profit += units * profit
    overall_roi = round(total_profit / total_cost, 2) if total_cost else 0.0
    return results, total_cost, total_profit, overall_roi


# Printing --------------------------------------------------------------

def print_table(rows: List[Dict[str, object]], totals):
    header = (
        f"{'ASIN':12} | {'Title':30} | {'Price':>6} | {'Cost':>6} | {'ROI':>5} | "
        f"{'TROI':>6} | {'Dem':>6} | {'Units':>5} | {'Tot Cost':>8} | {'Profit':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['asin']:12} | "
            f"{(r['title'] or '')[:30]:30} | "
            f"${r['price']:>6.2f} | "
            f"${r['cost']:>6.2f} | "
            f"{r['roi']:>5.2f} | "
            f"{r['temporal_roi']:>6.2f} | "
            f"{r['demand'][:6]:>6} | "
            f"{r['units_to_order']:>5} | "
            f"${r['total_cost']:>8.2f} | "
            f"${r['estimated_profit']:>7.2f}"
        )
    total_cost, total_profit, overall_roi = totals
    overall_troi = round(overall_roi * (365 / TURNOVER_DAYS), 2)
    print("-" * len(header))
    print(
        f"{'TOTAL':12} | "
        f"{'':30} | {'':>6} | {'':>6} | {'':>5} | {'':>6} | {'':>6} | {'':>5} | "
        f"${total_cost:>8.2f} | ${total_profit:>7.2f}"
    )
    print(f"Overall ROI: {overall_roi:.2f}  Temporal ROI: {overall_troi:.2f}")


# Main -----------------------------------------------------------------

def main() -> None:
    ensure_mock_data()
    profit_rows = load_rows(PROFITABILITY_CSV)
    demand_rows = load_rows(DEMAND_CSV)
    if not profit_rows or not demand_rows:
        print("Input files missing and mock data could not be created.")
        return
    combined = join_data(profit_rows, demand_rows)
    combined = [r for r in combined if str(r.get("demand_level")) in ("MEDIUM", "HIGH")]
    combined.sort(key=lambda x: parse_float(x.get("roi")) or 0.0, reverse=True)
    try:
        budget = float(input("Enter total budget in USD: "))
    except Exception:
        budget = 1000.0
    results, total_cost, total_profit, overall_roi = allocate_budget(combined, budget)
    print_table(results, (total_cost, total_profit, overall_roi))
    save_csv(
        results,
        OUTPUT_CSV,
        [
            "asin",
            "title",
            "price",
            "cost",
            "roi",
            "temporal_roi",
            "demand",
            "units_to_order",
            "total_cost",
            "estimated_profit",
        ],
    )
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
