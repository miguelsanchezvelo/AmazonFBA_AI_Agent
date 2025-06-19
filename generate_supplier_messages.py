"""Generate supplier quote request messages using OpenAI's Chat API."""

import argparse
import json
import os
from typing import List, Dict, Optional

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore


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


def main(argv: Optional[List[str]] = None) -> None:
    global INPUT_JSON, OUTPUT_JSON

    parser = argparse.ArgumentParser(
        description="Generate supplier quote request messages using OpenAI"
    )
    parser.add_argument(
        "--input",
        default=INPUT_JSON,
        help="Input JSON file with supplier requests",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_JSON,
        help="Where to save generated messages",
    )
    args = parser.parse_args(argv)

    INPUT_JSON = args.input
    OUTPUT_JSON = args.output

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

