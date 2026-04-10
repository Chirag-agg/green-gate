"""Deterministic demo dataset seeding for reports and product supply chain."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    CarbonReport,
    FactoryCarbonReport,
    FactoryProfile,
    Product,
    ProductCarbonReport,
    SupplyChainEdge,
    SupplyChainNode,
    User,
)
from routers import calculator as calculator_router
from routers.auth import hash_password
from routers.calculator import EmissionInput
from services.product_aggregation_service import ProductAggregationService

DEMO_PASSWORD = "Demo@12345"
DEMO_OWNER_EMAIL = "demo@greengate.local"
DEMO_OWNER_COMPANY = "GreenGate Demo Account"
DEMO_PRODUCT_ID = "demo-product-steel-automotive-component"

DEMO_REPORT_CASES: list[dict[str, Any]] = [
    {
        "report_id": "GG-DEMO-TEXTILE-2026",
        "profile": {
            "state": "Gujarat",
            "sector": "textile",
            "industry": "textile",
            "scale": "small",
            "location": "Gujarat",
            "energy_source": "coal",
            "production_type": "batch",
            "exports_to_eu": True,
        },
        "payload": {
            "company_name": "Arvind Limited (SME unit simulation)",
            "sector": "textile",
            "machinery": "dyeing",
            "state": "Gujarat",
            "region": "India",
            # production_output 12,000 units/month mapped to calibrated annual output tonnes.
            "annual_production_tonnes": 240,
            "eu_export_tonnes": 60,
            "electricity_kwh_per_month": 18000,
            "solar_kwh_per_month": 0,
            # 5 tonnes/month converted to kg/month for engine input.
            "coal_kg_per_month": 5000,
            "natural_gas_m3_per_month": 0,
            "diesel_litres_per_month": 800,
            "lpg_litres_per_month": 0,
            "furnace_oil_litres_per_month": 0,
            "biomass_kg_per_month": 0,
            "material_inputs": [],
        },
    },
    {
        "report_id": "GG-DEMO-STEEL-2026",
        "profile": {
            "state": "Jharkhand",
            "sector": "steel",
            "industry": "steel",
            "scale": "medium",
            "location": "Jharkhand",
            "energy_source": "coal",
            "production_type": "continuous",
            "exports_to_eu": True,
        },
        "payload": {
            "company_name": "Tata Steel Processing Unit (mid-scale simulation)",
            "sector": "steel",
            "machinery": "blast_furnace",
            "state": "Jharkhand",
            "region": "India",
            # production_output 6,000 units/month mapped to calibrated annual output tonnes.
            "annual_production_tonnes": 220,
            "eu_export_tonnes": 90,
            "electricity_kwh_per_month": 25000,
            "solar_kwh_per_month": 0,
            # 12 tonnes/month converted to kg/month for engine input.
            "coal_kg_per_month": 12000,
            "natural_gas_m3_per_month": 0,
            "diesel_litres_per_month": 1500,
            "lpg_litres_per_month": 0,
            "furnace_oil_litres_per_month": 0,
            "biomass_kg_per_month": 0,
            "material_inputs": [],
        },
    },
    {
        "report_id": "GG-DEMO-FOOD-2026",
        "profile": {
            "state": "Karnataka",
            "sector": "food",
            "industry": "food",
            "scale": "micro",
            "location": "Karnataka",
            "energy_source": "electric",
            "production_type": "automated",
            "exports_to_eu": False,
        },
        "payload": {
            "company_name": "Britannia Small Processing Unit (simulation)",
            "sector": "food",
            "machinery": "automated",
            "state": "Karnataka",
            "region": "India",
            # production_output 9,000 units/month mapped to calibrated annual output tonnes.
            "annual_production_tonnes": 350,
            "eu_export_tonnes": 0,
            "electricity_kwh_per_month": 7000,
            "solar_kwh_per_month": 0,
            "coal_kg_per_month": 0,
            "natural_gas_m3_per_month": 0,
            "diesel_litres_per_month": 200,
            "lpg_litres_per_month": 0,
            "furnace_oil_litres_per_month": 0,
            "biomass_kg_per_month": 0,
            "material_inputs": [],
        },
    },
]

DEMO_SUPPLY_CHAIN_NODES: list[dict[str, Any]] = [
    {
        "id": "demo-node-tata-steel",
        "name": "Tata Steel",
        "display_role": "Raw Material Supplier",
        "normalized_role": "raw_material",
        "industry": "steel",
        "location": "Jamshedpur, Jharkhand",
        "emissions_factor": 2.4,
    },
    {
        "id": "demo-node-jsw-steel",
        "name": "JSW Steel",
        "display_role": "Secondary Supplier",
        "normalized_role": "processing",
        "industry": "steel",
        "location": "Vijayanagar, Karnataka",
        "emissions_factor": 2.2,
    },
    {
        "id": "demo-node-bosch-india",
        "name": "Bosch India",
        "display_role": "Component Manufacturer",
        "normalized_role": "manufacturing",
        "industry": "automotive",
        "location": "Bengaluru, Karnataka",
        "emissions_factor": 1.5,
    },
    {
        "id": "demo-node-maruti-suzuki",
        "name": "Maruti Suzuki",
        "display_role": "Assembler",
        "normalized_role": "assembly",
        "industry": "automotive",
        "location": "Gurugram, Haryana",
        "emissions_factor": 1.2,
    },
    {
        "id": "demo-node-dhl-logistics",
        "name": "DHL Logistics",
        "display_role": "Transport",
        "normalized_role": "logistics",
        "industry": "logistics",
        "location": "Mumbai, Maharashtra",
        "emissions_factor": 0.8,
    },
]

DEMO_SUPPLY_CHAIN_EDGES: list[dict[str, str]] = [
    {
        "id": "demo-edge-tata-to-bosch",
        "from": "demo-node-tata-steel",
        "to": "demo-node-bosch-india",
    },
    {
        "id": "demo-edge-jsw-to-bosch",
        "from": "demo-node-jsw-steel",
        "to": "demo-node-bosch-india",
    },
    {
        "id": "demo-edge-bosch-to-maruti",
        "from": "demo-node-bosch-india",
        "to": "demo-node-maruti-suzuki",
    },
    {
        "id": "demo-edge-maruti-to-dhl",
        "from": "demo-node-maruti-suzuki",
        "to": "demo-node-dhl-logistics",
    },
]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _upsert_demo_user(db: Session, user_data: dict[str, Any]) -> User:
    user = db.query(User).filter(User.email == str(user_data["email"])).first()
    if user is None:
        user = User(
            email=str(user_data["email"]),
            hashed_password=hash_password(DEMO_PASSWORD),
            company_name=str(user_data["company_name"]),
            state=str(user_data["state"]),
            sector=str(user_data["sector"]),
            industry=str(user_data["industry"]),
            scale=str(user_data["scale"]),
            location=str(user_data["location"]),
            energy_source=str(user_data["energy_source"]),
            production_type=str(user_data["production_type"]),
            exports_to_eu=bool(user_data["exports_to_eu"]),
        )
        db.add(user)
        db.flush()
        return user

    user.company_name = str(user_data["company_name"])
    user.state = str(user_data["state"])
    user.sector = str(user_data["sector"])
    user.industry = str(user_data["industry"])
    user.scale = str(user_data["scale"])
    user.location = str(user_data["location"])
    user.energy_source = str(user_data["energy_source"])
    user.production_type = str(user_data["production_type"])
    user.exports_to_eu = bool(user_data["exports_to_eu"])
    return user


def _cleanup_legacy_demo_users(db: Session) -> None:
    legacy_users = (
        db.query(User)
        .filter(User.email.like("demo.%@greengate.local"))
        .filter(User.email != DEMO_OWNER_EMAIL)
        .all()
    )
    for legacy in legacy_users:
        db.query(CarbonReport).filter(CarbonReport.user_id == legacy.id).delete(synchronize_session=False)


def _ensure_demo_owner(db: Session) -> User:
    owner_profile = {
        "email": DEMO_OWNER_EMAIL,
        "company_name": DEMO_OWNER_COMPANY,
        "state": "Gujarat",
        "sector": "textile",
        "industry": "textile",
        "scale": "small",
        "location": "India",
        "energy_source": "coal",
        "production_type": "batch",
        "exports_to_eu": True,
    }
    owner = _upsert_demo_user(db, owner_profile)
    db.flush()
    _cleanup_legacy_demo_users(db)
    return owner


def _summarize_report(report: CarbonReport) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(str(report.full_output_json or "{}"))
    except Exception:
        payload = {}

    benchmark = payload.get("benchmark_comparison", {}) if isinstance(payload, dict) else {}
    recommendations = []
    try:
        recommendations = json.loads(str(report.recommendations_json or "[]"))
    except Exception:
        recommendations = []

    return {
        "report_id": str(report.report_id),
        "company": str(report.company_name),
        "sector": str(report.sector),
        "total_co2_tonnes": round(_to_float(report.total_co2_tonnes), 4),
        "intensity": round(_to_float(report.co2_per_tonne_product), 6),
        "cbam_liability_eur": round(_to_float(report.cbam_liability_eur), 4),
        "benchmark_avg": _to_float((benchmark.get("benchmark", {}) or {}).get("avg"), 0.0),
        "benchmark_label": str(benchmark.get("benchmark_label", "unknown")),
        "comparison_basis": str(benchmark.get("comparison_basis", "unknown")),
        "recommendation_1": (
            str(recommendations[0].get("action")) if recommendations and isinstance(recommendations[0], dict) else ""
        ),
        "verified_on_chain": bool(report.is_blockchain_certified),
        "tx_hash": str(report.tx_hash or ""),
    }


async def _seed_demo_reports(db: Session) -> list[dict[str, Any]]:
    report_summaries: list[dict[str, Any]] = []
    owner = _ensure_demo_owner(db)

    for case in DEMO_REPORT_CASES:
        profile = case["profile"]

        owner.state = str(profile["state"])
        owner.sector = str(profile["sector"])
        owner.industry = str(profile["industry"])
        owner.scale = str(profile["scale"])
        owner.location = str(profile["location"])
        owner.energy_source = str(profile["energy_source"])
        owner.production_type = str(profile["production_type"])
        owner.exports_to_eu = bool(profile["exports_to_eu"])

        db.flush()

        db.query(CarbonReport).filter(CarbonReport.report_id == case["report_id"]).delete(
            synchronize_session=False
        )
        db.flush()

        report_id_value = str(case["report_id"])
        original_generator = calculator_router._generate_report_id
        calculator_router._generate_report_id = lambda: report_id_value
        try:
            payload = EmissionInput(**case["payload"])
            await calculator_router.calculate_emissions(
                data=payload,
                db=db,
                current_user=owner,
                _=None,
            )
        finally:
            calculator_router._generate_report_id = original_generator

        existing = db.query(CarbonReport).filter(CarbonReport.report_id == case["report_id"]).first()

        if existing is None:
            raise RuntimeError(f"Failed to seed deterministic report: {case['report_id']}")

        report_summaries.append(_summarize_report(existing))

    return report_summaries


def _split_emissions(total: float, industry: str) -> tuple[float, float, float]:
    normalized = industry.strip().lower()
    if normalized == "steel":
        return round(total * 0.7, 4), round(total * 0.2, 4), round(total * 0.1, 4)
    if normalized == "automotive":
        return round(total * 0.5, 4), round(total * 0.35, 4), round(total * 0.15, 4)
    return round(total * 0.2, 4), round(total * 0.3, 4), round(total * 0.5, 4)


def _purge_existing_product_graph(db: Session, product: Product) -> None:
    node_ids = [str(node.id) for node in db.query(SupplyChainNode).filter(SupplyChainNode.product_id == product.id).all()]
    profile_ids: list[str] = []
    if node_ids:
        profile_ids = [
            str(profile.id)
            for profile in db.query(FactoryProfile).filter(FactoryProfile.node_id.in_(node_ids)).all()  # type: ignore[arg-type]
        ]

    if profile_ids:
        db.query(FactoryCarbonReport).filter(FactoryCarbonReport.factory_profile_id.in_(profile_ids)).delete(  # type: ignore[arg-type]
            synchronize_session=False
        )
    if node_ids:
        db.query(FactoryProfile).filter(FactoryProfile.node_id.in_(node_ids)).delete(  # type: ignore[arg-type]
            synchronize_session=False
        )

    db.query(ProductCarbonReport).filter(ProductCarbonReport.product_id == product.id).delete(synchronize_session=False)
    db.query(SupplyChainEdge).filter(SupplyChainEdge.product_id == product.id).delete(synchronize_session=False)
    db.query(SupplyChainNode).filter(SupplyChainNode.product_id == product.id).delete(synchronize_session=False)
    db.query(Product).filter(Product.id == product.id).delete(synchronize_session=False)


def _seed_supply_chain_product(db: Session, owner: User) -> dict[str, Any]:
    existing_product = db.query(Product).filter(Product.id == DEMO_PRODUCT_ID).first()
    if existing_product is not None:
        _purge_existing_product_graph(db, existing_product)
        db.flush()
        db.expire_all()

    product = Product(
        id=DEMO_PRODUCT_ID,
        user_id=owner.id,
        created_by=owner.id,
        product_name="Steel Automotive Component (Export to EU)",
        sector="steel",
    )
    db.add(product)

    for index, node_data in enumerate(DEMO_SUPPLY_CHAIN_NODES):
        metadata = {
            "display_role": node_data["display_role"],
            "industry": node_data["industry"],
            "emissions_factor": node_data["emissions_factor"],
        }
        node = SupplyChainNode(
            id=str(node_data["id"]),
            product_id=product.id,
            name=str(node_data["name"]),
            company_name=str(node_data["name"]),
            role=str(node_data["normalized_role"]),
            location=str(node_data["location"]),
            source_url="",
            discovered_source="curated_demo_dataset",
            confidence_score=0.98,
            metadata_json=json.dumps(metadata),
        )
        db.add(node)

        profile_id = f"demo-profile-{index + 1}"
        profile = FactoryProfile(
            id=profile_id,
            node_id=node.id,
            company_name=str(node_data["name"]),
            location=str(node_data["location"]),
            machinery_type=str(node_data["industry"]),
            production_capacity=1000.0,
            energy_sources=json.dumps(["electricity", "coal"]),
            scraped_sources=json.dumps(["curated_demo_dataset"]),
            confidence=0.95,
        )
        db.add(profile)

        total = round(float(node_data["emissions_factor"]) * 1000.0, 4)
        scope1, scope2, scope3 = _split_emissions(total, str(node_data["industry"]))

        db.add(
            FactoryCarbonReport(
                id=f"demo-factory-report-{index + 1}",
                factory_profile_id=profile.id,
                scope1_emissions=scope1,
                scope2_emissions=scope2,
                scope3_emissions=scope3,
                total_emissions=round(scope1 + scope2 + scope3, 4),
                confidence_score=0.96,
                verification_status="verified",
            )
        )

    for edge in DEMO_SUPPLY_CHAIN_EDGES:
        db.add(
            SupplyChainEdge(
                id=str(edge["id"]),
                product_id=product.id,
                from_node_id=str(edge["from"]),
                to_node_id=str(edge["to"]),
                relation="supplies_to",
                confidence=0.98,
            )
        )

    db.flush()

    aggregated = ProductAggregationService().aggregate_product_carbon(
        db=db,
        product=product,
        product_quantity=1000.0,
    )

    return {
        "product_id": str(product.id),
        "product_name": str(product.product_name),
        "total_emissions": round(_to_float(aggregated.get("total_emissions")), 4),
        "emission_intensity": round(_to_float(aggregated.get("emission_intensity")), 6),
        "cbam_risk": str(aggregated.get("cbam_risk", "unknown")),
        "nodes": [
            {
                "name": str(node["name"]),
                "role": str(node["display_role"]),
                "industry": str(node["industry"]),
                "emissions_factor": float(node["emissions_factor"]),
            }
            for node in DEMO_SUPPLY_CHAIN_NODES
        ],
        "edges": [
            f"{next(n['name'] for n in DEMO_SUPPLY_CHAIN_NODES if n['id'] == edge['from'])} -> "
            f"{next(n['name'] for n in DEMO_SUPPLY_CHAIN_NODES if n['id'] == edge['to'])}"
            for edge in DEMO_SUPPLY_CHAIN_EDGES
        ],
    }


async def seed_demo_data() -> dict[str, Any]:
    """Seed deterministic demo reports and product graph; returns validation summary."""
    db = SessionLocal()
    previous_offline_only = os.getenv("RECOMMENDATIONS_OFFLINE_ONLY")
    previous_mock_blockchain = os.getenv("MOCK_BLOCKCHAIN")

    os.environ["RECOMMENDATIONS_OFFLINE_ONLY"] = "true"
    os.environ["MOCK_BLOCKCHAIN"] = "true"

    try:
        report_summaries = await _seed_demo_reports(db)

        owner = db.query(User).filter(User.email == DEMO_OWNER_EMAIL).first()
        if owner is None:
            raise RuntimeError("Demo owner user missing after report seeding")

        supply_chain_summary = _seed_supply_chain_product(db, owner)
        db.commit()

        ordered = sorted(report_summaries, key=lambda item: _to_float(item.get("total_co2_tonnes")), reverse=True)
        emissions_order = [str(item["sector"]).lower() for item in ordered]

        return {
            "reports": report_summaries,
            "validation": {
                "reports_are_distinct": len({item["report_id"] for item in report_summaries}) == 3,
                "emissions_order": emissions_order,
                "expected_order_match": emissions_order == ["steel", "textile", "food"],
                "cbam_triggered": {
                    str(item["sector"]).lower(): _to_float(item.get("cbam_liability_eur")) > 0.0
                    for item in report_summaries
                },
            },
            "supply_chain": supply_chain_summary,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if previous_offline_only is None:
            os.environ.pop("RECOMMENDATIONS_OFFLINE_ONLY", None)
        else:
            os.environ["RECOMMENDATIONS_OFFLINE_ONLY"] = previous_offline_only

        if previous_mock_blockchain is None:
            os.environ.pop("MOCK_BLOCKCHAIN", None)
        else:
            os.environ["MOCK_BLOCKCHAIN"] = previous_mock_blockchain

        db.close()


if __name__ == "__main__":
    summary = asyncio.run(seed_demo_data())
    print(json.dumps(summary, indent=2))
