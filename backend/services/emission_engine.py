"""
Emission calculation engine for GreenGate CBAM compliance.
Implements rule-based carbon footprint calculation using IPCC/CEA emission factors.
"""

import json
import os
from typing import Any


class EmissionEngine:
    """Calculates carbon emissions for Indian MSME exporters."""

    def __init__(self) -> None:
        """Load emission factors from JSON data file."""
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "emission_factors.json"
        )
        with open(data_path, "r", encoding="utf-8") as f:
            self.factors: dict[str, Any] = json.load(f)

    def calculate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate carbon emissions based on input data.

        Args:
            input_data: Dictionary containing company profile and energy consumption data.

        Returns:
            Dictionary with detailed emission breakdown, CBAM liability, and benchmark comparison.
        """
        # Extract input values
        state: str = input_data.get("state", "")
        sector: str = input_data.get("sector", "")
        annual_production_tonnes: float = input_data.get("annual_production_tonnes", 0)
        eu_export_tonnes: float = input_data.get("eu_export_tonnes", 0)

        # Monthly energy inputs
        electricity_kwh: float = input_data.get("electricity_kwh_per_month", 0)
        solar_kwh: float = input_data.get("solar_kwh_per_month", 0)
        coal_kg: float = input_data.get("coal_kg_per_month", 0)
        natural_gas_m3: float = input_data.get("natural_gas_m3_per_month", 0)
        diesel_litres: float = input_data.get("diesel_litres_per_month", 0)
        lpg_litres: float = input_data.get("lpg_litres_per_month", 0)
        furnace_oil_litres: float = input_data.get("furnace_oil_litres_per_month", 0)
        biomass_kg: float = input_data.get("biomass_kg_per_month", 0)

        # Step 1: Get grid emission factor (state-specific or national average)
        grid_states: dict[str, float] = self.factors["grid_electricity"]["states"]
        national_avg: float = self.factors["grid_electricity"]["national_average"]
        grid_factor: float = grid_states.get(state, national_avg)

        # Step 2: Scope 1 — Direct emissions (monthly, then annualize)
        coal_co2_kg_monthly: float = coal_kg * 2.42
        diesel_co2_kg_monthly: float = diesel_litres * 2.68
        gas_co2_kg_monthly: float = natural_gas_m3 * 2.04
        lpg_co2_kg_monthly: float = lpg_litres * 2.98
        furnace_oil_co2_kg_monthly: float = furnace_oil_litres * 3.17
        biomass_co2_kg_monthly: float = biomass_kg * 0.0

        scope1_co2_kg_monthly: float = (
            coal_co2_kg_monthly
            + diesel_co2_kg_monthly
            + gas_co2_kg_monthly
            + lpg_co2_kg_monthly
            + furnace_oil_co2_kg_monthly
            + biomass_co2_kg_monthly
        )
        scope1_co2_kg: float = scope1_co2_kg_monthly * 12

        # Step 3: Scope 2 — Electricity emissions (net of solar)
        net_grid_kwh: float = max(electricity_kwh - solar_kwh, 0)
        scope2_co2_kg: float = net_grid_kwh * grid_factor * 12

        # Step 4: Total annual CO2
        total_co2_kg: float = scope1_co2_kg + scope2_co2_kg
        total_co2_tonnes: float = total_co2_kg / 1000

        scope1_co2_tonnes: float = scope1_co2_kg / 1000
        scope2_co2_tonnes: float = scope2_co2_kg / 1000

        # Step 5: Per-unit emission intensity
        co2_per_tonne_product: float = 0.0
        if annual_production_tonnes > 0:
            co2_per_tonne_product = total_co2_tonnes / annual_production_tonnes

        # Step 6: EU export embedded emissions
        eu_embedded_co2_tonnes: float = co2_per_tonne_product * eu_export_tonnes

        # Step 7: CBAM liability calculation
        eu_carbon_price: float = self.factors.get("eu_carbon_price_eur_per_tonne", 90.0)
        eur_to_inr: float = float(os.getenv("EUR_TO_INR_RATE", "90.0"))

        cbam_liability_eur: float = eu_embedded_co2_tonnes * eu_carbon_price
        cbam_liability_inr: float = cbam_liability_eur * eur_to_inr

        # Step 8: Sector benchmark comparison
        benchmark_data = self.factors["sector_benchmarks"].get(sector, {})
        benchmark: float = benchmark_data.get(
            "benchmark_tco2_per_tonne",
            benchmark_data.get("benchmark_tco2_per_kg", 0),
        )
        vs_benchmark_pct: float = 0.0
        if benchmark > 0:
            vs_benchmark_pct = ((co2_per_tonne_product - benchmark) / benchmark) * 100

        # Build the detailed breakdown
        electricity_co2_tonnes: float = scope2_co2_tonnes
        coal_co2_tonnes: float = (coal_co2_kg_monthly * 12) / 1000
        diesel_co2_tonnes: float = (diesel_co2_kg_monthly * 12) / 1000
        gas_co2_tonnes: float = (gas_co2_kg_monthly * 12) / 1000
        other_co2_tonnes: float = (
            (lpg_co2_kg_monthly + furnace_oil_co2_kg_monthly + biomass_co2_kg_monthly)
            * 12
        ) / 1000

        return {
            "scope1_co2_tonnes": round(scope1_co2_tonnes, 3),
            "scope2_co2_tonnes": round(scope2_co2_tonnes, 3),
            "total_co2_tonnes": round(total_co2_tonnes, 3),
            "co2_per_tonne_product": round(co2_per_tonne_product, 3),
            "eu_embedded_co2_tonnes": round(eu_embedded_co2_tonnes, 3),
            "cbam_liability_eur": round(cbam_liability_eur, 2),
            "cbam_liability_inr": round(cbam_liability_inr, 2),
            "vs_benchmark_pct": round(vs_benchmark_pct, 2),
            "grid_factor_used": grid_factor,
            "breakdown": {
                "electricity_co2_tonnes": round(electricity_co2_tonnes, 3),
                "coal_co2_tonnes": round(coal_co2_tonnes, 3),
                "diesel_co2_tonnes": round(diesel_co2_tonnes, 3),
                "gas_co2_tonnes": round(gas_co2_tonnes, 3),
                "other_co2_tonnes": round(other_co2_tonnes, 3),
            },
        }
