"""Pipeline orchestrator for the Amazon FBA AI agent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Tuple

from dotenv import load_dotenv


DATA_DIR = "data"
CONFIG_PATH = "config.json"
LOG_FILE = "log.txt"
OPENAI_MODEL = "gpt-4"


OUTPUTS: Dict[str, str] = {
    "product_discovery": os.path.join(DATA_DIR, "product_results.csv"),
    "market_analysis": os.path.join(DATA_DIR, "market_analysis_results.csv"),
    "profitability_estimation": os.path.join(DATA_DIR, "profitability_estimation_results.csv"),
    "demand_forecast": os.path.join(DATA_DIR, "demand_forecast_results.csv"),
    "supplier_selection": os.path.join(DATA_DIR, "supplier_selection_results.csv"),
    "supplier_contact_generator": "supplier_messages",
    "pricing_simulator": os.path.join(DATA_DIR, "pricing_suggestions.csv"),
    "inventory_management": os.path.join(DATA_DIR, "inventory_management_results.csv"),
}


def log(msg: str) -> None:
    """Append a timestamped message to ``log.txt``."""

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def load_config() -> Dict[str, str]:
    """Return configuration from ``config.json`` if it exists."""

    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_openai_model(model: str) -> bool:
    """Return ``True`` if the given OpenAI model is accessible."""

    script = (
        "import os\n"
        "from openai import OpenAI\n"
        "client=OpenAI(api_key=os.getenv('OPENAI_API_KEY'))\n"
        "try:\n"
        "    ids=[m.id for m in client.models.list().data]\n"
        f"    print('1' if any(i.startswith('{model}') for i in ids) else '0')\n"
        "except Exception:\n"
        "    print('0')\n"
    )
    try:
        res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    except Exception:
        return False
    return res.stdout.strip() == "1"


def detect_services() -> Tuple[Dict[str, bool], str | None, str | None, str | None, bool]:
    """Detect API keys and model availability."""

    load_dotenv()
    config = load_config()

    serp = os.getenv("SERPAPI_API_KEY") or config.get("serpapi_key")
    keepa = os.getenv("KEEPA_API_KEY") or config.get("keepa_key")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = False
    if openai_key:
        openai_model = check_openai_model(OPENAI_MODEL)

    services = {
        "SerpAPI": bool(serp),
        "Keepa": bool(keepa),
        "OpenAI": bool(openai_key),
        OPENAI_MODEL: openai_model,
    }
    return services, serp, keepa, openai_key, openai_model


def print_service_status(services: Dict[str, bool]) -> None:
    """Display a summary of available services."""

    print("Service availability:")
    for name, ok in services.items():
        symbol = "✓" if ok else "❌"
        print(f"  {symbol} {name}")

    missing = [k for k, v in services.items() if not v]
    if missing:
        print("\nImplications:")
        if "SerpAPI" in missing:
            print(" - product_discovery will be skipped")
            print(" - market_analysis will use mock data")
        elif not services.get("SerpAPI") and not services.get("Keepa"):
            print(" - market_analysis will use mock data")
        if "OpenAI" in missing:
            print(" - supplier_contact_generator and pricing_simulator disabled")
        elif OPENAI_MODEL in missing:
            print(f" - {OPENAI_MODEL} unavailable; OpenAI modules will be skipped")
    else:
        print("All services available.")


def run_step(args: List[str], step: str, input_data: str | None = None) -> str:
    """Run a subprocess step and return its status string."""

    print(f"\n=== Running {step} ===")
    log(f"START {step}")
    try:
        subprocess.run([sys.executable] + args, check=True, text=True, input=input_data)
    except subprocess.CalledProcessError as exc:
        print(f"Error during {step}: {exc}")
        log(f"ERROR {step}: {exc}")
        while True:
            choice = input("Retry (r), skip (s) or abort (a)? [s]: ").strip().lower()
            if choice in {"r", "s", "a", ""}:
                break
        if choice == "r":
            return run_step(args, step, input_data)
        if choice == "a":
            log("ABORT")
            return "abort"
        log(f"SKIP {step}")
        return "skipped"
    else:
        print(f"{step} completed successfully.")
        log(f"SUCCESS {step}")
        return "completed"


def check_output_exists(paths: List[str]) -> bool:
    """Return ``True`` if all files exist."""

    return all(os.path.exists(p) for p in paths)


def ensure_mock_data(services: Dict[str, bool]) -> None:
    """Prepare mock data when no APIs are configured."""

    if not any(services.values()):
        run_step(["prepare_mock_data.py"], "prepare_mock_data")


def ask_reuse(step: str, paths: List[str]) -> bool:
    """Ask the user whether to reuse existing outputs."""

    if check_output_exists(paths):
        choice = input(f"Existing results for {step} found. Reuse them? [y/N]: ").strip().lower()
        if choice == "y":
            print(f"Skipping {step} and reusing existing data.")
            log(f"REUSE {step}")
            return True
    return False


def main() -> None:
    services, serp, keepa, openai_key, openai_model = detect_services()
    print_service_status(services)
    ensure_mock_data(services)

    while True:
        try:
            budget = float(input("Enter your total startup budget in USD: "))
            break
        except ValueError:
            print("Please enter a valid number.")

    steps = [
        ("product_discovery", ["product_discovery.py"], f"{budget}\n", [OUTPUTS["product_discovery"]], services["SerpAPI"]),
        (
            "market_analysis",
            ["market_analysis.py", "--csv", OUTPUTS["product_discovery"] if services["SerpAPI"] else os.path.join(DATA_DIR, "mock_market_data.csv")],
            None,
            [OUTPUTS["market_analysis"]],
            services["SerpAPI"] or services["Keepa"],
        ),
        ("profitability_estimation", ["profitability_estimation.py"], None, [OUTPUTS["profitability_estimation"]], True),
        ("demand_forecast", ["demand_forecast.py"], None, [OUTPUTS["demand_forecast"]], True),
        ("supplier_selection", ["supplier_selection.py"], f"{budget}\n", [OUTPUTS["supplier_selection"]], True),
        ("supplier_contact_generator", ["supplier_contact_generator.py"], None, [OUTPUTS["supplier_contact_generator"]], services["OpenAI"] and services[OPENAI_MODEL]),
        ("pricing_simulator", ["pricing_simulator.py"], None, [OUTPUTS["pricing_simulator"]], services["OpenAI"] and services[OPENAI_MODEL]),
        ("inventory_management", ["inventory_management.py"], None, [OUTPUTS["inventory_management"]], True),
    ]

    generated: List[str] = []
    statuses: Dict[str, str] = {}

    for name, args, inp, paths, condition in steps:
        if not condition:
            print(f"Skipping {name} due to missing services.")
            log(f"SKIP {name} - service")
            statuses[name] = "skipped"
            continue
        if ask_reuse(name, paths):
            statuses[name] = "reused"
            generated.extend(p for p in paths if os.path.exists(p))
            continue
        result = run_step(args, name, inp)
        if result == "abort":
            print("Pipeline aborted.")
            return
        statuses[name] = result
        if result == "completed":
            generated.extend(p for p in paths if os.path.exists(p))

    print("\n=== Summary ===")
    for step, state in statuses.items():
        symbol = "✓" if state in {"completed", "reused"} else "❌"
        print(f" {symbol} {step}: {state}")

    if generated:
        print("\nGenerated or reused files:")
        for path in generated:
            print(f" - {path}")

    warnings = [s for s, st in statuses.items() if st == "skipped"]
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f" - {w} was skipped")

    suggestions = []
    if not services.get("SerpAPI"):
        suggestions.append("SerpAPI")
    if not services.get("Keepa"):
        suggestions.append("Keepa")
    if not services.get("OpenAI"):
        suggestions.append("OpenAI")
    elif not services.get(OPENAI_MODEL):
        suggestions.append(f"access to {OPENAI_MODEL}")

    if suggestions:
        print("\nSubscriptions that would improve results: " + ", ".join(suggestions))


if __name__ == "__main__":
    main()

