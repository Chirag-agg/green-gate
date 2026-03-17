"""Company intelligence enrichment service using Exa, Tavily, and Firecrawl."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx


MACHINERY_KEYWORDS = {
    "electric_arc_furnace": ["electric arc furnace", "eaf"],
    "blast_furnace": ["blast furnace", "bf-bof", "basic oxygen furnace"],
    "rotary_kiln": ["rotary kiln", "clinker kiln"],
    "smelter": ["smelter", "smelting"],
}

COMMON_EXPORT_MARKETS = [
    "Germany",
    "Netherlands",
    "France",
    "Italy",
    "Belgium",
    "Spain",
    "United Kingdom",
    "United States",
    "UAE",
    "Japan",
]

INDIAN_STATES = [
    "Maharashtra", "Gujarat", "Punjab", "Rajasthan", "Odisha", "Tamil Nadu",
    "Karnataka", "West Bengal", "Uttar Pradesh", "Haryana", "Andhra Pradesh",
    "Bihar", "Chhattisgarh", "Delhi", "Goa", "Jharkhand", "Kerala",
    "Madhya Pradesh", "Telangana", "Assam",
]


class CompanyIntelligenceService:
    """Collect and infer company profile signals from public web sources."""

    def __init__(self) -> None:
        self.exa_api_key = os.getenv("EXA_API_KEY", "").strip()
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()

    async def discover_company_profile(
        self,
        company_name: str,
        state: str,
        sector: str,
    ) -> dict[str, Any]:
        """Run intelligence discovery and return structured company profile."""
        exa_query = f"{company_name} manufacturing plant production capacity machinery"
        tavily_query = (
            f"What does {company_name} manufacture and where are their factories located?"
        )

        exa_results = await self._search_exa(exa_query)
        tavily_results = await self._search_tavily(tavily_query)

        website = self._extract_official_website(exa_results, tavily_results)
        firecrawl_text = await self._scrape_firecrawl_website(website) if website else ""

        combined_text = self._build_combined_text(exa_results, tavily_results, firecrawl_text)

        likely_machinery = self._infer_machinery(combined_text, sector)
        estimated_production = self._infer_production_scale(combined_text)
        export_markets = self._infer_export_markets(combined_text)
        factory_location = self._infer_factory_location(combined_text, state)

        summary = combined_text.strip()
        if len(summary) > 1200:
            summary = f"{summary[:1197]}..."

        sources = self._build_sources(exa_results, tavily_results, website)

        discovered_company_profile = {
            "company_name": company_name,
            "factory_location": factory_location,
            "estimated_production": estimated_production,
            "export_markets": export_markets,
            "likely_machinery": likely_machinery,
            "data_sources": sources,
            "scraped_summary": summary,
        }

        return {
            "discovered_company_profile": discovered_company_profile,
            "sources": sources,
            "suggested_machinery": likely_machinery,
            "suggested_production_range": estimated_production,
        }

    async def _search_exa(self, query: str) -> list[dict[str, Any]]:
        if not self.exa_api_key:
            return []

        url = "https://api.exa.ai/search"
        payload = {"query": query, "numResults": 5}
        headers = {"Authorization": f"Bearer {self.exa_api_key}"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                return results if isinstance(results, list) else []
        except Exception:
            return []

    async def _search_tavily(self, query: str) -> list[dict[str, Any]]:
        if not self.tavily_api_key:
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "max_results": 5,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                return results if isinstance(results, list) else []
        except Exception:
            return []

    async def _scrape_firecrawl_website(self, website_url: str) -> str:
        if not self.firecrawl_api_key or not website_url:
            return ""

        url = "https://api.firecrawl.dev/v1/scrape"
        headers = {"Authorization": f"Bearer {self.firecrawl_api_key}"}

        pages = [
            website_url,
            f"{website_url.rstrip('/')}/about",
            f"{website_url.rstrip('/')}/manufacturing",
            f"{website_url.rstrip('/')}/sustainability",
        ]

        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in pages:
                try:
                    response = await client.post(
                        url,
                        headers=headers,
                        json={"url": page, "formats": ["markdown"]},
                    )
                    response.raise_for_status()
                    data = response.json()
                    markdown = (
                        data.get("data", {}).get("markdown")
                        if isinstance(data.get("data"), dict)
                        else ""
                    )
                    if isinstance(markdown, str) and markdown.strip():
                        chunks.append(markdown)
                except Exception:
                    continue

        return "\n".join(chunks)

    def _extract_official_website(
        self,
        exa_results: list[dict[str, Any]],
        tavily_results: list[dict[str, Any]],
    ) -> str:
        for item in exa_results + tavily_results:
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            lowered = url.lower()
            if any(domain in lowered for domain in ["linkedin.com", "wikipedia.org", "youtube.com"]):
                continue
            return url
        return ""

    def _build_combined_text(
        self,
        exa_results: list[dict[str, Any]],
        tavily_results: list[dict[str, Any]],
        firecrawl_text: str,
    ) -> str:
        chunks: list[str] = []
        for item in exa_results:
            text = f"{item.get('title', '')} {item.get('text', '')}"
            if text.strip():
                chunks.append(text)
        for item in tavily_results:
            text = f"{item.get('title', '')} {item.get('content', '')}"
            if text.strip():
                chunks.append(text)
        if firecrawl_text.strip():
            chunks.append(firecrawl_text)
        return "\n".join(chunks)

    def _infer_machinery(self, text: str, sector: str) -> list[str]:
        lowered = text.lower()
        matches: list[str] = []

        for machinery, keywords in MACHINERY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(machinery)

        if matches:
            return matches

        sector_key = sector.strip().lower()
        if sector_key == "steel_eaf":
            return ["electric_arc_furnace"]
        if sector_key == "steel_bfbof":
            return ["blast_furnace"]
        if sector_key == "cement":
            return ["rotary_kiln"]
        if sector_key.startswith("aluminium"):
            return ["smelter"]

        return ["electric_arc_furnace"]

    def _infer_production_scale(self, text: str) -> str:
        pattern = re.compile(
            r"(\d+[\d,\.]*)(?:\s*(k|m))?\s*(?:tonnes|tons|tpa|tonnes per year|tons per year)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return "Unknown"

        value = match.group(1)
        suffix = (match.group(2) or "").lower()

        try:
            numeric = float(value.replace(",", ""))
        except ValueError:
            return "Unknown"

        if suffix == "m":
            numeric *= 1_000_000
        elif suffix == "k":
            numeric *= 1_000

        low = max(int(numeric * 0.8), 0)
        high = max(int(numeric * 1.2), low)
        return f"{low:,}–{high:,} tons annually"

    def _infer_export_markets(self, text: str) -> list[str]:
        found = [country for country in COMMON_EXPORT_MARKETS if country.lower() in text.lower()]
        return found[:5]

    def _infer_factory_location(self, text: str, fallback_state: str) -> str:
        for state in INDIAN_STATES:
            if state.lower() in text.lower():
                return state
        return fallback_state

    def _build_sources(
        self,
        exa_results: list[dict[str, Any]],
        tavily_results: list[dict[str, Any]],
        website: str,
    ) -> list[str]:
        urls: list[str] = []
        if website:
            urls.append(website)
        for item in exa_results:
            url = str(item.get("url", "")).strip()
            if url and url not in urls:
                urls.append(url)
        for item in tavily_results:
            url = str(item.get("url", "")).strip()
            if url and url not in urls:
                urls.append(url)
        return urls[:8]
