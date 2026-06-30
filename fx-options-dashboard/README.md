# FX Options Pricing & Risk Analytics Dashboard

A Python project for FX Options Trading and Financial Markets internship preparation. It builds a synthetic EUR/USD implied volatility surface, prices European FX options with the Garman-Kohlhagen model, calculates Greeks, runs scenario analysis, and produces a simple delta-hedging recommendation in an interactive Streamlit dashboard.

## Project Motivation

FX options desks need fast tools for pricing, risk explanation, and market scenario analysis. This project recreates a simplified analytics workflow: load market volatility data, interpolate an implied volatility, value an option, inspect Greeks, stress the market, and translate delta into a hedge action.

## Why FX Options Matter

FX options are used by banks, asset managers, corporates, and macro funds to hedge or express views on exchange rates. Unlike a forward, an option gives asymmetric payoff exposure, so traders need pricing models and risk measures to understand how option value changes with spot, volatility, time, and rates.

## Garman-Kohlhagen Model

The Garman-Kohlhagen model is the Black-Scholes framework adapted for foreign exchange. For EUR/USD, USD is the domestic currency and EUR is the foreign currency. The model discounts the strike at the domestic rate and discounts the spot exposure at the foreign rate.

For a European FX call:

```text
C = S0 * exp(-rf * T) * N(d1) - K * exp(-rd * T) * N(d2)
```

For a European FX put:

```text
P = K * exp(-rd * T) * N(-d2) - S0 * exp(-rf * T) * N(-d1)
```

## Implied Volatility Surface

An implied volatility surface maps option maturity and strike to the volatility implied by market option prices. Real FX options markets show smile and skew patterns: options away from at-the-money often trade at different implied volatilities because investors value tail protection and directional risk differently.

This project uses a synthetic but realistic EUR/USD surface across 1W, 1M, 3M, 6M, and 1Y maturities with strikes from 1.02 to 1.18.

## Greeks and Risk Management

Greeks explain how option value responds to market moves:

- Delta: directional exposure to spot.
- Gamma: sensitivity of delta to spot.
- Vega: sensitivity to implied volatility.
- Theta: time decay.
- Domestic rho: sensitivity to USD interest rates.
- Foreign rho: sensitivity to EUR interest rates.

These measures help a trader decide whether a book is mostly exposed to spot direction, volatility, time decay, or rates.

## Project Structure

```text
fx-options-dashboard/
├── README.md
├── requirements.txt
├── app.py
├── data/
│   └── sample_vol_surface.csv
├── src/
│   ├── __init__.py
│   ├── market_data.py
│   ├── volatility_surface.py
│   ├── garman_kohlhagen.py
│   ├── greeks.py
│   ├── scenario_analysis.py
│   ├── hedging.py
│   └── utils.py
└── tests/
    ├── test_garman_kohlhagen.py
    ├── test_greeks.py
    └── test_volatility_surface.py
```

## How to Run

```bash
cd fx-options-dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
pytest
```

## Interview Pitch

I built a Python-based FX options analytics dashboard that constructs an implied volatility surface, prices EUR/USD options using the Garman-Kohlhagen model, calculates Greeks, runs scenario analysis, and generates delta-hedging recommendations. The goal was to replicate a simplified version of the analytics workflow used on an FX Options trading desk.

## Talking Points

- The volatility surface separates market data from the pricing model.
- The option pricer validates inputs and supports both calls and puts.
- Greeks are analytical, which makes them fast and explainable.
- Scenario analysis shows how P&L changes under spot, volatility, rate, and time shocks.
- Delta hedging converts model output into a practical trading action.
