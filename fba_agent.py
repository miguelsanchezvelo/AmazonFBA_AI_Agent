import os
import sys
import subprocess
from typing import List

from dotenv import load_dotenv


DATA_DIR = "data"

OUTPUTS = {
    "product_discovery": os.path.join(DATA_DIR, "product_results.csv"),
    "market_analysis": os.path.join(DATA_DIR, "market_analysis_results.csv"),
    "profitability_estimation": os.path.join(DATA_DIR, "profitability_estimation_results.csv"),
    "demand_forecast": os.path.join(DATA_DIR, "demand_forecast_results.csv"),
    "supplier_selection": os.path.join(DATA_DIR, "supplier_selection_results.csv"),
    "supplier_contact_generator": "supplier_messages",
    "pricing_simulator": os.path.join(DATA_DIR, "pricing_suggestions.csv"),
    "inventory_management": os.path.join(DATA_DIR, "inventory_management_results.csv"),
}


load_dotenv()
SERP_KEY = os.getenv("SERPAPI_API_KEY")
KEEPA_KEY = os.getenv("KEEPA_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

SERVICES = {
    "SerpAPI": bool(SERP_KEY),
    "Keepa": bool(KEEPA_KEY),
    "OpenAI": bool(OPENAI_KEY),
}


def print_service_status() -> None:
    print("Service availability:")
    for name, available in SERVICES.items():
        status = "available" if available else "missing"
        print(f"  - {name}: {status}")

    if not any(SERVICES.values()):
        print("No API keys found. Running in mock mode.")
    else:
        missing = [name for name, ok in SERVICES.items() if not ok]
        if missing:
            print("Missing services: " + ", ".join(missing))
            print("Certain features will be disabled or use mock data.")


def run_subprocess(args: List[str], step: str, input_data: str | None = None) -> bool:
    print(f"\n=== Running {step} ===")
    try:
        subprocess.run([sys.executable] + args, check=True, text=True, input=input_data)
        print(f"{step} completed successfully.")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"Error during {step}: {exc}")
        choice = input("Continue to next step? [y/N]: ").strip().lower()
        return choice == "y"


def check_output_exists(paths: List[str]) -> bool:
    return all(os.path.exists(p) for p in paths)


def ensure_mock_data() -> None:
    if not any(SERVICES.values()):
        run_subprocess(["prepare_mock_data.py"], "prepare_mock_data")


def ask_reuse(step: str, paths: List[str]) -> bool:
    if check_output_exists(paths):
        choice = input(f"Existing results for {step} found. Reuse them? [y/N]: ").strip().lower()
        if choice == "y":
            print(f"Skipping {step} and reusing existing data.")
            return True
    return False


def main() -> None:
    print_service_status()
    ensure_mock_data()

    while True:
        try:
            budget = float(input("Enter your total startup budget in USD: "))
            break
        except ValueError:
            print("Please enter a valid number.")

    steps = [
        ("product_discovery", ["product_discovery.py"], str(budget) + "\n", [OUTPUTS["product_discovery"]], SERVICES["SerpAPI"]),
        (
            "market_analysis",
            ["market_analysis.py", "--csv", OUTPUTS["product_discovery"] if SERVICES["SerpAPI"] else os.path.join(DATA_DIR, "mock_market_data.csv")],
            None,
            [OUTPUTS["market_analysis"]],
            SERVICES["SerpAPI"] or SERVICES["Keepa"],
        ),
        ("profitability_estimation", ["profitability_estimation.py"], None, [OUTPUTS["profitability_estimation"]], True),
        ("demand_forecast", ["demand_forecast.py"], None, [OUTPUTS["demand_forecast"]], True),
        ("supplier_selection", ["supplier_selection.py"], str(budget) + "\n", [OUTPUTS["supplier_selection"]], True),
        ("supplier_contact_generator", ["supplier_contact_generator.py"], None, [OUTPUTS["supplier_contact_generator"]], SERVICES["OpenAI"]),
        ("pricing_simulator", ["pricing_simulator.py"], None, [OUTPUTS["pricing_simulator"]], SERVICES["OpenAI"]),
        ("inventory_management", ["inventory_management.py"], None, [OUTPUTS["inventory_management"]], True),
    ]

    generated: List[str] = []

    for name, args, inp, paths, condition in steps:
        if not condition:
            print(f"Skipping {name} due to missing services.")
            continue
        if ask_reuse(name, paths):
            generated.extend(p for p in paths if os.path.exists(p))
            continue
        cont = run_subprocess(args, name, inp)
        if not cont:
            print("Pipeline aborted.")
            return
        generated.extend(p for p in paths if os.path.exists(p))

    print("\nPipeline completed. Generated/used files:")
    for path in generated:
        print(f" - {path}")


if __name__ == "__main__":
    main()
