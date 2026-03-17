"""Machinery model verification service."""

from __future__ import annotations


class MachineryModelService:
    """Checks whether reported energy usage is physically realistic for machinery."""

    machinery_energy_profiles: dict[str, dict[str, float]] = {
        "electric_arc_furnace": {
            "min_kwh_per_ton": 350.0,
            "max_kwh_per_ton": 450.0,
        },
        "blast_furnace": {
            "min_kwh_per_ton": 500.0,
            "max_kwh_per_ton": 700.0,
        },
        "rotary_kiln": {
            "min_kwh_per_ton": 90.0,
            "max_kwh_per_ton": 140.0,
        },
        "smelter": {
            "min_kwh_per_ton": 1200.0,
            "max_kwh_per_ton": 1700.0,
        },
    }

    def calculate_machinery_score(
        self,
        product_type: str,
        machinery: str,
        production_volume: float,
        electricity_kwh: float,
    ) -> float:
        """Return machinery plausibility score in [0, 1]."""
        _ = product_type
        if production_volume <= 0 or electricity_kwh < 0:
            return 0.0

        profile = self.machinery_energy_profiles.get(machinery, None)
        if profile is None:
            return 0.8

        expected_min = production_volume * float(profile["min_kwh_per_ton"])
        if expected_min <= 0:
            return 0.0

        ratio = electricity_kwh / expected_min
        return round(max(0.0, min(1.0, ratio)), 4)
