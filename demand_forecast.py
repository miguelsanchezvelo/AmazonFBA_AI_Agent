import argparse
import csv
import os
import time
from typing import List, Dict, Optional, Set
import argparse

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

try:
    from tabulate import tabulate
    HAVE_TABULATE = True
except ImportError:  # pragma: no cover - optional dependency
    HAVE_TABULATE = False

INPUT_CSV = os.path.join("data", "market_analysis_results.csv")
MOCK_CSV = os.path.join("data", "mock_market_data.csv")
OUTPUT_CSV = os.path.join("data", "demand_forecast_results.csv")
FALLBACK_ROW = {
    "asin": "B0MOCK001",
    "title": "Mock Product",
    "bsr": 1000,
    "est_monthly_sales": 300,
    "demand_level": "MEDIUM",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate product demand from market analysis data")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--input', default=INPUT_CSV, help='Path to market analysis CSV file')
    parser.add_argument('--output', default=OUTPUT_CSV, help='Where to save demand forecast results')
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
            print("No input CSV files found. Generating minimal mock data.")
            rows = [FALLBACK_ROW]
        else:
            print(
                "⚠️ Using mock data from 'data/mock_market_data.csv' for demand forecast"
            )
    return rows


def process(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    valid = load_valid_asins()
    results: List[Dict[str, str]] = []
    unknown: Set[str] = set()
    for row in rows:
        asin = row.get("asin", "")
        if valid and asin and asin not in valid:
            unknown.add(asin)
            continue
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
    if unknown:
        print(
            "Warning: Skipping "
            f"{len(unknown)} products not found in product_results.csv: "
            + ", ".join(sorted(unknown))
        )
        log_asin_mismatch("demand_forecast", unknown)
        log(f"demand_forecast: ASIN mismatch {','.join(sorted(unknown))}")
        if not results:
            return []
    return results


def save_results(rows: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    if not rows:
        print("No valid ASINs to forecast. Skipping save.")
        return
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
    global INPUT_CSV, OUTPUT_CSV
    parser = argparse.ArgumentParser(description="Demand forecast")
    parser.add_argument('--input', default='data/profitability_estimation_results.csv', help='Input CSV file')
    parser.add_argument('--output', default='data/demand_forecast_results.csv', help='Output CSV file')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    args = parser.parse_args()
    INPUT_CSV = args.input
    OUTPUT_CSV = args.output
    use_mock = args.mock
    if use_mock:
        mock_demand = [
            {"asin": "B0MOCK001", "title": "Mock Product 1", "bsr": 350, "est_monthly_sales": 1000, "demand_level": "HIGH"},
            {"asin": "B0MOCK002", "title": "Mock Product 2", "bsr": 450, "est_monthly_sales": 500, "demand_level": "HIGH"},
            {"asin": "B0MOCK003", "title": "Mock Product 3", "bsr": 900, "est_monthly_sales": 250, "demand_level": "MEDIUM"},
            {"asin": "B0MOCK004", "title": "Mock Product 4", "bsr": 1200, "est_monthly_sales": 200, "demand_level": "MEDIUM"},
            {"asin": "B0MOCK005", "title": "Mock Product 5", "bsr": 1400, "est_monthly_sales": 100, "demand_level": "LOW"},
        ]
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["asin", "title", "bsr", "est_monthly_sales", "demand_level"])
            writer.writeheader()
            writer.writerows(mock_demand)
        print(f"Mock demand forecast data saved to {OUTPUT_CSV}")
        return
    rows = load_rows(INPUT_CSV)
    if not rows:
        msg = "No se encontraron productos para estimar demanda. El archivo de entrada está vacío."
        print(msg)
        log(msg)
        save_results([])
        print(f"Results saved to {OUTPUT_CSV}")
        return
    asin_invalid = 0
    no_demand_data = 0
    total = 0
    results = []
    for row in rows:
        total += 1
        asin = row.get("asin")
        if not asin:
            asin_invalid += 1
            continue
        # Simulación: si no hay datos de demanda, descartar
        demand_data = True  # Aquí iría la lógica real
        if not demand_data:
            no_demand_data += 1
            continue
        results.append(row)
    if not results:
        msg = (
            f"No se encontraron resultados viables en la estimación de demanda.\n"
            f"Total productos analizados: {total}.\n"
            f"Descartados por ASIN inválido: {asin_invalid}.\n"
            f"Descartados por falta de datos de demanda: {no_demand_data}.\n"
        )
        print(msg)
        log(msg)
        save_results([])
        print(f"Results saved to {OUTPUT_CSV}")
        return
    save_results(results)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
