"""Verification engine for benchmark credibility scoring."""

from __future__ import annotations


class VerificationEngine:
    """Classifies reported energy usage against benchmark expectations."""

    def verify_energy_claim(
        self,
        reported_energy: float,
        expected_energy: float,
    ) -> dict[str, float | str | list[str]]:
        """Verify claim and return deviation, score, and status metadata."""
        if expected_energy <= 0:
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

        return {
            "expected_energy": round(expected_energy, 2),
            "reported_energy": round(reported_energy, 2),
            "deviation_ratio": round(deviation_ratio, 4),
            "credibility_score": round(credibility_score, 4),
            "verification_status": verification_status,
            "suspicious_fields": suspicious_fields,
        }
