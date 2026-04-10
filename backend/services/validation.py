"""Validation service for extracted carbon metrics."""

from __future__ import annotations

from typing import Any


def _safe_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned.lower() in {"", "null", "none", "na", "n/a"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class ValidationService:
    """Applies range validations and returns corrected values with warnings."""

    ELECTRICITY_MIN = 50.0
    ELECTRICITY_MAX = 1_000_000.0
    DIESEL_MIN = 1.0
    DIESEL_MAX = 100_000.0

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = {
            "electricity_kwh": _safe_number(payload.get("electricity_kwh")),
            "diesel_liters": _safe_number(payload.get("diesel_liters")),
            "month": payload.get("month"),
        }

        corrected = dict(data)
        warnings: list[str] = []

        electricity = data["electricity_kwh"]
        if electricity is not None and not (self.ELECTRICITY_MIN <= electricity <= self.ELECTRICITY_MAX):
            corrected["electricity_kwh"] = _clamp(electricity, self.ELECTRICITY_MIN, self.ELECTRICITY_MAX)
            warnings.append(
                f"electricity_kwh out of range ({electricity}). Corrected to {corrected['electricity_kwh']}."
            )

        diesel = data["diesel_liters"]
        if diesel is not None and not (self.DIESEL_MIN <= diesel <= self.DIESEL_MAX):
            corrected["diesel_liters"] = _clamp(diesel, self.DIESEL_MIN, self.DIESEL_MAX)
            warnings.append(
                f"diesel_liters out of range ({diesel}). Corrected to {corrected['diesel_liters']}."
            )

        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
            "data": data,
            "corrected_data": corrected,
        }
