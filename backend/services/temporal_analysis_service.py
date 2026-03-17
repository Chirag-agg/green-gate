"""Temporal consistency verification service."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from models import CarbonReport


class TemporalAnalysisService:
    """Evaluates new report energy value against user historical reports."""

    def calculate_temporal_score(
        self,
        db: Session,
        user_id: str,
        new_electricity_value: float,
    ) -> float:
        """Return temporal consistency score based on deviation from recent history."""
        if new_electricity_value < 0:
            return 0.4

        recent_reports = (
            db.query(CarbonReport)
            .filter(CarbonReport.user_id == user_id)
            .order_by(CarbonReport.created_at.desc())
            .limit(3)
            .all()
        )

        historical_values: list[float] = []
        for report in recent_reports:
            full_input_json = getattr(report, "full_input_json", None)
            if full_input_json:
                try:
                    payload = json.loads(str(full_input_json))
                    electricity_monthly = float(payload.get("electricity_kwh_per_month", 0))
                    reported_annual = electricity_monthly * 12.0
                    if reported_annual > 0:
                        historical_values.append(reported_annual)
                        continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass

            expected_energy = getattr(report, "expected_energy", None)
            deviation_ratio = getattr(report, "deviation_ratio", None)
            if expected_energy is not None and deviation_ratio is not None:
                estimated_reported = float(expected_energy) * float(deviation_ratio)
                if estimated_reported > 0:
                    historical_values.append(estimated_reported)

        if not historical_values:
            return 0.8

        historical_mean = sum(historical_values) / len(historical_values)
        if historical_mean <= 0:
            return 0.8

        deviation = abs(new_electricity_value - historical_mean) / historical_mean

        if deviation < 0.2:
            return 1.0
        if 0.2 <= deviation <= 0.4:
            return 0.7
        return 0.4
