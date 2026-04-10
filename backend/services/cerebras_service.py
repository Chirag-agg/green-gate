"""Cerebras extraction service used only for structured data extraction."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CerebrasService:
    def __init__(self) -> None:
        self.api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
        self.base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1").strip()
        self.model = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507").strip()

    @staticmethod
    def _extract_json(raw_text: str) -> dict[str, Any]:
        cleaned = str(raw_text or "").strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            return json.loads(cleaned)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError("Cerebras response does not contain JSON.")
        return json.loads(match.group(0))

    async def extract(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("CEREBRAS_API_KEY is missing.")

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=120,
        )
        text = str(response.choices[0].message.content or "").strip()
        if not text:
            raise ValueError("Empty Cerebras response.")
        return self._extract_json(text)

    async def extract_electricity(self, transcript: str) -> float | None:
        prompt = (
            "Extract electricity usage in kWh from this text. Return JSON: {\"electricity_kwh\": number or null} "
            f"Text: {transcript}"
        )
        result = await self.extract(prompt)
        value = result.get("electricity_kwh")
        return float(value) if value is not None else None

    async def extract_diesel(self, transcript: str) -> float | None:
        prompt = (
            "Extract diesel usage in liters from this text. Return JSON: {\"diesel_liters\": number or null} "
            f"Text: {transcript}"
        )
        result = await self.extract(prompt)
        value = result.get("diesel_liters")
        return float(value) if value is not None else None
