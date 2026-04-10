"""Benchmark service for expected energy and intensity from similar factories."""

from __future__ import annotations

import json
import math
import os
from urllib import error as urlerror
from urllib import parse, request
from typing import Any

from sqlalchemy.orm import Session

from models import CarbonReport, IndustryBenchmark

from utils.logger import get_logger

logger = get_logger("benchmark_service")


class BenchmarkService:
    """Calculates expected benchmark metrics from reference factory peers."""

    def __init__(self) -> None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self._eu_benchmarks = self._load_json(os.path.join(data_dir, "eu_cbam_benchmarks.json"))
        self._industry_intensity = self._load_json(
            os.path.join(data_dir, "industry_emission_intensity.json")
        )
        self._api_url = os.getenv("EMISSION_FACTOR_API_URL", "").strip()
        self._india_regions = {
            "india",
            "maharashtra",
            "gujarat",
            "punjab",
            "rajasthan",
            "odisha",
            "tamil nadu",
            "karnataka",
            "west bengal",
            "uttar pradesh",
            "haryana",
        }

    @staticmethod
    def _load_json(path: str) -> dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            parsed = float(value)
            if math.isnan(parsed) or math.isinf(parsed):
                return default
            return parsed
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_industry(industry: str) -> str:
        normalized = industry.strip().lower().replace(" ", "_")
        aliases = {
            "textile": "textiles",
            "aluminium": "aluminum",
            "steel_bfbof": "steel",
            "steel_eaf": "steel",
            "fertiliser": "fertilizers",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_seed_industry(industry: str) -> str:
        normalized = industry.strip().lower().replace(" ", "_")
        aliases = {
            "textiles": "textile",
            "steel_eaf": "steel",
            "steel_bfbof": "steel",
            "foods": "food",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_machinery(machinery: str | None) -> str:
        if not machinery:
            return ""
        normalized = machinery.strip().lower().replace(" ", "_")
        aliases = {
            "furnace": "blast_furnace",
            "dye": "dyeing",
            "automated_line": "automated",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_energy_source(energy_source: str | None) -> str:
        if not energy_source:
            return ""
        normalized = energy_source.strip().lower().replace(" ", "_")
        aliases = {
            "grid": "electric",
            "electricity": "electric",
            "natural_gas": "gas",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _derive_scale(annual_production_tonnes: float, explicit_scale: str | None = None) -> str:
        if explicit_scale:
            return explicit_scale.strip().lower()
        production = float(annual_production_tonnes or 0.0)
        if production <= 1000:
            return "micro"
        if production <= 5000:
            return "small"
        if production <= 20000:
            return "medium"
        return "enterprise"

    def _is_india_region(self, region: str) -> bool:
        normalized_region = region.strip().lower()
        return normalized_region in self._india_regions

    def _fetch_emission_factor(self, energy_source: str) -> tuple[float, bool]:
        """Fetch an optional multiplier from external API; never fail closed."""
        if not self._api_url:
            return 1.0, False

        source = self._normalize_energy_source(energy_source)
        if not source:
            return 1.0, False

        url = f"{self._api_url}?energy_source={parse.quote(source)}"
        try:
            with request.urlopen(url, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            factor = self._safe_float(
                payload.get("factor", payload.get("multiplier", payload.get("emission_factor", 1.0))),
                1.0,
            )
            if factor <= 0:
                return 1.0, False
            return factor, True
        except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            logger.warn(
                "benchmark_emission_factor_api_failed",
                {
                    "energy_source": source,
                    "error": str(exc),
                },
            )
            return 1.0, False

    def _load_curated_candidates(
        self,
        db: Session,
        region: str,
        use_india_dataset: bool,
    ) -> list[IndustryBenchmark]:
        if not use_india_dataset:
            return []

        normalized_region = (region or "India").strip().lower()
        regional = (
            db.query(IndustryBenchmark)
            .filter(IndustryBenchmark.region.ilike(normalized_region))
            .all()
        )
        if regional:
            return regional

        india_fallback = (
            db.query(IndustryBenchmark)
            .filter(IndustryBenchmark.region.ilike("india"))
            .all()
        )
        if india_fallback:
            return india_fallback

        return db.query(IndustryBenchmark).all()

    def _score_benchmark_candidate(
        self,
        industry: str,
        machinery: str,
        energy_source: str,
        scale: str,
        candidate: IndustryBenchmark,
    ) -> int:
        score = 0
        candidate_industry = self._normalize_seed_industry(candidate.industry)
        candidate_machinery = self._normalize_machinery(candidate.machinery_type)
        candidate_energy = self._normalize_energy_source(candidate.energy_source)
        candidate_scale = str(candidate.scale or "").strip().lower()

        if industry and industry == candidate_industry:
            score += 50
        if machinery and machinery == candidate_machinery:
            score += 30
        if energy_source and energy_source == candidate_energy:
            score += 10
        if scale and scale == candidate_scale:
            score += 10

        return score

    @staticmethod
    def _confidence_from_match(score: int, confidence_label: str, api_applied: bool) -> float:
        confidence_map = {
            "high": 0.9,
            "medium": 0.75,
            "low": 0.6,
        }
        row_confidence = confidence_map.get((confidence_label or "medium").strip().lower(), 0.65)
        match_confidence = max(0.0, min(1.0, score / 100.0))
        hybrid_confidence = (0.7 * match_confidence) + (0.3 * row_confidence)
        if api_applied:
            hybrid_confidence = min(1.0, hybrid_confidence + 0.05)
        return round(hybrid_confidence, 2)

    def get_benchmark(
        self,
        industry: str,
        annual_production_tonnes: float,
        region: str = "India",
        db: Session | None = None,
        observed_intensity: float | None = None,
        machinery: str | None = None,
        energy_source: str | None = None,
        scale: str | None = None,
    ) -> dict[str, Any]:
        """Return normalized benchmark structure for industry and company scale."""
        legacy_industry_key = self._normalize_industry(industry)
        industry_key = self._normalize_seed_industry(industry)
        normalized_machinery = self._normalize_machinery(machinery)
        normalized_energy_source = self._normalize_energy_source(energy_source)
        normalized_scale = self._derive_scale(
            self._safe_float(annual_production_tonnes),
            explicit_scale=scale,
        )

        dataset_source = "fallback:industry_average"
        industry_avg = 0.0
        best_in_class = 0.0
        source_detail = "fallback"
        match_level = "fallback"
        similarity_score = 0
        confidence_label = "low"
        best_match: IndustryBenchmark | None = None
        use_india_dataset = self._is_india_region(region)

        if not use_india_dataset:
            dataset_source = "eu:benchmark_only"

        if db is not None:
            curated_candidates = self._load_curated_candidates(db=db, region=region, use_india_dataset=use_india_dataset)
            if curated_candidates:
                scored = [
                    (
                        self._score_benchmark_candidate(
                            industry=industry_key,
                            machinery=normalized_machinery,
                            energy_source=normalized_energy_source,
                            scale=normalized_scale,
                            candidate=candidate,
                        ),
                        candidate,
                    )
                    for candidate in curated_candidates
                ]
                scored.sort(key=lambda item: item[0], reverse=True)
                exact_matches = [item for item in scored if item[0] == 100]
                partial_matches = [item for item in scored if 60 <= item[0] < 100]
                industry_only_matches = [item for item in scored if 50 <= item[0] < 60]

                if exact_matches:
                    similarity_score, best_match = exact_matches[0]
                    match_level = "exact"
                elif partial_matches:
                    similarity_score, best_match = partial_matches[0]
                    match_level = "partial"
                elif industry_only_matches:
                    similarity_score, best_match = industry_only_matches[0]
                    match_level = "industry-only"

            if best_match is not None:
                dataset_source = "dataset:curated"
                source_detail = str(best_match.source or "curated")
                confidence_label = str(best_match.confidence or "medium")
                # Curated intensity is in tCO2/ton; normalize to kgCO2/unit.
                industry_avg = self._safe_float(best_match.avg_intensity, 0.0) * 1000.0
                best_in_class = self._safe_float(best_match.best_in_class, 0.0) * 1000.0

        if industry_avg <= 0 and db is not None and use_india_dataset:
            regional_reports = (
                db.query(CarbonReport)
                .filter(CarbonReport.sector == industry)
                .filter(CarbonReport.state == region)
                .all()
            )
            all_reports = db.query(CarbonReport).filter(CarbonReport.sector == industry).all()

            selected_reports = regional_reports if regional_reports else all_reports
            if regional_reports:
                dataset_source = "db:industry_region"
                source_detail = "observed_reports_region"
            elif all_reports:
                dataset_source = "db:industry_all"
                source_detail = "observed_reports_all"

            if selected_reports:
                intensities = [
                    self._safe_float(report.co2_per_tonne_product, 0.0) * 1000.0
                    for report in selected_reports
                    if self._safe_float(report.co2_per_tonne_product, 0.0) > 0
                ]
                if intensities:
                    industry_avg = sum(intensities) / len(intensities)
                    best_in_class = min(intensities)
                    similarity_score = max(similarity_score, 50 if use_india_dataset else 40)
                    confidence_label = "medium"
                    match_level = "industry-only"

        if industry_avg <= 0:
            dataset_source = "fallback:json_india" if use_india_dataset else "fallback:json_eu"
            source_detail = "static_dataset"
            eu_entry = self._eu_benchmarks.get(legacy_industry_key, self._eu_benchmarks.get("default", {}))
            eu_avg = self._safe_float(
                eu_entry.get("benchmark_tco2_per_ton", eu_entry.get("benchmark_tco2_per_tonne", 0.0)),
                0.0,
            )
            static_avg = self._safe_float(self._industry_intensity.get(legacy_industry_key, 0.0), 0.0)
            baseline_avg_tonnes = static_avg if use_india_dataset else eu_avg
            if baseline_avg_tonnes <= 0:
                baseline_avg_tonnes = eu_avg or static_avg or 1.5
            # Convert tCO2/t into kgCO2/unit for consistency.
            industry_avg = baseline_avg_tonnes * 1000.0
            best_in_class = industry_avg * 0.8
            similarity_score = max(similarity_score, 25)
            confidence_label = "low"
            match_level = "fallback"

        # Normalize for scale in-place.
        if normalized_scale == "micro":
            scale_multiplier = 1.1
        elif normalized_scale == "small":
            scale_multiplier = 1.05
        elif normalized_scale == "medium":
            scale_multiplier = 1.0
        else:
            scale_multiplier = 0.95
        industry_avg *= scale_multiplier
        best_in_class *= scale_multiplier

        emission_factor_multiplier, api_applied = self._fetch_emission_factor(normalized_energy_source)
        industry_avg *= emission_factor_multiplier
        best_in_class *= emission_factor_multiplier

        benchmark_industry = industry_key or legacy_industry_key
        comparison_basis = " + ".join(
            [
                benchmark_industry.replace("_", " ").title() if benchmark_industry else "General",
                normalized_machinery.replace("_", " ").title() if normalized_machinery else "General Machinery",
                normalized_energy_source.replace("_", " ").title() if normalized_energy_source else "Mixed Energy",
            ]
        )
        confidence_score = self._confidence_from_match(
            score=similarity_score,
            confidence_label=confidence_label,
            api_applied=api_applied,
        )

        benchmark = {
            "industry": benchmark_industry,
            "avg_intensity": round(industry_avg, 4),
            "best_in_class": round(best_in_class, 4),
            "unit": "kgCO2/unit",
            "scale": normalized_scale,
            "source": dataset_source,
            "source_detail": source_detail,
            "match_level": match_level,
            "data_source": "hybrid",
            "comparison_basis": comparison_basis,
            "similarity_score": similarity_score,
            "confidence_score": confidence_score,
            "api_enriched": api_applied,
            "api_factor": round(emission_factor_multiplier, 4),
            "machinery": normalized_machinery,
            "energy_source": normalized_energy_source,
        }

        logger.info("benchmark_dataset_used", {"source": dataset_source, "region": region})
        logger.info(
            "benchmark_profile_built",
            {
                "industry": benchmark_industry,
                "scale": normalized_scale,
                "machinery": normalized_machinery,
                "energy_source": normalized_energy_source,
                "similarity_score": similarity_score,
                "match_level": match_level,
                "observed_intensity": self._safe_float(observed_intensity, 0.0),
                "avg_intensity": benchmark["avg_intensity"],
                "best_in_class": benchmark["best_in_class"],
            },
        )
        return benchmark

    def compare_intensity(
        self,
        industry: str,
        annual_production_tonnes: float,
        observed_intensity: float,
        region: str = "India",
        db: Session | None = None,
        machinery: str | None = None,
        energy_source: str | None = None,
        scale: str | None = None,
    ) -> dict[str, Any]:
        """Compare observed intensity against normalized benchmark."""
        benchmark = self.get_benchmark(
            industry=industry,
            annual_production_tonnes=annual_production_tonnes,
            region=region,
            db=db,
            observed_intensity=observed_intensity,
            machinery=machinery,
            energy_source=energy_source,
            scale=scale,
        )

        user_value = self._safe_float(observed_intensity, 0.0)
        industry_avg = self._safe_float(benchmark.get("avg_intensity"), 0.0)
        best_in_class = self._safe_float(benchmark.get("best_in_class"), 0.0)

        label = "Needs improvement"
        if user_value <= best_in_class:
            label = "Best-in-class"
        elif user_value <= industry_avg:
            label = "Above average"

        vs_benchmark_pct = 0.0
        if industry_avg > 0:
            vs_benchmark_pct = ((user_value - industry_avg) / industry_avg) * 100

        comparison = {
            "user_value": round(user_value, 4),
            "industry_avg": round(industry_avg, 4),
            "best_in_class": round(best_in_class, 4),
            "label": label,
            "status": label,
            "unit": benchmark.get("unit", "kgCO2/unit"),
            "source": benchmark.get("source", "unknown"),
            "vs_benchmark_pct": round(vs_benchmark_pct, 2),
            "data_source": benchmark.get("data_source", "hybrid"),
            "comparison_basis": benchmark.get("comparison_basis", "General"),
            "confidence_score": self._safe_float(benchmark.get("confidence_score", 0.0), 0.0),
            "api_enriched": bool(benchmark.get("api_enriched", False)),
            "benchmark": {
                "avg": round(industry_avg, 4),
                "best": round(best_in_class, 4),
                "label": label,
                "unit": benchmark.get("unit", "kgCO2/unit"),
            },
            "benchmark_details": {
                "industry": benchmark.get("industry", industry),
                "avg_intensity": round(industry_avg, 4),
                "best_in_class": round(best_in_class, 4),
                "machinery": benchmark.get("machinery", ""),
                "energy_source": benchmark.get("energy_source", ""),
                "source_detail": benchmark.get("source_detail", ""),
                "similarity_score": int(benchmark.get("similarity_score", 0) or 0),
                "match_level": benchmark.get("match_level", "fallback"),
            },
        }

        logger.info("benchmark_comparison_completed", comparison)
        return comparison

    def calculate_expected_energy(
        self, similar_factories: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Return average expected electricity and emission intensity for matched peers."""
        if not similar_factories:
            logger.warn("benchmark_peers_missing", {"peer_count": 0})
            return {
                "expected_energy": 0.0,
                "expected_emission_intensity": 0.0,
            }

        electricity_values = [self._safe_float(factory.get("electricity_kwh", 0), 0.0) for factory in similar_factories]
        emission_intensities = [
            self._safe_float(factory.get("emission_intensity", 0), 0.0)
            for factory in similar_factories
        ]

        expected_energy = sum(electricity_values) / len(electricity_values)
        expected_emission_intensity = sum(emission_intensities) / len(emission_intensities)

        logger.info(
            "expected_energy_computed",
            {
                "peer_count": len(similar_factories),
                "expected_energy": round(expected_energy, 2),
                "expected_emission_intensity": round(expected_emission_intensity, 4),
            },
        )

        return {
            "expected_energy": round(expected_energy, 2),
            "expected_emission_intensity": round(expected_emission_intensity, 4),
        }
