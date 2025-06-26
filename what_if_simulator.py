"""Interactive what-if simulator for FBA product pricing and demand."""

from __future__ import annotations

import argparse
import os
from typing import List, Optional

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pd = None  # type: ignore

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    st = None  # type: ignore

PRODUCT_CSV = os.path.join("data", "product_results.csv")


def load_products(mock: bool = False) -> "pd.DataFrame":
    """Return dataframe with product info for the simulator."""
    if pd is None:
        raise RuntimeError("pandas is required to load product data")

    if not mock and os.path.exists(PRODUCT_CSV):
        df = pd.read_csv(PRODUCT_CSV)
        price = pd.to_numeric(df.get("price"), errors="coerce").fillna(0.0)
        margin = pd.to_numeric(df.get("margin"), errors="coerce").fillna(0.0)
        units = pd.to_numeric(df.get("units"), errors="coerce").fillna(0).astype(int)
        cost = (price - margin).clip(lower=0.01)
        data = pd.DataFrame(
            {
                "ASIN": df.get("asin", df.get("estimated_asin", "")),
                "Title": df.get("title", ""),
                "price": price,
                "cost": cost,
                "units": units,
            }
        )
    else:
        data = pd.DataFrame(
            [
                {"ASIN": "B0SIM001", "Title": "Sample Wireless Earbuds", "price": 29.99, "cost": 15.0, "units": 50, "demand": "HIGH"},
                {"ASIN": "B0SIM002", "Title": "Yoga Mat 6mm", "price": 20.0, "cost": 8.0, "units": 30, "demand": "MEDIUM"},
                {"ASIN": "B0SIM003", "Title": "Stainless Steel Water Bottle", "price": 16.0, "cost": 7.0, "units": 40, "demand": "HIGH"},
                {"ASIN": "B0SIM004", "Title": "Aluminum Laptop Stand", "price": 45.0, "cost": 20.0, "units": 25, "demand": "MEDIUM"},
                {"ASIN": "B0SIM005", "Title": "LED Desk Lamp", "price": 22.0, "cost": 12.0, "units": 20, "demand": "LOW"},
            ]
        )

    if "demand" not in data.columns:
        data["demand"] = "MEDIUM"

    return data[["ASIN", "Title", "price", "cost", "units", "demand"]]


def compute_metrics(df: "pd.DataFrame") -> "pd.DataFrame":
    """Return dataframe with profit metrics."""
    profit = (df["price"] - df["cost"]) * df["units"]
    roi = (df["price"] - df["cost"]) / df["cost"].replace(0, float("nan"))
    proj = df["price"] * df["units"]
    return pd.DataFrame({"ASIN": df["ASIN"], "Title": df["Title"], "Profit": profit, "ROI": roi, "Projected Value": proj})


def run_app(df: "pd.DataFrame") -> None:
    """Launch the Streamlit app."""
    if st is None:  # pragma: no cover - streamlit missing
        print(
            "Streamlit is required to run this simulator. "
            "Install it with `pip install streamlit` and run `streamlit run what_if_simulator.py`."
        )
        return

    st.title("What-If Simulator")
    st.write("Adjust price, cost, units and demand to explore profitability scenarios.")

    demand_opts = ["LOW", "MEDIUM", "HIGH"]
    column_config = {
        "price": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
        "cost": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
        "units": st.column_config.NumberColumn(min_value=0, step=1),
        "demand": st.column_config.SelectboxColumn(options=demand_opts),
    }

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config=column_config,
    )

    metrics = compute_metrics(edited)
    st.subheader("Projected Metrics")
    st.dataframe(metrics, use_container_width=True)

    total_profit = metrics["Profit"].sum()
    mean_roi = metrics["ROI"].fillna(0).mean()
    profitable = int((metrics["Profit"] > 0).sum())

    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Profit", f"${total_profit:,.2f}")
    col2.metric("Average ROI", f"{mean_roi:.2f}")
    col3.metric("Profitable Products", f"{profitable}")

    try:  # pragma: no cover - optional chart
        st.subheader("Profit by Product")
        st.bar_chart(metrics.set_index("ASIN")["Profit"])
    except Exception:
        pass


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the what-if simulator")
    parser.add_argument("--mock", action="store_true", help="use mock data")
    args = parser.parse_args(argv)

    if pd is None:
        print("pandas is required to run this simulator. Please install pandas.")
        return

    df = load_products(mock=args.mock)
    run_app(df)


if __name__ == "__main__":
    main()
