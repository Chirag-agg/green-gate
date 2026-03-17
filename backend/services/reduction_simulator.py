"""Carbon reduction simulation engine."""

from __future__ import annotations

import json
import os
from typing import Any


class ReductionSimulator:
    """Applies sequential reduction actions to emissions."""

    _actions_cache: dict[str, list[dict[str, Any]]] | None = None

    def __init__(self) -> None:
        if ReductionSimulator._actions_cache is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "reduction_actions.json",
            )
            with open(data_path, "r", encoding="utf-8") as file:
                loaded: Any = json.load(file)
                normalized: dict[str, list[dict[str, Any]]] = {}

                if isinstance(loaded, dict):
                    for sector, entries in loaded.items():
                        if not isinstance(entries, list):
                            continue
                        sector_key = str(sector).strip().lower()
                        normalized_entries: list[dict[str, Any]] = []
                        for item in entries:
                            if not isinstance(item, dict):
                                continue
                            action = str(item.get("action", "")).strip().lower()
                            reduction_percent = float(item.get("reduction_percent", 0.0) or 0.0)
                            payback_years = float(item.get("payback_years", 0.0) or 0.0)
                            normalized_entries.append(
                                {
                                    "action": action,
                                    "reduction_percent": reduction_percent,
                                    "payback_years": payback_years,
                                }
                            )
                        normalized[sector_key] = normalized_entries

                ReductionSimulator._actions_cache = normalized

    @property
    def actions_data(self) -> dict[str, list[dict[str, Any]]]:
        return ReductionSimulator._actions_cache or {}

    def simulate_reduction(
        self,
        current_emissions: float,
        actions: list[str],
    ) -> dict[str, float]:
        """Apply sequential reductions and return new emissions plus reduction amount."""
        baseline = max(float(current_emissions), 0.0)
        simulated_emissions = baseline

        factor_by_action: dict[str, float] = {}
        for sector_actions in self.actions_data.values():
            for entry in sector_actions:
                action_name = str(entry.get("action", "")).strip().lower()
                if not action_name or action_name in factor_by_action:
                    continue
                factor_by_action[action_name] = float(entry.get("reduction_percent", 0.0) or 0.0)

        for action in actions:
            reduction_percent = factor_by_action.get(str(action).strip().lower(), 0.0)
            reduction_percent = max(0.0, min(1.0, reduction_percent))
            simulated_emissions *= 1.0 - reduction_percent

        new_emissions = round(max(simulated_emissions, 0.0), 4)
        emission_reduction = round(max(baseline - new_emissions, 0.0), 4)

        return {
            "new_emissions": new_emissions,
            "emission_reduction": emission_reduction,
        }
