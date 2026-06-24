from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from scipy.interpolate import griddata
from scipy.optimize import brentq
from scipy.stats import norm


st.set_page_config(page_title="IV Surface Dashboard", layout="wide")


def latest_close(ticker_symbol):
    history = yf.Ticker(ticker_symbol).history(period="5d")
    close = history["Close"].dropna()
    if close.empty:
        raise RuntimeError(f"No recent close available for {ticker_symbol}")
    return float(close.iloc[-1])


def clean_options(options, max_relative_spread, min_open_interest):
    options = options.copy()
    options = options[(options["bid"] > 0) & (options["ask"] > options["bid"])].copy()
    options["mid_price"] = (options["bid"] + options["ask"]) / 2
    options["relative_spread"] = (options["ask"] - options["bid"]) / options["mid_price"]
    options = options[options["relative_spread"] <= max_relative_spread].copy()
    options = options[options["openInterest"].fillna(0) >= min_open_interest].copy()
    return options


def black_call_price(F, K, T, r, sigma):
    if min(F, K, T, sigma) <= 0:
        return np.nan
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))


def black_put_price(F, K, T, r, sigma):
    if min(F, K, T, sigma) <= 0:
        return np.nan
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def implied_volatility(market_price, F, K, T, r, option_type):
    def difference(sigma):
        if option_type == "call":
            model_price = black_call_price(F, K, T, r, sigma)
        elif option_type == "put":
            model_price = black_put_price(F, K, T, r, sigma)
        else:
            raise ValueError("option_type must be call or put")
        return model_price - market_price

    try:
        return brentq(difference, 0.0001, 5.0)
    except ValueError:
        return np.nan


def estimate_forward(calls, puts, spot_price, T, r):
    call_put_pairs = calls[["strike", "mid_price", "relative_spread"]].merge(puts[["strike", "mid_price", "relative_spread"]], on="strike", suffixes=("_call", "_put"))
    if call_put_pairs.empty:
        return np.nan
    call_put_pairs["forward_candidate"] = call_put_pairs["strike"] + np.exp(r * T) * (call_put_pairs["mid_price_call"] - call_put_pairs["mid_price_put"])
    near_atm_pairs = call_put_pairs[call_put_pairs["strike"].between(0.9 * spot_price, 1.1 * spot_price)].copy()
    if len(near_atm_pairs) < 3:
        return np.nan
    near_atm_pairs["pair_spread"] = near_atm_pairs["relative_spread_call"] + near_atm_pairs["relative_spread_put"]
    best_pairs = near_atm_pairs.nsmallest(max(3, len(near_atm_pairs) // 2), "pair_spread")
    return float(best_pairs["forward_candidate"].median())


def build_smile_for_expiration(ticker, expiration, spot_price, r, max_relative_spread, min_open_interest):
    today = pd.Timestamp.now().normalize()
    expiration_date = pd.Timestamp(expiration)
    T = (expiration_date - today).days / 365
    if T <= 0:
        return pd.DataFrame()

    option_chain = ticker.option_chain(expiration)
    calls = clean_options(option_chain.calls, max_relative_spread, min_open_interest)
    puts = clean_options(option_chain.puts, max_relative_spread, min_open_interest)
    forward_price = estimate_forward(calls, puts, spot_price, T, r)
    if np.isnan(forward_price):
        return pd.DataFrame()

    otm_puts = puts[puts["strike"] < forward_price].copy()
    otm_calls = calls[calls["strike"] >= forward_price].copy()
    otm_puts["my_implied_volatility"] = otm_puts.apply(lambda row: implied_volatility(row["mid_price"], forward_price, row["strike"], T, r, "put"), axis=1)
    otm_calls["my_implied_volatility"] = otm_calls.apply(lambda row: implied_volatility(row["mid_price"], forward_price, row["strike"], T, r, "call"), axis=1)
    otm_puts["option_type"] = "put"
    otm_calls["option_type"] = "call"

    smile = pd.concat([otm_puts, otm_calls], ignore_index=True)
    smile = smile.dropna(subset=["my_implied_volatility"])
    smile = smile[smile["my_implied_volatility"].between(0.01, 2.0)].copy()
    smile["expiration"] = expiration
    smile["T"] = T
    smile["forward"] = forward_price
    smile["log_moneyness"] = np.log(smile["strike"] / forward_price)
    smile["total_variance"] = smile["my_implied_volatility"] ** 2 * T
    smile = smile[smile["log_moneyness"].between(-0.35, 0.35)].copy()
    return smile.sort_values("strike")


@st.cache_data(show_spinner=False, ttl=900)
def build_surface_data(ticker_symbol, expiration_count, r, max_relative_spread, min_open_interest):
    ticker = yf.Ticker(ticker_symbol)
    spot_price = latest_close(ticker_symbol)
    expirations = list(ticker.options[:expiration_count])
    all_smiles = []

    for expiration in expirations:
        smile = build_smile_for_expiration(ticker, expiration, spot_price, r, max_relative_spread, min_open_interest)
        if not smile.empty:
            all_smiles.append(smile)

    if not all_smiles:
        raise RuntimeError("No usable option smiles were built. Try looser filters or another ticker.")

    surface_data = pd.concat(all_smiles, ignore_index=True)
    surface_data = surface_data.sort_values(["T", "strike", "option_type"]).reset_index(drop=True)
    return surface_data, spot_price, expirations


def make_surface_grid(surface_data, grid_size_k=80, grid_size_t=60):
    plot_data = surface_data.dropna(subset=["log_moneyness", "T", "total_variance"]).copy()
    k_min = plot_data["log_moneyness"].quantile(0.02)
    k_max = plot_data["log_moneyness"].quantile(0.98)
    t_min = plot_data["T"].min()
    t_max = plot_data["T"].max()
    k_grid = np.linspace(k_min, k_max, grid_size_k)
    t_grid = np.linspace(t_min, t_max, grid_size_t)
    K_GRID, T_GRID = np.meshgrid(k_grid, t_grid)
    points = plot_data[["log_moneyness", "T"]].to_numpy()
    values = plot_data["total_variance"].to_numpy()
    W_GRID = griddata(points=points, values=values, xi=(K_GRID, T_GRID), method="linear")
    W_GRID_NEAREST = griddata(points=points, values=values, xi=(K_GRID, T_GRID), method="nearest")
    W_GRID = np.where(np.isnan(W_GRID), W_GRID_NEAREST, W_GRID)
    IV_GRID = np.sqrt(np.maximum(W_GRID, 1e-12) / np.maximum(T_GRID, 1e-12))
    return K_GRID, T_GRID, IV_GRID


def make_surface_figure(surface_data, K_GRID, T_GRID, IV_GRID):
    fig = go.Figure()
    surface_trace = go.Surface(x=K_GRID, y=T_GRID * 365, z=IV_GRID, colorscale="Viridis", opacity=0.85, name="Interpolated IV surface", showscale=True, colorbar={"title": "IV"})
    quote_marker = {"size": 2, "color": surface_data["my_implied_volatility"], "colorscale": "Viridis", "opacity": 0.45}
    quote_trace = go.Scatter3d(x=surface_data["log_moneyness"], y=surface_data["T"] * 365, z=surface_data["my_implied_volatility"], mode="markers", marker=quote_marker, text=surface_data["expiration"], name="Option quotes")
    scene_labels = {"xaxis_title": "Log-moneyness log(K/F)", "yaxis_title": "Days to expiration", "zaxis_title": "Implied volatility"}
    fig.add_trace(surface_trace)
    fig.add_trace(quote_trace)
    fig.update_layout(title="Implied-volatility surface", scene=scene_labels, height=720, margin={"l": 0, "r": 0, "b": 0, "t": 45})
    return fig


def surface_iv(K_GRID, T_GRID, IV_GRID, log_moneyness, T):
    iv = griddata(points=np.column_stack([K_GRID.ravel(), T_GRID.ravel()]), values=IV_GRID.ravel(), xi=np.array([[log_moneyness, T]]), method="linear")[0]
    if np.isnan(iv):
        iv = griddata(points=np.column_stack([K_GRID.ravel(), T_GRID.ravel()]), values=IV_GRID.ravel(), xi=np.array([[log_moneyness, T]]), method="nearest")[0]
    return float(iv)


def forward_at(surface_data, T):
    forward_curve = surface_data.groupby("T")["forward"].median().reset_index().sort_values("T")
    return float(np.interp(T, forward_curve["T"], forward_curve["forward"]))


def digital_call_price(F, K, T, r, sigma):
    if min(F, K, T, sigma) <= 0:
        return np.nan
    d2 = (np.log(F / K) - 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    return float(np.exp(-r * T) * norm.cdf(d2))


st.title("Implied Volatility Surface Dashboard")
st.caption("Build SPY-style option smiles, interpolate a 3D IV surface, and price a simple OTC digital call.")

with st.sidebar:
    st.header("Inputs")
    ticker_symbol = st.text_input("Ticker", value="SPY").upper()
    expiration_count = st.slider("Number of expirations", min_value=5, max_value=40, value=25, step=1)
    r = st.number_input("Risk-free rate", min_value=0.0, max_value=0.2, value=0.04, step=0.005, format="%.4f")
    max_relative_spread = st.slider("Max relative spread", min_value=0.05, max_value=1.0, value=0.30, step=0.05)
    min_open_interest = st.number_input("Min open interest", min_value=0, max_value=1000, value=0, step=1)
    st.divider()
    notional = st.number_input("Digital notional", min_value=100.0, max_value=1_000_000.0, value=10_000.0, step=100.0)

with st.spinner("Building option surface from live option chains..."):
    surface_data, spot_price, expirations = build_surface_data(ticker_symbol, expiration_count, r, max_relative_spread, min_open_interest)
    K_GRID, T_GRID, IV_GRID = make_surface_grid(surface_data)

min_days = int(np.ceil(surface_data["T"].min() * 365))
max_days = int(np.floor(surface_data["T"].max() * 365))

with st.sidebar:
    maturity_days = st.slider("Target maturity in days", min_value=max(1, min_days), max_value=max_days, value=min(90, max_days), step=1)
    default_strike = 0.95 * spot_price
    strike = st.number_input("Target strike", min_value=0.01, max_value=3.0 * spot_price, value=float(default_strike), step=1.0)

target_T = maturity_days / 365
target_forward = forward_at(surface_data, target_T)
target_log_moneyness = np.log(strike / target_forward)
target_iv = surface_iv(K_GRID, T_GRID, IV_GRID, target_log_moneyness, target_T)
surface_price = digital_call_price(target_forward, strike, target_T, r, target_iv)
atm_iv = surface_iv(K_GRID, T_GRID, IV_GRID, 0.0, target_T)
flat_price = digital_call_price(target_forward, strike, target_T, r, atm_iv)

metric_columns = st.columns(5)
metric_columns[0].metric("Spot", f"{spot_price:,.2f}")
metric_columns[1].metric("Expirations", surface_data["expiration"].nunique())
metric_columns[2].metric("Quotes", f"{len(surface_data):,}")
metric_columns[3].metric("Target IV", f"{target_iv:.2%}")
metric_columns[4].metric("Digital value", f"${notional * surface_price:,.2f}")

tab_surface, tab_smiles, tab_pricing, tab_data = st.tabs(["3D surface", "Smiles", "Digital pricing", "Data"])

with tab_surface:
    st.plotly_chart(make_surface_figure(surface_data, K_GRID, T_GRID, IV_GRID), use_container_width=True)

with tab_smiles:
    fig_smiles = go.Figure()
    for expiration, data in surface_data.groupby("expiration"):
        fig_smiles.add_trace(go.Scatter(x=data["log_moneyness"], y=data["my_implied_volatility"], mode="markers", name=str(expiration), marker={"size": 5}))
    fig_smiles.update_layout(title="Smiles by expiration", xaxis_title="Log-moneyness log(K/F)", yaxis_title="Implied volatility", height=550)
    st.plotly_chart(fig_smiles, use_container_width=True)

with tab_pricing:
    pricing_table = pd.DataFrame([{"spot": spot_price, "strike": strike, "maturity_days": maturity_days, "forward": target_forward, "log_moneyness": target_log_moneyness, "surface_iv": target_iv, "atm_iv": atm_iv, "surface_digital_unit_price": surface_price, "flat_vol_unit_price": flat_price, "difference": surface_price - flat_price, "surface_notional_value": notional * surface_price, "flat_vol_notional_value": notional * flat_price}])
    st.dataframe(pricing_table, use_container_width=True)

with tab_data:
    summary = surface_data.groupby("expiration").agg(T=("T", "first"), forward=("forward", "first"), quotes=("strike", "size"), min_strike=("strike", "min"), max_strike=("strike", "max")).reset_index()
    st.subheader("Expiration summary")
    st.dataframe(summary, use_container_width=True)
    st.subheader("Surface data")
    st.dataframe(surface_data[["expiration", "option_type", "strike", "T", "forward", "log_moneyness", "my_implied_volatility", "total_variance"]], use_container_width=True)
