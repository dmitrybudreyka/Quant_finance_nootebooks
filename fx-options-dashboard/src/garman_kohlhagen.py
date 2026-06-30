"""Garman-Kohlhagen pricing model for European FX options."""

from __future__ import annotations

from math import exp

from scipy.stats import norm

from .utils import calculate_d1_d2, validate_option_inputs


def price_fx_option(
    spot: float,
    strike: float,
    maturity: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    option_type: str,
) -> float:
    """Price a European FX option using the Garman-Kohlhagen model.

    For EUR/USD, USD is the domestic currency and EUR is the foreign currency.
    The foreign discount factor captures the yield earned by holding the base
    currency instead of the option.
    """
    option_type = validate_option_inputs(spot, strike, maturity, volatility, option_type)

    if maturity == 0 or volatility == 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        return intrinsic

    d1, d2 = calculate_d1_d2(
        spot=spot,
        strike=strike,
        maturity=maturity,
        domestic_rate=domestic_rate,
        foreign_rate=foreign_rate,
        volatility=volatility,
    )
    foreign_df = exp(-foreign_rate * maturity)
    domestic_df = exp(-domestic_rate * maturity)

    if option_type == "call":
        return spot * foreign_df * norm.cdf(d1) - strike * domestic_df * norm.cdf(d2)
    return strike * domestic_df * norm.cdf(-d2) - spot * foreign_df * norm.cdf(-d1)
