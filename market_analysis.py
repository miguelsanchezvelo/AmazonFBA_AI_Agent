# market_analysis.py - Cleaned up version with dual API fallback
import os
import csv
import re
import argparse
import time
import json
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

CONFIG_PATH = "config.json"
DATA_PATH = os.path.join("data", "market_analysis_results.csv")
DISCOVERY_CSV = os.path.join("data", "product_results.csv")

SERPAPI_KEY: Optional[str] = None
KEEPA_KEY: Optional[str] = None


def load_keys() -> Tuple[str, str]:
    global SERPAPI_KEY, KEEPA_KEY
    config: Dict[str, str] = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            print(f"Warning: could not read {CONFIG_PATH}: {exc}")

    SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or config.get("serpapi_key")
    if not SERPAPI_KEY:
        SERPAPI_KEY = input("Enter your SerpAPI key: ").strip()

    KEEPA_KEY = os.getenv("KEEPA_API_KEY") or config.get("keepa_key")
    if not KEEPA_KEY:
        KEEPA_KEY = input("Enter your Keepa API key: ").strip()

    return SERPAPI_KEY, KEEPA_KEY


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"\d+\.\d+|\d+", value)
    return float(match.group()) if match else None


ASIN_PATTERN = r"^B0[A-Z0-9]{8}$"


def is_valid_asin(asin: str) -> bool:
    return bool(re.fullmatch(ASIN_PATTERN, (asin or "").upper()))


def evaluate_potential(product: Dict[str, Optional[float]]) -> str:
    rating = product.get("rating") or 0
    reviews = product.get("reviews") or 0
    bsr = product.get("bsr")
    if rating >= 4.3 and reviews >= 300 and bsr:
        return "HIGH"
    if rating >= 4.0:
        return "MEDIUM"
    return "LOW"


def get_product_data_serpapi(asin: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, str]]:
    key, _ = load_keys()
    if asin:
        params = {
            "engine": "amazon",
            "api_key": key,
            "amazon_domain": "amazon.com",
            "type": "product",
            "asin": asin,
        }
        try:
            result = GoogleSearch(params).get_dict()
            product = result.get("product_results") or {}
            if not product:
                return None
            title = product.get("title")
            price_raw = product.get("price", {}).get("raw") if isinstance(product.get("price"), dict) else product.get("price")
            price = parse_float(price_raw)
            rating = parse_float(str(product.get("rating")))
            reviews = parse_float(str(product.get("reviews")))
            link = product.get("url") or product.get("link")
            bsr = None
            for item in result.get("product_information", []):
                if "Best Sellers Rank" in item.get("title", ""):
                    bsr = item.get("value")
                    break
            return {
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "bsr": bsr,
                "link": link,
                "source": "serpapi",
                "estimated": False,
            }
        except Exception as e:
            print(f"SerpAPI error for ASIN {asin}: {e}")

    if title:
        params = {
            "engine": "amazon",
            "api_key": key,
            "amazon_domain": "amazon.com",
            "type": "search",
            "search_term": title,
        }
        try:
            result = GoogleSearch(params).get_dict()
            items = result.get("organic_results", [])
            if not items:
                return None
            best = items[0]
            asin = best.get("asin")
            link = best.get("link") or best.get("url")
            price = parse_float(best.get("price", {}).get("raw") if isinstance(best.get("price"), dict) else best.get("price"))
            rating = parse_float(str(best.get("rating")))
            reviews = parse_float(str(best.get("reviews")))
            return {
                "asin": asin,
                "title": best.get("title"),
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "bsr": None,
                "link": link,
                "source": "serpapi",
                "estimated": True,
            }
        except Exception as e:
            print(f"SerpAPI error for title '{title}': {e}")

    return None


def get_product_data_keepa(asin: Optional[str] = None, keywords: Optional[str] = None) -> Optional[Dict[str, str]]:
    _, key = load_keys()
    if asin:
        url = f"https://api.keepa.com/product?key={key}&domain=1&asin={asin}"
    elif keywords:
        url = f"https://api.keepa.com/search?key={key}&domain=1&term={requests.utils.quote(keywords)}"
    else:
        return None

    try:
        data = requests.get(url, timeout=20).json()
        products = data.get("products") or []
        if not products:
            return None
        item = products[0]
        asin = item.get("asin")
        return {
            "asin": asin,
            "title": item.get("title"),
            "price": parse_float(str(item.get("buyBoxSellerPrice") or item.get("buyBoxPrice"))),
            "rating": parse_float(str(item.get("rating"))),
            "reviews": parse_float(str(item.get("reviewCount"))),
            "bsr": item.get("salesRank"),
            "link": f"https://www.amazon.com/dp/{asin}",
            "source": "keepa",
            "estimated": keywords is not None and not asin,
        }
    except Exception as e:
        print(f"Keepa error: {e}")
    return None
