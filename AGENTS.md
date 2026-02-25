# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Amazon FBA AI Agent — a Python pipeline for discovering, analyzing, sourcing, and managing Amazon FBA product opportunities. Includes a KDP Toolkit. The Streamlit UI (`ui.py`) is the primary interface. See `README.md` for full details.

### Python environment

- Uses a virtualenv at `/workspace/venv/` (Linux). Activate with `source /workspace/venv/bin/activate` or call `/workspace/venv/bin/python` directly.
- The `requirements.txt` only lists a subset of dependencies. The full set includes: `streamlit`, `openai`, `colorama`, `python-dotenv`, `yagmail`, `lxml`, `plotly`, `pandas`, `serpapi`, `requests`.

### Running the application

```bash
/workspace/venv/bin/streamlit run ui.py --server.headless=true --server.port=8501
```

### Running tests and validation

```bash
/workspace/venv/bin/python test_all.py          # Tests all scripts (--help and --auto)
/workspace/venv/bin/python validate_all.py       # Validates pipeline outputs and scripts
```

### Generating mock data (offline mode)

```bash
/workspace/venv/bin/python mock_data_generator.py   # Populates data/ and supplier_messages/
/workspace/venv/bin/python market_analysis.py --mock # Generates data/market_analysis_results.csv
```

### Known issues

- Several scripts (`product_discovery.py`, `market_analysis.py`, `profitability_estimation.py`, `demand_forecast.py`, `supplier_selection.py`) have dual `argparse` parsers — the module-level parser and the `__main__` parser accept different flags. This causes `--auto` failures in `test_all.py` for these scripts. This is a pre-existing issue.
- The `market_analysis.py --mock` output does not include all columns that `validate_all.py` expects (`rating`, `reviews`, `bsr`, `link`, `source`, `estimated`, `potential`). Pre-existing inconsistency.
- External API keys (`SERPAPI_API_KEY`, `OPENAI_API_KEY`, `KEEPA_API_KEY`) are optional. The pipeline works in mock/offline mode without them.

### Environment variables

Copy `.env.example` to `.env`. No real API keys are needed for mock/offline mode.
