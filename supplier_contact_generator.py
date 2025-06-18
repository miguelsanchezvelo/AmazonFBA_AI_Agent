"""Generate supplier contact emails using OpenAI."""

import csv
import os
from typing import Dict, List

import openai
from dotenv import load_dotenv

INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_TXT = os.path.join("data", "supplier_emails.txt")


def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fallback_email(title: str) -> str:
    return (
        "Dear Sir or Madam,\n\n"
        f"I am interested in sourcing the product '{title}'. "
        "Could you please provide the minimum order quantity (MOQ), price per unit "
        "and lead time? I would also appreciate your catalogue of similar products.\n\n"
        "Best regards,\n"
        "Carlos Ruiz\n"
        "sourcing@example.com\n"
        "Spain"
    )


def generate_email(title: str) -> str:
    system = {
        "role": "system",
        "content": "You are an assistant that writes short professional sourcing emails in English.",
    }
    user = {
        "role": "user",
        "content": (
            "Write a brief email to a supplier about the product '"
            + title
            + "'. Ask for minimum order quantity, unit price and lead time. "
            "Request a catalogue of similar products and sign as Carlos Ruiz (sourcing@example.com) from Spain."
        ),
    }
    last_exc = None
    for model in ("gpt-4", "gpt-3.5-turbo"):
        try:
            resp = openai.ChatCompletion.create(model=model, messages=[system, user])
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover - network
            last_exc = exc
    raise RuntimeError(last_exc)  # pragma: no cover - network


def main() -> None:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    use_api = bool(key)
    if use_api:
        openai.api_key = key
    rows = load_rows(INPUT_CSV)
    if not rows:
        print(f"Input file '{INPUT_CSV}' not found. Run supplier_selection.py first.")
        return

    emails: List[str] = []
    for r in rows:
        try:
            units = int(float(r.get("units_to_order", "0")))
        except ValueError:
            units = 0
        if units <= 0:
            continue
        title = r.get("title", "")
        if use_api:
            try:
                msg = generate_email(title)
            except Exception as exc:  # pragma: no cover - network
                print(f"OpenAI error for '{title}': {exc}")
                msg = fallback_email(title)
        else:
            msg = fallback_email(title)
        emails.append(f"Product: {title}\n\n{msg}\n")

    if not emails:
        print("No products with units to order found.")
        return

    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        for i, mail in enumerate(emails):
            f.write(mail.strip() + "\n")
            if i < len(emails) - 1:
                f.write("-" * 40 + "\n")
    print(f"Saved {len(emails)} emails to {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
