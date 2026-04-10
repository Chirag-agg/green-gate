"""CBAM report generator for GreenGate.

Generates:
- JSON report payload for API/UI consumption.
- PDF export with EU-style CBAM formatting for downloads.
"""

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from utils.logger import get_logger

logger = get_logger("cbam_report")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_recommendation_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("title") or item.get("action") or item.get("recommendation") or "")
    return ""


def generate_cbam_report(
    input_data: dict[str, Any],
    calculation_result: dict[str, Any],
    recommendations: list[dict[str, Any]],
    report_id: str,
    tx_hash: str | None = None,
    report_hash: str | None = None,
) -> dict[str, Any]:
    """
    Generate a complete CBAM-formatted report.

    Args:
        input_data: Original calculation input data.
        calculation_result: Output from EmissionEngine.calculate().
        recommendations: AI-generated recommendations.
        report_id: Unique report identifier.
        tx_hash: Blockchain transaction hash (if certified).
        report_hash: SHA-256 report hash (if certified).

    Returns:
        Complete CBAM report dictionary.
    """
    total_co2_tonnes = _to_float(calculation_result.get("total_co2_tonnes", 0.0), 0.0)
    intensity_payload = calculation_result.get("intensity", {}) if isinstance(calculation_result, dict) else {}
    intensity_value = _to_float(intensity_payload.get("value", 0.0), 0.0)

    benchmark_comparison = calculation_result.get("benchmark_comparison", {})
    industry_avg = _to_float(benchmark_comparison.get("industry_avg", 0.0), 0.0)
    benchmark_label = str(benchmark_comparison.get("label", "Needs improvement"))
    benchmark_payload = benchmark_comparison.get("benchmark", {}) if isinstance(benchmark_comparison, dict) else {}

    profile = calculation_result.get("user_profile", {}) if isinstance(calculation_result, dict) else {}
    industry = str(profile.get("industry") or input_data.get("industry") or input_data.get("sector") or "general")
    scale = str(profile.get("scale") or input_data.get("scale") or "small")
    location = str(profile.get("location") or input_data.get("location") or input_data.get("region") or input_data.get("state") or "India")
    cbam_status = bool(calculation_result.get("cbam_status", input_data.get("exports_to_eu", False)))

    issues: list[str] = []
    solutions: list[dict[str, str]] = []

    if intensity_value > 0 and industry_avg > 0 and intensity_value > industry_avg:
        issues.append("Higher emissions than industry average")
        solutions.append(
            {
                "category": "Process",
                "problem": "Higher emissions than peer average",
                "solution": "Improve process efficiency and increase cleaner-energy share",
                "impact": "Can reduce unit intensity and carbon liability",
            }
        )

    breakdown = calculation_result.get("breakdown", {}) if isinstance(calculation_result, dict) else {}
    electricity_t = _to_float(breakdown.get("electricity_co2_tonnes", 0.0), 0.0)
    coal_t = _to_float(breakdown.get("coal_co2_tonnes", 0.0), 0.0)
    if coal_t > electricity_t:
        issues.append("High fossil fuel dependence in thermal operations")
        solutions.append(
            {
                "category": "Energy",
                "problem": "High fossil fuel dependence in thermal operations",
                "solution": "Switch to cleaner fuel alternatives",
                "impact": "Reduced combustion emissions and operating risk",
            }
        )

    if scale in {"micro", "small", "medium"} and intensity_value > 0:
        solutions.append(
            {
                "category": "Machinery",
                "problem": "MSME productivity-emissions tradeoff",
                "solution": "Upgrade machinery using MSME subsidy-backed financing pathways",
                "impact": "Improves energy productivity with manageable capex",
            }
        )

    if cbam_status and industry_avg > 0 and intensity_value > industry_avg:
        issues.append("Your emissions exceed EU CBAM thresholds")
        solutions.append(
            {
                "category": "Compliance",
                "problem": "CBAM exposure for export shipments",
                "solution": "Prepare verified monthly intensity records and supplier traceability evidence",
                "impact": "Reduces rejection risk in EU importer reviews",
            }
        )

    if not issues:
        issues.append("No major issues detected from current submission")
    if not solutions:
        solutions.append(
            {
                "category": "Process",
                "problem": "No major issues detected",
                "solution": "No major issues detected based on current data",
                "impact": "Maintain monitoring cadence and evidence quality",
            }
        )

    dynamic_recommendations = [
        text for text in [_extract_recommendation_text(item) for item in recommendations] if text
    ]
    for text in dynamic_recommendations[:2]:
        solutions.append(
            {
                "category": "Process",
                "problem": "Model-guided optimization opportunity",
                "solution": text,
                "impact": "Can improve emissions trajectory if executed",
            }
        )

    summary = (
        f"{input_data.get('company_name', 'Company')} reported {round(total_co2_tonnes, 3)} tCO2e "
        f"with intensity {round(intensity_value, 3)} kgCO2/unit; benchmark status: {benchmark_label}."
    )

    compact_recommendations = [
        str(solution.get("solution") or solution.get("problem") or "")
        for solution in solutions[:6]
        if str(solution.get("solution") or solution.get("problem") or "").strip()
    ]

    report: dict[str, Any] = {
        "summary": summary,
        "intensity": round(intensity_value, 3),
        "benchmark_label": benchmark_label,
        "top_issues": issues[:3],
        "recommendations": compact_recommendations,
        "comparison_basis": str(benchmark_comparison.get("comparison_basis", "General")),
        "verified": bool(tx_hash),
        # Backward-compatible payload keys retained.
        "user_profile": {
            "industry": industry,
            "scale": scale,
            "location": location,
        },
        "benchmark": {
            "avg": _to_float(benchmark_payload.get("avg", industry_avg), industry_avg),
            "best": _to_float(benchmark_payload.get("best", 0.0), 0.0),
            "label": str(benchmark_payload.get("label", benchmark_label)),
        },
        "data_source": str(benchmark_comparison.get("data_source", "hybrid")),
        "confidence_score": _to_float(benchmark_comparison.get("confidence_score", 0.0), 0.0),
        "personalized_solutions": solutions[:6],
        "cbam_status": cbam_status,
    }

    logger.info(
        "cbam_report_generated",
        {
            "report_id": report_id,
            "intensity": report["intensity"],
            "recommendation_count": len(report["personalized_solutions"]),
            "is_blockchain_certified": tx_hash is not None,
        },
    )

    return report


def _draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    line_height: float,
    font_name: str,
    font_size: float,
) -> float:
    """Draw wrapped text and return the final y position."""
    pdf.setFont(font_name, font_size)
    words = str(text or "").split()
    if not words:
        return y

    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
            line = candidate
            continue

        pdf.drawString(x, y, line)
        y -= line_height
        line = word

    if line:
        pdf.drawString(x, y, line)
        y -= line_height

    return y


def _money(value: float, currency: str = "EUR") -> str:
    amount = _to_float(value, 0.0)
    if currency == "INR":
        return f"INR {amount:,.2f}"
    return f"EUR {amount:,.2f}"


def generate_cbam_report_pdf(
    report_payload: dict[str, Any],
    *,
    report_id: str,
    company_name: str,
    sector: str,
    state: str,
    created_at_iso: str,
    total_co2_tonnes: float,
    scope1_co2_tonnes: float,
    scope2_co2_tonnes: float,
    co2_per_tonne_product: float,
    eu_export_tonnes: float,
    eu_embedded_co2_tonnes: float,
    cbam_liability_eur: float,
    cbam_liability_inr: float,
    tx_hash: str | None,
    report_hash: str | None,
) -> bytes:
    """Generate PDF bytes for EU CBAM-style report export."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    margin = 50
    y = page_h - margin
    max_text_width = page_w - (2 * margin)

    # Header
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, y, "EU CBAM Emissions Report")
    y -= 20

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, "GreenGate Carbon Border Adjustment Mechanism (CBAM) Export Statement")
    y -= 24

    # Operator details
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "1. Operator Details")
    y -= 16

    pdf.setFont("Helvetica", 10)
    details = [
        f"Report ID: {report_id}",
        f"Company: {company_name}",
        f"Sector: {sector}",
        f"State/Region: {state}",
        f"Generated At (UTC): {created_at_iso}",
    ]
    for row in details:
        pdf.drawString(margin, y, row)
        y -= 14

    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "2. Emissions Declaration")
    y -= 16

    pdf.setFont("Helvetica", 10)
    metrics = [
        f"Total Emissions (tCO2e): {_to_float(total_co2_tonnes):,.3f}",
        f"Scope 1 Emissions (tCO2e): {_to_float(scope1_co2_tonnes):,.3f}",
        f"Scope 2 Emissions (tCO2e): {_to_float(scope2_co2_tonnes):,.3f}",
        f"Emission Intensity (tCO2e/t product): {_to_float(co2_per_tonne_product):,.3f}",
        f"EU Export Quantity (t): {_to_float(eu_export_tonnes):,.3f}",
        f"Embedded Emissions in EU Exports (tCO2e): {_to_float(eu_embedded_co2_tonnes):,.3f}",
    ]
    for row in metrics:
        pdf.drawString(margin, y, row)
        y -= 14

    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "3. CBAM Financial Exposure")
    y -= 16

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Estimated CBAM Liability: {_money(cbam_liability_eur, 'EUR')}")
    y -= 14
    pdf.drawString(margin, y, f"Estimated CBAM Liability (Local Currency): {_money(cbam_liability_inr, 'INR')}")
    y -= 20

    benchmark_label = str(report_payload.get("benchmark_label", "Needs improvement"))
    comparison_basis = str(report_payload.get("comparison_basis", "General"))
    summary = str(report_payload.get("summary", ""))
    top_issues = report_payload.get("top_issues", [])
    recommendations = report_payload.get("recommendations", [])

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "4. Benchmark Assessment")
    y -= 16
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Benchmark Label: {benchmark_label}")
    y -= 14
    pdf.drawString(margin, y, f"Comparison Basis: {comparison_basis}")
    y -= 16
    y = _draw_wrapped_text(
        pdf,
        f"Summary: {summary}",
        margin,
        y,
        max_text_width,
        13,
        "Helvetica",
        10,
    )

    y -= 6
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "5. Recommended Corrective Actions")
    y -= 16
    pdf.setFont("Helvetica", 10)

    for index, item in enumerate(recommendations[:5], start=1):
        if y < 90:
            pdf.showPage()
            y = page_h - margin
            pdf.setFont("Helvetica", 10)
        y = _draw_wrapped_text(
            pdf,
            f"{index}. {str(item)}",
            margin,
            y,
            max_text_width,
            13,
            "Helvetica",
            10,
        )

    if top_issues:
        y -= 4
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin, y, "Declared Issues:")
        y -= 14
        pdf.setFont("Helvetica", 10)
        for issue in top_issues[:4]:
            if y < 80:
                pdf.showPage()
                y = page_h - margin
                pdf.setFont("Helvetica", 10)
            y = _draw_wrapped_text(
                pdf,
                f"- {str(issue)}",
                margin,
                y,
                max_text_width,
                13,
                "Helvetica",
                10,
            )

    # Footer / verification block
    if y < 120:
        pdf.showPage()
        y = page_h - margin

    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "6. Verification and Traceability")
    y -= 16
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Blockchain Certified: {'Yes' if bool(tx_hash) else 'No'}")
    y -= 14
    pdf.drawString(margin, y, f"Transaction Hash: {tx_hash or 'Not available'}")
    y -= 14
    pdf.drawString(margin, y, f"Report Hash: {report_hash or 'Not available'}")

    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(
        margin,
        30,
        "This report is generated for EU CBAM compliance workflows and importer documentation support.",
    )

    pdf.save()
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    return pdf_bytes
