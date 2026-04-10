"""Personalized carbon reduction recommendations for MSMEs.

Rule-based personalization uses:
- Industry
- Scale
- Region
- Energy source
- Production type
- CBAM export context
"""

import json
import logging
import os
from typing import Any

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT: str = (
    "You are an expert industrial carbon reduction consultant specializing in "
    "Indian MSMEs. You always respond in valid JSON only. No markdown, no "
    "explanation, just a JSON array."
)


def _build_user_prompt(input_data: dict[str, Any], result: dict[str, Any]) -> str:
    """Build the prompt from calculation inputs and results."""
    total = result.get("total_co2_tonnes", 0) or 1
    breakdown = result.get("breakdown", {})
    elec = breakdown.get("electricity_co2_tonnes", 0)
    coal = breakdown.get("coal_co2_tonnes", 0)
    diesel = breakdown.get("diesel_co2_tonnes", 0)

    elec_pct = round((elec / (total if total else 1)) * 100, 1)
    coal_pct = round((coal / (total if total else 1)) * 100, 1)
    diesel_pct = round((diesel / (total if total else 1)) * 100, 1)

    vs = result.get("vs_benchmark_pct", 0)
    direction = "above" if vs >= 0 else "below"

    return (
        f"An Indian MSME in the {input_data.get('sector', 'unknown')} sector "
        f"located in {input_data.get('state', 'unknown')} has the following carbon profile:\n"
        f"- Total annual CO2: {result.get('total_co2_tonnes', 0)} tonnes\n"
        f"- Electricity emissions: {elec} tonnes ({elec_pct}% of total)\n"
        f"- Coal emissions: {coal} tonnes ({coal_pct}% of total)\n"
        f"- Diesel emissions: {diesel} tonnes ({diesel_pct}% of total)\n"
        f"- Current vs sector benchmark: {abs(vs)}% {direction} benchmark\n"
        f"- Annual production: {input_data.get('annual_production_tonnes', 0)} tonnes\n"
        f"- CBAM liability: EUR {result.get('cbam_liability_eur', 0)} "
        f"(INR {result.get('cbam_liability_inr', 0)})\n\n"
        "Return a JSON array of exactly 3 recommendations, each with:\n"
        "{\n"
        "  \"rank\": 1,\n"
        "  \"title\": \"Short action title\",\n"
        "  \"action\": \"Specific, concrete action for this MSME\",\n"
        "  \"emission_reduction_tonnes\": <float>,\n"
        "  \"emission_reduction_pct\": <float>,\n"
        "  \"annual_cost_saving_inr\": <float>,\n"
        "  \"cbam_saving_eur\": <float>,\n"
        "  \"cbam_saving_inr\": <float>,\n"
        "  \"payback_months\": <int>,\n"
        "  \"difficulty\": \"Easy\" | \"Medium\" | \"Hard\",\n"
        "  \"implementation_steps\": [\"step 1\", \"step 2\", \"step 3\"]\n"
        "}\n"
        "Rank by ROI (best ROI = rank 1). Be specific and quantified. "
        "Use real Indian market prices."
    )


def _get_fallback_recommendations(
    input_data: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return hardcoded fallback recommendations when AI providers are unavailable."""
    total = result.get("total_co2_tonnes", 1)
    cbam_eur = result.get("cbam_liability_eur", 0)

    return [
        {
            "rank": 1,
            "title": "Install Rooftop Solar System",
            "action": (
                f"Install a 100 kW rooftop solar system to offset grid electricity. "
                f"This can reduce electricity emissions by up to 40%, saving approximately "
                f"{round(total * 0.15, 1)} tonnes of CO2 annually."
            ),
            "emission_reduction_tonnes": round(total * 0.15, 1),
            "emission_reduction_pct": 15.0,
            "annual_cost_saving_inr": round(total * 0.15 * 90 * 90 * 0.3, 2),
            "cbam_saving_eur": round(cbam_eur * 0.15, 2),
            "cbam_saving_inr": round(cbam_eur * 0.15 * 90, 2),
            "payback_months": 36,
            "difficulty": "Medium",
            "implementation_steps": [
                "Get a structural assessment of your rooftop",
                "Obtain quotes from 3+ MNRE-empanelled solar vendors",
                "Apply for state solar subsidy (30-40% available in most states)",
                "Install system and apply for net metering with your DISCOM",
            ],
        },
        {
            "rank": 2,
            "title": "Switch to Natural Gas from Coal",
            "action": (
                f"Replace coal-fired boilers with natural gas. Natural gas emits "
                f"40-50% less CO2 per unit of energy compared to coal. Potential "
                f"reduction of {round(total * 0.12, 1)} tonnes CO2 per year."
            ),
            "emission_reduction_tonnes": round(total * 0.12, 1),
            "emission_reduction_pct": 12.0,
            "annual_cost_saving_inr": round(total * 0.12 * 90 * 90 * 0.2, 2),
            "cbam_saving_eur": round(cbam_eur * 0.12, 2),
            "cbam_saving_inr": round(cbam_eur * 0.12 * 90, 2),
            "payback_months": 24,
            "difficulty": "Hard",
            "implementation_steps": [
                "Check PNG/CNG availability from local gas distributor",
                "Get quotation for gas pipeline connection and boiler conversion",
                "Apply for industrial gas connection from GAIL/city gas company",
                "Schedule boiler replacement during planned maintenance shutdown",
            ],
        },
        {
            "rank": 3,
            "title": "Implement Energy Efficiency Measures",
            "action": (
                f"Conduct a BEE-certified energy audit and implement VFDs on motors, "
                f"LED lighting, and waste heat recovery. Expected reduction of "
                f"{round(total * 0.08, 1)} tonnes CO2 annually."
            ),
            "emission_reduction_tonnes": round(total * 0.08, 1),
            "emission_reduction_pct": 8.0,
            "annual_cost_saving_inr": round(total * 0.08 * 90 * 90 * 0.5, 2),
            "cbam_saving_eur": round(cbam_eur * 0.08, 2),
            "cbam_saving_inr": round(cbam_eur * 0.08 * 90, 2),
            "payback_months": 18,
            "difficulty": "Easy",
            "implementation_steps": [
                "Hire a BEE-certified energy auditor to assess your facility",
                "Install VFDs on all motors above 5 HP — typical savings 20-30%",
                "Replace all lighting with industrial LEDs",
                "Install waste heat recovery on furnaces/boilers if applicable",
            ],
        },
    ]


def _normalize_recommendations(payload: Any) -> list[dict[str, Any]]:
    """Normalize provider output into a list of recommendation dictionaries."""
    parsed = payload

    if isinstance(parsed, str):
        stripped = parsed.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return []

    if isinstance(parsed, dict):
        for key in ("recommendations", "data", "results"):
            value = parsed.get(key)
            if isinstance(value, list):
                parsed = value
                break

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)][:3]

    return []


async def _get_cerebras_recommendations(
    input_data: dict[str, Any], calculation_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch recommendations from Cerebras using OpenAI-compatible API."""
    api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if not api_key:
        return []

    model = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")
    base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    user_prompt = _build_user_prompt(input_data, calculation_result)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    content: str = response.choices[0].message.content or "[]"
    return _normalize_recommendations(content)


async def _get_ollama_recommendations(
    input_data: dict[str, Any], calculation_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch recommendations from Ollama local endpoint."""
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

    user_prompt = _build_user_prompt(input_data, calculation_result)
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"User request:\n{user_prompt}\n\n"
        "Return valid JSON only."
    )

    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    return _normalize_recommendations(data.get("response", ""))


async def get_recommendations(
    input_data: dict[str, Any], calculation_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Generate recommendations from both rule-based and LLM sources."""
    offline_only = os.getenv("RECOMMENDATIONS_OFFLINE_ONLY", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    profile_industry = str(input_data.get("industry") or input_data.get("sector") or "general").strip().lower()
    profile_scale = str(input_data.get("scale") or "small").strip().lower()
    profile_location = str(input_data.get("location") or input_data.get("region") or input_data.get("state") or "India")
    profile_energy_source = str(input_data.get("energy_source") or "grid").strip().lower()
    profile_production_type = str(input_data.get("production_type") or "mixed").strip().lower()

    benchmark = calculation_result.get("benchmark_comparison", {})
    intensity_payload = calculation_result.get("intensity", {})
    intensity_value = float((intensity_payload.get("value", 0.0) or 0.0))
    industry_avg = float((benchmark.get("industry_avg", 0.0) or 0.0))

    exports_to_eu = bool(
        input_data.get("exports_to_eu")
        or float(input_data.get("eu_export_tonnes", 0.0) or 0.0) > 0
    )

    logger.info(
        "recommendation_inputs",
        {
            "industry": profile_industry,
            "scale": profile_scale,
            "location": profile_location,
            "energy_source": profile_energy_source,
            "production_type": profile_production_type,
            "exports_to_eu": exports_to_eu,
            "intensity": intensity_value,
            "industry_avg": industry_avg,
        },
    )

    rule_based: list[dict[str, Any]] = []
    ai_based: list[dict[str, Any]] = []

    if profile_industry.startswith("textile") and profile_energy_source == "coal":
        rule_based.append(
            {
                "category": "Energy",
                "problem": "Coal-based thermal process in textile operations",
                "solution": "Switch to gas or biomass to reduce emissions by ~30%",
                "impact": "Potential reduction in process emissions by ~30%",
            }
        )

    if intensity_value > industry_avg > 0:
        rule_based.append(
            {
                "category": "Machinery",
                "problem": "Emission intensity above comparable units",
                "solution": "Your emissions exceed similar units — optimize machinery efficiency",
                "impact": "Reduces intensity and improves benchmark standing",
            }
        )

    if intensity_value > industry_avg > 0 and profile_scale == "small":
        rule_based.append(
            {
                "category": "Finance",
                "problem": "Small-scale unit above benchmark",
                "solution": "Upgrade to energy-efficient machinery under MSME subsidy schemes",
                "impact": "Lower intensity and improved competitiveness in 12–24 months",
            }
        )

    electricity_tonnes = float((calculation_result.get("breakdown", {}) or {}).get("electricity_co2_tonnes", 0.0) or 0.0)
    total_tonnes = float(calculation_result.get("total_co2_tonnes", 0.0) or 0.0)
    if total_tonnes > 0 and (electricity_tonnes / total_tonnes) >= 0.45:
        rule_based.append(
            {
                "category": "Energy",
                "problem": "High electricity dependence",
                "solution": "Install solar rooftop with Indian MSME subsidy alignment",
                "impact": "Reduce electricity cost by 20–30% with lower Scope-2 emissions",
            }
        )

    if profile_production_type in {"continuous", "batch"}:
        rule_based.append(
            {
                "category": "Process",
                "problem": "Process energy losses",
                "solution": "Implement process-level monitoring and heat recovery checkpoints",
                "impact": "Improves throughput efficiency and reduces avoidable fuel usage",
            }
        )

    if exports_to_eu:
        rule_based.append(
            {
                "category": "Compliance",
                "problem": "EU export exposure under CBAM",
                "solution": "Maintain monthly emissions evidence and prepare product-level traceability",
                "impact": "Reduces CBAM reporting risk and improves importer confidence",
            }
        )

    if profile_location.strip().lower() == "india":
        rule_based.append(
            {
                "category": "Compliance",
                "problem": "Domestic + export compliance overlap",
                "solution": "Adopt Indian baseline tracking and parallel CBAM evidence pack",
                "impact": "Single data pipeline for domestic and EU reporting",
            }
        )

    # Always attempt LLM enrichment after rule-based recommendations unless explicitly disabled.
    if not offline_only:
        try:
            ai_based = await _get_cerebras_recommendations(input_data, calculation_result)
            if not ai_based:
                ai_based = await _get_ollama_recommendations(input_data, calculation_result)
        except Exception as exc:
            logger.warning("LLM failed, using fallback: %s", str(exc))
            ai_based = []

    if not ai_based:
        ai_based = _get_fallback_recommendations(input_data, calculation_result)

    merged_recommendations: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for recommendation in (rule_based + ai_based):
        if not isinstance(recommendation, dict):
            continue
        title = str(recommendation.get("title") or recommendation.get("problem") or "").strip()
        action = str(recommendation.get("action") or recommendation.get("solution") or "").strip()
        if not title and not action:
            continue
        dedupe_key = f"{title.lower()}::{action.lower()}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged_recommendations.append(recommendation)

    if len(merged_recommendations) == 0:
        merged_recommendations.append(
            {
                "category": "Process",
                "problem": "No major issues detected",
                "solution": "No major issues detected based on current data",
                "impact": "Continue monitoring to preserve current performance",
            }
        )

    for idx, recommendation in enumerate(merged_recommendations, start=1):
        recommendation["rank"] = idx
        recommendation["title"] = str(recommendation.get("title") or recommendation.get("problem") or "Recommendation")
        recommendation["action"] = str(recommendation.get("action") or recommendation.get("solution") or recommendation["title"])

    logger.info(
        "recommendation_outputs",
        {
            "rule_based_count": len(rule_based),
            "ai_based_count": len(ai_based),
            "final_count": len(merged_recommendations),
        },
    )
    return merged_recommendations[:6]
