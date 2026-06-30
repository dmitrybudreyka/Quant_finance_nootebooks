"""Implied volatility surface construction and interpolation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from .market_data import load_vol_surface_data


class VolatilitySurface:
    """Interpolated EUR/USD implied volatility surface."""

    def __init__(self, csv_path: str | Path) -> None:
        """Load volatility data and create a strike/maturity interpolator."""
        self.data = load_vol_surface_data(csv_path)
        self.maturities = np.array(sorted(self.data["time_to_maturity"].unique()))
        self.strikes = np.array(sorted(self.data["strike"].unique()))
        self._grid = self._build_grid()
        self._interpolator = RegularGridInterpolator(
            (self.maturities, self.strikes),
            self._grid,
            bounds_error=False,
            fill_value=None,
        )

    def _build_grid(self) -> np.ndarray:
        """Pivot market data into a complete maturity by strike matrix."""
        pivot = self.data.pivot(
            index="time_to_maturity",
            columns="strike",
            values="implied_volatility",
        ).reindex(index=self.maturities, columns=self.strikes)

        if pivot.isna().any().any():
            raise ValueError("Volatility surface data must contain a full rectangular grid.")
        return pivot.to_numpy()

    def get_implied_volatility(self, strike: float, maturity: float) -> float:
        """Interpolate implied volatility for an arbitrary strike and maturity."""
        if strike <= 0:
            raise ValueError("strike must be positive.")
        if maturity <= 0:
            raise ValueError("maturity must be positive.")

        clipped_maturity = float(np.clip(maturity, self.maturities.min(), self.maturities.max()))
        clipped_strike = float(np.clip(strike, self.strikes.min(), self.strikes.max()))
        volatility = float(self._interpolator((clipped_maturity, clipped_strike)))

        if volatility <= 0:
            raise ValueError("Interpolated volatility is not positive.")
        return volatility

    def surface_grid(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return meshgrid arrays for plotting the volatility surface."""
        strike_grid, maturity_grid = np.meshgrid(self.strikes, self.maturities)
        return strike_grid, maturity_grid, self._grid

    def smiles_dataframe(self) -> pd.DataFrame:
        """Return long-form volatility data suitable for plotting smiles."""
        return self.data.copy()
