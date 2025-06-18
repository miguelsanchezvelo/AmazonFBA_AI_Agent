import csv
import os
from typing import List, Dict, Optional

try:
    from tabulate import tabulate
    HAVE_TABULATE = True
except ImportError:  # pragma: no cover - optional dependency
    HAVE_TABULATE = False

INPUT_CSV = os.path.join("data", "market_analysis_results.csv")
MOCK_CSV = os.path.join("data", "mock_market_data.csv")
OUTPUT_CSV = os.path.join("data", "demand_forecast_results.csv")


def parse_bsr(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def estimate_sales(bsr: Optional[int]) -> int:
    if bsr is not None:
        if bsr < 500:
            return 1000
        if bsr < 1000:
            return 500
        if bsr < 2000:
            return 250
    return 100


def demand_level(sales: int) -> str:
    if sales >= 800:
        return "HIGH"
    if sales >= 300:
        return "MEDIUM"
    return "LOW"


def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def choose_input() -> List[Dict[str, str]]:
    rows = load_rows(INPUT_CSV)
    if not rows:
        rows = load_rows(MOCK_CSV)
        if not rows:
            print("No input CSV files found. Exiting.")
            raise SystemExit(1)
        print(
            "⚠️ Using mock data from 'data/mock_market_data.csv' for demand forecast"
        )
    return rows


def process(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for row in rows:
        asin = row.get("asin", "")
        title = row.get("title", "")
        bsr = parse_bsr(row.get("bsr"))
        sales = estimate_sales(bsr)
        level = demand_level(sales)
        results.append(
            {
                "asin": asin,
                "title": title,
                "bsr": bsr if bsr is not None else "",
                "est_monthly_sales": sales,
                "demand_level": level,
            }
        )
    return results


def save_results(rows: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "asin",
                "title",
                "bsr",
                "est_monthly_sales",
                "demand_level",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: List[Dict[str, str]]):
    table = []
    for r in rows:
        table.append(
            [
                r["asin"],
                (r["title"] or "")[:30],
                r.get("bsr", ""),
                r["est_monthly_sales"],
                r["demand_level"],
            ]
        )
    headers = ["ASIN", "Title", "BSR", "Est. Monthly Sales", "Demand Level"]
    if HAVE_TABULATE:
        print(tabulate(table, headers=headers, tablefmt="github"))
    else:
        header = f"{'ASIN':12} | {'Title':30} | {'BSR':>5} | {'Sales':>6} | {'Demand':>6}"
        print(header)
        print("-" * len(header))
        for row in table:
            asin, title, bsr, sales, level = row
            bsr_str = str(bsr) if bsr != "" else "N/A"
            print(
                f"{asin:12} | {title:30} | {bsr_str:>5} | {sales:>6} | {level:>6}"
            )


def main() -> None:
    rows = choose_input()
    results = process(rows)
    print_table(results)
    save_results(results)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
