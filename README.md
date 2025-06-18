# AmazonFBA AI Agent

This repository contains a simple script to discover potential Amazon FBA product opportunities using [SerpAPI](https://serpapi.com/).

## Setup
1. Install dependencies:
   ```bash
   pip install python-dotenv google-search-results openai
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


## Offline Mock Data
If you want to experiment without valid API keys, run `prepare_mock_data.py`.
It creates `data/mock_market_data.csv` with sample products and skips creation
if the file already exists or API credentials are detected.

## Supplier Quote Messages
The `generate_supplier_messages.py` script sends each product in
`data/supplier_contact_requests.json` to the OpenAI Chat API and saves the
resulting emails to `data/supplier_messages.json`. Set your OpenAI key in `.env`
as `OPENAI_API_KEY` before running:

```bash
python generate_supplier_messages.py
```

## Email Negotiation Agent
The `negotiation_agent.py` script connects to a Gmail inbox, summarizes unread supplier emails and optionally sends replies with GPT‑4. Configure `EMAIL_ADDRESS`, `EMAIL_PASSWORD` and `OPENAI_API_KEY` in your `.env` file. Enable automatic sending by setting `AUTO_REPLY=True`.

Run it manually with:
```bash
python negotiation_agent.py
```
It is also executed automatically by `fba_agent.py` when credentials are present.

## Email Manager
`email_manager.py` extends the automated workflow by keeping track of entire conversation threads. It connects to the same inbox using IMAP and SMTP, detects replies from suppliers and, if `AUTO_REPLY=True`, generates responses with OpenAI and sends them automatically. All processed threads are stored in `logs/email_threads.json`.

Run it manually with:
```bash
python email_manager.py
```
