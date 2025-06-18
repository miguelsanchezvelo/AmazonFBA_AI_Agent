"""Generate supplier quote request messages using OpenAI's Chat API."""

import json
import os
from typing import List, Dict

import openai
from dotenv import load_dotenv


INPUT_JSON = os.path.join("data", "supplier_contact_requests.json")
OUTPUT_JSON = os.path.join("data", "supplier_messages.json")


def load_requests(path: str) -> List[Dict[str, object]]:
    """Return list of contact requests from JSON file."""
    if not os.path.exists(path):
        print(f"Input file '{path}' not found.")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return []


def save_messages(rows: List[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception as exc:
        print(f"Error writing {path}: {exc}")


def generate_message(units: int, title: str) -> str:
    """Return a polite supplier message for the given product."""

    system = {
        "role": "system",
        "content": "You are an AI assistant helping a seller request quotes from suppliers.",
    }
    user = {
        "role": "user",
        "content": (
            "Please write a professional message to a supplier requesting a quote "
            f"for {units} units of '{title}'. Mention that we are evaluating "
            "suppliers for potential bulk orders and would like price and "
            "shipping details for this order quantity."
        ),
    }

    try:
        response = openai.ChatCompletion.create(model="gpt-4", messages=[system, user])
    except Exception as exc:
        raise RuntimeError(f"OpenAI API error: {exc}") from exc

    content = response["choices"][0]["message"]["content"]
    return content.strip()


def main() -> None:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY not set in environment")

    openai.api_key = key

    requests = load_requests(INPUT_JSON)
    if not requests:
        return

    messages: List[Dict[str, str]] = []
    for req in requests:
        asin = req.get("asin", "")
        title = req.get("title", "")
        units = req.get("units") or 0
        try:
            msg = generate_message(int(units), title)
        except Exception as exc:
            print(f"Failed to generate message for ASIN {asin}: {exc}")
            continue
        messages.append({"asin": asin, "title": title, "message": msg})

    if messages:
        save_messages(messages, OUTPUT_JSON)
        print(f"Generated {len(messages)} messages.")
    else:
        print("No messages were generated.")


if __name__ == "__main__":
    main()

