"""Streamlit dashboard for FX options pricing and risk analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.garman_kohlhagen import price_fx_option
from src.greeks import calculate_greeks
from src.hedging import generate_delta_hedge_recommendation
from src.scenario_analysis import run_scenario_analysis
from src.volatility_surface import VolatilitySurface


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "data" / "sample_vol_surface.csv"


@st.cache_resource
def load_surface() -> VolatilitySurface:
    """Load the volatility surface once per Streamlit session."""
    return VolatilitySurface(DATA_PATH)


def format_percent(value: float) -> str:
    """Format a decimal rate or volatility as a percentage string."""
    return f"{value:.2%}"


def main() -> None:
    """Render the FX options analytics dashboard."""
    st.set_page_config(
        page_title="FX Options Pricing & Risk Analytics",
        page_icon="FX",
        layout="wide",
    )

    surface = load_surface()

    st.title("FX Options Pricing & Risk Analytics Dashboard")
    st.caption("EUR/USD European options priced with the Garman-Kohlhagen model")

    with st.sidebar:
        st.header("Option Inputs")
        spot = st.number_input("Spot EUR/USD", min_value=0.0001, value=1.1000, step=0.0050, format="%.4f")
        strike = st.number_input("Strike", min_value=0.0001, value=1.1000, step=0.0050, format="%.4f")
        maturity = st.select_slider(
            "Maturity",
            options=[0.0192, 0.0833, 0.2500, 0.5000, 1.0000],
            value=0.2500,
            format_func=lambda x: {
                0.0192: "1W",
                0.0833: "1M",
                0.2500: "3M",
                0.5000: "6M",
                1.0000: "1Y",
            }[x],
        )
        domestic_rate = st.number_input("USD domestic rate", value=0.0500, step=0.0025, format="%.4f")
        foreign_rate = st.number_input("EUR foreign rate", value=0.0350, step=0.0025, format="%.4f")
        option_type = st.radio("Option type", options=["call", "put"], horizontal=True)
        notional = st.number_input("Notional EUR", min_value=1_000.0, value=1_000_000.0, step=50_000.0, format="%.0f")

    implied_volatility = surface.get_implied_volatility(strike=strike, maturity=maturity)
    option_price = price_fx_option(
        spot=spot,
        strike=strike,
        maturity=maturity,
        domestic_rate=domestic_rate,
        foreign_rate=foreign_rate,
        volatility=implied_volatility,
        option_type=option_type,
    )
    option_value = option_price * notional
    greeks = calculate_greeks(
        spot=spot,
        strike=strike,
        maturity=maturity,
        domestic_rate=domestic_rate,
        foreign_rate=foreign_rate,
        volatility=implied_volatility,
        option_type=option_type,
    )
    scenarios = run_scenario_analysis(
        spot=spot,
        strike=strike,
        maturity=maturity,
        domestic_rate=domestic_rate,
        foreign_rate=foreign_rate,
        volatility=implied_volatility,
        option_type=option_type,
    )
    hedge = generate_delta_hedge_recommendation(delta=greeks["delta"], notional=notional)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Implied volatility", format_percent(implied_volatility))
    metric_cols[1].metric("Option price", f"{option_price:.5f} USD")
    metric_cols[2].metric("Option value", f"${option_value:,.0f}")
    metric_cols[3].metric("Portfolio delta", f"{hedge['portfolio_delta']:,.0f} EUR")

    tab_market, tab_surface, tab_pricer, tab_scenarios, tab_hedging = st.tabs(
        ["Market Data", "Volatility Surface", "Option Pricer", "Scenario Analysis", "Hedging"]
    )

    with tab_market:
        st.subheader("Sample EUR/USD Implied Volatility Data")
        st.dataframe(surface.data, use_container_width=True)
        st.subheader("Summary Statistics")
        st.dataframe(surface.data.describe(include="all"), use_container_width=True)

    with tab_surface:
        strike_grid, maturity_grid, vol_grid = surface.surface_grid()
        fig = go.Figure(
            data=[
                go.Surface(
                    x=strike_grid,
                    y=maturity_grid,
                    z=vol_grid,
                    colorscale="Viridis",
                    colorbar={"title": "Vol"},
                )
            ]
        )
        fig.update_layout(
            title="EUR/USD Implied Volatility Surface",
            scene={
                "xaxis_title": "Strike",
                "yaxis_title": "Time to maturity",
                "zaxis_title": "Implied volatility",
            },
            height=560,
            margin={"l": 0, "r": 0, "t": 50, "b": 0},
        )
        st.plotly_chart(fig, use_container_width=True)

        smile_fig = px.line(
            surface.smiles_dataframe(),
            x="strike",
            y="implied_volatility",
            color="maturity",
            markers=True,
            title="Volatility Smiles by Maturity",
        )
        smile_fig.update_layout(yaxis_tickformat=".1%")
        st.plotly_chart(smile_fig, use_container_width=True)

    with tab_pricer:
        left, right = st.columns([1, 1])
        with left:
            st.subheader("Pricing Result")
            pricing_table = pd.DataFrame(
                {
                    "Measure": ["Spot", "Strike", "Maturity", "Domestic rate", "Foreign rate", "Implied volatility", "Option price", "Notional value"],
                    "Value": [
                        f"{spot:.4f}",
                        f"{strike:.4f}",
                        f"{maturity:.4f} years",
                        format_percent(domestic_rate),
                        format_percent(foreign_rate),
                        format_percent(implied_volatility),
                        f"{option_price:.5f} USD per EUR",
                        f"${option_value:,.0f}",
                    ],
                }
            )
            st.dataframe(pricing_table, hide_index=True, use_container_width=True)
        with right:
            st.subheader("Greeks")
            greek_table = pd.DataFrame(
                [
                    ("Delta", greeks["delta"], "Directional exposure to spot"),
                    ("Gamma", greeks["gamma"], "Sensitivity of delta to spot"),
                    ("Vega", greeks["vega"], "Sensitivity to volatility"),
                    ("Theta", greeks["theta"], "Time decay"),
                    ("Domestic rho", greeks["rho_domestic"], "Sensitivity to USD rates"),
                    ("Foreign rho", greeks["rho_foreign"], "Sensitivity to EUR rates"),
                ],
                columns=["Greek", "Value", "Meaning"],
            )
            st.dataframe(greek_table, hide_index=True, use_container_width=True)

    with tab_scenarios:
        st.subheader("Market Scenario Analysis")
        scenario_display = scenarios.copy()
        scenario_display["Position P&L"] = scenario_display["P&L"] * notional
        st.dataframe(scenario_display, hide_index=True, use_container_width=True)

        pnl_fig = px.bar(
            scenario_display[scenario_display["Scenario"] != "Base"],
            x="Scenario",
            y="Position P&L",
            title="Scenario P&L by Position Notional",
        )
        pnl_fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(pnl_fig, use_container_width=True)

    with tab_hedging:
        st.subheader("Delta Hedge Recommendation")
        st.metric("Hedge direction", hedge["hedge_direction"])
        st.metric("Hedge amount", f"EUR {hedge['hedge_amount']:,.0f}")
        st.info(hedge["recommendation"])


if __name__ == "__main__":
    main()
