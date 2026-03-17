"""Supply chain optimization engine for Phase 4 simulation workflows."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models import FactoryCarbonReport, FactoryProfile, Product, ProductCarbonReport, SupplyChainNode

_BENCHMARKS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "eu_cbam_benchmarks.json"
)


class SupplyChainOptimizer:
    """Simulate supplier/factory replacement and estimate emission + CBAM impact."""

    def __init__(self) -> None:
        self.exa_api_key = os.getenv("EXA_API_KEY", "").strip()
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def _load_benchmarks(self) -> dict[str, Any]:
        try:
            with open(_BENCHMARKS_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {"default": {"benchmark_tco2_per_ton": 1.5, "carbon_price_eur": 90}}

    def _risk(self, ratio: float) -> str:
        if ratio <= 0.9:
            return "low"
        if ratio <= 1.1:
            return "moderate"
        if ratio <= 1.5:
            return "high"
        return "critical"

    async def optimize(
        self,
        db: Session,
        product: Product,
        target_factory: str | None,
        product_quantity: float = 1000.0,
    ) -> dict[str, Any]:
        """Run optimization simulation for a product and return suggested alternatives."""
        node_rows: list[SupplyChainNode] = (
            db.query(SupplyChainNode)
            .filter(SupplyChainNode.product_id == product.id)  # type: ignore[arg-type]
            .order_by(SupplyChainNode.created_at.asc())
            .all()
        )
        node_ids = [str(node.id) for node in node_rows]

        profiles: list[FactoryProfile] = (
            db.query(FactoryProfile)
            .filter(FactoryProfile.node_id.in_(node_ids))  # type: ignore[arg-type]
            .all()
            if node_ids
            else []
        )
        if not profiles:
            raise ValueError("No factory profiles found. Run factory analysis first.")

        profile_ids = [str(profile.id) for profile in profiles]
        reports: list[FactoryCarbonReport] = (
            db.query(FactoryCarbonReport)
            .filter(FactoryCarbonReport.factory_profile_id.in_(profile_ids))  # type: ignore[arg-type]
            .all()
            if profile_ids
            else []
        )
        if not reports:
            raise ValueError("No factory carbon reports found. Run factory analysis first.")

        profiles_by_id = {str(profile.id): profile for profile in profiles}
        nodes_by_id = {str(node.id): node for node in node_rows}

        current_total = sum(self._to_float(report.total_emissions) for report in reports)
        if current_total <= 0:
            raise ValueError("Current product emissions are zero; optimization requires non-zero emissions.")

        current_factory_details: list[dict[str, Any]] = []
        for report in reports:
            profile = profiles_by_id.get(str(report.factory_profile_id))
            if profile is None:
                continue
            node = nodes_by_id.get(str(profile.node_id))
            total = self._to_float(report.total_emissions)
            current_factory_details.append(
                {
                    "factory_profile_id": str(profile.id),
                    "node_id": str(profile.node_id),
                    "company": str(profile.company_name or "Unknown"),
                    "location": str(profile.location or "Unknown"),
                    "machinery": str(profile.machinery_type or "unknown"),
                    "role": str(node.role if node is not None else "manufacturing"),
                    "total_emissions": total,
                    "share": (total / current_total),
                    "confidence": self._to_float(report.confidence_score, self._to_float(profile.confidence, 0.0)),
                }
            )

        current_factory_details.sort(key=lambda item: item["total_emissions"], reverse=True)

        selected = self._select_target(current_factory_details, target_factory)
        if selected is None:
            raise ValueError("No target factory available for optimization")

        selected_emissions = self._to_float(selected.get("total_emissions"), 0.0)
        selected_share = self._to_float(selected.get("share"), 0.0)

        alternatives = await self._search_alternatives(
            company=str(selected.get("company", "")),
            role=str(selected.get("role", "manufacturing")),
            sector=str(product.sector),  # type: ignore[arg-type]
            baseline_emissions=selected_emissions,
        )

        if not alternatives:
            alternatives = self._fallback_alternatives(selected_emissions)

        # Simulate replacement for each alternative
        qty = max(product_quantity, 1.0)
        benchmarks = self._load_benchmarks()
        sector_data = benchmarks.get(str(product.sector).lower().strip(), benchmarks.get("default", {}))  # type: ignore[arg-type]
        eu_benchmark = self._to_float(sector_data.get("benchmark_tco2_per_ton", 1.5), 1.5)
        carbon_price = self._to_float(sector_data.get("carbon_price_eur", 90), 90)

        current_intensity = current_total / qty
        current_excess = max(current_intensity - eu_benchmark, 0.0)
        current_cbam_per_ton = current_excess * carbon_price
        current_cbam_total = current_cbam_per_ton * qty

        for alt in alternatives:
            alt_total = self._to_float(alt.get("estimated_emissions"), selected_emissions)
            optimized_total = current_total - selected_emissions + alt_total
            optimized_intensity = optimized_total / qty
            optimized_excess = max(optimized_intensity - eu_benchmark, 0.0)
            optimized_cbam_per_ton = optimized_excess * carbon_price
            optimized_cbam_total = optimized_cbam_per_ton * qty

            alt["optimized_total_emissions"] = optimized_total
            alt["optimized_intensity"] = optimized_intensity
            alt["optimized_cbam_tax_total"] = optimized_cbam_total
            alt["emission_reduction"] = max(current_total - optimized_total, 0.0)
            alt["cbam_savings"] = max(current_cbam_total - optimized_cbam_total, 0.0)
            alt["optimized_cbam_risk"] = self._risk(optimized_intensity / eu_benchmark if eu_benchmark > 0 else 0.0)

        alternatives.sort(
            key=lambda alt: (self._to_float(alt.get("cbam_savings")), self._to_float(alt.get("emission_reduction"))),
            reverse=True,
        )

        best = alternatives[0]
        optimized_total = self._to_float(best.get("optimized_total_emissions"), current_total)
        optimized_intensity = self._to_float(best.get("optimized_intensity"), current_intensity)
        optimized_cbam_total = self._to_float(best.get("optimized_cbam_tax_total"), current_cbam_total)

        base_report = (
            db.query(ProductCarbonReport)
            .filter(ProductCarbonReport.product_id == product.id)  # type: ignore[arg-type]
            .first()
        )
        current_confidence = self._to_float(base_report.product_confidence if base_report else None, 0.0)
        optimized_confidence = min(1.0, max(0.0, current_confidence + 0.03))

        return {
            "product_id": str(product.id),
            "product_name": str(product.product_name),  # type: ignore[arg-type]
            "target_factory": str(selected.get("company", "Unknown")),
            "target_factory_share": round(selected_share * 100, 2),
            "current_emissions": round(current_total, 4),
            "optimized_emissions": round(optimized_total, 4),
            "emission_reduction": round(max(current_total - optimized_total, 0.0), 4),
            "current_intensity": round(current_intensity, 6),
            "optimized_intensity": round(optimized_intensity, 6),
            "eu_benchmark": eu_benchmark,
            "current_cbam_tax": round(current_cbam_total, 4),
            "optimized_cbam_tax": round(optimized_cbam_total, 4),
            "cbam_savings": round(max(current_cbam_total - optimized_cbam_total, 0.0), 4),
            "current_cbam_risk": self._risk(current_intensity / eu_benchmark if eu_benchmark > 0 else 0.0),
            "optimized_cbam_risk": self._risk(optimized_intensity / eu_benchmark if eu_benchmark > 0 else 0.0),
            "current_confidence": round(current_confidence, 6),
            "optimized_confidence": round(optimized_confidence, 6),
            "suggested_suppliers": alternatives,
            "current_factories": current_factory_details,
            "product_quantity": qty,
        }

    def _select_target(self, factories: list[dict[str, Any]], target_factory: str | None) -> dict[str, Any] | None:
        if not factories:
            return None
        if target_factory:
            needle = target_factory.strip().lower()
            for row in factories:
                if needle in str(row.get("company", "")).lower():
                    return row
        return factories[0]

    async def _search_alternatives(
        self,
        company: str,
        role: str,
        sector: str,
        baseline_emissions: float,
    ) -> list[dict[str, Any]]:
        """Search and estimate alternative lower-carbon suppliers."""
        query = f"low carbon {sector} manufacturers electric arc furnace Europe"

        exa_results = await self._search_exa(query)
        tavily_results = await self._search_tavily(query)
        candidates = self._extract_candidates(exa_results, tavily_results)

        if not candidates:
            return []

        alternatives: list[dict[str, Any]] = []
        for idx, candidate in enumerate(candidates[:6]):
            website = str(candidate.get("url", ""))
            context = await self._scrape_website(website) if website else ""
            machinery = self._infer_machinery(candidate.get("title", ""), candidate.get("snippet", ""), context)
            intensity_multiplier = self._estimate_intensity_multiplier(machinery, candidate.get("snippet", ""), context)
            estimated_emissions = max(0.0, baseline_emissions * intensity_multiplier)
            confidence = max(0.45, 0.82 - idx * 0.06)

            alternatives.append(
                {
                    "company": candidate.get("company") or candidate.get("title") or f"Alternative Supplier {idx + 1}",
                    "location": candidate.get("location") or "Europe",
                    "machinery": machinery,
                    "estimated_emissions": round(estimated_emissions, 4),
                    "estimated_emission_intensity": round(intensity_multiplier, 4),
                    "confidence": round(confidence, 4),
                    "source": website,
                    "temporary_node": {
                        "company": candidate.get("company") or candidate.get("title") or f"Alternative Supplier {idx + 1}",
                        "location": candidate.get("location") or "Europe",
                        "machinery": machinery,
                        "estimated_emissions": round(estimated_emissions, 4),
                        "confidence": round(confidence, 4),
                    },
                }
            )

        return alternatives

    async def _search_exa(self, query: str) -> list[dict[str, Any]]:
        if not self.exa_api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.exa.ai/search",
                    headers={"Authorization": f"Bearer {self.exa_api_key}"},
                    json={"query": query, "numResults": 8},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                return results if isinstance(results, list) else []
        except Exception:
            return []

    async def _search_tavily(self, query: str) -> list[dict[str, Any]]:
        if not self.tavily_api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": self.tavily_api_key, "query": query, "max_results": 8},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                return results if isinstance(results, list) else []
        except Exception:
            return []

    async def _scrape_website(self, website_url: str) -> str:
        if not self.firecrawl_api_key or not website_url:
            return ""

        pages = [
            website_url,
            f"{website_url.rstrip('/')}/about",
            f"{website_url.rstrip('/')}/sustainability",
            f"{website_url.rstrip('/')}/operations",
        ]

        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in pages:
                try:
                    response = await client.post(
                        "https://api.firecrawl.dev/v1/scrape",
                        headers={"Authorization": f"Bearer {self.firecrawl_api_key}"},
                        json={"url": page, "formats": ["markdown"]},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    markdown = payload.get("data", {}).get("markdown") if isinstance(payload.get("data"), dict) else ""
                    if isinstance(markdown, str) and markdown.strip():
                        chunks.append(markdown)
                except Exception:
                    continue

        return "\n".join(chunks)

    def _extract_candidates(self, exa_results: list[dict[str, Any]], tavily_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in exa_results:
            rows.append(
                {
                    "title": str(item.get("title", "")),
                    "snippet": str(item.get("text", "")),
                    "url": str(item.get("url", "")),
                    "company": str(item.get("title", "")),
                    "location": "Europe",
                }
            )
        for item in tavily_results:
            rows.append(
                {
                    "title": str(item.get("title", "")),
                    "snippet": str(item.get("content", "")),
                    "url": str(item.get("url", "")),
                    "company": str(item.get("title", "")),
                    "location": "Europe",
                }
            )

        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row.get("url") or row.get("title")).strip().lower()
            if not key or key in unique:
                continue
            unique[key] = row

        return [
            value for value in unique.values()
            if value.get("title") or value.get("company")
        ]

    def _infer_machinery(self, title: Any, snippet: Any, context: str) -> str:
        corpus = f"{str(title)} {str(snippet)} {context}".lower()
        if "electric arc furnace" in corpus or "eaf" in corpus:
            return "electric_arc_furnace"
        if "hydrogen" in corpus or "h2" in corpus:
            return "hydrogen_direct_reduction"
        if "blast furnace" in corpus:
            return "blast_furnace"
        if "recycled" in corpus:
            return "recycled_feedstock_mill"
        return "advanced_low_carbon_process"

    def _estimate_intensity_multiplier(self, machinery: str, snippet: Any, context: str) -> float:
        corpus = f"{machinery} {str(snippet)} {context}".lower()
        if "hydrogen" in corpus:
            return 0.45
        if "electric_arc_furnace" in corpus or "eaf" in corpus:
            return 0.55
        if "renewable" in corpus:
            return 0.6
        if "recycled" in corpus:
            return 0.62
        if "blast_furnace" in corpus:
            return 0.9
        return 0.7

    def _fallback_alternatives(self, baseline_emissions: float) -> list[dict[str, Any]]:
        rows = [
            ("H2 Green Steel", "Sweden", "hydrogen_direct_reduction", 0.45, 0.75),
            ("SSAB EAF Division", "Sweden", "electric_arc_furnace", 0.55, 0.72),
            ("ArcelorMittal EAF Plants", "Europe", "electric_arc_furnace", 0.62, 0.68),
        ]

        output: list[dict[str, Any]] = []
        for company, location, machinery, multiplier, confidence in rows:
            output.append(
                {
                    "company": company,
                    "location": location,
                    "machinery": machinery,
                    "estimated_emissions": round(baseline_emissions * multiplier, 4),
                    "estimated_emission_intensity": multiplier,
                    "confidence": confidence,
                    "source": "heuristic_fallback",
                    "temporary_node": {
                        "company": company,
                        "location": location,
                        "machinery": machinery,
                        "estimated_emissions": round(baseline_emissions * multiplier, 4),
                        "confidence": confidence,
                    },
                }
            )
        return output
