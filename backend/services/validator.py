"""Validation helpers for the voice chatbot state machine."""

from __future__ import annotations

from typing import Any


def _safe_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned.lower() in {"", "null", "none", "na", "n/a", "skip", "no"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class VoiceValidator:
    ELECTRICITY_MIN = 50.0
    ELECTRICITY_MAX = 1_000_000.0
    DIESEL_MIN = 1.0
    DIESEL_MAX = 100_000.0

    @staticmethod
    def normalize_month(text: Any) -> str | None:
        if text is None:
            return None
        value = str(text).strip()
        if not value:
            return None
        lower = value.lower()
        month_map = {
            "jan": "January",
            "january": "January",
            "janवरी": "January",
            "जनवरी": "January",
            "feb": "February",
            "february": "February",
            "फरवरी": "February",
            "mar": "March",
            "march": "March",
            "मार्च": "March",
            "apr": "April",
            "april": "April",
            "अप्रैल": "April",
            "may": "May",
            "मई": "May",
            "jun": "June",
            "june": "June",
            "जून": "June",
            "jul": "July",
            "july": "July",
            "जुलाई": "July",
            "aug": "August",
            "august": "August",
            "अगस्त": "August",
            "sep": "September",
            "september": "September",
            "सितंबर": "September",
            "oct": "October",
            "october": "October",
            "अक्टूबर": "October",
            "nov": "November",
            "november": "November",
            "नवंबर": "November",
            "dec": "December",
            "december": "December",
            "दिसंबर": "December",
        }
        for key, month in month_map.items():
            if key in lower:
                return month
        return None

    @classmethod
    def validate_electricity(cls, value: Any) -> tuple[float | None, str | None]:
        number = _safe_number(value)
        if number is None:
            return None, "Please repeat electricity usage."
        if not (cls.ELECTRICITY_MIN <= number <= cls.ELECTRICITY_MAX):
            return None, "Electricity value is out of range. Please repeat."
        return number, None

    @classmethod
    def validate_diesel(cls, value: Any) -> tuple[float | None, str | None]:
        number = _safe_number(value)
        if number is None:
            return None, None
        if not (cls.DIESEL_MIN <= number <= cls.DIESEL_MAX):
            return None, "Diesel value is out of range. Please repeat or say skip."
        return number, None

    @staticmethod
    def normalize_name_or_company(text: Any) -> str | None:
        value = str(text or "").strip()
        return value or None

    @staticmethod
    def is_yes(text: Any) -> bool:
        value = str(text or "").strip().lower()
        return value in {"yes", "y", "haan", "han", "ha", "haan ji", "yes please", "correct", "ok", "okay", "haanji"}

    @staticmethod
    def is_no(text: Any) -> bool:
        value = str(text or "").strip().lower()
        return value in {"no", "n", "nahin", "nahi", "nope", "incorrect", "reset", "change"}
