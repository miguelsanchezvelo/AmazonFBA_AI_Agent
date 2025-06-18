"""Generate supplier inquiry messages using OpenAI's Chat API."""

from __future__ import annotations

import argparse
import csv
import os
import time
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    """Return command line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate supplier inquiry messages using OpenAI"
    )
    parser.add_argument("--lang", default="en", help="language code for template")
    parser.add_argument("--tone", default="formal", help="tone for template")
    return parser.parse_args()


def load_template(lang: str, tone: str) -> str:
    """Load template file for the given language and tone."""

    names = [f"template_{lang}_{tone}.txt", "template.txt"]
    for name in names:
        if os.path.exists(name):
            with open(name, "r", encoding="utf-8") as f:
                text = f.read()
            if "{title}" not in text or "{asin}" not in text:
                raise ValueError(
                    f"Template '{name}' missing '{{title}}' or '{{asin}}' placeholder"
                )
            return text
    raise FileNotFoundError(
        "Template file not found (searched: " + ", ".join(names) + ")"
    )


def log_error(asin: str, title: str, error: str) -> None:
    """Append an error entry to ``supplier_errors.log``."""

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts}\t{asin}\t{title}\t{error}\n")
    except Exception:
        pass


INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_DIR = "supplier_messages"
ERROR_LOG = "supplier_errors.log"
DEFAULT_MODEL = "gpt-4"
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


def generate_message(
    client: OpenAI, model: str, template: str, asin: str, title: str
) -> str:
    """Generate a polite supplier message for the given product."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": template.format(title=title, asin=asin)},
    ]

    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content.strip()


def main() -> None:
    args = parse_args()

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in .env")
        return

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

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

    try:
        template = load_template(args.lang, args.tone)
        template_err: str | None = None
    except Exception as exc:
        template = ""
        template_err = str(exc)
        print(template_err)

    success = 0
    failures = 0

    for prod in products:
        asin = prod["asin"]
        title = prod["title"]

        if template_err:
            log_error(asin, title, template_err)
            failures += 1
            continue

        try:
            message = generate_message(client, model, template, asin, title)
        except Exception as exc:  # pragma: no cover - network
            print(f"Failed to generate message for {asin}: {exc}")
            log_error(asin, title, str(exc))
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
            log_error(asin, title, str(exc))
            failures += 1

    print(f"Messages generated: {success}. Failures: {failures}.")


if __name__ == "__main__":
    main()

