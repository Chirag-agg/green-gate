"""Scope-3 emissions estimation engine for supply-chain materials."""

from __future__ import annotations

from typing import Any

from services.supply_chain_service import SupplyChainService


class Scope3Engine:
    """Calculates supply-chain (Scope 3) emissions from material inputs."""

    def __init__(self) -> None:
        self._supply_chain_service = SupplyChainService()

    def calculate_scope3(self, material_inputs: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute Scope 3 emissions and material-wise breakdown."""
        if not material_inputs:
            return {"scope3_emissions": 0.0, "breakdown": []}

        breakdown: list[dict[str, Any]] = []
        total_scope3 = 0.0

        for item in material_inputs:
            material = str(item.get("material", "")).strip()
            country = str(item.get("country", "global")).strip() or "global"
            quantity_tons = float(item.get("quantity_tons", 0.0) or 0.0)

            emission_factor = self._supply_chain_service.lookup_emission_factor(material, country)
            emissions = round(quantity_tons * emission_factor, 4)
            total_scope3 += emissions

            breakdown.append(
                {
                    "material": material,
                    "country": country,
                    "quantity_tons": quantity_tons,
                    "emission_factor": emission_factor,
                    "emissions": emissions,
                }
            )

        return {
            "scope3_emissions": round(total_scope3, 4),
            "breakdown": breakdown,
        }
