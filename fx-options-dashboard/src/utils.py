"""Shared validation and numerical helpers for FX option analytics."""

from __future__ import annotations

from math import log, sqrt


VALID_OPTION_TYPES = {"call", "put"}


def normalise_option_type(option_type: str) -> str:
    """Return a lower-case option type after validating it."""
    normalised = option_type.lower().strip()
    if normalised not in VALID_OPTION_TYPES:
        raise ValueError("option_type must be either 'call' or 'put'.")
    return normalised


def validate_option_inputs(
    spot: float,
    strike: float,
    maturity: float,
    volatility: float,
    option_type: str,
) -> str:
    """Validate common option inputs and return the normalised option type."""
    if spot <= 0:
        raise ValueError("spot must be positive.")
    if strike <= 0:
        raise ValueError("strike must be positive.")
    if maturity < 0:
        raise ValueError("maturity cannot be negative.")
    if volatility < 0:
        raise ValueError("volatility cannot be negative.")
    return normalise_option_type(option_type)


def calculate_d1_d2(
    spot: float,
    strike: float,
    maturity: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
) -> tuple[float, float]:
    """Calculate Garman-Kohlhagen d1 and d2 terms."""
    if maturity <= 0 or volatility <= 0:
        raise ValueError("maturity and volatility must be positive to calculate d1 and d2.")

    sigma_root_t = volatility * sqrt(maturity)
    d1 = (
        log(spot / strike)
        + (domestic_rate - foreign_rate + 0.5 * volatility**2) * maturity
    ) / sigma_root_t
    d2 = d1 - sigma_root_t
    return d1, d2
