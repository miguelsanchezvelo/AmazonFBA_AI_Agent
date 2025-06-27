"""Generate supplier inquiry messages using OpenAI's Chat API.

This script reads products from ``data/supplier_selection_results.csv`` and
creates one text file per ASIN inside ``supplier_messages/``.
The prompt sent to OpenAI is loaded from a template file which contains
``{title}`` and ``{asin}`` placeholders.  By default ``template.txt`` is used,
but alternative files such as ``template_es_formal.txt`` or
``template_en_informal.txt`` can be selected via command line options.
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List
import time

LOG_FILE = "log.txt"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

try:
    from openai import OpenAI, OpenAIError
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore
    OpenAIError = Exception  # type: ignore


INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_DIR = "supplier_messages"
TEMPLATE_FILE = "template.txt"
ERROR_LOG = "supplier_errors.log"
PRODUCT_CSV = os.path.join("data", "product_results.csv")

SYSTEM_PROMPT = "You are an expert FBA sourcing agent helping contact suppliers."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate supplier messages")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--lang', default='en', help="Language code for the template (e.g. 'en', 'es')")
    parser.add_argument('--tone', default='formal', help="Tone of the template (e.g. 'formal', 'informal')")
    return parser.parse_args()


args = parse_args()


def parse_units(value: str | None) -> int:
    """Return integer units from a string, defaulting to zero."""

    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def load_valid_asins() -> set[str]:
    if not os.path.exists(PRODUCT_CSV):
        return set()
    with open(PRODUCT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            row.get("asin") or row.get("estimated_asin")
            for row in reader
            if row.get("asin") or row.get("estimated_asin")
        }


def load_products(path: str) -> List[Dict[str, str]]:
    """Load products with units to order greater than zero."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file '{path}' not found.")

    valid = load_valid_asins()
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
            if valid and asin and asin not in valid:
                log(f"supplier_contact_generator: unknown ASIN {asin}")
                continue
            rows.append({"asin": asin or "UNKNOWN", "title": title})
    return rows


def load_template(path: str) -> str:
    """Return template contents ensuring required placeholders."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Template file '{path}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "{title}" not in content or "{asin}" not in content:
        raise ValueError("Template missing required {title} or {asin} placeholders")
    return content


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
        if "model" in str(exc) or "404" in str(exc):
            fallback = "gpt-3.5-turbo"
            log(f"downgrading model to {fallback} for ASIN {asin}")
            try:
                resp = client.chat.completions.create(
                    model=fallback, messages=messages
                )
                model = fallback
            except Exception as exc2:
                raise RuntimeError(
                    f"OpenAI API error after fallback: {exc2}"
                ) from exc2
        else:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc
    return resp.choices[0].message.content.strip()


def log_error(asin: str, title: str, error: Exception) -> None:
    """Append an error entry to the log file."""

    os.makedirs(os.path.dirname(ERROR_LOG) or ".", exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"ASIN: {asin} | Title: {title} | Error: {error}\n")


def main() -> None:

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4")

    if not api_key:
        print("OPENAI_API_KEY not found in .env")
        return

    client = None
    if OpenAI and api_key:
        try:
            client = OpenAI(api_key=api_key)
        except Exception as exc:  # pragma: no cover - network
            log(f"supplier_contact_generator: OpenAI init failed {exc}")
            client = None

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

    template_file = (
        TEMPLATE_FILE
        if args.lang == "en" and args.tone == "formal"
        else f"template_{args.lang}_{args.tone}.txt"
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success = 0
    failures = 0

    for prod in products:
        asin = prod["asin"]
        title = prod["title"]
        try:
            template = load_template(template_file)
        except Exception as exc:
            print(f"Template error for {asin}: {exc}")
            log_error(asin, title, exc)
            failures += 1
            continue

        message = ""
        if client:
            try:
                message = generate_message(client, asin, title, template, model)
            except Exception as exc:  # pragma: no cover - network
                log_error(asin, title, exc)
                log(f"supplier_contact_generator: using fallback message for {asin}")
        if not message:
            message = (
                f"Hello, we are interested in '{title}' (ASIN {asin}). "
                "Please provide pricing and MOQ details."
            )

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
        f"Generated {success} messages with {failures} failures." + (
            f" See {ERROR_LOG} for details." if failures else ""
        )
    )


if __name__ == "__main__":
    main()

