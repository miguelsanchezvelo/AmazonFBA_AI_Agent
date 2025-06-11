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
Run the discovery script and enter your maximum unit price when prompted:

```bash
python product_discovery.py
```

The script searches several product categories and saves up to 20 results in `data/product_results.csv`.

## Market Analysis
To analyze the market potential of existing Amazon products by ASIN, run the
`market_analysis.py` script. Provide one or more ASINs separated by commas when
prompted. The script will fetch pricing, rating, review count, and best seller
rank using SerpAPI and save the data to `data/market_analysis_results.csv`.

```bash
python market_analysis.py
```
