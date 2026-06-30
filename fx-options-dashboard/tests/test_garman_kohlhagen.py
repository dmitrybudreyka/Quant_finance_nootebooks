from __future__ import annotations

from math import exp

import pytest

from src.garman_kohlhagen import price_fx_option


SPOT = 1.10
STRIKE = 1.10
MATURITY = 0.5
DOMESTIC_RATE = 0.05
FOREIGN_RATE = 0.035
VOLATILITY = 0.09


def test_call_price_is_positive() -> None:
    price = price_fx_option(
        SPOT,
        STRIKE,
        MATURITY,
        DOMESTIC_RATE,
        FOREIGN_RATE,
        VOLATILITY,
        "call",
    )

    assert price > 0


def test_put_price_is_positive() -> None:
    price = price_fx_option(
        SPOT,
        STRIKE,
        MATURITY,
        DOMESTIC_RATE,
        FOREIGN_RATE,
        VOLATILITY,
        "put",
    )

    assert price > 0


def test_fx_put_call_parity_holds() -> None:
    call_price = price_fx_option(
        SPOT,
        STRIKE,
        MATURITY,
        DOMESTIC_RATE,
        FOREIGN_RATE,
        VOLATILITY,
        "call",
    )
    put_price = price_fx_option(
        SPOT,
        STRIKE,
        MATURITY,
        DOMESTIC_RATE,
        FOREIGN_RATE,
        VOLATILITY,
        "put",
    )
    parity_value = SPOT * exp(-FOREIGN_RATE * MATURITY) - STRIKE * exp(-DOMESTIC_RATE * MATURITY)

    assert call_price - put_price == pytest.approx(parity_value, abs=1e-10)


def test_invalid_option_type_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="option_type"):
        price_fx_option(
            SPOT,
            STRIKE,
            MATURITY,
            DOMESTIC_RATE,
            FOREIGN_RATE,
            VOLATILITY,
            "digital",
        )
