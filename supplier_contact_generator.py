"""Generate supplier inquiry messages using OpenAI's Chat API.

This script reads products from ``data/supplier_selection_results.csv`` and
creates one text file per ASIN inside ``supplier_messages/``. The prompt sent to
OpenAI is loaded from ``template.txt`` which should contain ``{title}`` and
``{asin}`` placeholders. Messages are generated in English only.
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_DIR = "supplier_messages"
TEMPLATE_FILE = "template.txt"
ERROR_LOG = "supplier_errors.log"

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


def load_template(path: str) -> str:
    """Return template contents or raise FileNotFoundError."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Template file '{path}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_message(
    client: OpenAI,
    asin: str,
    title: str,
    template: str,
    model: str,
) -> str:
    """Generate a supplier message based on the given template."""

    user_prompt = template.format(asin=asin, title=title)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = client.chat.completions.create(model=model, messages=messages)
    except OpenAIError as exc:
        if "model" in str(exc):
            raise RuntimeError(f"Model '{model}' not available: {exc}") from exc
        raise RuntimeError(f"OpenAI API error: {exc}") from exc
    return resp.choices[0].message.content.strip()


def log_error(asin: str, title: str, error: Exception) -> None:
    """Append an error entry to the log file."""

    os.makedirs(os.path.dirname(ERROR_LOG) or ".", exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"ASIN: {asin} | Title: {title} | Error: {error}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate supplier messages")
    parser.parse_args()

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4")
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

    success = 0
    failures = 0
    total = len(products)

    for prod in products:
        asin = prod["asin"]
        title = prod["title"]
        try:
            template = load_template(TEMPLATE_FILE)
        except Exception as exc:
            print(f"Template error for {asin}: {exc}")
            log_error(asin, title, exc)
            failures += 1
            continue

        try:
            message = generate_message(client, asin, title, template, model)
        except Exception as exc:  # pragma: no cover - network
            print(f"Failed to generate message for {asin}: {exc}")
            log_error(asin, title, exc)
            failures += 1
            continue

        out_path = os.path.join(OUTPUT_DIR, f"{asin}.txt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"ASIN: {asin}\nTitle: {title}\n\n{message}\n")
            print(f"Saved message for {asin} in {out_path}")
            success += 1
        except Exception as exc:
            print(f"Error saving message for {asin}: {exc}")
            log_error(asin, title, exc)
            failures += 1

    print(
        f"Attempted {total} messages: {success} succeeded, {failures} failed." + (
            f" See {ERROR_LOG} for details." if failures else ""
        )
    )


if __name__ == "__main__":
    main()

