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
2. Copy `.env.example` to `.env` and add your SerpAPI API key. Optionally copy
   `config.example.json` to `config.json` to store both SerpAPI and Keepa keys:
   ```bash
   cp .env.example .env
   # edit .env and set SERPAPI_API_KEY
   cp config.example.json config.json  # edit and set KEEPPA/SerpAPI keys
   ```

## Usage
Run the discovery script and enter your total startup budget when prompted.
The script reserves part of that budget for tools and subscriptions (the amount is controlled by the `FIXED_COST` constant in `product_discovery.py`) and uses the rest for product research. The discovery step queries Amazon directly using SerpAPI's Amazon engine:


```bash
python product_discovery.py [--debug]
```

The script searches several product categories, estimates profitability, and saves the top 20 opportunities in `data/product_results.csv`. Use the optional `--debug` flag to print raw SerpAPI results for troubleshooting.

## Market Analysis
To analyze the market potential of existing Amazon products by ASIN, run the
`market_analysis.py` script. You can enter one or more ASINs when prompted or
provide a CSV file containing an `asin` column via the `--csv` option. If you
press **Enter** without typing any ASINs, the script will automatically load the
values from `data/product_results.csv` created by `product_discovery.py`. The
The script fetches pricing, rating, review count, and best seller rank. It uses
SerpAPI as the primary source and falls back to Keepa when necessary. You can
disable keyword-based fallback searches with the `--no-fallback` flag. Results
are saved to `data/market_analysis_results.csv`.

```bash
python market_analysis.py
```

