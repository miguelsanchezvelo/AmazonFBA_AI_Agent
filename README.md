# AmazonFBA AI Agent

This repository contains a simple script to discover potential Amazon FBA product opportunities using [SerpAPI](https://serpapi.com/).

## Setup
1. Install dependencies:
   ```bash
   pip install python-dotenv google-search-results
   ```
   The SerpAPI client is imported in the code as `from serpapi import GoogleSearch`.
   If you previously installed the wrong package, you can remove it with:
   ```bash
   pip uninstall serpapi
   ```
2. Copy `.env.example` to `.env` and add your SerpAPI API key:
   ```bash
   cp .env.example .env
   # edit .env and set SERPAPI_API_KEY
   ```

## Usage
Run the discovery script and enter your total startup budget when prompted.
The script reserves part of that budget for tools and subscriptions (the amount is controlled by the `FIXED_COST` constant in `product_discovery.py`) and uses the rest for product research:

```bash
python product_discovery.py
```

The script searches several product categories, estimates profitability, and saves the top 10 opportunities in `data/product_results.csv`.

## Market Analysis
To analyze the market potential of existing Amazon products by ASIN, run the
`market_analysis.py` script. You can enter one or more ASINs when prompted or
provide a CSV file containing an `asin` column via the `--csv` option. If you
press **Enter** without typing any ASINs, the script will automatically load the
values from `data/product_results.csv` created by `product_discovery.py`. The
script fetches pricing, rating, review count, and best seller rank using
SerpAPI, assigns a simple score (HIGH/MEDIUM/LOW) based on rating and review
count, then saves the results to `data/market_analysis_results.csv`.

```bash
python market_analysis.py
```

