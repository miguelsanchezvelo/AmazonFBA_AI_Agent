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

MOCK_ASINS = [
    ("B0MOCK001", "Mock Product 1"),
    ("B0MOCK002", "Mock Product 2"),
    ("B0MOCK003", "Mock Product 3"),
    ("B0MOCK004", "Mock Product 4"),
    ("B0MOCK005", "Mock Product 5"),
]

PRODUCTS = [
    {
        "asin": MOCK_ASINS[0][0],
        "title": MOCK_ASINS[0][1],
        "price": 25.99,
        "rating": 4.7,
        "reviews": 820,
        "bsr": 350,
    },
    {
        "asin": MOCK_ASINS[1][0],
        "title": MOCK_ASINS[1][1],
        "price": 32.50,
        "rating": 4.6,
        "reviews": 560,
        "bsr": 450,
    },
    {
        "asin": MOCK_ASINS[2][0],
        "title": MOCK_ASINS[2][1],
        "price": 40.00,
        "rating": 4.2,
        "reviews": 210,
        "bsr": 900,
    },
    {
        "asin": MOCK_ASINS[3][0],
        "title": MOCK_ASINS[3][1],
        "price": 23.99,
        "rating": 4.1,
        "reviews": 150,
        "bsr": 1200,
    },
    {
        "asin": MOCK_ASINS[4][0],
        "title": MOCK_ASINS[4][1],
        "price": 18.50,
        "rating": 4.5,
        "reviews": 300,
        "bsr": 1400,
    },
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


def generate_product_results() -> List[Dict[str, object]]:
    rows = []
    for i, p in enumerate(PRODUCTS):
        margin = round(p["price"] * 0.25, 2)
        units = 40 + i * 5
        total_profit = round(margin * units, 2)
        rows.append(
            {
                "title": p["title"],
                "asin": p["asin"],
                "estimated_asin": "",
                "price": p["price"],
                "margin": margin,
                "units": units,
                "total_profit": total_profit,
            }
        )
    return rows


def generate_market_analysis() -> List[Dict[str, object]]:
    rows = []
    for p in PRODUCTS:
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
    for p in PRODUCTS:
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


def generate_profitability() -> List[Dict[str, object]]:
    rows = []
    for p in PRODUCTS:
        cost = round(p["price"] * 0.55, 2)
        fba_fees = round(p["price"] * 0.15 + 3.0, 2)
        profit = round(p["price"] - cost - SHIPPING - fba_fees, 2)
        roi = round(profit / (cost + SHIPPING + fba_fees), 2)
        score = "HIGH" if roi >= 0.3 else "MEDIUM"
        rows.append(
            {
                "asin": p["asin"],
                "title": p["title"],
                "price": p["price"],
                "cost": cost,
                "fba_fees": fba_fees,
                "shipping": SHIPPING,
                "profit": profit,
                "roi": roi,
                "score": score,
            }
        )
    return rows


def generate_demand(rows_market: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = []
    for p in rows_market:
        sales = estimate_sales(int(p["bsr"]))
        level = demand_level(sales)
        rows.append(
            {
                "asin": p["asin"],
                "title": p["title"],
                "bsr": p["bsr"],
                "est_monthly_sales": sales,
                "demand_level": level,
            }
        )
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


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate mock data for the full pipeline")
    parser.add_argument(
        "--full",
        action="store_true",
        help="overwrite existing files instead of keeping them",
    )
    args = parser.parse_args(argv)

    ensure_dirs()
    overwrite = args.full

    product_rows = generate_product_results()
    write_csv(
        os.path.join(DATA_DIR, "product_results.csv"),
        ["title", "asin", "estimated_asin", "price", "margin", "units", "total_profit"],
        product_rows,
        overwrite,
    )

    market_rows = generate_market_analysis()
    write_csv(
        os.path.join(DATA_DIR, "market_analysis_results.csv"),
        [
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
        market_rows,
        overwrite,
    )

    review_rows = generate_review_analysis()
    write_csv(
        os.path.join(DATA_DIR, "review_analysis_results.csv"),
        ["asin", "title", "positives", "negatives", "diffs"],
        review_rows,
        overwrite,
    )

    profit_rows = generate_profitability()
    write_csv(
        os.path.join(DATA_DIR, "profitability_estimation_results.csv"),
        [
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
        profit_rows,
        overwrite,
    )

    demand_rows = generate_demand(market_rows)
    write_csv(
        os.path.join(DATA_DIR, "demand_forecast_results.csv"),
        ["asin", "title", "bsr", "est_monthly_sales", "demand_level"],
        demand_rows,
        overwrite,
    )

    selection_rows = generate_supplier_selection(profit_rows, demand_rows)
    write_csv(
        os.path.join(DATA_DIR, "supplier_selection_results.csv"),
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
        selection_rows,
        overwrite,
    )

    pricing_rows = generate_pricing(profit_rows)
    write_csv(
        os.path.join(DATA_DIR, "pricing_suggestions.csv"),
        ["ASIN", "Title", "Suggested Price", "Notes"],
        pricing_rows,
        overwrite,
    )

    inventory_rows = generate_inventory(selection_rows)
    write_csv(
        os.path.join(DATA_DIR, "inventory_management_results.csv"),
        ["asin", "title", "recommended_stock", "stock_cost", "projected_value"],
        inventory_rows,
        overwrite,
    )

    # Create supplier emails and message files
    emails = generate_emails(selection_rows)
    email_path = os.path.join(DATA_DIR, "supplier_emails.txt")
    if overwrite or not os.path.exists(email_path):
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(emails)

    generate_message_files(selection_rows, overwrite)

    print("Mock data written to 'data/' and 'supplier_messages/'")


if __name__ == "__main__":
    main()
