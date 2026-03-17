"""Regional energy mix verification service."""

from __future__ import annotations

import json
import os
from typing import Any


class RegionalEnergyService:
    """Compares claimed renewable share against regional benchmark averages."""

    _regional_cache: dict[str, Any] | None = None

    def __init__(self) -> None:
        if RegionalEnergyService._regional_cache is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "regional_energy_mix.json",
            )
            with open(data_path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
                RegionalEnergyService._regional_cache = loaded if isinstance(loaded, dict) else {}

    @property
    def regional_mix(self) -> dict[str, Any]:
        return RegionalEnergyService._regional_cache or {}

    def calculate_regional_score(self, region: str, claimed_renewable_share: float) -> float:
        """Return regional consistency score in [0, 1]."""
        if claimed_renewable_share < 0:
            return 0.0

        region_name = region.strip() if region else "India"
        region_data = self.regional_mix.get(region_name) or self.regional_mix.get("India", {})
        regional_average = float(region_data.get("renewable_share", 0.28))

        difference = abs(claimed_renewable_share - regional_average)
        score = max(0.0, 1.0 - difference)
        return round(score, 4)
