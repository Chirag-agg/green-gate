"""Confidence score aggregation engine."""

from __future__ import annotations


class ConfidenceEngine:
    """Aggregates verification layer scores into one confidence score."""

    def calculate_confidence_score(
        self,
        credibility_score: float,
        machinery_score: float,
        regional_energy_score: float,
        temporal_score: float,
        supply_chain_score: float,
        twin_consistency_score: float,
    ) -> float:
        """Compute weighted confidence score normalized to [0, 1]."""
        confidence = (
            (0.25 * credibility_score)
            + (0.20 * machinery_score)
            + (0.15 * regional_energy_score)
            + (0.15 * temporal_score)
            + (0.15 * supply_chain_score)
            + (0.10 * twin_consistency_score)
        )
        return round(max(0.0, min(1.0, confidence)), 4)
