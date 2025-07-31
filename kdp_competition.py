#!/usr/bin/env python3
"""Generate mock Amazon KDP competitor data.

This script simulates fetching book data for a given niche on Amazon KDP.
It outputs a CSV file with the individual competitor entries and summary
statistics at the bottom. Only a mock mode is implemented.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from typing import List, Dict

OUTPUT_CSV = os.path.join("data", "competitor_analysis.csv")


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze KDP competition")
    parser.add_argument("--niche", required=True, help="Selected niche")
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock data (only mode available)",
    )
    return parser.parse_args(argv)


def generate_mock_data(niche: str, n: int = 20) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for i in range(1, n + 1):
        title = f"{niche.title()} Book {i}"
        price = round(random.uniform(4.99, 12.99), 2)
        reviews = random.randint(0, 2000)
        bsr = random.randint(5000, 500000)
        keyword_density = round(random.uniform(0.1, 0.8), 2)
        url = f"https://example.com/{niche.replace(' ', '_')}/{i}"
        rows.append(
            {
                "title": title,
                "price": price,
                "reviews": reviews,
                "bsr": bsr,
                "keyword_density": keyword_density,
                "url": url,
            }
        )
    return rows


def compute_averages(rows: List[Dict[str, object]]) -> Dict[str, float]:
    total_price = sum(row["price"] for row in rows)
    total_reviews = sum(row["reviews"] for row in rows)
    total_bsr = sum(row["bsr"] for row in rows)
    total_kd = sum(row["keyword_density"] for row in rows)
    n = len(rows)
    return {
        "title": "AVERAGES",
        "price": round(total_price / n, 2),
        "reviews": round(total_reviews / n, 2),
        "bsr": round(total_bsr / n, 2),
        "keyword_density": round(total_kd / n, 3),
        "url": "-",
    }


def save_csv(rows: List[Dict[str, object]], averages: Dict[str, float], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["title", "price", "reviews", "bsr", "keyword_density", "url"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(averages)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    niche = args.niche.strip()
    rows = generate_mock_data(niche)
    averages = compute_averages(rows)
    save_csv(rows, averages, OUTPUT_CSV)

    print(f"Saved {len(rows)} rows to {OUTPUT_CSV}")
    print("Summary:")
    print(f"  Average price: ${averages['price']}")
    print(f"  Average reviews: {averages['reviews']}")
    print(f"  Average BSR: {averages['bsr']}")
    print(f"  Average keyword density: {averages['keyword_density']}")


if __name__ == "__main__":
    main()
