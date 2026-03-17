"""
Calculator router for GreenGate.
Handles the /api/calculate endpoint that processes emission data and generates reports.
"""

import json
from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from database import get_db
from models import User, CarbonReport, CompanyProfile
from routers.auth import get_current_user
from services.emission_engine import EmissionEngine
from services.ai_recommendations import get_recommendations
from services.industrial_twin_service import IndustrialTwinService
from services.benchmark_service import BenchmarkService
from services.verification_engine import VerificationEngine
from services.machinery_model_service import MachineryModelService
from services.regional_energy_service import RegionalEnergyService
from services.temporal_analysis_service import TemporalAnalysisService
from services.scope3_engine import Scope3Engine
from services.confidence_engine import ConfidenceEngine
from services.reduction_simulator import ReductionSimulator
from services.cbam_engine import CbamEngine
from services.company_intelligence_service import CompanyIntelligenceService
from services.digital_twin_service import DigitalTwinService
from services.rate_limiter import rate_limit

router = APIRouter(prefix="/api", tags=["Calculator"])


# ──── Pydantic Schemas ────


class MaterialInput(BaseModel):
    material: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    quantity_tons: float = Field(ge=0)


class EmissionInput(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    sector: str = Field(min_length=1, max_length=100)
    product_type: Optional[str] = ""
    machinery: Optional[str] = ""
    region: Optional[str] = "India"
    claimed_renewable_share: Optional[float] = Field(default=None, ge=0, le=1)
    state: str = Field(min_length=1, max_length=100)
    annual_production_tonnes: float = Field(gt=0)
    eu_export_tonnes: float = Field(ge=0)
    eu_importer_name: Optional[str] = ""
    factory_location: Optional[str] = ""
    estimated_production: Optional[str] = ""
    export_markets: list[str] = Field(default_factory=list)
    likely_machinery: list[str] = Field(default_factory=list)
    primary_furnace_type: Optional[str] = ""
    machine_manufacturer: Optional[str] = ""
    machine_model: Optional[str] = ""
    year_installed: Optional[int] = Field(default=None, ge=1900, le=2100)
    energy_efficiency_rating: Optional[str] = ""

    electricity_kwh_per_month: float = Field(default=0, ge=0)
    solar_kwh_per_month: float = Field(default=0, ge=0)
    coal_kg_per_month: float = Field(default=0, ge=0)
    natural_gas_m3_per_month: float = Field(default=0, ge=0)
    diesel_litres_per_month: float = Field(default=0, ge=0)
    lpg_litres_per_month: float = Field(default=0, ge=0)
    furnace_oil_litres_per_month: float = Field(default=0, ge=0)
    biomass_kg_per_month: float = Field(default=0, ge=0)

    iron_ore_tonnes_per_month: float = Field(default=0, ge=0)
    scrap_steel_tonnes_per_month: float = Field(default=0, ge=0)
    limestone_tonnes_per_month: float = Field(default=0, ge=0)
    material_inputs: list[MaterialInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_export_not_above_production(self):
        if self.eu_export_tonnes > self.annual_production_tonnes:
            raise ValueError("eu_export_tonnes cannot be greater than annual_production_tonnes")
        return self


class BreakdownResponse(BaseModel):
    electricity_co2_tonnes: float
    coal_co2_tonnes: float
    diesel_co2_tonnes: float
    gas_co2_tonnes: float
    other_co2_tonnes: float


class CalculationResponse(BaseModel):
    scope1_co2_tonnes: float
    scope2_co2_tonnes: float
    total_co2_tonnes: float
    co2_per_tonne_product: float
    eu_embedded_co2_tonnes: float
    cbam_liability_eur: float
    cbam_liability_inr: float
    vs_benchmark_pct: float
    grid_factor_used: float
    breakdown: BreakdownResponse


class CalculateFullResponse(BaseModel):
    report_id: str
    calculation_result: CalculationResponse
    recommendations: list
    expected_energy: float
    deviation_ratio: float
    credibility_score: float
    estimated_emissions: float
    machinery_score: float
    regional_energy_score: float
    temporal_score: float
    scope3_emissions: float
    scope3_breakdown: list[dict[str, object]]
    twin_consistency_score: float
    confidence_score: float
    verification_status: str
    suspicious_fields: list[str]
    requires_evidence: bool
    verification_notes: Optional[str] = None
    warnings: list[str]


class ReductionSimulationRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=100)
    actions: list[str] = Field(default_factory=list)


class ReductionSimulationResponse(BaseModel):
    current_emissions: float
    new_emissions: float
    emission_reduction: float
    cbam_tax_before: float
    cbam_tax_after: float
    savings: float


class CompanyIntelligenceRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    state: str = Field(min_length=1, max_length=100)
    sector: str = Field(min_length=1, max_length=100)


class CompanyIntelligenceResponse(BaseModel):
    discovered_company_profile: dict[str, object]
    sources: list[str]
    suggested_machinery: list[str]
    suggested_production_range: str


def _generate_report_id() -> str:
    """Generate a unique report ID in format GG-{YEAR}-{8-char-uuid}."""
    year = datetime.now(timezone.utc).year
    return f"GG-{year}-{uuid.uuid4().hex[:8].upper()}"


def _infer_twin_profile(sector: str) -> tuple[str, str]:
    normalized = sector.strip().lower()
    if normalized == "steel_eaf":
        return "steel", "electric_arc_furnace"
    if normalized == "steel_bfbof":
        return "steel", "blast_furnace"
    if normalized == "cement":
        return "cement", "rotary_kiln"
    if normalized.startswith("aluminium") or normalized.startswith("aluminum"):
        return "aluminum", "smelter"
    return "steel", "electric_arc_furnace"


def _build_verification_notes(
    machinery: str,
    expected_min: float,
    expected_max: float,
    reported_energy: float,
    deviation_ratio: float,
) -> Optional[str]:
    if expected_max <= 0:
        return None
    if deviation_ratio >= 0.8:
        return None

    if reported_energy < expected_min:
        lower_by = (1.0 - (reported_energy / expected_min)) * 100 if expected_min > 0 else 0.0
        return (
            f"Energy usage is {lower_by:.0f}% lower than expected for {machinery} production. "
            f"Expected: {expected_min:.0f} – {expected_max:.0f} kWh. "
            f"Reported: {reported_energy:.0f} kWh."
        )

    higher_by = ((reported_energy / expected_max) - 1.0) * 100 if expected_max > 0 else 0.0
    return (
        f"Energy usage is {higher_by:.0f}% higher than expected for {machinery} production. "
        f"Expected: {expected_min:.0f} – {expected_max:.0f} kWh. "
        f"Reported: {reported_energy:.0f} kWh."
    )


def _calculate_twin_consistency_score(deviation_ratio: float) -> float:
    """Map deviation ratio to twin consistency score."""
    if 0.8 <= deviation_ratio <= 1.2:
        return 0.9
    if 0.5 <= deviation_ratio < 0.8:
        return 0.6
    if deviation_ratio < 0.5:
        return 0.2
    return 0.6


# ──── Endpoints ────


@router.post("/company-intelligence", response_model=CompanyIntelligenceResponse)
async def company_intelligence(
    data: CompanyIntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:company-intelligence", max_requests=20, window_seconds=60)),
) -> CompanyIntelligenceResponse:
    """Discover company profile signals before emissions reporting workflow."""
    _ = current_user
    service = CompanyIntelligenceService()
    result = await service.discover_company_profile(
        company_name=data.company_name,
        state=data.state,
        sector=data.sector,
    )

    profile_payload = result.get("discovered_company_profile", {})
    sources = result.get("sources", [])

    profile = CompanyProfile(
        company_name=str(profile_payload.get("company_name", data.company_name)),
        scraped_summary=str(profile_payload.get("scraped_summary", "")),
        factory_location=str(profile_payload.get("factory_location", data.state)),
        estimated_production=str(profile_payload.get("estimated_production", "Unknown")),
        likely_machinery=json.dumps(profile_payload.get("likely_machinery", [])),
        export_markets=json.dumps(profile_payload.get("export_markets", [])),
        sources=json.dumps(sources),
    )
    db.add(profile)
    db.commit()

    return CompanyIntelligenceResponse(
        discovered_company_profile=dict(profile_payload),
        sources=[str(source) for source in sources],
        suggested_machinery=[str(item) for item in result.get("suggested_machinery", [])],
        suggested_production_range=str(result.get("suggested_production_range", "Unknown")),
    )


@router.post("/calculate", response_model=CalculateFullResponse)
async def calculate_emissions(
    data: EmissionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:calculate", max_requests=20, window_seconds=60)),
) -> CalculateFullResponse:
    """
    Calculate carbon emissions and generate AI recommendations.
    Saves the report to the database (as draft, not yet blockchain-certified).
    """
    input_dict = data.model_dump()

    # Step 1: Industrial twin benchmark
    inferred_product_type, inferred_machinery = _infer_twin_profile(data.sector)
    product_type = (data.product_type or "").strip() or inferred_product_type
    machinery = (data.machinery or "").strip() or inferred_machinery

    reported_energy = float(data.electricity_kwh_per_month) * 12.0

    twin_service = IndustrialTwinService()
    similar_factories = twin_service.find_similar_factories(
        product_type=product_type,
        machinery=machinery,
        production_volume=float(data.annual_production_tonnes),
    )

    benchmark_service = BenchmarkService()
    benchmark_metrics = benchmark_service.calculate_expected_energy(similar_factories)

    # Step 2: Credibility verification
    verification_engine = VerificationEngine()
    verification_result = verification_engine.verify_energy_claim(
        reported_energy=reported_energy,
        expected_energy=float(benchmark_metrics.get("expected_energy", 0.0)),
    )

    warnings: list[str] = []

    # Hard constraint: physically unrealistic energy for machinery profile
    machinery_profile = MachineryModelService.machinery_energy_profiles.get(machinery, None)
    expected_min = 0.0
    expected_max = 0.0
    if machinery_profile is not None:
        expected_min = float(data.annual_production_tonnes) * float(
            machinery_profile.get("min_kwh_per_ton", 0.0)
        )
        expected_max = float(data.annual_production_tonnes) * float(
            machinery_profile.get("max_kwh_per_ton", 0.0)
        )
        minimum_energy = expected_min
        if minimum_energy > 0 and reported_energy < (0.2 * minimum_energy):
            verification_result["verification_status"] = "invalid_input"
            verification_result["credibility_score"] = min(
                float(verification_result.get("credibility_score", 0.0)),
                0.2,
            )
            warnings.append(
                "Energy consumption is inconsistent with machinery energy requirements."
            )

    # Step 3: Machinery score
    machinery_model_service = MachineryModelService()
    machinery_score = machinery_model_service.calculate_machinery_score(
        product_type=product_type,
        machinery=machinery,
        production_volume=float(data.annual_production_tonnes),
        electricity_kwh=reported_energy,
    )

    if data.claimed_renewable_share is not None:
        claimed_renewable_share = float(data.claimed_renewable_share)
    else:
        electricity_total = float(data.electricity_kwh_per_month) + float(data.solar_kwh_per_month)
        claimed_renewable_share = (
            float(data.solar_kwh_per_month) / electricity_total if electricity_total > 0 else 0.0
        )

    # Step 4: Regional energy score
    regional_energy_service = RegionalEnergyService()
    regional_energy_score = regional_energy_service.calculate_regional_score(
        region=(data.region or "India"),
        claimed_renewable_share=claimed_renewable_share,
    )

    # Step 5: Temporal score
    temporal_analysis_service = TemporalAnalysisService()
    temporal_score = temporal_analysis_service.calculate_temporal_score(
        db=db,
        user_id=current_user.id,
        new_electricity_value=reported_energy,
    )

    # Step 6: Scope-3 inference
    scope3_engine = Scope3Engine()
    scope3_result = scope3_engine.calculate_scope3(
        [item.model_dump() for item in data.material_inputs]
    )

    verification_deviation_ratio = float(verification_result.get("deviation_ratio", 0.0) or 0.0)
    credibility_score = float(verification_result.get("credibility_score", 0.0) or 0.0)

    verification_notes = _build_verification_notes(
        machinery=machinery,
        expected_min=expected_min,
        expected_max=expected_max,
        reported_energy=reported_energy,
        deviation_ratio=verification_deviation_ratio,
    )

    # Step 8: Emission engine
    engine = EmissionEngine()
    try:
        calc_result = engine.calculate(input_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

    # Step 9: Digital twin estimator and deviation analysis
    digital_twin_service = DigitalTwinService()
    estimated_emissions = digital_twin_service.estimate_emissions(
        product_type=data.sector,
        machinery=machinery,
        production_volume=float(data.annual_production_tonnes),
    )

    reported_emissions = float(calc_result.get("total_co2_tonnes", 0.0) or 0.0)
    twin_deviation_ratio = (
        reported_emissions / estimated_emissions if estimated_emissions > 0 else 1.0
    )
    twin_consistency_score = _calculate_twin_consistency_score(twin_deviation_ratio)

    # Step 10: Supply chain score and confidence score
    scope3_breakdown = scope3_result.get("breakdown", [])
    if scope3_breakdown:
        valid_supply_chain_entries = len(
            [entry for entry in scope3_breakdown if float(entry.get("emission_factor", 0.0) or 0.0) > 0]
        )
        supply_chain_score = valid_supply_chain_entries / len(scope3_breakdown)
    else:
        supply_chain_score = 0.8

    confidence_engine = ConfidenceEngine()
    confidence_score = confidence_engine.calculate_confidence_score(
        credibility_score=credibility_score,
        machinery_score=machinery_score,
        regional_energy_score=regional_energy_score,
        temporal_score=temporal_score,
        supply_chain_score=supply_chain_score,
        twin_consistency_score=twin_consistency_score,
    )

    requires_evidence = twin_deviation_ratio < 0.5 or credibility_score < 0.5

    if requires_evidence:
        warnings.append("Supporting evidence is required due to low credibility indicators.")

    # Step 11: AI recommendations
    try:
        recommendations = await get_recommendations(input_dict, calc_result)
    except Exception as e:
        recommendations = []

    # Generate report ID
    report_id = _generate_report_id()

    # Step 12: Save CarbonReport
    full_output_with_scope3 = {
        **calc_result,
        "scope3_emissions": float(scope3_result["scope3_emissions"]),
        "scope3_breakdown": scope3_result["breakdown"],
        "estimated_emissions": estimated_emissions,
        "deviation_ratio": round(twin_deviation_ratio, 4),
        "twin_consistency_score": twin_consistency_score,
        "confidence_score": confidence_score,
        "requires_evidence": requires_evidence,
        "verification_notes": verification_notes,
        "warnings": warnings,
    }

    report = CarbonReport(
        user_id=current_user.id,
        report_id=report_id,
        company_name=data.company_name,
        sector=data.sector,
        state=data.state,
        annual_production_tonnes=data.annual_production_tonnes,
        eu_export_tonnes=data.eu_export_tonnes,
        total_co2_tonnes=calc_result["total_co2_tonnes"],
        scope1_co2_tonnes=calc_result["scope1_co2_tonnes"],
        scope2_co2_tonnes=calc_result["scope2_co2_tonnes"],
        co2_per_tonne_product=calc_result["co2_per_tonne_product"],
        eu_embedded_co2_tonnes=calc_result["eu_embedded_co2_tonnes"],
        cbam_liability_eur=calc_result["cbam_liability_eur"],
        cbam_liability_inr=calc_result["cbam_liability_inr"],
        vs_benchmark_pct=calc_result["vs_benchmark_pct"],
        expected_energy=float(verification_result["expected_energy"]),
        deviation_ratio=round(twin_deviation_ratio, 4),
        credibility_score=float(verification_result["credibility_score"]),
        machinery_score=machinery_score,
        regional_energy_score=regional_energy_score,
        temporal_score=temporal_score,
        scope3_emissions=float(scope3_result["scope3_emissions"]),
        scope3_breakdown=json.dumps(scope3_result["breakdown"]),
        estimated_emissions=estimated_emissions,
        twin_consistency_score=twin_consistency_score,
        confidence_score=confidence_score,
        verification_status=str(verification_result["verification_status"]),
        requires_evidence=requires_evidence,
        evidence_files=json.dumps([]),
        verification_notes=verification_notes,
        full_input_json=json.dumps(input_dict),
        full_output_json=json.dumps(full_output_with_scope3),
        recommendations_json=json.dumps(recommendations),
        is_blockchain_certified=False,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return CalculateFullResponse(
        report_id=report_id,
        calculation_result=CalculationResponse(**calc_result),
        recommendations=recommendations,
        expected_energy=float(verification_result["expected_energy"]),
        deviation_ratio=round(twin_deviation_ratio, 4),
        credibility_score=float(verification_result["credibility_score"]),
        estimated_emissions=estimated_emissions,
        machinery_score=machinery_score,
        regional_energy_score=regional_energy_score,
        temporal_score=temporal_score,
        scope3_emissions=float(scope3_result["scope3_emissions"]),
        scope3_breakdown=scope3_result["breakdown"],
        twin_consistency_score=twin_consistency_score,
        confidence_score=confidence_score,
        verification_status=str(verification_result["verification_status"]),
        suspicious_fields=list(verification_result["suspicious_fields"]),
        requires_evidence=requires_evidence,
        verification_notes=verification_notes,
        warnings=warnings,
    )


@router.post("/simulate-reduction", response_model=ReductionSimulationResponse)
def simulate_reduction(
    data: ReductionSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:simulate-reduction", max_requests=20, window_seconds=60)),
) -> ReductionSimulationResponse:
    """Simulate emission reduction actions and estimate CBAM tax savings."""
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == data.report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    scope3 = float(report.scope3_emissions or 0.0)
    current_emissions = float(report.total_co2_tonnes) + scope3

    reduction_simulator = ReductionSimulator()
    simulation = reduction_simulator.simulate_reduction(
        current_emissions=current_emissions,
        actions=data.actions,
    )

    new_emissions = float(simulation["new_emissions"])
    emission_reduction = float(simulation["emission_reduction"])

    annual_production = float(report.annual_production_tonnes or 0.0)
    current_intensity = current_emissions / annual_production if annual_production > 0 else 0.0
    new_intensity = new_emissions / annual_production if annual_production > 0 else 0.0

    emission_engine = EmissionEngine()
    benchmark_data = emission_engine.factors.get("sector_benchmarks", {}).get(report.sector, {})
    eu_benchmark = float(
        benchmark_data.get("benchmark_tco2_per_tonne", benchmark_data.get("benchmark_tco2_per_kg", 0.0))
        or 0.0
    )
    cbam_price = float(emission_engine.factors.get("eu_carbon_price_eur_per_tonne", 90.0) or 90.0)

    cbam_engine = CbamEngine()
    cbam_tax_before = float(
        cbam_engine.calculate_cbam_tax(
            emission_intensity=current_intensity,
            eu_benchmark=eu_benchmark,
            cbam_price=cbam_price,
            export_volume=float(report.eu_export_tonnes or 0.0),
        )["cbam_tax"]
    )
    cbam_tax_after = float(
        cbam_engine.calculate_cbam_tax(
            emission_intensity=new_intensity,
            eu_benchmark=eu_benchmark,
            cbam_price=cbam_price,
            export_volume=float(report.eu_export_tonnes or 0.0),
        )["cbam_tax"]
    )

    savings = round(max(cbam_tax_before - cbam_tax_after, 0.0), 4)

    return ReductionSimulationResponse(
        current_emissions=round(current_emissions, 4),
        new_emissions=round(new_emissions, 4),
        emission_reduction=round(emission_reduction, 4),
        cbam_tax_before=round(cbam_tax_before, 4),
        cbam_tax_after=round(cbam_tax_after, 4),
        savings=savings,
    )
