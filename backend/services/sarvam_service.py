"""Sarvam AI extraction service for multilingual structured carbon data."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = (
    "Extract structured carbon data from the following multilingual input "
    "(Hindi, Hinglish, or English).\n\n"
    "Return ONLY JSON:\n"
    "{{\n"
    '"electricity_kwh": number or null,\n'
    '"diesel_liters": number or null,\n'
    '"month": string or null\n'
    "}}\n\n"
    "Text: {user_input}"
)


class SarvamService:
    """Calls Sarvam API and parses strict JSON extraction output."""

    def __init__(self) -> None:
        self.api_key = os.getenv("SARVAM_API_KEY", "").strip()
        self.api_url = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/v1/chat/completions").strip()
        self.model = os.getenv("SARVAM_MODEL", "sarvam-m").strip() or "sarvam-m"
        self.timeout = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "30"))

        if not self.api_key:
            logger.warning("SARVAM_API_KEY is missing. Falling back to local extraction.")

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
    def _extract_json_text(raw: str) -> str:
        text = str(raw or "").strip()
        if text.startswith("{") and text.endswith("}"):
            return text
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("Sarvam response does not contain valid JSON.")
        return match.group(0)

    @staticmethod
    def _normalize_month(month: Any) -> str | None:
        if month is None:
            return None
        token = str(month).strip()
        return token.title() if token else None

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "electricity_kwh": SarvamService._safe_number(payload.get("electricity_kwh")),
            "diesel_liters": SarvamService._safe_number(payload.get("diesel_liters")),
            "month": SarvamService._normalize_month(payload.get("month")),
        }

    @staticmethod
    def _local_fallback_extract(user_input: str) -> dict[str, Any]:
        """Best-effort parser when Sarvam API key is unavailable."""
        text = str(user_input or "")
        lower = text.lower()

        def pick_number(pattern: str) -> float | None:
            match = re.search(pattern, lower, flags=re.IGNORECASE)
            if not match:
                return None
            return SarvamService._safe_number(match.group(1))

        electricity = pick_number(r"(?:electricity|kwh|units?|bijli)\D{0,20}(\d+(?:\.\d+)?)")
        diesel = pick_number(r"(?:diesel|liters?|litres?)\D{0,20}(\d+(?:\.\d+)?)")

        if electricity is None:
            electricity = pick_number(r"(\d+(?:\.\d+)?)\s*(?:kwh|units?)")
        if diesel is None:
            diesel = pick_number(r"(\d+(?:\.\d+)?)\s*(?:liters?|litres?)\s*diesel")

        month_match = re.search(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
            lower,
            flags=re.IGNORECASE,
        )
        month = month_match.group(1).title() if month_match else None

        return {
            "electricity_kwh": electricity,
            "diesel_liters": diesel,
            "month": month,
        }

    @staticmethod
    def _extract_content_from_response(body: dict[str, Any]) -> str:
        """Support OpenAI-compatible and simple text response shapes."""
        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                text = first.get("text")
                if isinstance(text, str):
                    return text

        direct_text = body.get("output_text") or body.get("text") or body.get("response")
        if isinstance(direct_text, str):
            return direct_text

        raise ValueError("Unable to locate model output content in Sarvam response.")

    async def extract_structured_data(self, user_input: str) -> dict[str, Any]:
        """Extract structured emissions JSON from multilingual input text."""
        if not self.api_key:
            return self._normalize_payload(self._local_fallback_extract(user_input))

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(user_input=user_input)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 200,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info("Sending extraction request to Sarvam API")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.api_url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Sarvam API failed: {resp.status_code} {resp.text}")
                body = resp.json()

            content = self._extract_content_from_response(body)
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = json.loads(self._extract_json_text(content))

            if not isinstance(parsed, dict):
                raise ValueError("Sarvam output is not a JSON object.")

            normalized = self._normalize_payload(parsed)
            logger.info("Sarvam extraction parsed successfully")
            return normalized
        except Exception as exc:
            logger.warning("Sarvam extraction failed, using local fallback: %s", exc)
            return self._normalize_payload(self._local_fallback_extract(user_input))
