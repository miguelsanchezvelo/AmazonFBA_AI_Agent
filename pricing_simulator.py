"""ChatGPT-based pricing optimization for FBA products."""

import argparse
import csv
import os
import re
from typing import Dict, List, Optional, Tuple

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

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profit = parse_float(row.get("profit"))
            if profit is not None:
                rows.append(row)

    if not rows:
        print("No products found in profitability results.")
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

    answer = ask_question(client, model, messages, question)
    suggested_price = parse_float(answer)
    return (f"${suggested_price:.2f}" if suggested_price is not None else "", answer)


def main(argv: Optional[List[str]] = None) -> None:
    global INPUT_CSV, OUTPUT_CSV

    parser = argparse.ArgumentParser(
        description="Get ChatGPT pricing suggestions for top products"
    )
    parser.add_argument(
        "--input",
        default=INPUT_CSV,
        help="CSV with profitability results",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_CSV,
        help="Where to save pricing suggestions",
    )
    args = parser.parse_args(argv)
    INPUT_CSV = args.input
    OUTPUT_CSV = args.output

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment or .env file.")
        return

    client = OpenAI(api_key=api_key)

    model = choose_model(client)
    products = load_top_products(INPUT_CSV)
    if not products:
        return

    results: List[Dict[str, str]] = []
    for row in products:
        try:
            suggested, notes = analyze_product(client, model, row)
        except Exception as exc:  # pragma: no cover - network
            asin = row.get("asin", "")
            print(f"Failed to get pricing advice for ASIN {asin}: {exc}")
            continue
        results.append(
            {
                "ASIN": row.get("asin", ""),
                "Title": row.get("title", ""),
                "Suggested Price": suggested,
                "Notes": notes,
            }
        )

    if results:
        save_results(results, OUTPUT_CSV)
        print(f"Results saved to {OUTPUT_CSV}")
    else:
        print("No results to save.")


if __name__ == "__main__":
    main()
