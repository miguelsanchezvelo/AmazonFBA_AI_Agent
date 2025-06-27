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
    ("Run Product Discovery", "product_discovery.py"),
    ("Run Market Analysis", "market_analysis.py"),
    ("Run Profitability Estimation", "profitability_estimation.py"),
    ("Run Demand Forecast", "demand_forecast.py"),
    ("Run Supplier Selection", "supplier_selection.py"),
    ("Generate Supplier Emails", "supplier_contact_generator.py"),
    ("Simulate Pricing Strategy", "pricing_simulator.py"),
    ("Manage Inventory", "inventory_management.py"),
]


def run_module(script_name: str, budget: float = 0.0) -> Tuple[str, str, int, str]:
    """Run a module and return (stdout, stderr, exit_code, detailed_log)."""
    cmd = [sys.executable, script_name, "--auto"]
    inp = None
    if script_name == "product_discovery.py":
        cmd = [sys.executable, script_name]
        inp = f"{budget}\n"

    log_lines = []
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
            input=inp,
        )
        log_lines.append("📝 Stdout:")
        log_lines.append(result.stdout.strip())
        log_lines.append("📝 Stderr:")
        log_lines.append(result.stderr.strip())
        log_lines.append(f"Exit code: {result.returncode}")
        if result.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(f"❌ Step failed with exit code {result.returncode}.")
            log_lines.append("Troubleshooting:")
            log_lines.append(" - Check the output above for specific errors.")
            log_lines.append(" - Ensure all required dependencies are installed (pip install -r requirements.txt).")
            log_lines.append(f" - Try running the step manually in your terminal:")
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {' '.join(cmd)}")
        return result.stdout, result.stderr, result.returncode, "\n".join(log_lines)
    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(f"💥 An exception occurred: {exc}")
        return "", str(exc), 1, "\n".join(log_lines)


def commit_and_push_changes(
    message: str = "Auto: update after running Streamlit action",
) -> None:
    """Commit and push changes using Git if available."""
    try:
        if not os.path.isdir(os.path.join(os.getcwd(), ".git")):
            return
        subprocess.run(["git", "add", "."], cwd=os.getcwd(), check=False)
        subprocess.run(["git", "commit", "-m", message], cwd=os.getcwd(), check=False)
        subprocess.run(["git", "push"], cwd=os.getcwd(), check=False)
    except Exception:
        pass


def file_has_content(path: str) -> bool:
    """Return ``True`` if a file exists and has content (more than a header for CSVs)."""
    if not os.path.exists(path):
        return False
    if os.path.isdir(path):
        try:
            return bool(os.listdir(path))
        except OSError:
            return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) > 1
    except (IOError, UnicodeDecodeError):
        return False


def run_test_all() -> Tuple[str, int]:
    """Execute ``test_all.py`` and return a detailed log and exit code."""
    script_path = os.path.join(ROOT_DIR, "test_all.py")
    log_lines = []

    if not os.path.exists(script_path):
        log_lines.append(f"❌ Error: Test script not found at {script_path}")
        log_lines.append(
            "Troubleshooting: Ensure 'test_all.py' exists in the root directory."
        )
        return "\n".join(log_lines), 1

    cmd = [sys.executable, script_path]
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )

        output = res.stdout + res.stderr
        log_lines.append("📝 Output:")
        log_lines.append(output.strip())

        if res.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(f"❌ Test run failed with exit code {res.returncode}.")
            log_lines.append("Troubleshooting:")
            log_lines.append(" - Check the output above for specific errors.")
            log_lines.append(
                " - Ensure all required dependencies are installed (e.g., pip install -r requirements.txt)."
            )
            log_lines.append(
                " - Run the tests from your terminal directly to see if the issue persists:"
            )
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {os.path.basename(sys.executable)} test_all.py")

        return "\n".join(log_lines), res.returncode

    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(
            f"💥 An exception occurred while trying to run the tests: {exc}"
        )
        return "\n".join(log_lines), 1


def run_validate_all() -> Tuple[str, int]:
    """Execute ``validate_all.py`` and return a detailed log and exit code."""
    script_path = os.path.join(ROOT_DIR, "validate_all.py")
    log_lines = []

    if not os.path.exists(script_path):
        log_lines.append(f"❌ Error: Validation script not found at {script_path}")
        log_lines.append(
            "Troubleshooting: Ensure 'validate_all.py' exists in the root directory."
        )
        return "\n".join(log_lines), 1

    cmd = [sys.executable, script_path]
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )

        output = res.stdout + res.stderr
        log_lines.append("📝 Output:")
        log_lines.append(output.strip())

        if res.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(
                f"❌ Validation failed with exit code {res.returncode}."
            )
            log_lines.append("Troubleshooting:")
            log_lines.append(
                " - Look for 'Error' or 'Missing' messages in the output above."
            )
            log_lines.append(
                " - Some validation checks depend on pipeline outputs. Ensure required steps have been run."
            )
            log_lines.append(
                " - Run validation from your terminal directly to see if the issue persists:"
            )
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {os.path.basename(sys.executable)} validate_all.py")

        return "\n".join(log_lines), res.returncode

    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(
            f"💥 An exception occurred while trying to run validation: {exc}"
        )
        return "\n".join(log_lines), 1


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
    if "tests_ok" not in st.session_state:
        st.session_state.tests_ok = True
    if "validation_ok" not in st.session_state:
        st.session_state.validation_ok = True

    st.sidebar.title("Configuration")
    budget = st.sidebar.number_input(
        "Startup Budget (USD)", min_value=100.0, value=3000.0, step=100.0
    )
    if "budget" not in st.session_state:
        st.session_state.budget = 3000.0
    st.session_state.budget = budget

    if st.button("Run Tests"):
        with st.spinner("Running tests..."):
            out, code = run_test_all()
        with st.expander("Test Output", expanded=code != 0):
            st.code(out)
        st.session_state.tests_ok = code == 0
        if st.session_state.tests_ok:
            st.success("Tests passed")
        else:
            st.error("Tests failed. Check output for details.")

    if st.button("Validate Pipeline"):
        with st.spinner("Validating pipeline..."):
            vout, vcode = run_validate_all()
        with st.expander("Validation Output", expanded=vcode != 0):
            st.code(vout)
        st.session_state.validation_ok = vcode == 0
        if st.session_state.validation_ok:
            st.success("Validation passed")
        else:
            st.error("Validation reported issues. Check output for details.")

    st.divider()

    disabled = not (st.session_state.tests_ok and st.session_state.validation_ok)

    if st.button("Run All", disabled=disabled):
        for label, script in MODULES:
            step_name = os.path.splitext(script)[0]
            required_inputs = fba_agent.STEP_INPUTS.get(step_name, [])
            if all(file_has_content(p) for p in required_inputs):
                run_step_ui(label, script, st.session_state.budget)
            else:
                st.toast(f"Skipping {label} - prerequisites not met.")

    for label, script in MODULES:
        with st.expander(label, expanded=False):
            step_name = os.path.splitext(script)[0]
            required_inputs = fba_agent.STEP_INPUTS.get(step_name, [])
            prereqs_met = all(file_has_content(p) for p in required_inputs)
            is_step_disabled = disabled or not prereqs_met

            if st.button(label, key=f"btn_{script}", disabled=is_step_disabled):
                run_step_ui(label, script, st.session_state.budget)
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


def run_step_ui(label: str, script: str, budget: float) -> None:
    """Execute a module and display the results in the UI."""
    with st.spinner(f"Running {label}..."):
        stdout, stderr, returncode, log = run_module(script, budget)
    st.session_state.logs[label] = stdout if returncode == 0 else stderr
    if returncode == 0:
        st.success(f"✅ {label} completed successfully")
        commit_and_push_changes(f"Auto: updated results after {label}")
    else:
        st.error(f"❌ {label} failed")
    with st.expander("Step Log", expanded=returncode != 0):
        st.code(log)


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
