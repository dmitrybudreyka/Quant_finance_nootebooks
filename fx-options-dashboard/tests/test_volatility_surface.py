from __future__ import annotations

from pathlib import Path

from src.scenario_analysis import run_scenario_analysis
from src.volatility_surface import VolatilitySurface


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_vol_surface.csv"


def test_interpolated_volatility_is_positive() -> None:
    surface = VolatilitySurface(DATA_PATH)

    volatility = surface.get_implied_volatility(strike=1.11, maturity=0.30)

    assert volatility > 0


def test_surface_grid_has_expected_shape() -> None:
    surface = VolatilitySurface(DATA_PATH)

    strike_grid, maturity_grid, vol_grid = surface.surface_grid()

    assert strike_grid.shape == maturity_grid.shape == vol_grid.shape


def test_scenario_analysis_returns_non_empty_dataframe() -> None:
    scenarios = run_scenario_analysis(
        spot=1.10,
        strike=1.10,
        maturity=0.5,
        domestic_rate=0.05,
        foreign_rate=0.035,
        volatility=0.09,
        option_type="call",
    )

    assert not scenarios.empty
    assert {"Scenario", "Option price", "P&L", "Delta", "Gamma", "Vega", "Theta"}.issubset(
        scenarios.columns
    )
