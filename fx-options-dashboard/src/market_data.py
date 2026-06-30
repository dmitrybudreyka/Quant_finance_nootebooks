"""Market data loading utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_VOL_COLUMNS = {
    "maturity",
    "time_to_maturity",
    "strike",
    "implied_volatility",
}


def load_vol_surface_data(path: str | Path) -> pd.DataFrame:
    """Load and validate an implied volatility surface CSV."""
    data = pd.read_csv(path)
    missing = REQUIRED_VOL_COLUMNS.difference(data.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Volatility data is missing required columns: {missing_cols}")

    data = data.copy()
    data["time_to_maturity"] = data["time_to_maturity"].astype(float)
    data["strike"] = data["strike"].astype(float)
    data["implied_volatility"] = data["implied_volatility"].astype(float)

    if (data["time_to_maturity"] <= 0).any():
        raise ValueError("All time_to_maturity values must be positive.")
    if (data["strike"] <= 0).any():
        raise ValueError("All strike values must be positive.")
    if (data["implied_volatility"] <= 0).any():
        raise ValueError("All implied volatility values must be positive.")

    return data.sort_values(["time_to_maturity", "strike"]).reset_index(drop=True)
