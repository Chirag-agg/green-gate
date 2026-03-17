"""CBAM tax calculation engine."""

from __future__ import annotations


class CbamEngine:
    """Computes CBAM tax from emission intensity over benchmark."""

    def calculate_cbam_tax(
        self,
        emission_intensity: float,
        eu_benchmark: float,
        cbam_price: float,
        export_volume: float,
    ) -> dict[str, float]:
        """Return CBAM tax for positive intensity excess only."""
        excess = max(0.0, float(emission_intensity) - float(eu_benchmark))
        tax = excess * max(float(cbam_price), 0.0) * max(float(export_volume), 0.0)
        return {"cbam_tax": round(tax, 4)}
