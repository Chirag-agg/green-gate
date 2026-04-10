"""
Reports router for GreenGate.
Handles listing, viewing, certifying, and downloading CBAM reports.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import Response

from database import get_db
from models import User, CarbonReport
from routers.auth import get_current_user
from services.blockchain import BlockchainService
from services.cbam_report import generate_cbam_report, generate_cbam_report_pdf
from services.cbam_xml_service import generate_cbam_xml
from services.verification_engine import VerificationEngine
from utils.logger import get_logger

router = APIRouter(prefix="/api/reports", tags=["Reports"])
logger = get_logger("reports_router")

EVIDENCE_STORAGE_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "evidence_uploads"
)


# ──── Pydantic Schemas ────


class ReportSummary(BaseModel):
    report_id: str
    company_name: str
    sector: str
    state: str
    total_co2_tonnes: float
    cbam_liability_eur: float
    cbam_liability_inr: float
    credibility_score: Optional[float] = None
    confidence_score: Optional[float] = None
    verification_status: Optional[str] = None
    requires_evidence: Optional[bool] = None
    is_blockchain_certified: bool
    created_at: str

    class Config:
        from_attributes = True


class ReportDetail(BaseModel):
    report_id: str
    company_name: str
    sector: str
    state: str
    annual_production_tonnes: float
    eu_export_tonnes: float
    total_co2_tonnes: float
    scope1_co2_tonnes: float
    scope2_co2_tonnes: float
    co2_per_tonne_product: float
    eu_embedded_co2_tonnes: float
    cbam_liability_eur: float
    cbam_liability_inr: float
    vs_benchmark_pct: float
    expected_energy: Optional[float] = None
    deviation_ratio: Optional[float] = None
    credibility_score: Optional[float] = None
    machinery_score: Optional[float] = None
    regional_energy_score: Optional[float] = None
    temporal_score: Optional[float] = None
    estimated_emissions: Optional[float] = None
    scope3_emissions: Optional[float] = None
    scope3_breakdown: Optional[str] = None
    twin_consistency_score: Optional[float] = None
    confidence_score: Optional[float] = None
    verification_status: Optional[str] = None
    requires_evidence: Optional[bool] = None
    evidence_files: Optional[str] = None
    verification_notes: Optional[str] = None
    full_output_json: Optional[str] = None
    recommendations_json: Optional[str] = None
    report_hash: Optional[str] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    polygonscan_url: Optional[str] = None
    blockchain_verified_at: Optional[str] = None
    blockchain_note: Optional[str] = None
    hash_verified: Optional[bool] = None
    is_blockchain_certified: bool
    created_at: str

    class Config:
        from_attributes = True


class CertifyResponse(BaseModel):
    report_id: str
    report_hash: str
    tx_hash: Optional[str] = None
    polygonscan_url: Optional[str] = None
    block_number: Optional[int] = None
    hash_verified: bool = True
    blockchain_verified_at: Optional[str] = None
    verified: bool = True
    note: Optional[str] = None


class EvidenceUploadResponse(BaseModel):
    report_id: str
    uploaded_files: list[str]


class ReportConsistencyResponse(BaseModel):
    report_id: str
    is_consistent: bool
    flags: list[str]
    stored_total_co2_tonnes: float
    recalculated_total_co2_tonnes: float
    stored_co2_per_tonne_product: float
    recalculated_co2_per_tonne_product: float
    benchmark_status: str
    benchmark_vs_pct: float


def _build_report_hash_payload(report: CarbonReport) -> dict[str, object]:
    """Create deterministic hash payload for tamper detection and chain storage."""
    return {
        "report_id": report.report_id,
        "user_id": report.user_id,
        "timestamp": report.created_at.isoformat() if report.created_at else "",
        "total_co2_tonnes": float(report.total_co2_tonnes or 0.0),
        "co2_per_tonne_product": float(report.co2_per_tonne_product or 0.0),
        "cbam_liability_eur": float(report.cbam_liability_eur or 0.0),
    }


def _store_evidence_file(report_id: str, upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    report_dir = EVIDENCE_STORAGE_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    original_name = os.path.basename(upload.filename or "evidence.pdf")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_name = f"{timestamp}_{original_name.replace(' ', '_')}"
    destination = report_dir / safe_name

    file_bytes = upload.file.read()
    destination.write_bytes(file_bytes)

    return str(destination.relative_to(Path(__file__).resolve().parent.parent)).replace("\\", "/")


def _build_report_xml_payload(
    report: CarbonReport,
    current_user: User,
    input_data: dict[str, object],
    calc_result: dict[str, object],
) -> dict[str, object]:
    product_payload = input_data.get("product") if isinstance(input_data.get("product"), dict) else {}
    cbam_payload = input_data.get("cbam") if isinstance(input_data.get("cbam"), dict) else {}

    eu_embedded = float(report.eu_embedded_co2_tonnes or 0.0)
    cbam_eur = float(report.cbam_liability_eur or 0.0)
    ets_price_fallback = (cbam_eur / eu_embedded) if eu_embedded > 0 else 0.0

    importer_name = (
        str(input_data.get("importer_name") or "").strip()
        or str(input_data.get("eu_importer_name") or "").strip()
        or "EU Importer (Unknown)"
    )
    importer_country = (
        str(input_data.get("importer_country") or "").strip()
        or str(input_data.get("eu_country") or "").strip()
        or "EU"
    )
    eori = (
        str(input_data.get("eori") or "").strip()
        or str(input_data.get("importer_eori") or "").strip()
        or str(current_user.iec_number or "").strip()
        or str(current_user.gstin or "").strip()
        or "UNKNOWN-EORI"
    )

    cn_code = (
        str(product_payload.get("cn_code") if isinstance(product_payload, dict) else "").strip()
        or str(input_data.get("cn_code") or "").strip()
        or str(input_data.get("hsn_code") or "").strip()
        or "N/A"
    )
    description = (
        str(product_payload.get("description") if isinstance(product_payload, dict) else "").strip()
        or str(input_data.get("product_description") or "").strip()
        or str(input_data.get("product_name") or "").strip()
        or f"{report.sector} product"
    )
    quantity = (
        float(product_payload.get("quantity", 0.0))
        if isinstance(product_payload, dict)
        else 0.0
    ) or float(report.eu_export_tonnes or 0.0) or float(report.annual_production_tonnes or 0.0)

    verification_status = (
        str(report.verification_status or "").strip()
        or ("BlockchainVerified" if report.is_blockchain_certified else "SelfDeclared")
    )

    payload = {
        "importer_name": importer_name,
        "eori": eori,
        "importer_country": importer_country,
        "exporter_name": str(report.company_name or "N/A"),
        "exporter_country": str(input_data.get("exporter_country") or "India"),
        "installation_id": str(input_data.get("installation_id") or f"INST-{report.report_id}"),
        "location": str(input_data.get("location") or report.state or "N/A"),
        "product": {
            "cn_code": cn_code,
            "description": description,
            "quantity": quantity,
            "embedded_emissions": float(report.eu_embedded_co2_tonnes or 0.0),
        },
        "emissions": {
            "scope1": float(report.scope1_co2_tonnes or 0.0),
            "scope2": float(report.scope2_co2_tonnes or 0.0),
            "total": float(report.total_co2_tonnes or 0.0),
        },
        "cbam": {
            "ets_price": float(cbam_payload.get("ets_price", ets_price_fallback))
            if isinstance(cbam_payload, dict)
            else ets_price_fallback,
            "total_cost": float(report.cbam_liability_eur or 0.0),
        },
        "verification": {
            "status": verification_status,
            "report_hash": str(report.report_hash or "N/A"),
        },
        "report_id": str(report.report_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return payload


# ──── Endpoints ────


@router.get("", response_model=list[ReportSummary])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportSummary]:
    """List all reports for the current user."""
    reports = (
        db.query(CarbonReport)
        .filter(CarbonReport.user_id == current_user.id)
        .order_by(CarbonReport.created_at.desc())
        .all()
    )
    return [
        ReportSummary(
            report_id=r.report_id,
            company_name=r.company_name,
            sector=r.sector,
            state=r.state,
            total_co2_tonnes=r.total_co2_tonnes,
            cbam_liability_eur=r.cbam_liability_eur,
            cbam_liability_inr=r.cbam_liability_inr,
            credibility_score=r.credibility_score,
            confidence_score=r.confidence_score,
            verification_status=r.verification_status,
            requires_evidence=r.requires_evidence,
            is_blockchain_certified=r.is_blockchain_certified,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetail:
    """Get a full report with all details and recommendations."""
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.report_hash:
        recomputed_hash = BlockchainService.generate_report_hash(_build_report_hash_payload(report))
        hash_verified = recomputed_hash == report.report_hash
        report.hash_verified = hash_verified
        if not hash_verified:
            logger.warn(
                "report_integrity_compromised",
                {
                    "report_id": report.report_id,
                    "stored_hash": report.report_hash,
                    "recomputed_hash": recomputed_hash,
                },
            )
            report.blockchain_note = "Report integrity compromised"
        db.commit()
        db.refresh(report)

    return ReportDetail(
        report_id=report.report_id,
        company_name=report.company_name,
        sector=report.sector,
        state=report.state,
        annual_production_tonnes=report.annual_production_tonnes,
        eu_export_tonnes=report.eu_export_tonnes,
        total_co2_tonnes=report.total_co2_tonnes,
        scope1_co2_tonnes=report.scope1_co2_tonnes,
        scope2_co2_tonnes=report.scope2_co2_tonnes,
        co2_per_tonne_product=report.co2_per_tonne_product,
        eu_embedded_co2_tonnes=report.eu_embedded_co2_tonnes,
        cbam_liability_eur=report.cbam_liability_eur,
        cbam_liability_inr=report.cbam_liability_inr,
        vs_benchmark_pct=report.vs_benchmark_pct,
        expected_energy=report.expected_energy,
        deviation_ratio=report.deviation_ratio,
        credibility_score=report.credibility_score,
        machinery_score=report.machinery_score,
        regional_energy_score=report.regional_energy_score,
        temporal_score=report.temporal_score,
        estimated_emissions=report.estimated_emissions,
        scope3_emissions=report.scope3_emissions,
        scope3_breakdown=report.scope3_breakdown,
        twin_consistency_score=report.twin_consistency_score,
        confidence_score=report.confidence_score,
        verification_status=report.verification_status,
        requires_evidence=report.requires_evidence,
        evidence_files=report.evidence_files,
        verification_notes=report.verification_notes,
        full_output_json=report.full_output_json,
        recommendations_json=report.recommendations_json,
        report_hash=report.report_hash,
        tx_hash=report.tx_hash,
        block_number=report.block_number,
        polygonscan_url=report.polygonscan_url,
        blockchain_verified_at=(
            report.blockchain_verified_at.isoformat() if report.blockchain_verified_at else None
        ),
        blockchain_note=report.blockchain_note,
        hash_verified=report.hash_verified,
        is_blockchain_certified=report.is_blockchain_certified,
        created_at=report.created_at.isoformat() if report.created_at else "",
    )


@router.post("/{report_id}/certify", response_model=CertifyResponse)
async def certify_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CertifyResponse:
    """
    Certify a report on the Polygon blockchain.
    Generates a SHA-256 hash, submits to the smart contract, and updates the DB.
    """
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.is_blockchain_certified:
        raise HTTPException(
            status_code=400, detail="Report is already blockchain certified"
        )

    if float(report.confidence_score or 0.0) < 0.75:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confidence score too low for blockchain certification. "
                "Improve data quality or provide supporting evidence."
            ),
        )

    try:
        blockchain = BlockchainService()

        # Store and certify only deterministic report hash payload.
        report_hash_payload = _build_report_hash_payload(report)
        report_hash = blockchain.generate_report_hash(report_hash_payload)
        co2_kg = int(report.total_co2_tonnes * 1000)

        logger.info(
            "certify_requested",
            {
                "report_id": report.report_id,
                "company_name": report.company_name,
                "co2_kg": co2_kg,
            },
        )

        result = await blockchain.submit_to_blockchain(
            report_id=report.report_id,
            report_hash=report_hash,
            company_name=report.company_name,
            co2_kg=co2_kg,
        )

        # Update DB
        report.report_hash = report_hash
        report.tx_hash = result["tx_hash"]
        report.block_number = result["block_number"]
        report.polygonscan_url = result["polygonscan_url"]
        report.is_blockchain_certified = True
        report.hash_verified = True
        report.blockchain_note = None
        report.blockchain_verified_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)

        logger.info(
            "certify_completed",
            {
                "report_id": report.report_id,
                "tx_hash": result["tx_hash"],
                "block_number": result["block_number"],
            },
        )

        return CertifyResponse(
            report_id=report.report_id,
            report_hash=report_hash,
            tx_hash=result["tx_hash"],
            polygonscan_url=result["polygonscan_url"],
            block_number=result["block_number"],
            hash_verified=True,
            blockchain_verified_at=(
                report.blockchain_verified_at.isoformat()
                if report.blockchain_verified_at
                else None
            ),
            verified=True,
            note=None,
        )

    except ValueError as e:
        logger.warn("certify_failed_validation", {"report_id": report_id, "error": str(e)})
        report_hash = report.report_hash or BlockchainService.generate_report_hash(_build_report_hash_payload(report))
        report.report_hash = report_hash
        report.is_blockchain_certified = False
        report.hash_verified = False
        report.blockchain_note = "Blockchain verification unavailable"
        report.blockchain_verified_at = None
        db.commit()
        db.refresh(report)
        return CertifyResponse(
            report_id=report.report_id,
            report_hash=report_hash,
            tx_hash=None,
            polygonscan_url=None,
            block_number=None,
            hash_verified=False,
            blockchain_verified_at=None,
            verified=False,
            note="Blockchain verification unavailable",
        )
    except Exception as e:
        logger.error("certify_failed", {"report_id": report_id, "error": str(e)})
        report_hash = report.report_hash or BlockchainService.generate_report_hash(_build_report_hash_payload(report))
        report.report_hash = report_hash
        report.is_blockchain_certified = False
        report.hash_verified = False
        report.blockchain_note = "Blockchain verification unavailable"
        report.blockchain_verified_at = None
        db.commit()
        db.refresh(report)
        return CertifyResponse(
            report_id=report.report_id,
            report_hash=report_hash,
            tx_hash=None,
            polygonscan_url=None,
            block_number=None,
            hash_verified=False,
            blockchain_verified_at=None,
            verified=False,
            note="Blockchain verification unavailable",
        )


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    format: str = Query(default="xml", pattern="^(xml|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download report as EU CBAM XML (default) or legacy PDF (format=pdf)."""
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    input_data = json.loads(report.full_input_json) if report.full_input_json else {}
    calc_result = json.loads(report.full_output_json) if report.full_output_json else {}
    recommendations = (
        json.loads(report.recommendations_json) if report.recommendations_json else []
    )

    if format == "xml":
        xml_payload = _build_report_xml_payload(report, current_user, input_data, calc_result)
        xml_text = generate_cbam_xml(xml_payload)
        logger.info(
            "download_generated_xml",
            {
                "report_id": report_id,
                "is_certified": report.tx_hash is not None,
                "xml_report_id": xml_payload.get("report_id"),
            },
        )
        return Response(
            content=xml_text.encode("utf-8"),
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="{report.report_id}_cbam_report.xml"'
            },
        )

    cbam_report = generate_cbam_report(
        input_data=input_data,
        calculation_result=calc_result,
        recommendations=recommendations,
        report_id=report.report_id,
        tx_hash=report.tx_hash,
        report_hash=report.report_hash,
    )

    logger.info(
        "download_generated",
        {
            "report_id": report_id,
            "has_recommendations": len(recommendations) > 0,
            "is_certified": report.tx_hash is not None,
        },
    )

    pdf_bytes = generate_cbam_report_pdf(
        report_payload=cbam_report,
        report_id=str(report.report_id),
        company_name=str(report.company_name),
        sector=str(report.sector),
        state=str(report.state),
        created_at_iso=(report.created_at.isoformat() if report.created_at else ""),
        total_co2_tonnes=float(report.total_co2_tonnes or 0.0),
        scope1_co2_tonnes=float(report.scope1_co2_tonnes or 0.0),
        scope2_co2_tonnes=float(report.scope2_co2_tonnes or 0.0),
        co2_per_tonne_product=float(report.co2_per_tonne_product or 0.0),
        eu_export_tonnes=float(report.eu_export_tonnes or 0.0),
        eu_embedded_co2_tonnes=float(report.eu_embedded_co2_tonnes or 0.0),
        cbam_liability_eur=float(report.cbam_liability_eur or 0.0),
        cbam_liability_inr=float(report.cbam_liability_inr or 0.0),
        tx_hash=(str(report.tx_hash) if report.tx_hash else None),
        report_hash=(str(report.report_hash) if report.report_hash else None),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report.report_id}_cbam_report.pdf"'
        },
    )


@router.post("/{report_id}/upload-evidence", response_model=EvidenceUploadResponse)
async def upload_evidence(
    report_id: str,
    electricity_bill: UploadFile | None = File(default=None),
    energy_audit_report: UploadFile | None = File(default=None),
    renewable_energy_certificate: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceUploadResponse:
    """Upload evidence PDFs for reports flagged as requiring evidence."""
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    uploads = [electricity_bill, energy_audit_report, renewable_energy_certificate]
    provided = [upload for upload in uploads if upload is not None]
    if not provided:
        raise HTTPException(status_code=400, detail="At least one evidence file is required")

    existing_files = json.loads(report.evidence_files) if report.evidence_files else []
    uploaded_paths: list[str] = []

    for upload in provided:
        stored_path = _store_evidence_file(report_id, upload)
        uploaded_paths.append(stored_path)

    merged_files = existing_files + uploaded_paths
    report.evidence_files = json.dumps(merged_files)
    report.requires_evidence = False
    db.commit()
    db.refresh(report)

    logger.info(
        "evidence_uploaded",
        {"report_id": report_id, "uploaded_count": len(uploaded_paths)},
    )

    return EvidenceUploadResponse(report_id=report_id, uploaded_files=uploaded_paths)


@router.get("/{report_id}/verify-consistency", response_model=ReportConsistencyResponse)
def verify_report_consistency(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportConsistencyResponse:
    """Recompute emissions + benchmark and compare against stored report output."""
    report = (
        db.query(CarbonReport)
        .filter(
            CarbonReport.report_id == report_id,
            CarbonReport.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.full_input_json:
        raise HTTPException(status_code=400, detail="Report input snapshot is missing")

    input_data = json.loads(report.full_input_json)
    stored_output = json.loads(report.full_output_json) if report.full_output_json else {
        "total_co2_tonnes": report.total_co2_tonnes,
        "co2_per_tonne_product": report.co2_per_tonne_product,
        "cbam_liability_eur": report.cbam_liability_eur,
    }

    verification_engine = VerificationEngine()
    consistency = verification_engine.verify_report_consistency(
        input_data=input_data,
        stored_output=stored_output,
        industry=report.sector,
        annual_production_tonnes=float(report.annual_production_tonnes or 0.0),
    )

    recalculated = consistency.get("recalculated", {})
    benchmark_comparison = consistency.get("benchmark_comparison", {})

    logger.info(
        "consistency_check_completed",
        {
            "report_id": report_id,
            "is_consistent": bool(consistency.get("is_consistent", False)),
            "flag_count": len(consistency.get("flags", [])),
        },
    )

    return ReportConsistencyResponse(
        report_id=report_id,
        is_consistent=bool(consistency.get("is_consistent", False)),
        flags=[str(flag) for flag in consistency.get("flags", [])],
        stored_total_co2_tonnes=float(stored_output.get("total_co2_tonnes", 0.0) or 0.0),
        recalculated_total_co2_tonnes=float(recalculated.get("total_co2_tonnes", 0.0) or 0.0),
        stored_co2_per_tonne_product=float(stored_output.get("co2_per_tonne_product", 0.0) or 0.0),
        recalculated_co2_per_tonne_product=float(recalculated.get("co2_per_tonne_product", 0.0) or 0.0),
        benchmark_status=str(benchmark_comparison.get("status", "unknown")),
        benchmark_vs_pct=float(benchmark_comparison.get("vs_benchmark_pct", 0.0) or 0.0),
    )
