# AmazonFBA AI Agent

This repository contains a simple script to discover potential Amazon FBA product opportunities using [SerpAPI](https://serpapi.com/).

## Setup
1. Install dependencies:
   ```bash
   pip install python-dotenv serpapi
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
