"""Products router for supply chain discovery and traceability graph persistence."""

from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    FactoryCarbonReport,
    FactoryProfile,
    Product,
    ProductCarbonReport,
    SupplyChainEdge,
    SupplyChainNode,
    User,
)
from routers.auth import get_current_user
from services.factory_intelligence_service import FactoryIntelligenceService
from services.product_aggregation_service import ProductAggregationService
from services.product_supply_chain_service import ProductSupplyChainService
from services.rate_limiter import rate_limit
from services.supply_chain_optimizer import SupplyChainOptimizer

router = APIRouter(prefix="/api/products", tags=["Products"])


class ProductDiscoverRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    sector: str = Field(min_length=1, max_length=100)
    company_name: str = Field(default="", max_length=200)
    potential_supplier: str = Field(default="", max_length=200)


class SearchQueryPlanResponse(BaseModel):
    company_query: str
    supplier_query: str


class SupplyChainNodeResponse(BaseModel):
    id: str
    company_name: str
    role: str
    location: str
    discovered_source: str
    confidence_score: float


class SupplyChainEdgeResponse(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    relation: str
    confidence: float


class ProductDiscoverResponse(BaseModel):
    product_id: str
    product_name: str
    sector: str
    nodes: list[SupplyChainNodeResponse]
    edges: list[SupplyChainEdgeResponse]
    sources: list[str]
    query_plan: SearchQueryPlanResponse | None = None


class FactoryEmissionResponse(BaseModel):
    scope1: float
    scope2: float
    scope3: float
    total: float


class FactoryAnalysisItemResponse(BaseModel):
    factory_profile_id: str
    node_id: str
    company: str
    location: str
    machinery: str
    production_capacity: float
    energy_sources: list[str]
    scraped_sources: list[str]
    confidence: float
    verification_status: str
    emissions: FactoryEmissionResponse


class FactoryContributionResponse(BaseModel):
    company: str
    location: str
    node_id: str
    role: str
    scope1: float
    scope2: float
    scope3: float
    total: float
    confidence: float
    percentage: float


class ProductCarbonReportResponse(BaseModel):
    product_id: str
    product_name: str
    sector: str
    scope1_total: float
    scope2_total: float
    scope3_total: float
    total_emissions: float
    emission_intensity: float
    product_confidence: float
    eu_benchmark: float
    eu_default_penalty: float
    cbam_risk: str
    cbam_tax_per_ton: float
    excess_emissions: float
    cbam_savings_eur: float
    cbam_savings_inr: float
    factory_count: int
    product_quantity: float
    report_hash: str
    factory_contributions: list[FactoryContributionResponse]


class ProductDetailResponse(BaseModel):
    product_id: str
    product_name: str
    sector: str
    nodes: list[SupplyChainNodeResponse]
    edges: list[SupplyChainEdgeResponse]
    factory_analysis: list[FactoryAnalysisItemResponse]
    carbon_report: ProductCarbonReportResponse | None = None


class AnalyzeFactoriesResponse(BaseModel):
    product_id: str
    factories: list[FactoryAnalysisItemResponse]


class OptimizeRequest(BaseModel):
    target_factory: str | None = None
    product_quantity: float = Field(default=1000.0, gt=0)


class AttestRequest(BaseModel):
    machinery_type: str = Field(min_length=1, max_length=100)
    production_capacity: float = Field(gt=0)
    energy_sources: list[str] = Field(default_factory=list)
    has_uploaded_evidence: bool = Field(default=True)


class SuggestedSupplierResponse(BaseModel):
    company: str
    location: str
    machinery: str
    estimated_emissions: float
    estimated_emission_intensity: float
    confidence: float
    source: str
    optimized_total_emissions: float
    optimized_intensity: float
    optimized_cbam_tax_total: float
    emission_reduction: float
    cbam_savings: float
    optimized_cbam_risk: str


class CurrentFactoryResponse(BaseModel):
    factory_profile_id: str
    node_id: str
    company: str
    location: str
    machinery: str
    role: str
    total_emissions: float
    share: float
    confidence: float


class OptimizeResponse(BaseModel):
    product_id: str
    product_name: str
    target_factory: str
    target_factory_share: float
    current_emissions: float
    optimized_emissions: float
    emission_reduction: float
    current_intensity: float
    optimized_intensity: float
    eu_benchmark: float
    current_cbam_tax: float
    optimized_cbam_tax: float
    cbam_savings: float
    current_cbam_risk: str
    optimized_cbam_risk: str
    current_confidence: float
    optimized_confidence: float
    product_quantity: float
    current_factories: list[CurrentFactoryResponse]
    suggested_suppliers: list[SuggestedSupplierResponse]


class SupplyChainNodeInput(BaseModel):
    id: str | None = None
    company_name: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    discovered_source: str = ""
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)


class SupplyChainEdgeInput(BaseModel):
    from_node_id: str
    to_node_id: str
    relation: str = Field(default="supplies_to", min_length=1, max_length=50)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class ConfirmSupplyChainRequest(BaseModel):
    nodes: list[SupplyChainNodeInput] = Field(default_factory=list)
    edges: list[SupplyChainEdgeInput] = Field(default_factory=list)


ALLOWED_ROLES = {"raw_material", "processing", "manufacturing", "assembly", "logistics"}


def _serialize_nodes(nodes: list[SupplyChainNode]) -> list[SupplyChainNodeResponse]:
    return [
        SupplyChainNodeResponse(
            id=str(node.id),
            company_name=str((cast(Any, node.company_name) or node.name)),
            role=str(node.role if str(node.role) in ALLOWED_ROLES else "manufacturing"),
            location=str(node.location or "Unknown"),
            discovered_source=str((cast(Any, node.discovered_source) or node.source_url or "")),
            confidence_score=float((cast(Any, node.confidence_score) or 0.75)),
        )
        for node in nodes
    ]


def _serialize_edges(edges: list[SupplyChainEdge]) -> list[SupplyChainEdgeResponse]:
    return [
        SupplyChainEdgeResponse(
            id=str(edge.id),
            from_node_id=str(edge.from_node_id),
            to_node_id=str(edge.to_node_id),
            relation=str(edge.relation),
            confidence=float(cast(Any, edge.confidence) or 0.75),
        )
        for edge in edges
    ]


def _serialize_factory_analysis(
    profiles: list[FactoryProfile],
    reports_map: dict[str, FactoryCarbonReport],
) -> list[FactoryAnalysisItemResponse]:
    result: list[FactoryAnalysisItemResponse] = []
    for profile in profiles:
        report = reports_map.get(str(profile.id))
        energy_sources_raw = str(profile.energy_sources or "[]")
        scraped_sources_raw = str(profile.scraped_sources or "[]")
        try:
            energy_sources = [str(item) for item in json.loads(energy_sources_raw)]
        except Exception:
            energy_sources = []
        try:
            scraped_sources = [str(item) for item in json.loads(scraped_sources_raw)]
        except Exception:
            scraped_sources = []

        result.append(
            FactoryAnalysisItemResponse(
                factory_profile_id=str(profile.id),
                node_id=str(profile.node_id),
                company=str(profile.company_name or "Unknown"),
                location=str(profile.location or "Unknown"),
                machinery=str(profile.machinery_type or "unknown"),
                production_capacity=float(cast(Any, profile.production_capacity) or 0.0),
                energy_sources=energy_sources,
                scraped_sources=scraped_sources,
                confidence=float((cast(Any, report.confidence_score) if report else cast(Any, profile.confidence)) or 0.0),
                verification_status=str((cast(Any, report.verification_status) if report else "unknown") or "unknown"),
                emissions=FactoryEmissionResponse(
                    scope1=float(cast(Any, report.scope1_emissions) or 0.0) if report else 0.0,
                    scope2=float(cast(Any, report.scope2_emissions) or 0.0) if report else 0.0,
                    scope3=float(cast(Any, report.scope3_emissions) or 0.0) if report else 0.0,
                    total=float(cast(Any, report.total_emissions) or 0.0) if report else 0.0,
                ),
            )
        )
    return result


def _serialize_product_carbon_report(
    pcr: ProductCarbonReport,
    profiles: list[FactoryProfile],
    reports_map: dict[str, FactoryCarbonReport],
    nodes: list[SupplyChainNode],
    product_name: str,
    sector: str,
) -> ProductCarbonReportResponse:
    """Build ProductCarbonReportResponse from a persisted ProductCarbonReport row."""
    nodes_map = {str(n.id): n for n in nodes}
    total_emissions = float(cast(Any, pcr.total_emissions) or 0.0)

    factory_contributions: list[FactoryContributionResponse] = []
    for profile in profiles:
        report = reports_map.get(str(profile.id))
        if report is None:
            continue
        node = nodes_map.get(str(profile.node_id))
        factory_total = float(cast(Any, report.total_emissions) or 0.0)
        factory_contributions.append(
            FactoryContributionResponse(
                company=str(profile.company_name or "Unknown"),
                location=str(profile.location or "Unknown"),
                node_id=str(profile.node_id),
                role=str(node.role if node is not None else "manufacturing"),
                scope1=float(cast(Any, report.scope1_emissions) or 0.0),
                scope2=float(cast(Any, report.scope2_emissions) or 0.0),
                scope3=float(cast(Any, report.scope3_emissions) or 0.0),
                total=factory_total,
                confidence=float(cast(Any, report.confidence_score) or 0.0),
                percentage=round((factory_total / max(total_emissions, 1.0)) * 100, 1),
            )
        )
    factory_contributions.sort(key=lambda x: x.total, reverse=True)

    # Dynamic Calculation for India Default Penalty (Money Saved)
    # The default EU penalty assigned if no verified MSME data is submitted
    eu_default_penalty = 4.32  # tCO2/t fallback for Indian steel/heavy manufacturing
    emission_intensity = float(cast(Any, pcr.emission_intensity) or 0.0)
    qty = float(cast(Any, pcr.product_quantity) or 1000.0)
    
    # Calculate savings: (Penalty - Actual) * EUR Price * Volume
    carbon_price_eur = 90.0
    eur_to_inr = 90.0
    
    # If intensity is higher than penalty, savings is 0
    intensity_diff = max(eu_default_penalty - emission_intensity, 0.0)
    cbam_savings_eur = intensity_diff * carbon_price_eur * qty
    cbam_savings_inr = cbam_savings_eur * eur_to_inr

    return ProductCarbonReportResponse(
        product_id=str(pcr.product_id),
        product_name=product_name,
        sector=sector,
        scope1_total=float(cast(Any, pcr.scope1_total) or 0.0),
        scope2_total=float(cast(Any, pcr.scope2_total) or 0.0),
        scope3_total=float(cast(Any, pcr.scope3_total) or 0.0),
        total_emissions=total_emissions,
        emission_intensity=emission_intensity,
        product_confidence=float(cast(Any, pcr.product_confidence) or 0.0),
        eu_benchmark=float(cast(Any, pcr.eu_benchmark) or 0.0),
        eu_default_penalty=eu_default_penalty,
        cbam_risk=str(cast(Any, pcr.cbam_risk) or "unknown"),
        cbam_tax_per_ton=float(cast(Any, pcr.cbam_tax_per_ton) or 0.0),
        excess_emissions=float(cast(Any, pcr.excess_emissions) or 0.0),
        cbam_savings_eur=cbam_savings_eur,
        cbam_savings_inr=cbam_savings_inr,
        factory_count=int(cast(Any, pcr.factory_count) or 0),
        product_quantity=qty,
        report_hash=str(cast(Any, pcr.report_hash) or ""),
        factory_contributions=factory_contributions,
    )


def _serialize_optimize_response(payload: dict[str, Any]) -> OptimizeResponse:
    current_factories = [
        CurrentFactoryResponse(
            factory_profile_id=str(item.get("factory_profile_id", "")),
            node_id=str(item.get("node_id", "")),
            company=str(item.get("company", "Unknown")),
            location=str(item.get("location", "Unknown")),
            machinery=str(item.get("machinery", "unknown")),
            role=str(item.get("role", "manufacturing")),
            total_emissions=float(item.get("total_emissions", 0.0) or 0.0),
            share=float(item.get("share", 0.0) or 0.0),
            confidence=float(item.get("confidence", 0.0) or 0.0),
        )
        for item in payload.get("current_factories", [])
    ]

    suggested_suppliers = [
        SuggestedSupplierResponse(
            company=str(item.get("company", "Unknown Supplier")),
            location=str(item.get("location", "Unknown")),
            machinery=str(item.get("machinery", "unknown")),
            estimated_emissions=float(item.get("estimated_emissions", 0.0) or 0.0),
            estimated_emission_intensity=float(item.get("estimated_emission_intensity", 0.0) or 0.0),
            confidence=float(item.get("confidence", 0.0) or 0.0),
            source=str(item.get("source", "")),
            optimized_total_emissions=float(item.get("optimized_total_emissions", 0.0) or 0.0),
            optimized_intensity=float(item.get("optimized_intensity", 0.0) or 0.0),
            optimized_cbam_tax_total=float(item.get("optimized_cbam_tax_total", 0.0) or 0.0),
            emission_reduction=float(item.get("emission_reduction", 0.0) or 0.0),
            cbam_savings=float(item.get("cbam_savings", 0.0) or 0.0),
            optimized_cbam_risk=str(item.get("optimized_cbam_risk", "unknown")),
        )
        for item in payload.get("suggested_suppliers", [])
    ]

    return OptimizeResponse(
        product_id=str(payload.get("product_id", "")),
        product_name=str(payload.get("product_name", "")),
        target_factory=str(payload.get("target_factory", "")),
        target_factory_share=float(payload.get("target_factory_share", 0.0) or 0.0),
        current_emissions=float(payload.get("current_emissions", 0.0) or 0.0),
        optimized_emissions=float(payload.get("optimized_emissions", 0.0) or 0.0),
        emission_reduction=float(payload.get("emission_reduction", 0.0) or 0.0),
        current_intensity=float(payload.get("current_intensity", 0.0) or 0.0),
        optimized_intensity=float(payload.get("optimized_intensity", 0.0) or 0.0),
        eu_benchmark=float(payload.get("eu_benchmark", 0.0) or 0.0),
        current_cbam_tax=float(payload.get("current_cbam_tax", 0.0) or 0.0),
        optimized_cbam_tax=float(payload.get("optimized_cbam_tax", 0.0) or 0.0),
        cbam_savings=float(payload.get("cbam_savings", 0.0) or 0.0),
        current_cbam_risk=str(payload.get("current_cbam_risk", "unknown")),
        optimized_cbam_risk=str(payload.get("optimized_cbam_risk", "unknown")),
        current_confidence=float(payload.get("current_confidence", 0.0) or 0.0),
        optimized_confidence=float(payload.get("optimized_confidence", 0.0) or 0.0),
        product_quantity=float(payload.get("product_quantity", 1000.0) or 1000.0),
        current_factories=current_factories,
        suggested_suppliers=suggested_suppliers,
    )


@router.post("/discover", response_model=ProductDiscoverResponse)
async def discover_product_supply_chain(
    data: ProductDiscoverRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-discover", max_requests=20, window_seconds=60)),
) -> ProductDiscoverResponse:
    """Discover and persist supply chain graph for a product."""
    service = ProductSupplyChainService()
    discovery = await service.discover_supply_chain(
        product_name=data.product_name,
        sector=data.sector,
        company_name=data.company_name,
        potential_supplier=data.potential_supplier,
    )

    nodes_payload = discovery.get("nodes", [])
    edges_payload = discovery.get("edges", [])
    sources_payload = [str(source) for source in discovery.get("sources", [])]

    if not nodes_payload:
        raise HTTPException(status_code=422, detail="Unable to discover supply chain entities")

    product = Product(
        user_id=current_user.id,
        created_by=current_user.id,
        product_name=data.product_name,
        sector=data.sector,
    )
    db.add(product)
    db.flush()

    persisted_nodes: list[SupplyChainNode] = []
    for node in nodes_payload:
        record = SupplyChainNode(
            product_id=product.id,
            name=str(node.get("name", "Unknown")),
            company_name=str(node.get("name", "Unknown")),
            role=str(node.get("role", "manufacturing")),
            location=str(node.get("location", "Unknown")),
            source_url=str(node.get("source_url", "")),
            discovered_source=str(node.get("discovered_source", node.get("source_url", ""))),
            confidence_score=float(node.get("confidence_score", 0.75) or 0.75),
            metadata_json=None,
        )
        db.add(record)
        db.flush()
        persisted_nodes.append(record)

    persisted_edges: list[SupplyChainEdge] = []
    for edge in edges_payload:
        from_index = int(edge.get("from_index", -1))
        to_index = int(edge.get("to_index", -1))
        if from_index < 0 or to_index < 0:
            continue
        if from_index >= len(persisted_nodes) or to_index >= len(persisted_nodes):
            continue

        edge_record = SupplyChainEdge(
            product_id=product.id,
            from_node_id=persisted_nodes[from_index].id,
            to_node_id=persisted_nodes[to_index].id,
            relation=str(edge.get("relation", "supplies_to")),
            confidence=float(edge.get("confidence", 0.75) or 0.75),
        )
        db.add(edge_record)
        db.flush()
        persisted_edges.append(edge_record)

    db.commit()

    return ProductDiscoverResponse(
        product_id=str(product.id),
        product_name=str(product.product_name),
        sector=str(product.sector),
        nodes=_serialize_nodes(persisted_nodes),
        edges=_serialize_edges(persisted_edges),
        sources=sources_payload,
        query_plan=SearchQueryPlanResponse(
            company_query=str(discovery.get("query_plan", {}).get("company_query", "")),
            supplier_query=str(discovery.get("query_plan", {}).get("supplier_query", "")),
        ) if isinstance(discovery.get("query_plan"), dict) else None,
    )


@router.post("/{product_id}/confirm-supply-chain", response_model=ProductDiscoverResponse)
async def confirm_product_supply_chain(
    product_id: str,
    data: ConfirmSupplyChainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-confirm", max_requests=30, window_seconds=60)),
) -> ProductDiscoverResponse:
    """Confirm/edit discovered supply chain graph and persist final nodes and edges."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not data.nodes:
        raise HTTPException(status_code=422, detail="At least one supply chain node is required")

    db.query(SupplyChainEdge).filter(SupplyChainEdge.product_id == product.id).delete()
    db.query(SupplyChainNode).filter(SupplyChainNode.product_id == product.id).delete()
    db.flush()

    persisted_nodes: list[SupplyChainNode] = []
    input_to_persisted: dict[str, str] = {}

    for index, node in enumerate(data.nodes):
        role = node.role.strip().lower().replace(" ", "_")
        if role not in ALLOWED_ROLES:
            role = "manufacturing"

        persisted = SupplyChainNode(
            product_id=product.id,
            name=node.company_name.strip(),
            company_name=node.company_name.strip(),
            role=role,
            location=node.location.strip() or "Unknown",
            source_url=node.discovered_source.strip(),
            discovered_source=node.discovered_source.strip(),
            confidence_score=float(node.confidence_score),
            metadata_json=None,
        )
        db.add(persisted)
        db.flush()
        persisted_nodes.append(persisted)
        input_to_persisted[str(node.id or f"idx-{index}")] = str(persisted.id)

    persisted_edges: list[SupplyChainEdge] = []
    if data.edges:
        for edge in data.edges:
            from_id = input_to_persisted.get(edge.from_node_id, edge.from_node_id)
            to_id = input_to_persisted.get(edge.to_node_id, edge.to_node_id)
            if from_id == to_id:
                continue
            valid_from = any(str(node.id) == from_id for node in persisted_nodes)
            valid_to = any(str(node.id) == to_id for node in persisted_nodes)
            if not valid_from or not valid_to:
                continue

            persisted_edge = SupplyChainEdge(
                product_id=product.id,
                from_node_id=from_id,
                to_node_id=to_id,
                relation=edge.relation,
                confidence=float(edge.confidence),
            )
            db.add(persisted_edge)
            db.flush()
            persisted_edges.append(persisted_edge)
    else:
        for idx in range(len(persisted_nodes) - 1):
            chained_edge = SupplyChainEdge(
                product_id=product.id,
                from_node_id=str(persisted_nodes[idx].id),
                to_node_id=str(persisted_nodes[idx + 1].id),
                relation="supplies_to",
                confidence=0.75,
            )
            db.add(chained_edge)
            db.flush()
            persisted_edges.append(chained_edge)

    db.commit()

    sources_payload = [
        str(node.discovered_source or node.source_url or "")
        for node in persisted_nodes
        if str(node.discovered_source or node.source_url or "").strip()
    ]

    return ProductDiscoverResponse(
        product_id=str(product.id),
        product_name=str(product.product_name),
        sector=str(product.sector),
        nodes=_serialize_nodes(persisted_nodes),
        edges=_serialize_edges(persisted_edges),
        sources=sources_payload,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductDetailResponse:
    """Get product graph and latest factory intelligence results."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    nodes = (
        db.query(SupplyChainNode)
        .filter(SupplyChainNode.product_id == product.id)
        .order_by(SupplyChainNode.created_at.asc())
        .all()
    )
    edges = (
        db.query(SupplyChainEdge)
        .filter(SupplyChainEdge.product_id == product.id)
        .order_by(SupplyChainEdge.created_at.asc())
        .all()
    )
    node_ids = [str(node.id) for node in nodes]

    profiles = (
        db.query(FactoryProfile)
        .filter(FactoryProfile.node_id.in_(node_ids))
        .all()
        if node_ids
        else []
    )
    profile_ids = [str(profile.id) for profile in profiles]
    reports = (
        db.query(FactoryCarbonReport)
        .filter(FactoryCarbonReport.factory_profile_id.in_(profile_ids))
        .all()
        if profile_ids
        else []
    )
    reports_map = {str(report.factory_profile_id): report for report in reports}

    # Load product carbon report (if already aggregated)
    pcr: ProductCarbonReport | None = (
        db.query(ProductCarbonReport)
        .filter(ProductCarbonReport.product_id == product.id)
        .first()
    )
    carbon_report_response: ProductCarbonReportResponse | None = None
    if pcr is not None:
        carbon_report_response = _serialize_product_carbon_report(
            pcr, profiles, reports_map, nodes, str(product.product_name), str(product.sector)
        )

    return ProductDetailResponse(
        product_id=str(product.id),
        product_name=str(product.product_name),
        sector=str(product.sector),
        nodes=_serialize_nodes(nodes),
        edges=_serialize_edges(edges),
        factory_analysis=_serialize_factory_analysis(profiles, reports_map),
        carbon_report=carbon_report_response,
    )


@router.post("/{product_id}/analyze-factories", response_model=AnalyzeFactoriesResponse)
async def analyze_product_factories(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-analyze", max_requests=15, window_seconds=60)),
) -> AnalyzeFactoriesResponse:
    """Run factory intelligence and emission verification for each product node."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    nodes = (
        db.query(SupplyChainNode)
        .filter(SupplyChainNode.product_id == product.id)
        .order_by(SupplyChainNode.created_at.asc())
        .all()
    )
    if not nodes:
        raise HTTPException(status_code=422, detail="No supply chain nodes found for this product")

    service = FactoryIntelligenceService()
    analysis_result: list[FactoryAnalysisItemResponse] = []

    for node in nodes:
        result = await service.analyze_factory_node(
            db=db,
            user_id=str(current_user.id),
            sector=str(product.sector),
            node=node,
        )
        analysis_result.append(
            FactoryAnalysisItemResponse(
                factory_profile_id=str(result.get("factory_profile_id", "")),
                node_id=str(result.get("node_id", "")),
                company=str(result.get("company", "Unknown")),
                location=str(result.get("location", "Unknown")),
                machinery=str(result.get("machinery", "unknown")),
                production_capacity=float(result.get("production_capacity", 0.0) or 0.0),
                energy_sources=[str(item) for item in result.get("energy_sources", [])],
                scraped_sources=[str(item) for item in result.get("scraped_sources", [])],
                confidence=float(result.get("confidence", 0.0) or 0.0),
                verification_status=str(result.get("verification_status", "unknown")),
                emissions=FactoryEmissionResponse(
                    scope1=float(result.get("emissions", {}).get("scope1", 0.0) or 0.0),
                    scope2=float(result.get("emissions", {}).get("scope2", 0.0) or 0.0),
                    scope3=float(result.get("emissions", {}).get("scope3", 0.0) or 0.0),
                    total=float(result.get("emissions", {}).get("total", 0.0) or 0.0),
                ),
            )
        )

    db.commit()

    return AnalyzeFactoriesResponse(
        product_id=str(product.id),
        factories=analysis_result,
    )


@router.post("/{product_id}/aggregate-carbon", response_model=ProductCarbonReportResponse)
async def aggregate_product_carbon(
    product_id: str,
    product_quantity: float = 1000.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-aggregate", max_requests=20, window_seconds=60)),
) -> ProductCarbonReportResponse:
    """Aggregate all factory emissions into a product-level carbon footprint and EU CBAM analysis."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    agg_service = ProductAggregationService()
    try:
        result = agg_service.aggregate_product_carbon(
            db=db, product=product, product_quantity=product_quantity
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()

    # Reload persisted record to pass to serializer
    pcr: ProductCarbonReport | None = (
        db.query(ProductCarbonReport)
        .filter(ProductCarbonReport.product_id == product.id)
        .first()
    )
    if pcr is None:
        raise HTTPException(status_code=500, detail="Failed to persist product carbon report")

    nodes = (
        db.query(SupplyChainNode)
        .filter(SupplyChainNode.product_id == product.id)
        .all()
    )
    profiles = (
        db.query(FactoryProfile)
        .filter(FactoryProfile.node_id.in_([str(n.id) for n in nodes]))
        .all()
        if nodes
        else []
    )
    profile_ids = [str(p.id) for p in profiles]
    reports = (
        db.query(FactoryCarbonReport)
        .filter(FactoryCarbonReport.factory_profile_id.in_(profile_ids))
        .all()
        if profile_ids
        else []
    )
    reports_map = {str(r.factory_profile_id): r for r in reports}

    return _serialize_product_carbon_report(
        pcr, profiles, reports_map, nodes,
        str(product.product_name), str(product.sector)
    )


@router.post("/{product_id}/optimize", response_model=OptimizeResponse)
async def optimize_product_supply_chain(
    product_id: str,
    data: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-optimize", max_requests=20, window_seconds=60)),
) -> OptimizeResponse:
    """Simulate supply-chain replacement scenarios and estimate emission + CBAM impact."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    optimizer = SupplyChainOptimizer()
    try:
        result = await optimizer.optimize(
            db=db,
            product=product,
            target_factory=data.target_factory,
            product_quantity=float(data.product_quantity),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _serialize_optimize_response(result)

@router.post("/{product_id}/nodes/{node_id}/attest", response_model=FactoryAnalysisItemResponse)
async def attest_factory_node(
    product_id: str,
    node_id: str,
    data: AttestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("api:products-attest", max_requests=20, window_seconds=60)),
) -> FactoryAnalysisItemResponse:
    """Submit primary data for a pending attestation MSME node."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    node = (
        db.query(SupplyChainNode)
        .filter(SupplyChainNode.id == node_id, SupplyChainNode.product_id == product.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    service = FactoryIntelligenceService()
    result = await service.attest_factory_node(
        db=db,
        user_id=str(current_user.id),
        sector=str(product.sector),
        node=node,
        machinery_type=data.machinery_type,
        production_capacity=data.production_capacity,
        energy_sources=data.energy_sources,
    )
    
    db.commit()

    return FactoryAnalysisItemResponse(
        factory_profile_id=str(result.get("factory_profile_id", "")),
        node_id=str(result.get("node_id", "")),
        company=str(result.get("company", "Unknown")),
        location=str(result.get("location", "Unknown")),
        machinery=str(result.get("machinery", "unknown")),
        production_capacity=float(result.get("production_capacity", 0.0) or 0.0),
        energy_sources=[str(item) for item in result.get("energy_sources", [])],
        scraped_sources=[str(item) for item in result.get("scraped_sources", [])],
        confidence=float(result.get("confidence", 0.0) or 0.0),
        verification_status=str(result.get("verification_status", "unknown")),
        emissions=FactoryEmissionResponse(
            scope1=float(result.get("emissions", {}).get("scope1", 0.0) or 0.0),
            scope2=float(result.get("emissions", {}).get("scope2", 0.0) or 0.0),
            scope3=float(result.get("emissions", {}).get("scope3", 0.0) or 0.0),
            total=float(result.get("emissions", {}).get("total", 0.0) or 0.0),
        ),
    )
