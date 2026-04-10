"""CBAM XML export router."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.cbam_xml_service import generate_cbam_xml, save_cbam_xml

router = APIRouter(tags=["CBAM XML"])


class CBAMXMLExportRequest(BaseModel):
    company_name: str
    installation_id: str
    country: str
    reporting_period: str
    electricity_kwh: float
    diesel_liters: float
    total_emissions_tco2: float
    report_id: str | None = None
    generated_at: str | None = None
    filename: str | None = Field(default="cbam_report.xml")
    download: bool = False


class CBAMProductPayload(BaseModel):
    cn_code: str = Field(min_length=1)
    description: str = Field(min_length=1)
    quantity: float
    embedded_emissions: float


class CBAMEmissionsPayload(BaseModel):
    scope1: float
    scope2: float
    total: float


class CBAMCostPayload(BaseModel):
    ets_price: float
    total_cost: float


class CBAMVerificationPayload(BaseModel):
    status: str = Field(min_length=1)
    report_hash: str = Field(min_length=1)


class CBAMEUExportRequest(BaseModel):
    importer_name: str = Field(min_length=1)
    eori: str = Field(min_length=1)
    importer_country: str = Field(min_length=1)
    exporter_name: str = Field(min_length=1)
    exporter_country: str = Field(min_length=1)
    installation_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    product: CBAMProductPayload
    emissions: CBAMEmissionsPayload
    cbam: CBAMCostPayload
    verification: CBAMVerificationPayload
    report_id: str | None = None
    generated_at: str | None = None
    filename: str | None = Field(default="cbam_eu_report.xml")
    download: bool = False


@router.post("/export-xml")
def export_xml(payload: CBAMXMLExportRequest) -> Any:
    """Export EU-style CBAM XML either as inline XML text or downloadable XML file."""
    try:
        data = payload.model_dump()
        if not data.get("generated_at"):
            data["generated_at"] = datetime.now(timezone.utc).isoformat()

        if payload.download:
            target_dir = Path(__file__).resolve().parent.parent / "data" / "xml_exports"
            file_path = save_cbam_xml(data, str(target_dir / (payload.filename or "cbam_report.xml")))
            return FileResponse(
                path=file_path,
                media_type="application/xml",
                filename=Path(file_path).name,
            )

        xml_content = generate_cbam_xml(data)
        report_id_start = xml_content.find("<ReportID>")
        report_id_end = xml_content.find("</ReportID>")
        generated_at_start = xml_content.find("<GeneratedAt>")
        generated_at_end = xml_content.find("</GeneratedAt>")
        xml_report_id = (
            xml_content[report_id_start + 10:report_id_end]
            if report_id_start != -1 and report_id_end != -1
            else data.get("report_id")
        )
        xml_generated_at = (
            xml_content[generated_at_start + 13:generated_at_end]
            if generated_at_start != -1 and generated_at_end != -1
            else data.get("generated_at")
        )
        return {
            "xml": xml_content,
            "generated_at": xml_generated_at,
            "report_id": xml_report_id,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"XML export failed: {exc}") from exc


@router.post("/export-cbam-xml")
def export_cbam_xml(payload: CBAMEUExportRequest) -> Any:
    """Export EU CBAM XML as inline text or downloadable XML file."""
    try:
        data = payload.model_dump()
        if not data.get("generated_at"):
            data["generated_at"] = datetime.now(timezone.utc).isoformat()

        xml_content = generate_cbam_xml(data)

        target_dir = Path(__file__).resolve().parent.parent / "data" / "xml_exports"
        target_name = payload.filename or "cbam_eu_report.xml"
        saved_file = save_cbam_xml(data, str(target_dir / target_name))

        if payload.download:
            return FileResponse(
                path=saved_file,
                media_type="application/xml",
                filename=Path(saved_file).name,
            )

        report_id_start = xml_content.find("<ReportID>")
        report_id_end = xml_content.find("</ReportID>")
        generated_at_start = xml_content.find("<GeneratedAt>")
        generated_at_end = xml_content.find("</GeneratedAt>")
        xml_report_id = (
            xml_content[report_id_start + 10:report_id_end]
            if report_id_start != -1 and report_id_end != -1
            else data.get("report_id")
        )
        xml_generated_at = (
            xml_content[generated_at_start + 13:generated_at_end]
            if generated_at_start != -1 and generated_at_end != -1
            else data.get("generated_at")
        )

        return {
            "xml": xml_content,
            "report_id": xml_report_id,
            "generated_at": xml_generated_at,
            "saved_file": saved_file,
            "download_filename": Path(saved_file).name,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CBAM XML export failed: {exc}") from exc
