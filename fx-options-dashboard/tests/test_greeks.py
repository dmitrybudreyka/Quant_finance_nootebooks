from __future__ import annotations

from src.greeks import calculate_greeks


def test_call_delta_is_between_zero_and_one() -> None:
    greeks = calculate_greeks(
        spot=1.10,
        strike=1.10,
        maturity=0.5,
        domestic_rate=0.05,
        foreign_rate=0.035,
        volatility=0.09,
        option_type="call",
    )

    assert 0 < greeks["delta"] < 1


def test_put_delta_is_between_minus_one_and_zero() -> None:
    greeks = calculate_greeks(
        spot=1.10,
        strike=1.10,
        maturity=0.5,
        domestic_rate=0.05,
        foreign_rate=0.035,
        volatility=0.09,
        option_type="put",
    )

    assert -1 < greeks["delta"] < 0


def test_gamma_and_vega_are_positive() -> None:
    greeks = calculate_greeks(
        spot=1.10,
        strike=1.10,
        maturity=0.5,
        domestic_rate=0.05,
        foreign_rate=0.035,
        volatility=0.09,
        option_type="call",
    )

    assert greeks["gamma"] > 0
    assert greeks["vega"] > 0
