# AmazonFBA_AI_Agent - Documentation

## Overview
AmazonFBA_AI_Agent is an AI-powered assistant for Amazon FBA sellers, automating and optimizing the product sourcing, analysis, and management pipeline.

## Main Modules

### 1. Product Discovery
Identifies potential products to sell on Amazon using market data, trends, and custom criteria.

### 2. Market Analysis
Analyzes the discovered products for market size, competition, and demand using APIs and web scraping.

### 3. Profitability Estimation
Estimates the expected profit for each product, considering costs, fees, and price history.

### 4. Demand Forecast
Forecasts future sales for each product using:
- **Classical methods:** Correction Factor, Exponential Smoothing, Holt-Winters (seasonal)
- **AI/ML methods:** Prophet (Meta), with plans to add XGBoost and RandomForest

#### Forecasting Theory
- **Correction Factor:** Adjusts forecast by the ratio of real to estimated demand.
- **Exponential Smoothing:** Combines last real demand and last forecast, good for stable series.
- **Holt-Winters:** Captures trend and seasonality, requires several periods of data.
- **Prophet:** Robust to outliers and seasonality, provides confidence intervals for each forecast.

#### Anomaly Detection with Prophet
Prophet provides a prediction interval (`yhat_lower`, `yhat_upper`) for each forecasted point. If the real sales value falls outside this interval, it is flagged as an anomaly. The system alerts the user and suggests reviewing inventory or contacting suppliers.

### 5. Supplier Selection
Selects the best suppliers based on price, reliability, and lead time.

### 6. Pricing Simulator
Simulates pricing strategies and their impact on sales and profit.

### 7. Inventory Management
Tracks stock, sales, and manual movements, and triggers alerts for low stock or anomalies.

---

*This documentation will be expanded and refined as the project evolves.*
