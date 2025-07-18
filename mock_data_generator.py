#!/usr/bin/env python3
"""Create synthetic outputs for the entire FBA pipeline.

This script populates the ``data/`` folder with CSV files resembling the
results produced by each stage of the project. It also creates a few
supplier message examples inside ``supplier_messages/``. The data is
intentionally fake but formatted so that downstream scripts and the
validation tool can run without external dependencies.
"""

import argparse
import csv
import os
from typing import List, Dict, Optional

DATA_DIR = "data"
MSG_DIR = "supplier_messages"

# --- Productos mock y reales para variedad ---
MOCK_ASINS = [
    ("B0MOCK001", "Mock Product 1"),
    ("B0MOCK002", "Mock Product 2"),
    ("B0MOCK003", "Mock Product 3"),
]
REAL_ASINS = [
    ("B08K3RCTVJ", "Baby Shark Collection"),
    ("B0161VA394", "BabyFirst Art Music"),
    ("B09FYTG37V", "Adjustable Dumbbells"),
]
ALL_PRODUCTS = [
    {"asin": a, "title": t, "price": 25.99 + i*5, "rating": 4.7-i*0.2, "reviews": 800-i*100, "bsr": 350+i*200}
    for i, (a, t) in enumerate(MOCK_ASINS + REAL_ASINS)
]

SHIPPING = 2.50


def ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MSG_DIR, exist_ok=True)


def write_csv(
    path: str,
    fieldnames: List[str],
    rows: List[Dict[str, object]],
    overwrite: bool = False,
) -> None:
    if not overwrite and os.path.exists(path) and os.path.getsize(path) > 0:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def estimate_sales(bsr: int) -> int:
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


def generate_product_results_var():
    rows = []
    for i, p in enumerate(ALL_PRODUCTS):
        margin = round(p["price"] * (0.25 if i%2==0 else 0.1), 2)
        units = 40 + i * 5
        total_profit = round(margin * units, 2)
        rows.append({
            "title": p["title"],
            "asin": p["asin"],
            "estimated_asin": "",
            "price": p["price"],
            "margin": margin,
            "units": units,
            "total_profit": total_profit,
        })
    return rows


def generate_market_analysis() -> List[Dict[str, object]]:
    rows = []
    for p in ALL_PRODUCTS:
        potential = "HIGH" if p["rating"] >= 4.5 else "MEDIUM"
        rows.append(
            {
                "asin": p["asin"],
                "title": p["title"],
                "price": p["price"],
                "rating": p["rating"],
                "reviews": p["reviews"],
                "bsr": p["bsr"],
                "link": f"https://example.com/{p['asin']}",
                "source": "mock",
                "estimated": False,
                "potential": potential,
            }
        )
    return rows


def generate_review_analysis() -> List[Dict[str, str]]:
    rows = []
    for p in ALL_PRODUCTS:
        rows.append(
            {
                "asin": p["asin"],
                "title": p["title"],
                "positives": "Good quality; Value for money",
                "negatives": "Limited colors",
                "diffs": "Minor design variations",
            }
        )
    return rows


def generate_profitability_var():
    rows = []
    for i, p in enumerate(ALL_PRODUCTS):
        cost = round(p["price"] * (0.55 if i%2==0 else 0.9), 2)
        fba_fees = round(p["price"] * 0.15 + 3.0, 2)
        profit = round(p["price"] - cost - SHIPPING - fba_fees, 2)
        roi = round(profit / (cost + SHIPPING + fba_fees), 2) if (cost + SHIPPING + fba_fees) > 0 else 0
        score = "HIGH" if roi >= 0.3 else ("MEDIUM" if roi >= 0.15 else "LOW")
        viable = "YES" if roi >= 0.15 and profit > 0 else "NO"
        rows.append({
            "asin": p["asin"],
            "title": p["title"],
            "price": p["price"],
            "cost": cost,
            "fba_fees": fba_fees,
            "shipping": SHIPPING,
            "profit": profit,
            "roi": roi,
            "score": score,
            "Viable": viable,
        })
    return rows


def generate_demand_var():
    rows = []
    for i, p in enumerate(ALL_PRODUCTS):
        sales = estimate_sales(int(p["bsr"]))
        level = demand_level(sales)
        # Forzar variedad
        if i == 0:
            level = "HIGH"
        elif i == 1:
            level = "MEDIUM"
        elif i == 2:
            level = "LOW"
        rows.append({
            "asin": p["asin"],
            "title": p["title"],
            "bsr": p["bsr"],
            "est_monthly_sales": sales,
            "demand_level": level,
        })
    return rows


def generate_supplier_selection(profit_rows: List[Dict[str, object]], demand_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    demand_map = {d["asin"]: d for d in demand_rows}
    rows = []
    for p in profit_rows:
        d = demand_map[p["asin"]]
        units = min(100, int(d["est_monthly_sales"] / 4))
        total_cost = round(units * p["cost"], 2)
        est_profit = round(units * p["profit"], 2)
        temporal_roi = round(p["roi"] * 4, 2)
        rows.append(
            {
                "asin": p["asin"],
                "title": p["title"],
                "price": p["price"],
                "cost": p["cost"],
                "roi": p["roi"],
                "temporal_roi": temporal_roi,
                "demand": d["demand_level"],
                "units_to_order": units,
                "total_cost": total_cost,
                "estimated_profit": est_profit,
            }
        )
    return rows


def generate_pricing(profit_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = []
    for p in profit_rows:
        new_price = round(p["price"] + 1.0, 2)
        rows.append(
            {
                "ASIN": p["asin"],
                "Title": p["title"],
                "Suggested Price": new_price,
                "Notes": "Introductory pricing",
            }
        )
    return rows


def generate_inventory(selection_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = []
    for s in selection_rows:
        recommended = int(s["units_to_order"] * 1.25)
        stock_cost = round(recommended * s["cost"], 2)
        proj_value = round(recommended * s["price"], 2)
        rows.append(
            {
                "asin": s["asin"],
                "title": s["title"],
                "recommended_stock": recommended,
                "stock_cost": stock_cost,
                "projected_value": proj_value,
            }
        )
    return rows


def generate_emails(selection_rows: List[Dict[str, object]]) -> str:
    messages = []
    for row in selection_rows:
        asin = row["asin"]
        title = row["title"]
        msg = (
            f"ASIN: {asin}\n"
            f"Title: {title}\n\n"
            "Dear Supplier,\n"
            f"Please provide your best quote for {row['units_to_order']} units of {title}.\n"
        )
        messages.append(msg)
    return "\n" + ("-" * 40 + "\n").join(messages)


def generate_message_files(selection_rows: List[Dict[str, object]], overwrite: bool = False) -> None:
    for row in selection_rows:
        asin = row["asin"]
        text = (
            f"Hello,\nWe are interested in purchasing {row['units_to_order']} units of {row['title']}.\n"
            "Please send pricing and lead time information.\n"
        )
        path = os.path.join(MSG_DIR, f"{asin}.txt")
        if not overwrite and os.path.exists(path):
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def file_exists_and_has_data(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate mock data for the full pipeline (varied)")
    args = parser.parse_args(argv)
    ensure_dirs()

    # PRODUCT RESULTS
    prod_path = os.path.join(DATA_DIR, "product_results.csv")
    if not file_exists_and_has_data(prod_path):
        product_rows = generate_product_results_var()
        write_csv(
            prod_path,
            ["title", "asin", "estimated_asin", "price", "margin", "units", "total_profit"],
            product_rows,
            overwrite=True,
        )

    # PROFITABILITY
    profit_path = os.path.join(DATA_DIR, "profitability_estimation_results.csv")
    if not file_exists_and_has_data(profit_path):
        profit_rows = generate_profitability_var()
        write_csv(
            profit_path,
            ["asin", "title", "price", "cost", "fba_fees", "shipping", "profit", "roi", "score", "Viable"],
            profit_rows,
            overwrite=True,
        )

    # DEMAND
    demand_path = os.path.join(DATA_DIR, "demand_forecast_results.csv")
    if not file_exists_and_has_data(demand_path):
        demand_rows = generate_demand_var()
        write_csv(
            demand_path,
            ["asin", "title", "bsr", "est_monthly_sales", "demand_level"],
            demand_rows,
            overwrite=True,
        )

    # SUPPLIER SELECTION: solo productos viables
    sel_path = os.path.join(DATA_DIR, "supplier_selection_results.csv")
    if not file_exists_and_has_data(sel_path):
        profit_rows = generate_profitability_var()
        demand_rows = generate_demand_var()
        selection_rows = []
        for p in profit_rows:
            if p["Viable"] == "YES":
                d = next((d for d in demand_rows if d["asin"] == p["asin"]), None)
                units = 25 if d else 10
                selection_rows.append({
                    "asin": p["asin"],
                    "title": p["title"],
                    "price": p["price"],
                    "cost": p["cost"],
                    "roi": p["roi"],
                    "temporal_roi": p["roi"]*4,
                    "demand": d["demand_level"] if d else "LOW",
                    "units_to_order": units,
                    "total_cost": units*p["cost"],
                    "estimated_profit": units*p["profit"],
                })
        write_csv(
            sel_path,
            ["asin", "title", "price", "cost", "roi", "temporal_roi", "demand", "units_to_order", "total_cost", "estimated_profit"],
            selection_rows,
            overwrite=True,
        )

    # PRICING: solo productos viables
    pricing_path = os.path.join(DATA_DIR, "pricing_suggestions.csv")
    if not file_exists_and_has_data(pricing_path):
        profit_rows = generate_profitability_var()
        pricing_rows = []
        for p in profit_rows:
            if p["Viable"] == "YES":
                pricing_rows.append({
                    "ASIN": p["asin"],
                    "Title": p["title"],
                    "Suggested Price": p["price"]+1.0,
                    "Notes": "Introductory pricing",
                })
        write_csv(
            pricing_path,
            ["ASIN", "Title", "Suggested Price", "Notes"],
            pricing_rows,
            overwrite=True,
        )

    # INVENTORY: todos los productos seleccionados
    inv_path = os.path.join(DATA_DIR, "inventory_management_results.csv")
    if not file_exists_and_has_data(inv_path):
        sel_rows = []
        if os.path.exists(sel_path):
            with open(sel_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                sel_rows = list(reader)
        inventory_rows = []
        for s in sel_rows:
            recommended = int(float(s["units_to_order"]) * 1.25)
            stock_cost = round(recommended * float(s["cost"]), 2)
            proj_value = round(recommended * float(s["price"]), 2)
            inventory_rows.append({
                "asin": s["asin"],
                "title": s["title"],
                "recommended_stock": recommended,
                "stock_cost": stock_cost,
                "projected_value": proj_value,
            })
        write_csv(
            inv_path,
            ["asin", "title", "recommended_stock", "stock_cost", "projected_value"],
            inventory_rows,
            overwrite=True,
        )

    # MENSAJES DE PROVEEDOR: solo productos seleccionados
    if os.path.exists(sel_path):
        with open(sel_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            sel_rows = list(reader)
        for row in sel_rows:
            asin = row["asin"]
            text = (
                f"Hello,\nWe are interested in purchasing {row['units_to_order']} units of {row['title']}.\n"
                "Please send pricing and lead time information.\n"
            )
            path = os.path.join(MSG_DIR, f"{asin}.txt")
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    print("Varied mock data written to 'data/' and 'supplier_messages/' (no overwrite if file exists). Includes viable/non-viable, mock/real, and edge cases.")


if __name__ == "__main__":
    main()
