"""
Product Carbon Aggregation Service — Phase 3.

Aggregates verified factory emissions into a product-level carbon footprint,
computes EU CBAM compliance, and generates a signed product carbon certificate.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from sqlalchemy.orm import Session

from models import (
    FactoryCarbonReport,
    FactoryProfile,
    Product,
    ProductCarbonReport,
    SupplyChainNode,
)

_BENCHMARKS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "eu_cbam_benchmarks.json"
)


def _load_benchmarks() -> dict[str, Any]:
    try:
        with open(_BENCHMARKS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"default": {"benchmark_tco2_per_ton": 1.5, "carbon_price_eur": 90}}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _cbam_risk(ratio: float) -> str:
    """Classify CBAM risk from emission_intensity / eu_benchmark ratio."""
    if ratio <= 0.9:
        return "low"
    if ratio <= 1.1:
        return "moderate"
    if ratio <= 1.5:
        return "high"
    return "critical"


class ProductAggregationService:
    """Aggregate factory emissions → product carbon footprint → EU compliance check."""

    def aggregate_product_carbon(
        self,
        db: Session,
        product: Product,
        product_quantity: float = 1000.0,
    ) -> dict[str, Any]:
        """
        Full aggregation pipeline:
        1. Load FactoryCarbonReport records linked to the product
        2. Sum scope1 / scope2 / scope3 across all factories
        3. Compute emission intensity (tCO₂/ton)
        4. Weighted confidence (heavier factories weigh more)
        5. Compare against EU CBAM sector benchmark
        6. Estimate CBAM tax exposure
        7. SHA-256 product certificate hash
        8. Upsert ProductCarbonReport row
        """
        # ── Step 1: Load factory reports ────────────────────────────────────────
        nodes: list[SupplyChainNode] = (
            db.query(SupplyChainNode)
            .filter(SupplyChainNode.product_id == product.id)  # type: ignore[arg-type]
            .all()
        )
        node_ids = [str(n.id) for n in nodes]

        profiles: list[FactoryProfile] = (
            db.query(FactoryProfile)
            .filter(FactoryProfile.node_id.in_(node_ids))  # type: ignore[arg-type]
            .all()
            if node_ids
            else []
        )
        profile_ids = [str(p.id) for p in profiles]

        reports: list[FactoryCarbonReport] = (
            db.query(FactoryCarbonReport)
            .filter(FactoryCarbonReport.factory_profile_id.in_(profile_ids))  # type: ignore[arg-type]
            .all()
            if profile_ids
            else []
        )

        if not reports:
            raise ValueError(
                "No factory carbon reports found for this product. "
                "Run factory analysis first."
            )

        # ── Step 2: Aggregate emissions ──────────────────────────────────────────
        scope1_total = sum(_to_float(r.scope1_emissions) for r in reports)
        scope2_total = sum(_to_float(r.scope2_emissions) for r in reports)
        scope3_total = sum(_to_float(r.scope3_emissions) for r in reports)
        total_emissions = scope1_total + scope2_total + scope3_total

        # ── Step 3: Weighted product confidence ──────────────────────────────────
        weights = [_to_float(r.total_emissions) for r in reports]
        confidences = [_to_float(r.confidence_score) for r in reports]
        total_weight = sum(weights)
        if total_weight > 0:
            product_confidence = (
                sum(w * c for w, c in zip(weights, confidences)) / total_weight
            )
        else:
            product_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

        # ── Step 4: Emission intensity per ton ───────────────────────────────────
        qty = max(product_quantity, 1.0)
        emission_intensity = total_emissions / qty

        # ── Step 5: EU benchmark comparison ─────────────────────────────────────
        benchmarks = _load_benchmarks()
        sector_key = str(product.sector).lower().strip()  # type: ignore[arg-type]
        sector_data: dict[str, Any] = benchmarks.get(
            sector_key, benchmarks.get("default", {})
        )
        eu_benchmark = _to_float(sector_data.get("benchmark_tco2_per_ton", 1.5), 1.5)
        carbon_price = _to_float(sector_data.get("carbon_price_eur", 90.0), 90.0)

        excess_emissions = max(emission_intensity - eu_benchmark, 0.0)
        ratio = emission_intensity / eu_benchmark if eu_benchmark > 0 else 0.0
        cbam_risk = _cbam_risk(ratio)

        # ── Step 6: CBAM tax estimate ────────────────────────────────────────────
        cbam_tax_per_ton = excess_emissions * carbon_price  # EUR / ton of product

        # ── Step 7: Certificate hash ─────────────────────────────────────────────
        certificate_data = {
            "product_id": str(product.id),
            "product_name": str(product.product_name),  # type: ignore[arg-type]
            "sector": str(product.sector),  # type: ignore[arg-type]
            "scope1_total": round(scope1_total, 4),
            "scope2_total": round(scope2_total, 4),
            "scope3_total": round(scope3_total, 4),
            "total_emissions": round(total_emissions, 4),
            "emission_intensity": round(emission_intensity, 6),
            "product_confidence": round(product_confidence, 6),
            "eu_benchmark": eu_benchmark,
            "cbam_risk": cbam_risk,
            "factory_count": len(reports),
        }
        cert_json = json.dumps(certificate_data, sort_keys=True)
        report_hash = hashlib.sha256(cert_json.encode("utf-8")).hexdigest()

        # ── Step 8: Upsert ProductCarbonReport ───────────────────────────────────
        existing: ProductCarbonReport | None = (
            db.query(ProductCarbonReport)
            .filter(ProductCarbonReport.product_id == product.id)  # type: ignore[arg-type]
            .first()
        )
        if existing is not None:
            from typing import cast as _cast

            rec = _cast(Any, existing)
            rec.scope1_total = scope1_total
            rec.scope2_total = scope2_total
            rec.scope3_total = scope3_total
            rec.total_emissions = total_emissions
            rec.emission_intensity = emission_intensity
            rec.product_confidence = product_confidence
            rec.eu_benchmark = eu_benchmark
            rec.cbam_risk = cbam_risk
            rec.cbam_tax_per_ton = cbam_tax_per_ton
            rec.excess_emissions = excess_emissions
            rec.factory_count = len(reports)
            rec.product_quantity = qty
            rec.report_hash = report_hash
        else:
            new_record = ProductCarbonReport(
                product_id=product.id,
                scope1_total=scope1_total,
                scope2_total=scope2_total,
                scope3_total=scope3_total,
                total_emissions=total_emissions,
                emission_intensity=emission_intensity,
                product_confidence=product_confidence,
                eu_benchmark=eu_benchmark,
                cbam_risk=cbam_risk,
                cbam_tax_per_ton=cbam_tax_per_ton,
                excess_emissions=excess_emissions,
                factory_count=len(reports),
                product_quantity=qty,
                report_hash=report_hash,
            )
            db.add(new_record)

        db.flush()

        # ── Build factory contribution list ──────────────────────────────────────
        profiles_map = {str(p.id): p for p in profiles}
        nodes_map = {str(n.id): n for n in nodes}
        factory_contributions: list[dict[str, Any]] = []

        for report in reports:
            profile = profiles_map.get(str(report.factory_profile_id))
            if profile is None:
                continue
            node = nodes_map.get(str(profile.node_id))
            factory_total = _to_float(report.total_emissions)
            factory_contributions.append(
                {
                    "company": str(profile.company_name or "Unknown"),
                    "location": str(profile.location or "Unknown"),
                    "node_id": str(profile.node_id),
                    "role": str(node.role if node is not None else "manufacturing"),
                    "scope1": _to_float(report.scope1_emissions),
                    "scope2": _to_float(report.scope2_emissions),
                    "scope3": _to_float(report.scope3_emissions),
                    "total": factory_total,
                    "confidence": _to_float(report.confidence_score),
                    "percentage": round(
                        (factory_total / max(total_emissions, 1.0)) * 100, 1
                    ),
                }
            )

        # Sort by total emissions descending for chart readability
        factory_contributions.sort(key=lambda x: x["total"], reverse=True)

        # Dynamic Calculation for India Default Penalty (Money Saved)
        eu_default_penalty = 4.32  # tCO2/t fallback for Indian steel/heavy manufacturing
        
        # Calculate savings: (Penalty - Actual) * EUR Price * Volume
        carbon_price_eur = 90.0
        eur_to_inr = 90.0
        
        # If intensity is higher than penalty, savings is 0
        intensity_diff = max(eu_default_penalty - emission_intensity, 0.0)
        cbam_savings_eur = intensity_diff * carbon_price_eur * qty
        cbam_savings_inr = cbam_savings_eur * eur_to_inr

        return {
            "product_id": str(product.id),
            "product_name": str(product.product_name),  # type: ignore[arg-type]
            "sector": str(product.sector),  # type: ignore[arg-type]
            "scope1_total": scope1_total,
            "scope2_total": scope2_total,
            "scope3_total": scope3_total,
            "total_emissions": total_emissions,
            "emission_intensity": emission_intensity,
            "product_confidence": product_confidence,
            "eu_benchmark": eu_benchmark,
            "eu_default_penalty": eu_default_penalty,
            "cbam_risk": cbam_risk,
            "cbam_tax_per_ton": cbam_tax_per_ton,
            "excess_emissions": excess_emissions,
            "cbam_savings_eur": cbam_savings_eur,
            "cbam_savings_inr": cbam_savings_inr,
            "factory_count": len(reports),
            "product_quantity": qty,
            "report_hash": report_hash,
            "factory_contributions": factory_contributions,
        }
