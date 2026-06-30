"""Simple delta-hedging recommendations for FX option positions."""

from __future__ import annotations


def generate_delta_hedge_recommendation(delta: float, notional: float) -> dict[str, float | str]:
    """Generate a rule-based EUR/USD forward hedge recommendation.

    Delta is expressed per one unit of base currency notional. Multiplying by
    option notional gives the EUR exposure that should be offset with forwards.
    """
    if notional <= 0:
        raise ValueError("notional must be positive.")

    portfolio_delta = delta * notional
    if abs(portfolio_delta) < 1e-8:
        direction = "No hedge"
        hedge_amount = 0.0
        recommendation = "The position is already approximately delta-neutral."
    elif portfolio_delta > 0:
        direction = "Sell EUR/USD forward"
        hedge_amount = abs(portfolio_delta)
        recommendation = (
            "The position has positive EUR delta exposure. "
            f"Sell EUR/USD forward with EUR {hedge_amount:,.0f} notional to become approximately delta-neutral."
        )
    else:
        direction = "Buy EUR/USD forward"
        hedge_amount = abs(portfolio_delta)
        recommendation = (
            "The position has negative EUR delta exposure. "
            f"Buy EUR/USD forward with EUR {hedge_amount:,.0f} notional to become approximately delta-neutral."
        )

    return {
        "portfolio_delta": portfolio_delta,
        "hedge_direction": direction,
        "hedge_amount": hedge_amount,
        "recommendation": recommendation,
    }
