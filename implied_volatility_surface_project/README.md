# Implied Volatility Surface Project

This project builds SPY option smiles across expirations, interpolates an implied-volatility surface, and uses the surface to price a simple OTC-style digital call option.

## Notebook

Open:

```bash
jupyter notebook estimation_of_an_OTC_opt.ipynb
```

## Interactive Dashboard

Run the Streamlit dashboard from the repository root:

```bash
.venv/bin/streamlit run implied_volatility_surface_project/dashboard.py
```

The dashboard lets you:

- choose a ticker and number of expirations;
- build a live implied-volatility surface from option chains;
- inspect smiles by expiration;
- view a 3D Plotly IV surface;
- choose strike, maturity, rate, and notional;
- compare a surface-based digital call value with a flat-volatility value.

The app uses live Yahoo Finance data, so results depend on current quote availability and quote quality.
