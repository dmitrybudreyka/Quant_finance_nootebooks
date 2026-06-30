"""Scenario analysis engine for FX option prices and Greeks."""

from __future__ import annotations

import pandas as pd

from .garman_kohlhagen import price_fx_option
from .greeks import calculate_greeks


def run_scenario_analysis(
    spot: float,
    strike: float,
    maturity: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    option_type: str,
) -> pd.DataFrame:
    """Run standard spot, volatility, rates, and combined stress scenarios."""
    scenarios = [
        ("Base", 1.00, 0.0000, 0.0000, 0.0000, 0.0000),
        ("Spot +1%", 1.01, 0.0000, 0.0000, 0.0000, 0.0000),
        ("Spot -1%", 0.99, 0.0000, 0.0000, 0.0000, 0.0000),
        ("Vol +1 pp", 1.00, 0.0100, 0.0000, 0.0000, 0.0000),
        ("Vol -1 pp", 1.00, -0.0100, 0.0000, 0.0000, 0.0000),
        ("Rates +25 bps", 1.00, 0.0000, 0.0025, 0.0025, 0.0000),
        ("Rates -25 bps", 1.00, 0.0000, -0.0025, -0.0025, 0.0000),
        ("Spot +1%, Vol +1 pp", 1.01, 0.0100, 0.0000, 0.0000, 0.0000),
        ("Spot -1%, Vol +1 pp", 0.99, 0.0100, 0.0000, 0.0000, 0.0000),
        ("Time -1M", 1.00, 0.0000, 0.0000, 0.0000, -1.0 / 12.0),
    ]

    base_price = price_fx_option(
        spot=spot,
        strike=strike,
        maturity=maturity,
        domestic_rate=domestic_rate,
        foreign_rate=foreign_rate,
        volatility=volatility,
        option_type=option_type,
    )

    rows: list[dict[str, float | str]] = []
    for name, spot_multiplier, vol_shift, rd_shift, rf_shift, maturity_shift in scenarios:
        scenario_spot = spot * spot_multiplier
        scenario_vol = max(volatility + vol_shift, 0.0001)
        scenario_domestic_rate = domestic_rate + rd_shift
        scenario_foreign_rate = foreign_rate + rf_shift
        scenario_maturity = max(maturity + maturity_shift, 1.0 / 365.0)

        option_price = price_fx_option(
            spot=scenario_spot,
            strike=strike,
            maturity=scenario_maturity,
            domestic_rate=scenario_domestic_rate,
            foreign_rate=scenario_foreign_rate,
            volatility=scenario_vol,
            option_type=option_type,
        )
        greeks = calculate_greeks(
            spot=scenario_spot,
            strike=strike,
            maturity=scenario_maturity,
            domestic_rate=scenario_domestic_rate,
            foreign_rate=scenario_foreign_rate,
            volatility=scenario_vol,
            option_type=option_type,
        )

        rows.append(
            {
                "Scenario": name,
                "Spot": scenario_spot,
                "Volatility": scenario_vol,
                "Domestic rate": scenario_domestic_rate,
                "Foreign rate": scenario_foreign_rate,
                "Maturity": scenario_maturity,
                "Option price": option_price,
                "P&L": option_price - base_price,
                "Delta": greeks["delta"],
                "Gamma": greeks["gamma"],
                "Vega": greeks["vega"],
                "Theta": greeks["theta"],
            }
        )

    return pd.DataFrame(rows)
