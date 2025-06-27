import argparse
import logging
import os
import subprocess
import sys
from typing import List, Tuple

SCRIPTS = [
    "product_discovery.py",
    "market_analysis.py",
    "profitability_estimation.py",
    "demand_forecast.py",
    "supplier_selection.py",
    "supplier_contact_generator.py",
    "pricing_simulator.py",
    "inventory_management.py",
    "email_monitor.py",
    "order_placement_agent.py",
    "fba_agent.py",
]

LOG_FILE = "test_report.log"


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


def check_help(script: str) -> Tuple[bool, str]:
    """Return ``True`` if the script's help lists the required options."""
    ok, out = run_command([sys.executable, script, "--help"])
    expected = ["--auto", "--debug", "--verbose", "--max-products"]
    if ok:
        ok = all(opt in out for opt in expected)
    return ok, out


def run_auto(script: str) -> Tuple[bool, str]:
    """Run script with ``--auto`` and return success status and output."""
    return run_command([sys.executable, script, "--auto"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Test all scripts")
    parser.add_argument("--verbose", action="store_true", help="show detailed output")
    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, filemode="w", level=logging.INFO)

    results = []

    for script in SCRIPTS:
        print(f"Testing {script}...")
        logging.info("=== %s ===", script)
        if not os.path.exists(script):
            msg = "File not found"
            print(f"  {script}: ❌ {msg}")
            logging.error(msg)
            results.append((script, False, False))
            continue

        help_ok, help_out = check_help(script)
        auto_ok, auto_out = run_auto(script)

        if args.verbose:
            if help_out.strip():
                print(help_out.strip())
            if auto_out.strip():
                print(auto_out.strip())

        results.append((script, help_ok, auto_ok))
        if help_ok and auto_ok:
            print(f"  {script}: ✅")
        elif help_ok:
            print(f"  {script}: ⚠️ auto mode failed")
        else:
            print(f"  {script}: ❌ help/auto failure")

    # Summary
    print("\nSummary:\n")
    header = f"{'Script':30} {'Help':>6} {'Auto':>6}"
    print(header)
    print("-" * len(header))
    for script, help_ok, auto_ok in results:
        help_status = "OK" if help_ok else "Fail"
        auto_status = "OK" if auto_ok else "Fail"
        print(f"{script:30} {help_status:>6} {auto_status:>6}")

    test_reset_pipeline()


def test_reset_pipeline() -> None:
    subprocess.run([sys.executable, "reset_pipeline.py"], check=True)


if __name__ == "__main__":
    main()
