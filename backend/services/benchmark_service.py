"""Benchmark service for expected energy and intensity from similar factories."""

from __future__ import annotations

from typing import Any


class BenchmarkService:
    """Calculates expected benchmark metrics from reference factory peers."""

    def calculate_expected_energy(
        self, similar_factories: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Return average expected electricity and emission intensity for matched peers."""
        if not similar_factories:
            return {
                "expected_energy": 0.0,
                "expected_emission_intensity": 0.0,
            }

        electricity_values = [
            float(factory.get("electricity_kwh", 0)) for factory in similar_factories
        ]
        emission_intensities = [
            float(factory.get("emission_intensity", 0)) for factory in similar_factories
        ]

        expected_energy = sum(electricity_values) / len(electricity_values)
        expected_emission_intensity = sum(emission_intensities) / len(emission_intensities)

        return {
            "expected_energy": round(expected_energy, 2),
            "expected_emission_intensity": round(expected_emission_intensity, 4),
        }
