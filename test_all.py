import argparse
import importlib.util
import logging
import os
import subprocess
import sys
from typing import List, Tuple, Optional

SCRIPTS = [
    "product_discovery.py",
    "market_analysis.py",
    "profitability_estimation.py",
    "demand_forecast.py",
    "supplier_selection.py",
    "supplier_contact_generator.py",
    "pricing_simulator.py",
    "inventory_management.py",
    "order_placement_agent.py",
    "fba_agent.py",
]

LOG_FILE = "test_report.log"


def supports_help(path: str) -> bool:
    """Return True if the script likely supports --help."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return False
    return "argparse" in text or "ArgumentParser" in text


def run_command(cmd: List[str]) -> Tuple[bool, str]:
    """Run a command and return (success, output)."""
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            stdin=subprocess.DEVNULL,
        )
        out = res.stdout + res.stderr
        return res.returncode == 0, out
    except Exception as exc:
        return False, str(exc)


def check_import(path: str) -> Tuple[bool, str]:
    """Attempt to import a module from the given path."""
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return False, "spec creation failed"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return True, ""
    except Exception as exc:  # pragma: no cover - import error
        return False, str(exc)


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
            results.append((script, "missing", "-", "-"))
            continue

        # Compile
        ok_compile, out_compile = run_command([sys.executable, "-m", "py_compile", script])
        logging.info("compile output:\n%s", out_compile)

        # Import
        ok_import, out_import = check_import(script)
        logging.info("import output:\n%s", out_import)

        # Help
        if supports_help(script):
            ok_help, out_help = run_command([sys.executable, script, "--help"])
            logging.info("help output:\n%s", out_help)
        else:
            ok_help = None
            out_help = ""  # pragma: no cover - help not supported

        if args.verbose:
            if out_compile.strip():
                print(out_compile.strip())
            if out_import.strip():
                print(out_import.strip())
            if ok_help is not None and out_help.strip():
                print(out_help.strip())

        compile_status = "OK" if ok_compile else "Error"
        import_status = "OK" if ok_import else "Error"
        help_status = "N/A" if ok_help is None else ("OK" if ok_help else "Error")

        results.append((script, compile_status, import_status, help_status))
        overall = ok_compile and ok_import and (ok_help if ok_help is not None else True)
        print("  ✅ OK" if overall else "  ❌ Error")

    # Summary
    print("\nSummary:\n")
    header = f"{'Script':30} {'Compile':>8} {'Import':>8} {'Help':>8}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(f"{row[0]:30} {row[1]:>8} {row[2]:>8} {row[3]:>8}")


if __name__ == "__main__":
    main()
