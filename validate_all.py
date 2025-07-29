import os
import sys
import subprocess
import logging
from typing import List, Dict, Optional, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas missing
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas"], check=False)
    try:  # pragma: no cover - installation may fail
        import pandas as pd  # type: ignore
    except Exception as exc:  # pragma: no cover - still missing
        print("Failed to import pandas:", exc, file=sys.stderr)
        sys.exit(1)

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    USE_COLOR = True
except Exception:  # pragma: no cover - colorama missing
    class _Dummy:
        RESET_ALL = ""
        RED = GREEN = YELLOW = ""

    Fore = Style = _Dummy()  # type: ignore
    USE_COLOR = False

DATA_DIR = "data"

FILES = {
    "product_results.csv": {
        "cols": [
            "title",
            "asin",
            "estimated_asin",
            "price",
            "margin",
            "units",
            "total_profit",
        ],
    },
    "market_analysis_results.csv": {
        "cols": [
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
        ],
    },
    "profitability_estimation_results.csv": {
        "cols": [
            "asin",
            "title",
            "price",
            "cost",
            "fba_fees",
            "shipping",
            "profit",
            "roi",
            "score",
        ],
    },
    "demand_forecast_results.csv": {
        "cols": ["asin", "title", "bsr", "est_monthly_sales", "demand_level"],
    },
    "supplier_selection_results.csv": {
        "cols": [
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
    },
    "pricing_suggestions.csv": {
        "cols": ["ASIN", "Title", "Suggested Price", "Notes"],
    },
    "inventory_management_results.csv": {
        "cols": [
            "asin",
            "title",
            "recommended_stock",
            "stock_cost",
            "projected_value",
        ],
    },
}

# mapping of CLI scripts to the CSV files they should generate in ``--auto`` mode
SCRIPT_OUTPUTS = {
    "product_discovery.py": "product_results.csv",
    "market_analysis.py": "market_analysis_results.csv",
    "profitability_estimation.py": "profitability_estimation_results.csv",
    "demand_forecast.py": "demand_forecast_results.csv",
    "supplier_selection.py": "supplier_selection_results.csv",
    "pricing_simulator.py": "pricing_suggestions.csv",
    "inventory_management.py": "inventory_management_results.csv",
}


class Result:
    def __init__(self, module: str, status: str, message: str = ""):
        self.module = module
        self.status = status
        self.message = message

    def as_tuple(self) -> Tuple[str, str, str]:
        return self.module, self.status, self.message


def run_command(cmd: List[str]) -> Tuple[bool, str]:
    """Run ``cmd`` and return ``(success, output)``."""
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = res.stdout + res.stderr
        return res.returncode == 0, out
    except Exception as exc:  # pragma: no cover - unexpected failure
        return False, str(exc)


def check_script(script: str, output_file: str) -> Result:
    """Run ``script`` with ``--help`` and ``--auto`` and verify output file."""
    help_ok, help_out = run_command([sys.executable, script, "--help"])
    required = ["--auto", "--debug", "--verbose", "--max-products"]
    if help_ok:
        help_ok = all(opt in help_out for opt in required)

    auto_ok, auto_out = run_command([sys.executable, script, "--auto"])

    csv_path = os.path.join(DATA_DIR, output_file)
    csv_ok = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    status = "OK" if help_ok and auto_ok and csv_ok else ("Warning" if help_ok and auto_ok else "Error")
    notes = []
    if not csv_ok:
        notes.append("CSV missing")
    if not help_ok:
        notes.append("help")
    if not auto_ok:
        notes.append("auto")
    msg = ", ".join(notes)
    return Result(script, status, msg)


def print_script_results(results: List[Result]) -> None:
    header = f"{'Script':30} {'Status':>8}  Notes"
    print(header)
    print("-" * len(header))
    for r in results:
        note = r.message if r.message else "-"
        print(f"{r.module:30} {r.status:>8}  {note}")


def validate_scripts() -> List[Result]:
    """Run each CLI script in auto mode and verify its output."""
    results: List[Result] = []
    for script, fname in SCRIPT_OUTPUTS.items():
        res = check_script(script, fname)
        results.append(res)
    print("Validated scripts:\n")
    print_script_results(results)
    return results


def load_csv(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        logging.error("Missing file: %s", path)
        return None
    try:
        if os.stat(path).st_size == 0:
            logging.error("Empty file: %s", path)
            return None
    except Exception:
        pass
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - malformed CSV
        logging.error("Failed to read %s: %s", path, exc)
        return None
    if df.empty:
        logging.error("Empty file: %s", path)
        return None
    return df


def validate_columns(df: pd.DataFrame, expected: List[str]) -> Tuple[bool, List[str]]:
    missing = [c for c in expected if c not in df.columns]
    return not missing, missing


def validate_product_results(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    if (df["price"] <= 0).any():
        issues.append("non-positive price")
    if (df["margin"] < 0).any():
        issues.append("negative margin")
    if (df["units"] <= 0).any():
        issues.append("non-positive units")
    if (df["total_profit"] < 0).any():
        issues.append("negative total_profit")
    return issues, 0


def validate_market_analysis(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    if (df["price"] <= 0).any():
        issues.append("non-positive price")
    if (df["rating"] < 0).any() or (df["rating"] > 5).any():
        issues.append("rating out of range")
    if (df["reviews"] < 0).any():
        issues.append("negative reviews")
    if (pd.to_numeric(df["bsr"], errors="coerce") <= 0).any():
        issues.append("non-positive bsr")
    if "source" in df.columns and (df["source"].str.contains("mock", case=False)).any():
        issues.append("mock data source")
    return issues, 0


def validate_profitability(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    bad_count = 0
    if (df["price"] <= 0).any():
        issues.append("non-positive price")
    if (df["cost"] < 0).any():
        issues.append("negative cost")
    if (df["roi"] <= 0).any():
        bad = df.loc[df["roi"] <= 0, "asin"].astype(str).tolist()
        bad_count = len(bad)
    if (df["profit"] <= 0).any():
        issues.append("non-positive profit")
    return issues, bad_count


def validate_demand(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    if (pd.to_numeric(df["est_monthly_sales"], errors="coerce") <= 0).any():
        issues.append("non-positive est_monthly_sales")
    if not df["demand_level"].isin(["HIGH", "MEDIUM", "LOW"]).all():
        issues.append("invalid demand_level")
    return issues, 0


def validate_supplier_selection(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    bad_count = 0
    if (df["units_to_order"] < 0).any():
        issues.append("negative units_to_order")
    if (df["roi"] <= 0).any():
        bad = df.loc[df["roi"] <= 0, "asin"].astype(str).tolist()
        bad_count = len(bad)
    if (df["total_cost"] < 0).any():
        issues.append("negative total_cost")
    return issues, bad_count


def validate_pricing(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    if "Suggested Price" in df.columns:
        try:
            prices = df["Suggested Price"].astype(str).str.replace("$", "").astype(float)
            if (prices <= 0).any():
                issues.append("non-positive Suggested Price")
        except Exception:
            issues.append("invalid Suggested Price values")
    return issues, 0


def validate_inventory(df: pd.DataFrame) -> Tuple[List[str], int]:
    issues = []
    if (df["recommended_stock"] < 0).any():
        issues.append("negative recommended_stock")
    if (df["stock_cost"] < 0).any():
        issues.append("negative stock_cost")
    if (df["projected_value"] < 0).any():
        issues.append("negative projected_value")
    return issues, 0


VALIDATORS = {
    "product_results.csv": validate_product_results,
    "market_analysis_results.csv": validate_market_analysis,
    "profitability_estimation_results.csv": validate_profitability,
    "demand_forecast_results.csv": validate_demand,
    "supplier_selection_results.csv": validate_supplier_selection,
    "pricing_suggestions.csv": validate_pricing,
    "inventory_management_results.csv": validate_inventory,
}


def validate_file(fname: str) -> Tuple[Optional[pd.DataFrame], Result]:
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        load_csv(path)  # log
        return None, Result(fname, "Missing", "file not found")
    if os.stat(path).st_size == 0:
        load_csv(path)  # log
        return None, Result(fname, "Empty", "zero bytes")
    df = load_csv(path)
    if df is None:
        return None, Result(fname, "Error", "invalid or empty")
    ok_cols, missing = validate_columns(df, FILES[fname]["cols"])
    if not ok_cols:
        return df, Result(fname, "Error", f"Missing columns: {', '.join(missing)}")
    validator = VALIDATORS.get(fname)
    if validator:
        issues, bad_roi = validator(df)
    else:
        issues, bad_roi = [], 0
    if bad_roi and fname in (
        "profitability_estimation_results.csv",
        "supplier_selection_results.csv",
    ):
        print(
            f"WARNING: Some products have ROI ≤ 0 (check {fname})"
        )
    status = "OK" if not issues else "Warning"
    message = "; ".join(issues)
    return df, Result(fname, status, message)


def cross_check(data: Dict[str, pd.DataFrame]) -> List[Result]:
    results: List[Result] = []
    prod = data.get("product_results.csv")
    if prod is None:
        return results

    prod_asins = set(prod["asin"].dropna()) | set(prod["estimated_asin"].dropna())

    mapping = {
        "market_analysis_results.csv": ("asin", "market"),
        "profitability_estimation_results.csv": ("asin", "profitability"),
        "demand_forecast_results.csv": ("asin", "demand"),
        "supplier_selection_results.csv": ("asin", "supplier"),
        "pricing_suggestions.csv": ("ASIN", "pricing"),
        "inventory_management_results.csv": ("asin", "inventory"),
    }

    for fname, (col, label) in mapping.items():
        df = data.get(fname)
        if df is None:
            continue
        other_asins = set(df[col].dropna())
        missing = other_asins - prod_asins
        if missing:
            results.append(Result(f"{label} -> product", "ASIN mismatch", "ASIN missing from product_results"))

    supplier = data.get("supplier_selection_results.csv")
    pricing = data.get("pricing_suggestions.csv")
    if supplier is not None and pricing is not None:
        sup_asins = set(supplier["asin"].dropna())
        price_asins = set(pricing["ASIN"].dropna())
        if sup_asins != price_asins:
            results.append(Result("supplier vs pricing", "Warning", "ASIN mismatch"))

    demand = data.get("demand_forecast_results.csv")
    profit = data.get("profitability_estimation_results.csv")
    inventory = data.get("inventory_management_results.csv")
    if demand is not None and profit is not None and inventory is not None:
        d_asins = set(demand["asin"].dropna())
        p_asins = set(profit["asin"].dropna())
        i_asins = set(inventory["asin"].dropna())
        common = d_asins & p_asins & i_asins
        if not common:
            results.append(Result("demand/profitability/inventory", "Error", "No common ASINs"))
        else:
            for name, s in [("demand", d_asins), ("profitability", p_asins), ("inventory", i_asins)]:
                if s != common:
                    results.append(Result(f"{name} set", "Warning", "ASIN set differs"))

    return results


def min_product_check(data: Dict[str, pd.DataFrame]) -> List[Result]:
    results: List[Result] = []
    for fname in [
        "product_results.csv",
        "market_analysis_results.csv",
        "profitability_estimation_results.csv",
    ]:
        df = data.get(fname)
        if df is not None and len(df) < 5:
            results.append(Result(fname, "Warning", "fewer than 5 products"))
    return results


def print_summary(results: List[Result]) -> None:
    header = f"{'File':35} {'Status':>8}  Notes"
    print(header)
    print("-" * len(header))

    def fmt(status: str) -> str:
        if not USE_COLOR:
            return status
        color = {
            "OK": Fore.GREEN,
            "Warning": Fore.YELLOW,
            "Error": Fore.RED,
            "Missing": Fore.RED,
            "Empty": Fore.RED,
            "ASIN mismatch": Fore.RED,
        }.get(status, "")
        return f"{color}{status}{Style.RESET_ALL}"

    for r in results:
        msg = r.message if r.message else "-"
        status = fmt(r.status)
        print(f"{r.module:35} {status:>8}  {msg}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    script_results = validate_scripts()
    all_data: Dict[str, pd.DataFrame] = {}
    results: List[Result] = []
    for fname in FILES:
        df, res = validate_file(fname)
        if df is not None:
            all_data[fname] = df
        results.append(res)

    results.extend(cross_check(all_data))
    results.extend(min_product_check(all_data))

    if script_results:
        results = script_results + results

    print_summary(results)
    if any(r.status != "OK" for r in results):
        print("\nSuggested Fix:")
        print(
            "Run `python mock_data_generator.py` to regenerate missing or invalid files using mock data."
        )


if __name__ == "__main__":
    main()
