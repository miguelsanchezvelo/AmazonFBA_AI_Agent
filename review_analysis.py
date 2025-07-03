"""Analyze competitor product reviews for Amazon FBA."""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

try:
    from serpapi import GoogleSearch
except Exception:  # pragma: no cover - optional dependency
    GoogleSearch = None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from mock_data import get_mock_asins

INPUT_CSV = os.path.join("data", "market_analysis_results.csv")
OUTPUT_CSV = os.path.join("data", "review_analysis_results.csv")


load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
KEEPA_KEY = os.getenv("KEEPA_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze competitor product reviews")
    parser.add_argument('--auto', action='store_true', help='Run in auto mode with default values')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed console output')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (if applicable)')
    parser.add_argument('--csv', default=INPUT_CSV, help='Input CSV with ASIN and Title')
    parser.add_argument('--output', default=OUTPUT_CSV, help='Where to save analysis results')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')
    return parser.parse_args()


args = parse_args()


def load_rows(path: str) -> List[Dict[str, str]]:
    """Load rows from input CSV."""
    if not os.path.exists(path):
        print(f"Input CSV '{path}' not found.")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def fetch_reviews_serpapi(asin: str, max_reviews: int = 10) -> List[str]:
    """Return review texts using SerpAPI if possible."""
    if not (SERPAPI_KEY and GoogleSearch):
        return []
    params = {
        "engine": "amazon_reviews",
        "api_key": SERPAPI_KEY,
        "amazon_domain": "amazon.com",
        "asin": asin,
        "page": 1,
    }
    try:
        data = GoogleSearch(params).get_dict()
    except Exception:
        return []
    reviews = data.get("reviews", []) or []
    texts: List[str] = []
    for r in reviews:
        txt = r.get("body") or r.get("snippet") or ""
        if txt:
            texts.append(txt)
        if len(texts) >= max_reviews:
            break
    return texts


def generate_mock_reviews(title: str) -> List[str]:
    """Return simple mock reviews for fallback."""
    return [
        f"I really like the {title}. It works great!",
        "Quality could be better but it does the job.",
        "Decent value for the price.",
    ]


def fetch_reviews_openai(client: OpenAI, model: str, title: str) -> List[str]:
    """Generate synthetic reviews with OpenAI."""
    system = {"role": "system", "content": "Generate brief customer reviews."}
    user = {
        "role": "user",
        "content": (
            "Provide three short and diverse customer reviews for the product "
            f"'{title}'."
        ),
    }
    try:
        response = client.chat.completions.create(model=model, messages=[system, user])
    except Exception:
        return []
    content = response.choices[0].message.content
    if not content:
        return []
    return [r.strip() for r in content.split("\n") if r.strip()]


def analyze_reviews_openai(
    client: OpenAI, model: str, reviews: List[str]
) -> Dict[str, str]:
    """Summarize reviews using OpenAI."""
    joined = "\n".join(reviews)
    system = {
        "role": "system",
        "content": (
            "You analyze customer reviews and summarise positives, negatives and "
            "product improvement ideas."
        ),
    }
    user = {
        "role": "user",
        "content": (
            "Reviews:\n" + joined + "\n" +
            "Provide a short summary of the most common compliments, the most "
            "common complaints, and 2-3 possible improvements or "
            "differentiators."
        ),
    }
    try:
        resp = client.chat.completions.create(model=model, messages=[system, user])
    except Exception:
        return {
            "positives": "",
            "negatives": "",
            "diffs": "",
        }
    txt = resp.choices[0].message.content or ""
    # Expect sections separated by newlines
    parts = [p.strip() for p in txt.split("\n") if p.strip()]
    return {
        "positives": parts[0] if parts else "",
        "negatives": parts[1] if len(parts) > 1 else "",
        "diffs": parts[2] if len(parts) > 2 else "",
    }


def analyze_reviews_simple(reviews: List[str]) -> Dict[str, str]:
    """Basic heuristic analysis when OpenAI is unavailable."""
    text = " ".join(reviews).lower()
    positives = []
    negatives = []
    if any(word in text for word in ["good", "great", "excellent", "love"]):
        positives.append("Quality")
    if "price" in text:
        positives.append("Price")
    if any(word in text for word in ["bad", "poor", "broke", "broken"]):
        negatives.append("Durability")
    if "slow" in text or "late" in text:
        negatives.append("Shipping")
    return {
        "positives": ", ".join(positives) or "General satisfaction",
        "negatives": ", ".join(negatives) or "Minor issues",
        "diffs": "Improve quality and add unique features.",
    }


def process_row(client: Optional[OpenAI], model: str, row: Dict[str, str]) -> Dict[str, str]:
    asin = row.get("asin") or row.get("ASIN") or ""
    title = row.get("title") or row.get("Title") or ""
    reviews = fetch_reviews_serpapi(asin)
    if not reviews and client and title:
        reviews = fetch_reviews_openai(client, model, title)
    if not reviews and title:
        reviews = generate_mock_reviews(title)
    if client and reviews:
        analysis = analyze_reviews_openai(client, model, reviews)
    else:
        analysis = analyze_reviews_simple(reviews)
    return {
        "asin": asin,
        "title": title,
        "positives": analysis.get("positives", ""),
        "negatives": analysis.get("negatives", ""),
        "diffs": analysis.get("diffs", ""),
    }


def save_results(rows: List[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["asin", "title", "positives", "negatives", "diffs"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    global INPUT_CSV, OUTPUT_CSV

    INPUT_CSV = args.csv
    OUTPUT_CSV = args.output

    use_mock = args.mock
    if use_mock:
        mock_reviews = [dict(row, **{"review_summary": f"Resumen de reviews para {row['title']}"}) for row in get_mock_asins()]
        save_results(mock_reviews, OUTPUT_CSV)
        print(f"[MOCK] Saved {len(mock_reviews)} review analysis rows to {OUTPUT_CSV}")
        return

    rows = load_rows(INPUT_CSV)
    if not rows:
        print("No input data found.")
        return

    client: Optional[OpenAI] = None
    model = "gpt-4"
    if OPENAI_KEY and OpenAI:
        try:
            client = OpenAI(api_key=OPENAI_KEY)
            model = "gpt-4"
            # quick capability check
            _ = client.models.retrieve(model)
        except Exception:
            try:
                model = "gpt-3.5-turbo"
                _ = client.models.retrieve(model) if client else None
            except Exception:
                client = None

    results = []
    for row in rows:
        result = process_row(client, model, row)
        results.append(result)

    save_results(results, OUTPUT_CSV)
    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
