"""ChatGPT-based pricing optimization for FBA products."""

import argparse
import csv
import os
import re
import time
from typing import Dict, List, Optional, Tuple, Set
import time
from mock_data import get_mock_asins

LOG_FILE = "log.txt"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass

PRODUCT_CSV = os.path.join("data", "product_results.csv")


def load_valid_asins() -> Set[str]:
    if not os.path.exists(PRODUCT_CSV):
        return set()
    with open(PRODUCT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            row.get("asin") or row.get("estimated_asin")
            for row in reader
            if row.get("asin") or row.get("estimated_asin")
        }

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

SYSTEM_PROMPT = (
    "You are an Amazon pricing consultant who gives short, actionable advice "
    "for optimizing FBA product prices."
)

INPUT_CSV = os.path.join("data", "profitability_estimation_results.csv")
OUTPUT_CSV = os.path.join("data", "pricing_suggestions.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Get ChatGPT pricing suggestions for top products")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--input', default=INPUT_CSV, help='CSV with profitability results')
    parser.add_argument('--output', default=OUTPUT_CSV, help='Where to save pricing suggestions')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    return parser.parse_args()


args = parse_args()


def parse_float(value: Optional[str]) -> Optional[float]:
    """Return float extracted from a string or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+\.\d+|\d+", str(value))
    return float(match.group()) if match else None


def load_top_products(path: str, count: int = 5) -> List[Dict[str, str]]:
    """Return the most profitable products from the CSV file."""
    if not os.path.exists(path):
        print(f"Input file '{path}' not found. Run profitability_estimation.py first.")
        return []

    valid = load_valid_asins()
    rows: List[Dict[str, str]] = []
    unknown: Set[str] = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profit = parse_float(row.get("profit"))
            asin = (row.get("asin") or "").strip()
            if profit is not None:
                if valid and asin and asin not in valid:
                    unknown.add(asin)
                    continue
                viable_flag = str(row.get("Viable", "YES")).strip().upper()
                roi_val = parse_float(row.get("roi")) or 0.0
                if roi_val <= 0 and viable_flag != "YES":
                    continue
                rows.append(row)

    if unknown:
        log(f"pricing_simulator: ASIN mismatch {','.join(sorted(unknown))}")
        if not rows:
            print("ASIN mismatch with product_results.csv")

    if not rows:
        print("No viable products found in profitability results.")
        return []

    rows.sort(key=lambda r: parse_float(r.get("profit")) or 0.0, reverse=True)
    return rows[:count]


def choose_model(client: OpenAI) -> str:
    """Return gpt-4 if available else gpt-3.5-turbo."""
    try:
        available = {m.id for m in client.models.list().data}
    except Exception as exc:
        print(f"Failed to list models: {exc}")
        return "gpt-3.5-turbo"

    if any(m.startswith("gpt-4") for m in available):
        return "gpt-4"

    print("Model 'gpt-4' not available. Using 'gpt-3.5-turbo'.")
    return "gpt-3.5-turbo"


def save_results(rows: List[Dict[str, str]], path: str) -> None:
    """Save pricing suggestions to CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ASIN", "Title", "Suggested Price", "Notes"],
        )
        writer.writeheader()
        writer.writerows(rows)


def ask_question(client: OpenAI, model: str, messages: List[Dict[str, str]], question: str) -> str:
    """Send a question to ChatGPT and return the answer."""
    messages.append({"role": "user", "content": question})
    try:
        response = client.chat.completions.create(model=model, messages=messages)
    except Exception as exc:
        if "model" in str(exc) or "404" in str(exc):
            fallback = "gpt-3.5-turbo"
            log(f"pricing_simulator: downgrading model to {fallback}")
            response = client.chat.completions.create(model=fallback, messages=messages)
            model = fallback
        else:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc
    answer = response.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": answer})
    return answer


def analyze_product(client: OpenAI, model: str, row: Dict[str, str]) -> Tuple[str, str]:
    """Return suggested price and notes for the given product."""
    title = row.get("title", "")
    price = parse_float(row.get("price"))
    cost = parse_float(row.get("cost"))

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    price_str = f"${price:.2f}" if price is not None else "N/A"
    cost_str = f"${cost:.2f}" if cost is not None else "N/A"
    question = (
        "Given the following product details:\n"
        f"Title: {title}\n"
        f"Current Amazon price: {price_str}\n"
        f"Cost to produce: {cost_str}\n"
        "What is the optimal selling price in USD to maximize profitability while remaining competitive?"
        " Provide the price and a short reasoning."
    )

    try:
        answer = ask_question(client, model, messages, question)
        suggested_price = parse_float(answer)
    except Exception as exc:
        log(f"pricing_simulator: using fallback price for {row.get('asin')}: {exc}")
        suggested_price = None
        answer = "No model response; recommend keeping current price."
    return (f"${suggested_price:.2f}" if suggested_price is not None else "", answer)


def main() -> None:
    global INPUT_CSV, OUTPUT_CSV

    INPUT_CSV = args.input
    OUTPUT_CSV = args.output
    auto = args.auto
    use_mock = args.mock

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    if api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
        except Exception as exc:
            log(f"pricing_simulator: OpenAI init failed {exc}")
            client = None
    if client is None:
        log("pricing_simulator: proceeding without OpenAI")

    model = choose_model(client) if client else "gpt-3.5-turbo"
    products = load_top_products(INPUT_CSV)
    if not products:
        print("No products available for pricing suggestions.")
        save_results([], OUTPUT_CSV)
        return

    if use_mock:
        mock_pricing = [dict(row, **{"suggested_price": row["price"] * 1.05, "expected_roi": row["roi"] + 0.05}) for row in get_mock_asins()]
        save_results(mock_pricing, OUTPUT_CSV)
        print(f"[MOCK] Saved {len(mock_pricing)} pricing suggestions to {OUTPUT_CSV}")
        return

    results: List[Dict[str, str]] = []
    for row in products:
        try:
            if client:
                suggested, notes = analyze_product(client, model, row)
            else:
                raise RuntimeError("OpenAI unavailable")
        except Exception as exc:  # pragma: no cover - network
            asin = row.get("asin", "")
            log(f"pricing_simulator: fallback for {asin} {exc}")
            suggested = ""
            notes = "No pricing suggestion available"
        results.append(
            {
                "ASIN": row.get("asin", ""),
                "Title": row.get("title", ""),
                "Suggested Price": suggested,
                "Notes": notes,
            }
        )

    if not results:
        if auto:
            results = [
                {
                    "ASIN": "B0MOCK001",
                    "Title": "Mock Product",
                    "Suggested Price": "$19.99",
                    "Notes": "Fallback pricing data",
                }
            ]
        else:
            print("No pricing suggestions generated.")
            return
    save_results(results, OUTPUT_CSV)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
