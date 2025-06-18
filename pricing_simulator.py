"""ChatGPT-based pricing optimization for FBA products."""

import csv
import os
import re
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

INPUT_CSV = os.path.join("data", "profitability_estimation_results.csv")
OUTPUT_CSV = os.path.join("data", "pricing_simulation_results.csv")


def parse_float(value: Optional[str]) -> Optional[float]:
    """Return float extracted from a string or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+\.\d+|\d+", str(value))
    return float(match.group()) if match else None


def load_profitable_products(path: str) -> List[Dict[str, str]]:
    """Load rows with ROI >= 0.5 from the CSV file."""
    if not os.path.exists(path):
        print(f"Input file '{path}' not found. Run profitability_estimation.py first.")
        return []
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            roi = parse_float(row.get("roi"))
            if roi is not None and roi >= 0.5:
                rows.append(row)
    if not rows:
        print("No products with ROI >= 0.5 found.")
    return rows


def save_results(rows: List[Dict[str, str]], path: str) -> None:
    """Save pricing suggestions to CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ASIN", "Title", "Recommended Price Strategy", "Notes"],
        )
        writer.writeheader()
        writer.writerows(rows)


def ask_question(client: OpenAI, messages: List[Dict[str, str]], question: str) -> str:
    """Send a question to ChatGPT and return the answer."""
    messages.append({"role": "user", "content": question})
    response = client.chat.completions.create(model="gpt-4", messages=messages)
    answer = response.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": answer})
    return answer


def analyze_product(client: OpenAI, asin: str, title: str) -> Tuple[str, str]:
    """Run a short pricing conversation for a product."""
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a pricing strategy expert for FBA products"}
    ]

    q1 = "\u00bfQu\u00e9 rango de precios maximizar\u00eda ventas sin comprometer margen?"
    q2 = "\u00bfUn aumento de precio del 10% afectar\u00eda significativamente la demanda?"
    q3 = (
        "\u00bfQu\u00e9 estrategia de precios podr\u00eda aplicarse para lanzamiento "
        "(descuento, bundle, etc.)?"
    )

    print(f"\n### ASIN {asin} - {title}")
    a1 = ask_question(client, messages, f"Producto: {title}. {q1}")
    print(f"Q1: {q1}\nA1: {a1}")
    a2 = ask_question(client, messages, q2)
    print(f"Q2: {q2}\nA2: {a2}")
    a3 = ask_question(client, messages, q3)
    print(f"Q3: {q3}\nA3: {a3}\n")

    notes = f"{a1} | {a2}"
    return a3, notes


def main() -> None:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment or .env file.")
        return

    client = OpenAI(api_key=api_key)

    products = load_profitable_products(INPUT_CSV)
    if not products:
        return

    results: List[Dict[str, str]] = []
    for row in products:
        asin = row.get("asin", "")
        title = row.get("title", "")
        try:
            strategy, notes = analyze_product(client, asin, title)
        except Exception as exc:  # pragma: no cover - network
            print(f"Failed to get pricing advice for ASIN {asin}: {exc}")
            continue
        results.append(
            {
                "ASIN": asin,
                "Title": title,
                "Recommended Price Strategy": strategy,
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
