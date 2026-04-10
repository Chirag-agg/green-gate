"""EU-compliant CBAM XML generation and export utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import xml.etree.ElementTree as ET


def _to_float(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required and must be numeric.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value}") from exc


def _normalize_text(value: Any, *, default: str = "N/A") -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} is required and must be an object.")
    return value


def _require_text(value: Any, field_name: str) -> str:
    text = _normalize_text(value, default="")
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _validate_payload(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary.")

    # Required importer fields
    importer_name = _require_text(data.get("importer_name"), "importer_name")
    eori = _require_text(data.get("eori"), "eori")
    importer_country = _require_text(data.get("importer_country"), "importer_country")

    exporter_name = _require_text(data.get("exporter_name"), "exporter_name")
    exporter_country = _require_text(data.get("exporter_country"), "exporter_country")

    installation_id = _require_text(data.get("installation_id"), "installation_id")
    location = _require_text(data.get("location"), "location")

    product = _require_dict(data.get("product"), "product")
    emissions = _require_dict(data.get("emissions"), "emissions")
    cbam = _require_dict(data.get("cbam"), "cbam")
    verification = _require_dict(data.get("verification"), "verification")

    cn_code = _require_text(product.get("cn_code"), "product.cn_code")
    description = _normalize_text(product.get("description"))
    quantity = _to_float(product.get("quantity"), "product.quantity")
    embedded_emissions = _to_float(product.get("embedded_emissions"), "product.embedded_emissions")

    scope1 = _to_float(emissions.get("scope1"), "emissions.scope1")
    scope2 = _to_float(emissions.get("scope2"), "emissions.scope2")
    total = _to_float(emissions.get("total"), "emissions.total")

    ets_price = _to_float(cbam.get("ets_price"), "cbam.ets_price")
    total_cost = _to_float(cbam.get("total_cost"), "cbam.total_cost")

    verification_status = _normalize_text(verification.get("status"))
    report_hash = _normalize_text(verification.get("report_hash"))

    return {
        "importer_name": importer_name,
        "eori": eori,
        "importer_country": importer_country,
        "exporter_name": exporter_name,
        "exporter_country": exporter_country,
        "installation_id": installation_id,
        "location": location,
        "product": {
            "cn_code": cn_code,
            "description": description,
            "quantity": quantity,
            "embedded_emissions": embedded_emissions,
        },
        "emissions": {
            "scope1": scope1,
            "scope2": scope2,
            "total": total,
        },
        "cbam": {
            "ets_price": ets_price,
            "total_cost": total_cost,
        },
        "verification": {
            "status": verification_status,
            "report_hash": report_hash,
        },
    }


def generate_cbam_xml(data: dict[str, Any]) -> str:
    """Convert structured CBAM payload into EU-style CBAM XML string."""
    payload = _validate_payload(data)

    report_id = str(data.get("report_id") or f"CBAM-{uuid4().hex[:12].upper()}")
    generated_at = str(data.get("generated_at") or datetime.now(timezone.utc).isoformat())

    root = ET.Element("CBAMReport")

    report_id_el = ET.SubElement(root, "ReportID")
    report_id_el.text = report_id

    generated_at_el = ET.SubElement(root, "GeneratedAt")
    generated_at_el.text = generated_at

    declarant = ET.SubElement(root, "Declarant")
    declarant_name = ET.SubElement(declarant, "ImporterName")
    declarant_name.text = payload["importer_name"]
    declarant_eori = ET.SubElement(declarant, "EORI")
    declarant_eori.text = payload["eori"]
    declarant_country = ET.SubElement(declarant, "Country")
    declarant_country.text = payload["importer_country"]

    exporter = ET.SubElement(root, "Exporter")
    exporter_name = ET.SubElement(exporter, "Name")
    exporter_name.text = payload["exporter_name"]
    exporter_country = ET.SubElement(exporter, "Country")
    exporter_country.text = payload["exporter_country"]

    installation = ET.SubElement(root, "Installation")
    installation_id = ET.SubElement(installation, "InstallationID")
    installation_id.text = payload["installation_id"]
    installation_location = ET.SubElement(installation, "Location")
    installation_location.text = payload["location"]

    goods = ET.SubElement(root, "Goods")
    product = ET.SubElement(goods, "Product")
    product_cn = ET.SubElement(product, "CNCode")
    product_cn.text = payload["product"]["cn_code"]
    product_description = ET.SubElement(product, "Description")
    product_description.text = payload["product"]["description"]
    product_quantity = ET.SubElement(product, "Quantity", {"unit": "tonnes"})
    product_quantity.text = f"{payload['product']['quantity']:.2f}".rstrip("0").rstrip(".")
    product_embedded = ET.SubElement(product, "EmbeddedEmissions", {"unit": "tCO2"})
    product_embedded.text = f"{payload['product']['embedded_emissions']:.3f}".rstrip("0").rstrip(".")

    emissions = ET.SubElement(root, "Emissions")
    scope1 = ET.SubElement(emissions, "Scope1", {"unit": "tCO2"})
    scope1.text = f"{payload['emissions']['scope1']:.3f}".rstrip("0").rstrip(".")
    scope2 = ET.SubElement(emissions, "Scope2", {"unit": "tCO2"})
    scope2.text = f"{payload['emissions']['scope2']:.3f}".rstrip("0").rstrip(".")
    total = ET.SubElement(emissions, "Total", {"unit": "tCO2"})
    total.text = f"{payload['emissions']['total']:.3f}".rstrip("0").rstrip(".")

    cbam_cost = ET.SubElement(root, "CBAMCost")
    ets_price = ET.SubElement(cbam_cost, "ETSPrice", {"unit": "EUR/tCO2"})
    ets_price.text = f"{payload['cbam']['ets_price']:.2f}".rstrip("0").rstrip(".")
    total_cost = ET.SubElement(cbam_cost, "TotalCost", {"unit": "EUR"})
    total_cost.text = f"{payload['cbam']['total_cost']:.2f}".rstrip("0").rstrip(".")

    verification = ET.SubElement(root, "Verification")
    verification_status = ET.SubElement(verification, "Status")
    verification_status.text = payload["verification"]["status"]
    verification_hash = ET.SubElement(verification, "ReportHash")
    verification_hash.text = payload["verification"]["report_hash"]

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    xml_body = ET.tostring(root, encoding="unicode")
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + xml_body


def save_cbam_xml(data: dict[str, Any], filename: str) -> str:
    """Generate CBAM XML and save it as a .xml file."""
    xml_content = generate_cbam_xml(data)

    target = Path(filename)
    if target.suffix.lower() != ".xml":
        target = target.with_suffix(".xml")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(xml_content, encoding="utf-8")
    return str(target.resolve())
