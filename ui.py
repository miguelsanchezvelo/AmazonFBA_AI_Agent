import argparse
import os
import sys
import subprocess
from typing import List, Tuple, Dict

# Absolute path to the repository root so modules are executed
# consistently regardless of the working directory.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

import streamlit as st
import pandas as pd

import fba_agent

FRIENDLY_NAMES: Dict[str, str] = {
    "product_discovery.py": "Product Discovery",
    "market_analysis.py": "Market Analysis",
    "profitability_estimation.py": "Profitability Estimation",
    "demand_forecast.py": "Demand Forecast",
    "supplier_selection.py": "Supplier Selection",
    "supplier_contact_generator.py": "Supplier Contact Generator",
    "pricing_simulator.py": "Pricing Simulator",
    "inventory_management.py": "Inventory Management",
}

MODULES: List[Tuple[str, str]] = [
    ("Product Discovery", "product_discovery.py"),
    ("Market Analysis", "market_analysis.py"),
    ("Profitability Estimation", "profitability_estimation.py"),
    ("Demand Forecast", "demand_forecast.py"),
    ("Supplier Selection", "supplier_selection.py"),
    ("Supplier Contact Generator", "supplier_contact_generator.py"),
    ("Pricing Simulator", "pricing_simulator.py"),
    ("Inventory Management", "inventory_management.py"),
]


def run_module(script_name: str) -> Tuple[str, str, int]:
    """Run a module with ``--auto`` and capture the output."""
    result = subprocess.run(
        [sys.executable, script_name, "--auto"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
    )
    return result.stdout, result.stderr, result.returncode


def display_csv(path: str, title: str) -> None:
    if not os.path.exists(path):
        st.warning(f"{title}: file missing")
        return
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        st.warning(f"Failed to read {path}: {exc}")
        return
    if df.empty:
        st.warning(f"{title}: file is empty")
        return
    st.subheader(title)
    st.dataframe(df)


def show_messages(dir_path: str) -> None:
    if not os.path.isdir(dir_path):
        return
    st.subheader("Supplier Messages")
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".txt"):
            continue
        msg_path = os.path.join(dir_path, name)
        try:
            with open(msg_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = ""
        new = st.text_area(f"{name}", content, key=msg_path)
        if new != content:
            with open(msg_path, "w", encoding="utf-8") as f:
                f.write(new)
            st.success(f"Updated {name}")


def summary_screen() -> None:
    sel_path = fba_agent.OUTPUTS["supplier_selection"]
    if not os.path.exists(sel_path):
        st.info("Run Supplier Selection to generate summary data.")
        return
    try:
        df = pd.read_csv(sel_path)
    except Exception as exc:
        st.warning(f"Failed to read {sel_path}: {exc}")
        return
    if df.empty:
        st.warning("Supplier selection results are empty")
        return
    total_profit = df.get("estimated_profit", pd.Series(dtype=float)).sum()
    st.metric("Total Projected Profit", f"${total_profit:,.2f}")
    if "roi" in df.columns and "asin" in df.columns:
        import plotly.express as px

        fig = px.bar(df, x="asin", y="roi", title="ROI per Product")
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df)


def pipeline_ui() -> None:
    st.title("Amazon FBA AI Agent")
    if "logs" not in st.session_state:
        st.session_state.logs = {label: "" for label, _ in MODULES}

    if st.button("Run All"):
        for label, script in MODULES:
            run_step_ui(label, script)

    for label, script in MODULES:
        with st.expander(label, expanded=False):
            if st.button(f"Run {label}", key=f"btn_{script}"):
                run_step_ui(label, script)
            if st.session_state.logs[label]:
                st.text_area("Log", st.session_state.logs[label], height=150)

    display_csv(fba_agent.OUTPUTS["product_discovery"], "Product Results")
    display_csv(fba_agent.OUTPUTS["market_analysis"], "Market Analysis")
    display_csv(fba_agent.OUTPUTS["profitability_estimation"], "Profitability")
    display_csv(fba_agent.OUTPUTS["demand_forecast"], "Demand Forecast")
    display_csv(fba_agent.OUTPUTS["supplier_selection"], "Supplier Selection")
    display_csv(fba_agent.OUTPUTS["pricing_simulator"], "Pricing Suggestions")
    display_csv(fba_agent.OUTPUTS["inventory_management"], "Inventory Management")

    show_messages(fba_agent.OUTPUTS["supplier_contact_generator"])

    st.header("Summary")
    summary_screen()


def run_step_ui(label: str, script: str) -> None:
    """Execute a module and display the results in the UI."""
    with st.spinner(f"Running {label}..."):
        stdout, stderr, returncode = run_module(script)
    st.session_state.logs[label] = stdout if returncode == 0 else stderr
    if returncode == 0:
        st.success(f"✅ {label} completed successfully")
    else:
        st.error(f"❌ {label} failed")
    with st.expander("Details"):
        st.text(st.session_state.logs[label])


def run_headless(auto: bool = False) -> None:
    cmd = [sys.executable, "fba_agent.py"]
    if auto:
        cmd.append("--auto")
    subprocess.run(cmd, check=False)


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FBA Streamlit UI", add_help=False)
    parser.add_argument("--headless", action="store_true", help="run without UI")
    parser.add_argument("--auto", action="store_true", help="run pipeline automatically")
    args, _ = parser.parse_known_args()
    return args


if __name__ == "__main__":
    args = parse_cli()
    if args.headless:
        run_headless(auto=args.auto)
    else:
        pipeline_ui()
