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
import pandas as pd

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


def clean_mock_files():
    files = [
        "product_results.csv",
        "market_analysis_results.csv",
        "review_analysis_results.csv",
        "profitability_estimation_results.csv",
        "demand_forecast_results.csv",
        "supplier_selection_results.csv",
        "pricing_suggestions.csv",
        "inventory_management_results.csv",
        "supplier_emails.txt",
    ]
    for fname in files:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
    # Limpia mensajes mock
    if os.path.exists(MSG_DIR):
        for f in os.listdir(MSG_DIR):
            if f.startswith("B0MOCK") and f.endswith(".txt"):
                os.remove(os.path.join(MSG_DIR, f))


# --- Generación de historial de ventas con suficiente longitud y outliers para pruebas de forecasting y anomalías ---
def generate_sales_history(asin, path):
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    np.random.seed(hash(asin) % 2**32)
    n_periods = 36  # 3 años de datos mensuales
    base = 50 + np.random.randint(-10, 10)
    trend = np.linspace(0, 15, n_periods)
    seasonality = 10 * np.sin(np.linspace(0, 2 * np.pi, n_periods))
    noise = np.random.normal(0, 5, n_periods)
    sales = base + trend + seasonality + noise
    # Insertar algunos outliers
    sales[5] += 30
    sales[15] -= 25
    sales[25] += 40
    sales = np.round(np.clip(sales, 5, None)).astype(int)
    dates = [datetime.today() - timedelta(days=30 * (n_periods-1 - i)) for i in range(n_periods)]
    df = pd.DataFrame({'Date': [d.strftime('%Y-%m-%d') for d in dates], 'Units_Sold': sales})
    df.to_csv(path, index=False)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate mock data for the full pipeline (varied)")
    parser.add_argument('--clean', action='store_true', help='Remove mock data files before generating')
    args = parser.parse_args(argv)
    ensure_dirs()
    if args.clean:
        clean_mock_files()

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
    else:
        # Si existe, añade los mock si no están
        df = pd.read_csv(prod_path)
        existing_asins = set(df['asin'])
        mock_rows = [row for row in generate_product_results_var() if row['asin'] not in existing_asins]
        if mock_rows:
            df = pd.concat([df, pd.DataFrame(mock_rows)], ignore_index=True)
            df.to_csv(prod_path, index=False)

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

    # PRICING: todos los productos viables (mock y reales)
    pricing_path = os.path.join(DATA_DIR, "pricing_suggestions.csv")
    if not file_exists_and_has_data(pricing_path):
        profit_rows = generate_profitability_var()
        pricing_rows = []
        notes_options = [
            "Introductory pricing",
            "Matches top competitor",
            "Maximizes ROI",
            "Discounted for launch",
            "Price matched to market"
        ]
        for i, p in enumerate(profit_rows):
            if p["Viable"] == "YES":
                note = notes_options[i % len(notes_options)]
                suggested_price = round(float(p["price"]) + 2.0 - (i % 3), 2)
                pricing_rows.append({
                    "ASIN": p["asin"],
                    "Title": p["title"],
                    "Suggested Price": suggested_price,
                    "Notes": note,
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

    # SALES HISTORY: ventas diarias para todos los productos
    sales_hist_path = os.path.join(DATA_DIR, "sales_history.csv")
    if not file_exists_and_has_data(sales_hist_path):
        sales_rows = []
        import random, datetime
        today = datetime.date.today()
        for p in ALL_PRODUCTS:
            asin = p["asin"]
            # Generar ventas para los últimos 3 meses
            for month_delta in range(3):
                for day in range(1, 29):
                    date = today.replace(day=1) - datetime.timedelta(days=month_delta*30) + datetime.timedelta(days=day-1)
                    units = random.randint(0, 5) + (3 if month_delta == 0 else 0)  # Más ventas el mes actual
                    sales_rows.append({
                        "ASIN": asin,
                        "Date": date.strftime("%Y-%m-%d"),
                        "Units_Sold": units
                    })
        write_csv(sales_hist_path, ["ASIN", "Date", "Units_Sold"], sales_rows, overwrite=True)

    # INVENTORY MOVEMENTS: entradas y salidas para todos los productos
    inv_mov_path = os.path.join(DATA_DIR, "inventory_movements_mock.csv")
    if not file_exists_and_has_data(inv_mov_path):
        inv_rows = []
        import random, datetime
        today = datetime.date.today()
        for p in ALL_PRODUCTS:
            asin = p["asin"]
            # Simular 2 entradas de stock y varias salidas (ventas)
            for i in range(2):
                date_in = today - datetime.timedelta(days=60 - i*30)
                qty_in = random.randint(80, 120)
                inv_rows.append({
                    "ASIN": asin,
                    "Date": date_in.strftime("%Y-%m-%d"),
                    "Type": "IN",
                    "Quantity": qty_in,
                    "Note": "Stock arrival"
                })
            # Simular salidas (ventas) repartidas
            for i in range(20):
                date_out = today - datetime.timedelta(days=random.randint(0, 59))
                qty_out = random.randint(1, 6)
                inv_rows.append({
                    "ASIN": asin,
                    "Date": date_out.strftime("%Y-%m-%d"),
                    "Type": "OUT",
                    "Quantity": qty_out,
                    "Note": "Sale"
                })
        write_csv(inv_mov_path, ["ASIN", "Date", "Type", "Quantity", "Note"], inv_rows, overwrite=True)

    # Obtener la lista de ASINs mock generados
    asins = [row['asin'] for row in generate_product_results_var()]
    for asin in asins:
        sales_history_path = os.path.join(DATA_DIR, f"sales_history_{asin}.csv")
        generate_sales_history(asin, sales_history_path)

    print("Varied mock data written to 'data/' and 'supplier_messages/' (no overwrite if file exists). Includes viable/non-viable, mock/real, and edge cases.")


if __name__ == "__main__":
    main()
