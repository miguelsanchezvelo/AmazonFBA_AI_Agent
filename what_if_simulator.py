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

try:
    import altair as alt  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    alt = None  # type: ignore

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
        rating = pd.to_numeric(df.get("rating"), errors="coerce")
        reviews = pd.to_numeric(df.get("reviews"), errors="coerce")
        cost = (price - margin).clip(lower=0.01)
        data = pd.DataFrame(
            {
                "ASIN": df.get("asin", df.get("estimated_asin", "")),
                "Title": df.get("title", ""),
                "price": price,
                "cost": cost,
                "units": units,
                "rating": rating,
                "reviews": reviews,
            }
        )
    else:
        data = pd.DataFrame(
            [
                {"ASIN": "B0SIM001", "Title": "Sample Wireless Earbuds", "price": 29.99, "cost": 15.0, "units": 50, "demand": "HIGH", "rating": 4.6, "reviews": 1500},
                {"ASIN": "B0SIM002", "Title": "Yoga Mat 6mm", "price": 20.0, "cost": 8.0, "units": 30, "demand": "MEDIUM", "rating": 4.3, "reviews": 800},
                {"ASIN": "B0SIM003", "Title": "Stainless Steel Water Bottle", "price": 16.0, "cost": 7.0, "units": 40, "demand": "HIGH", "rating": 4.5, "reviews": 600},
                {"ASIN": "B0SIM004", "Title": "Aluminum Laptop Stand", "price": 45.0, "cost": 20.0, "units": 25, "demand": "MEDIUM", "rating": 4.4, "reviews": 250},
                {"ASIN": "B0SIM005", "Title": "LED Desk Lamp", "price": 22.0, "cost": 12.0, "units": 20, "demand": "LOW", "rating": 4.2, "reviews": 120},
            ]
        )

    if "demand" not in data.columns:
        data["demand"] = "MEDIUM"

    cols = ["ASIN", "Title", "price", "cost", "units", "demand"]
    if "rating" in data.columns:
        cols.append("rating")
    if "reviews" in data.columns:
        cols.append("reviews")
    return data[cols]


def compute_metrics(df: "pd.DataFrame") -> "pd.DataFrame":
    """Return dataframe with profit metrics."""
    profit = (df["price"] - df["cost"]) * df["units"]
    roi = (df["price"] - df["cost"]) / df["cost"].replace(0, float("nan"))
    proj = df["price"] * df["units"]

    rating = pd.to_numeric(df.get("rating"), errors="coerce")
    reviews = pd.to_numeric(df.get("reviews"), errors="coerce")

    metrics = pd.DataFrame(
        {
            "ASIN": df["ASIN"],
            "Title": df["Title"],
            "Profit": profit,
            "ROI": roi,
            "Projected Value": proj,
            "Demand": df.get("demand", ""),
            "Rating": rating,
            "Reviews": reviews,
        }
    )

    # Normalized values for scoring
    roi_norm = roi.clip(lower=0).clip(upper=1)
    units = pd.to_numeric(df["units"], errors="coerce")
    min_sales = units.min()
    max_sales = units.max()
    sales_norm = (units - min_sales) / (max_sales - min_sales) if max_sales != min_sales else 1.0

    if reviews.notna().any():
        min_rev = reviews.min()
        max_rev = reviews.max()
        reviews_norm = (reviews - min_rev) / (max_rev - min_rev) if max_rev != min_rev else 1.0
    else:
        reviews_norm = pd.Series([float("nan")] * len(reviews))

    rating_norm = rating / 5.0

    weights = {
        "roi": 0.4,
        "sales": 0.3,
        "reviews": 0.15,
        "rating": 0.15,
    }

    def row_score(row: pd.Series) -> float:
        total = 0.0
        weight_sum = 0.0
        if not pd.isna(row["roi"]):
            total += row["roi"] * weights["roi"]
            weight_sum += weights["roi"]
        if not pd.isna(row["sales"]):
            total += row["sales"] * weights["sales"]
            weight_sum += weights["sales"]
        if not pd.isna(row["reviews"]):
            total += row["reviews"] * weights["reviews"]
            weight_sum += weights["reviews"]
        if not pd.isna(row["rating"]):
            total += row["rating"] * weights["rating"]
            weight_sum += weights["rating"]
        return total / weight_sum if weight_sum else float("nan")

    score_df = pd.DataFrame(
        {
            "roi": roi_norm,
            "sales": sales_norm,
            "reviews": reviews_norm,
            "rating": rating_norm,
        }
    )
    metrics["Composite Score"] = score_df.apply(row_score, axis=1)

    return metrics


def abbreviate_title(title: str, asin: str, words: int = 4) -> str:
    """Return shortened title using a few words with ASIN fallback."""
    if not title or str(title).strip() == "" or str(title).lower() == "nan":
        return asin
    short = " ".join(str(title).split()[:words])
    return short if short else asin


def run_app(df: "pd.DataFrame") -> None:
    """Launch the Streamlit app."""
    if st is None:  # pragma: no cover - streamlit missing
        print(
            "Streamlit is required to run this simulator. "
            "Install it with `pip install streamlit` and run `streamlit run what_if_simulator.py`."
        )
        return

    try:  # pragma: no cover - optional API
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("What-If Simulator")
    st.write("Adjust price, cost, units and demand to explore profitability scenarios.")

    label_choice = st.selectbox(
        "X-axis label",
        options=["ASIN", "Product Name"],
        index=1,
    )

    demand_opts = ["LOW", "MEDIUM", "HIGH"]
    column_config = {
        "price": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
        "cost": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
        "units": st.column_config.NumberColumn(min_value=0, step=1),
        "demand": st.column_config.SelectboxColumn(options=demand_opts),
    }
    if "rating" in df.columns:
        column_config["rating"] = st.column_config.NumberColumn(
            min_value=0.0, max_value=5.0, step=0.1, format="%.1f"
        )
    if "reviews" in df.columns:
        column_config["reviews"] = st.column_config.NumberColumn(min_value=0, step=1)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config=column_config,
    )

    metrics = compute_metrics(edited)
    metrics["Short Title"] = metrics.apply(
        lambda r: abbreviate_title(r["Title"], r["ASIN"]), axis=1
    )
    dups = metrics["Short Title"].duplicated(keep=False)
    metrics.loc[dups, "Short Title"] = (
        metrics.loc[dups, "Short Title"] + " (" + metrics.loc[dups, "ASIN"] + ")"
    )
    metrics["Label"] = metrics["ASIN"] if label_choice == "ASIN" else metrics["Short Title"]

    st.subheader("Projected Metrics")
    st.dataframe(
        metrics.drop(columns=["Short Title", "Label"]), use_container_width=True
    )

    with st.expander("Composite Score Formula"):
        st.markdown(
            """
            **Composite Score** is a weighted average of normalized metrics:

            - ROI (40%) – ROI clipped to the range [0, 1]
            - Forecasted Demand (30%) – sales volume normalized between the minimum and maximum
            - Review Count (15%) – normalized between the minimum and maximum
            - Rating (15%) – rating divided by 5

            Missing values omit that factor and the remaining weights are rescaled proportionally.
            """
        )

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
        if alt is not None:
            chart = (
                alt.Chart(metrics)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Label:N",
                        title=label_choice,
                        sort=None,
                        axis=alt.Axis(labelAngle=-30),
                    ),
                    y=alt.Y("Profit:Q", title="Profit"),
                    tooltip=[
                        alt.Tooltip("Title:N", title="Title"),
                        alt.Tooltip("ASIN:N", title="ASIN"),
                        alt.Tooltip("ROI:Q", format=".2f", title="ROI"),
                        alt.Tooltip("Profit:Q", format=".2f", title="Profit"),
                        alt.Tooltip("Demand:N", title="Demand"),
                    ],
                )
                .properties(width=800)
            )
            st.altair_chart(chart, use_container_width=False)
        else:
            st.bar_chart(metrics.set_index("Label")["Profit"])
    except Exception:
        pass

    try:  # pragma: no cover - optional chart
        st.subheader("Composite Score by Product")
        sorted_scores = metrics.sort_values("Composite Score", ascending=False)
        if alt is not None:
            score_chart = (
                alt.Chart(sorted_scores)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Label:N",
                        title=label_choice,
                        sort=None,
                        axis=alt.Axis(labelAngle=-30),
                    ),
                    y=alt.Y("Composite Score:Q", title="Composite Score"),
                    tooltip=[
                        alt.Tooltip("Title:N", title="Title"),
                        alt.Tooltip("ASIN:N", title="ASIN"),
                        alt.Tooltip("Composite Score:Q", format=".2f", title="Score"),
                    ],
                )
                .properties(width=800)
            )
            st.altair_chart(score_chart, use_container_width=False)
        else:
            st.bar_chart(sorted_scores.set_index("Label")["Composite Score"])
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
