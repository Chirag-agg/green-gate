"""Cerebras LLM service for structured carbon data extraction."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import AsyncOpenAI


_EXTRACT_PROMPT = (
    "Extract structured carbon data from the following text.\n\n"
    "Return ONLY JSON:\n"
    "{\n"
    '  "electricity_kwh": number or null,\n'
    '  "diesel_liters": number or null,\n'
    '  "month": string or null\n'
    "}\n\n"
    "Text: {user_input}"
)

_MONTH_MAP = {
    "jan": "January",
    "january": "January",
    "feb": "February",
    "february": "February",
    "mar": "March",
    "march": "March",
    "apr": "April",
    "april": "April",
    "may": "May",
    "jun": "June",
    "june": "June",
    "jul": "July",
    "july": "July",
    "aug": "August",
    "august": "August",
    "sep": "September",
    "sept": "September",
    "september": "September",
    "oct": "October",
    "october": "October",
    "nov": "November",
    "november": "November",
    "dec": "December",
    "december": "December",
    # Hindi / Hinglish variants
    "janwari": "January",
    "farvari": "February",
    "march": "March",
    "aprail": "April",
    "jun": "June",
    "julai": "July",
    "agast": "August",
    "sitambar": "September",
    "aktubar": "October",
    "navambar": "November",
    "disambar": "December",
}


class CerebrasExtractionService:
    """Extracts structured emissions data with Cerebras API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
        self.base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1").strip()
        self.model = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507").strip()

        if not self.api_key:
            raise RuntimeError("CEREBRAS_API_KEY is missing in environment.")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    @staticmethod
    def _normalize_text(raw_text: str) -> str:
        """Normalize Hinglish/Hindi keywords into canonical English tokens."""
        text = str(raw_text or "")
        replacements = {
            "bijli": "electricity",
            "light bill": "electricity",
            "unit": "kwh",
            "diesel fuel": "diesel",
            "litre": "liter",
            "litres": "liters",
            "mahina": "month",
            "mahine": "month",
        }
        normalized = text.lower()
        for src, target in replacements.items():
            normalized = normalized.replace(src, target)
        return normalized

    @staticmethod
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

    @staticmethod
    def _normalize_month(month: Any) -> str | None:
        if month is None:
            return None
        token = str(month).strip().lower()
        if not token:
            return None
        token = token.replace(".", "")
        return _MONTH_MAP.get(token, str(month).strip().title())

    @staticmethod
    def _extract_json_block(raw: str) -> str:
        """Extract first JSON object from noisy LLM output safely."""
        raw = str(raw or "").strip()
        if raw.startswith("{") and raw.endswith("}"):
            return raw

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("LLM response did not contain a JSON object.")
        return match.group(0)

    def _normalize_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "electricity_kwh": self._safe_number(payload.get("electricity_kwh")),
            "diesel_liters": self._safe_number(payload.get("diesel_liters")),
            "month": self._normalize_month(payload.get("month")),
        }

    async def extract(self, raw_text: str) -> dict[str, Any]:
        """Call Cerebras and return strict structured JSON data."""
        normalized_text = self._normalize_text(raw_text)
        prompt = _EXTRACT_PROMPT.format(user_input=normalized_text)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You extract carbon metrics and return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )

        content = str(response.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = json.loads(self._extract_json_block(content))

        if not isinstance(parsed, dict):
            raise ValueError("Parsed extraction is not a JSON object.")

        return self._normalize_output(parsed)
