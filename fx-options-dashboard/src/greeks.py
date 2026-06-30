"""Analytical Greeks for Garman-Kohlhagen FX options."""

from __future__ import annotations

from math import exp, sqrt

from scipy.stats import norm

from .utils import calculate_d1_d2, validate_option_inputs


def calculate_greeks(
    spot: float,
    strike: float,
    maturity: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    option_type: str,
) -> dict[str, float]:
    """Return analytical FX option Greeks for one unit of base currency notional."""
    option_type = validate_option_inputs(spot, strike, maturity, volatility, option_type)
    if maturity == 0 or volatility == 0:
        return {
            "delta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho_domestic": 0.0,
            "rho_foreign": 0.0,
        }

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
    pdf_d1 = norm.pdf(d1)

    gamma = foreign_df * pdf_d1 / (spot * volatility * sqrt(maturity))
    vega = spot * foreign_df * pdf_d1 * sqrt(maturity)

    if option_type == "call":
        delta = foreign_df * norm.cdf(d1)
        theta = (
            -spot * foreign_df * pdf_d1 * volatility / (2 * sqrt(maturity))
            + foreign_rate * spot * foreign_df * norm.cdf(d1)
            - domestic_rate * strike * domestic_df * norm.cdf(d2)
        )
        rho_domestic = strike * maturity * domestic_df * norm.cdf(d2)
        rho_foreign = -maturity * spot * foreign_df * norm.cdf(d1)
    else:
        delta = -foreign_df * norm.cdf(-d1)
        theta = (
            -spot * foreign_df * pdf_d1 * volatility / (2 * sqrt(maturity))
            - foreign_rate * spot * foreign_df * norm.cdf(-d1)
            + domestic_rate * strike * domestic_df * norm.cdf(-d2)
        )
        rho_domestic = -strike * maturity * domestic_df * norm.cdf(-d2)
        rho_foreign = maturity * spot * foreign_df * norm.cdf(-d1)

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho_domestic": rho_domestic,
        "rho_foreign": rho_foreign,
    }
