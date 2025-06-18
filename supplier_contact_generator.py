"""Generate supplier inquiry messages using OpenAI's Chat API."""

from __future__ import annotations

import csv
import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI


INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_DIR = "supplier_messages"
MODEL = "gpt-4"
SYSTEM_PROMPT = "You are an expert FBA sourcing agent helping contact suppliers."


def parse_units(value: str | None) -> int:
    """Return integer units from a string, defaulting to zero."""

    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def load_products(path: str) -> List[Dict[str, str]]:
    """Load products with units to order greater than zero."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file '{path}' not found.")

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            units = parse_units(
                row.get("units_to_order") or row.get("Units") or row.get("units")
            )
            if units <= 0:
                continue
            asin = (row.get("asin") or row.get("ASIN") or "").strip()
            title = (row.get("title") or row.get("Title") or "").strip()
            rows.append({"asin": asin or "UNKNOWN", "title": title})
    return rows


def generate_message(client: OpenAI, title: str) -> str:
    """Generate a polite supplier message for the given product title."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Write a short message to the supplier about the product titled "
                f"'{title}'. Ask for minimum order quantity (MOQ), unit price, "
                "catalogue of similar items and delivery time."
            ),
        },
    ]

    resp = client.chat.completions.create(model=MODEL, messages=messages)
    return resp.choices[0].message.content.strip()


def main() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in .env")
        return

    client = OpenAI(api_key=api_key)

    try:
        products = load_products(INPUT_CSV)
    except FileNotFoundError as exc:
        print(exc)
        return
    except Exception as exc:  # pragma: no cover - unexpected errors
        print(f"Error reading {INPUT_CSV}: {exc}")
        return

    if not products:
        print("No products with assigned units found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for prod in products:
        asin = prod["asin"]
        title = prod["title"]
        try:
            message = generate_message(client, title)
        except Exception as exc:  # pragma: no cover - network
            print(f"Failed to generate message for {asin}: {exc}")
            continue

        out_path = os.path.join(OUTPUT_DIR, f"{asin}.txt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"ASIN: {asin}\nTitle: {title}\n\n{message}\n")
            print(f"Saved message for {asin} in {out_path}")
        except Exception as exc:
            print(f"Error saving message for {asin}: {exc}")


if __name__ == "__main__":
    main()

