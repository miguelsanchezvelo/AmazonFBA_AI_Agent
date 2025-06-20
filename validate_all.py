import os
import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd

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


class Result:
    def __init__(self, module: str, status: str, message: str = ""):
        self.module = module
        self.status = status
        self.message = message

    def as_tuple(self) -> Tuple[str, str, str]:
        return self.module, self.status, self.message


def load_csv(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        logging.error("File not found: %s", path)
        return None
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - malformed CSV
        logging.error("Failed to read %s: %s", path, exc)
        return None
    if df.empty:
        logging.error("File %s is empty", path)
        return None
    return df


def validate_columns(df: pd.DataFrame, expected: List[str]) -> Tuple[bool, List[str]]:
    missing = [c for c in expected if c not in df.columns]
    return not missing, missing


def validate_product_results(df: pd.DataFrame) -> List[str]:
    issues = []
    if (df["price"] <= 0).any():
        issues.append("non-positive price")
    if (df["margin"] < 0).any():
        issues.append("negative margin")
    if (df["units"] <= 0).any():
        issues.append("non-positive units")
    if (df["total_profit"] < 0).any():
        issues.append("negative total_profit")
    return issues


def validate_market_analysis(df: pd.DataFrame) -> List[str]:
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
    return issues


def validate_profitability(df: pd.DataFrame) -> List[str]:
    issues = []
    if (df["price"] <= 0).any():
        issues.append("non-positive price")
    if (df["cost"] < 0).any():
        issues.append("negative cost")
    if (df["roi"] <= 0).any():
        issues.append("non-positive ROI")
    if (df["profit"] <= 0).any():
        issues.append("non-positive profit")
    return issues


def validate_demand(df: pd.DataFrame) -> List[str]:
    issues = []
    if (pd.to_numeric(df["est_monthly_sales"], errors="coerce") <= 0).any():
        issues.append("non-positive est_monthly_sales")
    if not df["demand_level"].isin(["HIGH", "MEDIUM", "LOW"]).all():
        issues.append("invalid demand_level")
    return issues


def validate_supplier_selection(df: pd.DataFrame) -> List[str]:
    issues = []
    if (df["units_to_order"] < 0).any():
        issues.append("negative units_to_order")
    if (df["roi"] <= 0).any():
        issues.append("non-positive ROI")
    if (df["total_cost"] < 0).any():
        issues.append("negative total_cost")
    return issues


def validate_pricing(df: pd.DataFrame) -> List[str]:
    issues = []
    if "Suggested Price" in df.columns:
        try:
            prices = df["Suggested Price"].astype(str).str.replace("$", "").astype(float)
            if (prices <= 0).any():
                issues.append("non-positive Suggested Price")
        except Exception:
            issues.append("invalid Suggested Price values")
    return issues


def validate_inventory(df: pd.DataFrame) -> List[str]:
    issues = []
    if (df["recommended_stock"] < 0).any():
        issues.append("negative recommended_stock")
    if (df["stock_cost"] < 0).any():
        issues.append("negative stock_cost")
    if (df["projected_value"] < 0).any():
        issues.append("negative projected_value")
    return issues


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
    df = load_csv(path)
    if df is None:
        return None, Result(fname, "Error", "Missing or empty file")
    ok_cols, missing = validate_columns(df, FILES[fname]["cols"])
    if not ok_cols:
        return df, Result(fname, "Error", f"Missing columns: {', '.join(missing)}")
    validator = VALIDATORS.get(fname)
    issues: List[str] = validator(df) if validator else []
    status = "OK" if not issues else "Warning"
    message = "; ".join(issues)
    return df, Result(fname, status, message)


def cross_check(data: Dict[str, pd.DataFrame]) -> List[Result]:
    results: List[Result] = []
    prod = data.get("product_results.csv")
    market = data.get("market_analysis_results.csv")
    profit = data.get("profitability_estimation_results.csv")
    demand = data.get("demand_forecast_results.csv")
    supplier = data.get("supplier_selection_results.csv")
    pricing = data.get("pricing_suggestions.csv")
    inventory = data.get("inventory_management_results.csv")

    if prod is not None and market is not None:
        prod_asins = set(prod["asin"].dropna()) | set(prod["estimated_asin"].dropna())
        market_asins = set(market["asin"].dropna())
        if not prod_asins & market_asins:
            results.append(Result("product -> market", "Error", "No ASIN overlap"))
    if market is not None and profit is not None:
        if not set(market["asin"].dropna()) & set(profit["asin"].dropna()):
            results.append(Result("market -> profitability", "Error", "No ASIN overlap"))
    if market is not None and demand is not None:
        if not set(market["asin"].dropna()) & set(demand["asin"].dropna()):
            results.append(Result("market -> demand", "Error", "No ASIN overlap"))
    if profit is not None and demand is not None and supplier is not None:
        combined = set(profit["asin"].dropna()) & set(demand["asin"].dropna())
        if not combined:
            results.append(Result("profit/demand -> supplier", "Error", "No ASIN overlap"))
        else:
            if not combined & set(supplier["asin"].dropna()):
                results.append(Result("profit/demand -> supplier", "Error", "Supplier ASIN mismatch"))
    if supplier is not None and pricing is not None:
        if not set(supplier["asin"].dropna()) & set(pricing["ASIN"].dropna()):
            results.append(Result("supplier -> pricing", "Error", "No ASIN overlap"))
    if supplier is not None and inventory is not None:
        if not set(supplier["asin"].dropna()) & set(inventory["asin"].dropna()):
            results.append(Result("supplier -> inventory", "Error", "No ASIN overlap"))
    return results


def print_summary(results: List[Result]) -> None:
    header = f"{'Module':35} {'Status':>8}  Message"
    print(header)
    print("-" * len(header))
    for r in results:
        msg = r.message if r.message else "-"
        print(f"{r.module:35} {r.status:>8}  {msg}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    all_data: Dict[str, pd.DataFrame] = {}
    results: List[Result] = []
    for fname in FILES:
        df, res = validate_file(fname)
        if df is not None:
            all_data[fname] = df
        results.append(res)

    results.extend(cross_check(all_data))
    print_summary(results)


if __name__ == "__main__":
    main()
