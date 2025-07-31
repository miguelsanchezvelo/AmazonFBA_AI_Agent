#!/usr/bin/env python3
"""Discover potential KDP niches using Amazon autocomplete suggestions.

The script searches Amazon for autocomplete phrases based on a seed keyword,
then gathers basic competition data for each suggestion. Results are saved to
``niches_found.csv``.
"""

from __future__ import annotations

import argparse
import time
from typing import List, Tuple

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def get_driver() -> webdriver.Chrome:
    """Return a headless Chrome WebDriver with a custom user agent."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(options=chrome_options)


def get_suggestions(driver: webdriver.Chrome, base_keyword: str) -> List[str]:
    """Return autocomplete suggestions for ``base_keyword`` on Amazon."""
    driver.get("https://www.amazon.es/")
    time.sleep(2)
    search_box = driver.find_element(By.ID, "twotabsearchtextbox")
    search_box.send_keys(base_keyword)
    time.sleep(2)
    suggestions = driver.find_elements(By.CSS_SELECTOR, ".s-suggestion")[:10]
    return [s.text.strip() for s in suggestions if base_keyword.lower() in s.text.lower()]


def get_competition_and_bsr(driver: webdriver.Chrome, keyword: str) -> Tuple[int, float]:
    """Return the number of results and average BSR for ``keyword`` search."""
    driver.get("https://www.amazon.es/")
    time.sleep(2)
    search_box = driver.find_element(By.ID, "twotabsearchtextbox")
    search_box.clear()
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    try:
        results_text = driver.find_element(By.XPATH, "//span[contains(text(),'resultados')]").text
        competition = int("".join(filter(str.isdigit, results_text.split()[0])))
    except Exception:
        competition = 0

    bsr_list: List[int] = []
    books = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot div[data-asin]")[:10]
    for book in books:
        try:
            bsr_text = book.find_element(By.XPATH, ".//span[contains(text(),'n.º')]").text
            bsr = int("".join(filter(str.isdigit, bsr_text)))
            bsr_list.append(bsr)
        except Exception:
            continue

    avg_bsr = round(sum(bsr_list) / len(bsr_list), 2) if bsr_list else 999999.0
    return competition, avg_bsr


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover KDP niches")
    parser.add_argument("--keyword", required=True, help="Seed keyword")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    driver = get_driver()
    print(f"\N{LEFT-POINTING MAGNIFYING GLASS} Searching suggestions for: {args.keyword}")
    suggestions = get_suggestions(driver, args.keyword)
    print(f"Found {len(suggestions)} suggestions.")

    results = []
    for niche in suggestions:
        print(f"\N{BOOKS} Analyzing niche: {niche}")
        competition, avg_bsr = get_competition_and_bsr(driver, niche)
        saturation = round(competition / avg_bsr, 4) if avg_bsr else 9999.0
        results.append(
            {
                "niche": niche,
                "search_volume": "N/A",  # Placeholder
                "competition": competition,
                "avg_bsr": avg_bsr,
                "saturation": saturation,
            }
        )
        time.sleep(2)

    df = pd.DataFrame(results)
    df.to_csv("niches_found.csv", index=False)
    print("\n\N{check mark} Saved niches to niches_found.csv")
    driver.quit()


if __name__ == "__main__":
    main()
