"""Verification engine for benchmark credibility scoring."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from services.benchmark_service import BenchmarkService
from services.emission_engine import EmissionEngine
from utils.logger import get_logger

logger = get_logger("verification_engine")


class VerificationEngine:
    """Classifies reported energy usage against benchmark expectations."""

    def verify_energy_claim(
        self,
        reported_energy: float,
        expected_energy: float,
    ) -> dict[str, float | str | list[str]]:
        """Verify claim and return deviation, score, and status metadata."""
        reported_energy = float(reported_energy or 0.0)
        expected_energy = float(expected_energy or 0.0)

        if expected_energy <= 0:
            logger.warn(
                "energy_claim_unverified_missing_benchmark",
                {"reported_energy": reported_energy, "expected_energy": expected_energy},
            )
            return {
                "expected_energy": expected_energy,
                "reported_energy": reported_energy,
                "deviation_ratio": 0.0,
                "credibility_score": 0.32,
                "verification_status": "insufficient_benchmark_data",
                "suspicious_fields": ["electricity_kwh"] if reported_energy > 0 else [],
            }

        deviation_ratio = reported_energy / expected_energy if expected_energy else 0.0

        if 0.8 <= deviation_ratio <= 1.2:
            verification_status = "normal"
        elif 0.5 <= deviation_ratio < 0.8:
            verification_status = "suspicious"
        elif deviation_ratio < 0.5:
            verification_status = "high_risk"
        elif deviation_ratio > 1.5:
            verification_status = "inefficient"
        else:
            verification_status = "normal"

        benchmark_score = min(1.0, max(deviation_ratio, 0.0))
        credibility_score = (0.6 * benchmark_score) + (0.4 * 0.8)

        suspicious_fields = []
        if verification_status in {"suspicious", "high_risk", "inefficient"}:
            suspicious_fields.append("electricity_kwh")

        result = {
            "expected_energy": round(expected_energy, 2),
            "reported_energy": round(reported_energy, 2),
            "deviation_ratio": round(deviation_ratio, 4),
            "credibility_score": round(credibility_score, 4),
            "verification_status": verification_status,
            "suspicious_fields": suspicious_fields,
        }

        logger.info("energy_claim_verified", result)
        return result

    def verify_report_consistency(
        self,
        input_data: dict[str, Any],
        stored_output: dict[str, Any],
        industry: str,
        annual_production_tonnes: float,
        region: str = "India",
        db: Session | None = None,
        threshold: float = 0.02,
    ) -> dict[str, Any]:
        """Recalculate emissions + benchmark and flag mismatches with stored output."""
        engine = EmissionEngine()
        benchmark_service = BenchmarkService()

        recalculated = engine.calculate(input_data)
        benchmark_comparison = benchmark_service.compare_intensity(
            industry=industry,
            annual_production_tonnes=annual_production_tonnes,
            observed_intensity=float(
                (recalculated.get("intensity", {}) or {}).get("value", 0.0) or 0.0
            ),
            region=region,
            db=db,
            machinery=str(input_data.get("machinery", "") or ""),
            energy_source=str(input_data.get("energy_source", "") or ""),
            scale=str(input_data.get("scale", "") or ""),
        )

        flags: list[str] = []

        def _validate_delta(field: str) -> None:
            expected = float(recalculated.get(field, 0.0) or 0.0)
            actual = float(stored_output.get(field, 0.0) or 0.0)
            if math.fabs(expected - actual) > threshold:
                flags.append(f"Mismatch in calculation: {field}")

        _validate_delta("total_co2_tonnes")
        _validate_delta("co2_per_tonne_product")
        _validate_delta("cbam_liability_eur")
        expected_intensity = float((recalculated.get("intensity", {}) or {}).get("value", 0.0) or 0.0)
        actual_intensity = float((stored_output.get("intensity", {}) or {}).get("value", 0.0) or 0.0)
        if expected_intensity and math.fabs(expected_intensity - actual_intensity) > 0.01:
            flags.append("Mismatch in intensity calculation")

        result = {
            "recalculated": recalculated,
            "benchmark_comparison": benchmark_comparison,
            "flags": flags,
            "is_consistent": len(flags) == 0,
        }
        logger.info(
            "report_consistency_verified",
            {
                "is_consistent": result["is_consistent"],
                "flag_count": len(flags),
                "industry": industry,
            },
        )
        return result
