"""Industrial twin service for benchmark-based factory similarity matching."""

from __future__ import annotations

import json
import os
from typing import Any


class IndustrialTwinService:
    """Finds similar reference factories from verified benchmark datasets."""

    _factories_cache: list[dict[str, Any]] | None = None

    def __init__(self) -> None:
        if IndustrialTwinService._factories_cache is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "verified_factories.json",
            )
            with open(data_path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
                IndustrialTwinService._factories_cache = loaded if isinstance(loaded, list) else []

    @property
    def factories(self) -> list[dict[str, Any]]:
        return IndustrialTwinService._factories_cache or []

    def find_similar_factories(
        self,
        product_type: str,
        machinery: str,
        production_volume: float,
    ) -> list[dict[str, Any]]:
        """Return top-3 closest factories by production volume for matching type and machinery."""
        product_type_normalized = product_type.strip().lower()
        machinery_normalized = machinery.strip().lower()

        matches = [
            factory
            for factory in self.factories
            if str(factory.get("product_type", "")).strip().lower() == product_type_normalized
            and str(factory.get("machinery", "")).strip().lower() == machinery_normalized
        ]

        if not matches:
            return []

        ranked = sorted(
            matches,
            key=lambda factory: abs(float(factory.get("production_volume", 0)) - production_volume),
        )
        return ranked[:3]
