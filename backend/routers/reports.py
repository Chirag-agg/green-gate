"""
Reports router for GreenGate.
Handles listing, viewing, certifying, and downloading CBAM reports.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from database import get_db
from models import User, CarbonReport
from routers.auth import get_current_user
from services.blockchain import BlockchainService
from services.cbam_report import generate_cbam_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])

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
    is_blockchain_certified: bool
    created_at: str

    class Config:
        from_attributes = True


class CertifyResponse(BaseModel):
    report_id: str
    report_hash: str
    tx_hash: str
    polygonscan_url: str
    block_number: int


class EvidenceUploadResponse(BaseModel):
    report_id: str
    uploaded_files: list[str]


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

        # Build report dict for hashing
        report_data = {
            "report_id": report.report_id,
            "company_name": report.company_name,
            "sector": report.sector,
            "state": report.state,
            "total_co2_tonnes": report.total_co2_tonnes,
            "scope1_co2_tonnes": report.scope1_co2_tonnes,
            "scope2_co2_tonnes": report.scope2_co2_tonnes,
            "co2_per_tonne_product": report.co2_per_tonne_product,
            "eu_embedded_co2_tonnes": report.eu_embedded_co2_tonnes,
            "cbam_liability_eur": report.cbam_liability_eur,
        }

        report_hash = blockchain.generate_report_hash(report_data)
        co2_kg = int(report.total_co2_tonnes * 1000)

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
        db.commit()
        db.refresh(report)

        return CertifyResponse(
            report_id=report.report_id,
            report_hash=report_hash,
            tx_hash=result["tx_hash"],
            polygonscan_url=result["polygonscan_url"],
            block_number=result["block_number"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain certification failed: {str(e)}",
        )


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a full CBAM report as JSON."""
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

    cbam_report = generate_cbam_report(
        input_data=input_data,
        calculation_result=calc_result,
        recommendations=recommendations,
        report_id=report.report_id,
        tx_hash=report.tx_hash,
        report_hash=report.report_hash,
    )

    return JSONResponse(
        content=cbam_report,
        headers={
            "Content-Disposition": f'attachment; filename="{report.report_id}_cbam_report.json"'
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

    return EvidenceUploadResponse(report_id=report_id, uploaded_files=uploaded_paths)
