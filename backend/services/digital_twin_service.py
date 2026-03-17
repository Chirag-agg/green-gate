"""Digital factory twin estimator using benchmark emission intensities."""

from __future__ import annotations

import json
import os
from typing import Any


class DigitalTwinService:
    """Estimate emissions from benchmark intensity by product/machinery profile."""

    _intensity_cache: dict[str, float] | None = None

    def __init__(self) -> None:
        if DigitalTwinService._intensity_cache is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "industry_emission_intensity.json",
            )
            with open(data_path, "r", encoding="utf-8") as file:
                loaded: Any = json.load(file)
                if isinstance(loaded, dict):
                    DigitalTwinService._intensity_cache = {
                        str(key).strip().lower(): float(value)
                        for key, value in loaded.items()
                        if isinstance(value, (int, float))
                    }
                else:
                    DigitalTwinService._intensity_cache = {}

    @property
    def intensity_data(self) -> dict[str, float]:
        return DigitalTwinService._intensity_cache or {}

    def estimate_emissions(self, product_type: str, machinery: str, production_volume: float) -> float:
        """Estimate emissions = production volume * benchmark emission intensity."""
        product = (product_type or "").strip().lower()
        machine = (machinery or "").strip().lower()

        lookup_keys = [
            f"{product}_{machine}",
            product,
            machine,
        ]

        intensity = 0.0
        for key in lookup_keys:
            if key in self.intensity_data:
                intensity = float(self.intensity_data[key])
                break

        if intensity <= 0:
            if machine == "electric_arc_furnace":
                intensity = float(self.intensity_data.get("steel_eaf", 1.4))
            elif machine == "blast_furnace":
                intensity = float(self.intensity_data.get("steel_blast_furnace", 2.2))
            elif machine == "rotary_kiln":
                intensity = float(self.intensity_data.get("cement", 0.9))
            elif machine == "smelter":
                intensity = float(self.intensity_data.get("aluminum_smelter", 1.7))
            else:
                intensity = 1.0

        return round(max(float(production_volume), 0.0) * intensity, 4)
