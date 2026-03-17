"""Supply-chain emission factor lookup service."""

from __future__ import annotations

import json
import os
from typing import Any


class SupplyChainService:
    """Resolves material emission factors by material and country."""

    _factors_cache: dict[str, dict[str, float]] | None = None

    def __init__(self) -> None:
        if SupplyChainService._factors_cache is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "material_emission_factors.json",
            )
            with open(data_path, "r", encoding="utf-8") as file:
                loaded: Any = json.load(file)
                normalized: dict[str, dict[str, float]] = {}

                if isinstance(loaded, dict):
                    for material, country_map in loaded.items():
                        if not isinstance(country_map, dict):
                            continue
                        material_key = str(material).strip().lower()
                        normalized[material_key] = {
                            str(country).strip().lower(): float(value)
                            for country, value in country_map.items()
                            if isinstance(value, (int, float))
                        }

                SupplyChainService._factors_cache = normalized

    @property
    def factors(self) -> dict[str, dict[str, float]]:
        return SupplyChainService._factors_cache or {}

    def lookup_emission_factor(self, material: str, country: str) -> float:
        """Return emission factor by material/country, falling back to global if needed."""
        material_key = (material or "").strip().lower()
        country_key = (country or "").strip().lower()

        country_factors = self.factors.get(material_key, {})
        if country_key in country_factors:
            return float(country_factors[country_key])

        if "global" in country_factors:
            return float(country_factors["global"])

        return 0.0
