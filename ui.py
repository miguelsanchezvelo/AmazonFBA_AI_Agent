import argparse
import os
import sys
import subprocess
from typing import List, Tuple, Dict

import streamlit as st
import pandas as pd

import fba_agent

FRIENDLY_NAMES: Dict[str, str] = {
    "product_discovery": "Product Discovery",
    "market_analysis": "Market Overview",
    "review_analysis": "Customer Feedback",
    "profitability_estimation": "Profit Estimation",
    "demand_forecast": "Demand Forecast",
    "supplier_selection": "Supplier Selection",
    "supplier_contact_generator": "Supplier Messaging",
    "pricing_simulator": "Price Simulator",
    "inventory_management": "Inventory Planner",
    "order_placement_agent": "Order Placement",
    "negotiation_agent": "Negotiation Assistant",
    "email_manager": "Email Management",
    "reset_pipeline": "Reset Pipeline",
}


STEPS: List[Tuple[str, List[str]]] = [
    ("product_discovery", ["product_discovery.py"]),
    (
        "market_analysis",
        ["market_analysis.py", "--csv", fba_agent.OUTPUTS["product_discovery"]],
    ),
    ("review_analysis", ["review_analysis.py", "--csv", fba_agent.OUTPUTS["market_analysis"]]),
    ("profitability_estimation", ["profitability_estimation.py"]),
    ("demand_forecast", ["demand_forecast.py"]),
    ("supplier_selection", ["supplier_selection.py", "--budget", "{BUDGET}"]),
    ("supplier_contact_generator", ["supplier_contact_generator.py"]),
    ("pricing_simulator", ["pricing_simulator.py", "--auto"]),
    ("inventory_management", ["inventory_management.py"]),
    ("negotiation_agent", ["negotiation_agent.py"]),
    ("email_manager", ["email_manager.py"]),
    ("order_placement_agent", ["order_placement_agent.py"]),
]


def run_script(args: List[str], input_data: str | None = None) -> Tuple[bool, str]:
    """Run a script and return ``(success, output)`` with real-time logging."""
    try:
        proc = subprocess.Popen(
            [sys.executable] + args,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if input_data and proc.stdin:
            proc.stdin.write(input_data)
            proc.stdin.close()
        lines: List[str] = []
        placeholder = st.empty()
        assert proc.stdout  # for type checkers
        for line in proc.stdout:
            lines.append(line)
            placeholder.text("".join(lines))
        proc.wait()
        out = "".join(lines)
        return proc.returncode == 0, out
    except Exception as exc:  # pragma: no cover - execution error
        return False, str(exc)


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


def pipeline_ui(auto: bool = False) -> None:
    st.title("Amazon FBA AI Agent")
    budget = st.number_input(
        "Startup budget (USD)", min_value=0.0, value=float(fba_agent.DEFAULT_BUDGET)
    )
    if "statuses" not in st.session_state:
        st.session_state.statuses = {name: "pending" for name, _ in STEPS}
        st.session_state.logs = {name: "" for name, _ in STEPS}

    if st.button("Run All"):
        for name, cmd in STEPS:
            if "{BUDGET}" in " ".join(cmd):
                cmd = [c.replace("{BUDGET}", str(budget)) for c in cmd]
            run_step_ui(name, cmd)

    for name, cmd in STEPS:
        friendly = FRIENDLY_NAMES.get(name, name)
        status = st.session_state.statuses[name]
        with st.expander(f"{friendly} - {status}", expanded=False):
            if st.button(f"Run {friendly}", key=f"btn_{name}"):
                if "{BUDGET}" in " ".join(cmd):
                    cmd = [c.replace("{BUDGET}", str(budget)) for c in cmd]
                run_step_ui(name, cmd)
            if st.session_state.logs[name]:
                st.text_area("Log", st.session_state.logs[name], height=150)

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


def run_step_ui(name: str, cmd: List[str]) -> None:
    friendly = FRIENDLY_NAMES.get(name, name)
    st.session_state.statuses[name] = "running"
    with st.status(f"Running {friendly}...", expanded=True) as stat:
        ok, out = run_script(cmd)
        st.session_state.logs[name] = out
        if ok:
            st.session_state.statuses[name] = "completed"
            stat.update(label=f"{friendly} completed", state="complete")
        else:
            st.session_state.statuses[name] = "failed"
            stat.update(label=f"{friendly} failed", state="error")


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
        pipeline_ui(auto=args.auto)
