from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
from statistics import pstdev
from typing import Any, Dict, List, Optional


# CBAM baseline ranges used to detect impossible/suspicious declared operational data.
INDUSTRY_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "steel": {
        "min_energy_intensity": 350.0,
        "max_energy_intensity": 700.0,
        "min_physical_energy": 280.0,
        "typical_fuel_ratio": 35.0,
        "max_single_jump_pct": 0.35,
    },
    "cement": {
        "min_energy_intensity": 80.0,
        "max_energy_intensity": 130.0,
        "min_physical_energy": 65.0,
        "typical_fuel_ratio": 18.0,
        "max_single_jump_pct": 0.30,
    },
    "aluminium": {
        "min_energy_intensity": 13500.0,
        "max_energy_intensity": 15500.0,
        "min_physical_energy": 12800.0,
        "typical_fuel_ratio": 5.0,
        "max_single_jump_pct": 0.20,
    },
    "chemicals": {
        "min_energy_intensity": 200.0,
        "max_energy_intensity": 600.0,
        "min_physical_energy": 150.0,
        "typical_fuel_ratio": 25.0,
        "max_single_jump_pct": 0.40,
    },
}


@dataclass
class CarbonInput:
    production: float
    electricity: float
    fuel: Optional[float]
    industry: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    evidence_provided: bool = False

    # CBAM data quality guard to reject structurally invalid submissions before scoring.
    def validate_types(self) -> None:
        if self.production <= 0:
            raise ValueError("production must be > 0")
        if self.electricity < 0:
            raise ValueError("electricity must be >= 0")
        if self.fuel is not None and self.fuel < 0:
            raise ValueError("fuel must be >= 0 when provided")
        if self.industry not in INDUSTRY_BENCHMARKS:
            raise ValueError(
                f"industry must be one of: {', '.join(sorted(INDUSTRY_BENCHMARKS.keys()))}"
            )


@dataclass
class LayerResult:
    passed: bool
    penalty: int
    flags: List[str]
    details: Dict[str, Any]


# CBAM consistency check for declared energy/fuel intensity against sector norms.
def check_consistency(data: CarbonInput) -> LayerResult:
    try:
        data.validate_types()
        benchmark: Dict[str, float] = INDUSTRY_BENCHMARKS[data.industry]

        energy_per_ton: float = data.electricity / data.production
        fuel_per_ton: float = (data.fuel / data.production) if data.fuel is not None else 0.0

        midpoint: float = (
            benchmark["min_energy_intensity"] + benchmark["max_energy_intensity"]
        ) / 2.0
        pct_deviation_from_midpoint: float = (
            ((energy_per_ton - midpoint) / midpoint) * 100.0 if midpoint > 0 else 0.0
        )

        flags: List[str] = []
        if energy_per_ton < benchmark["min_energy_intensity"]:
            flags.append("Energy suspiciously low")
        if energy_per_ton > benchmark["max_energy_intensity"]:
            flags.append("Energy suspiciously high")
        if data.fuel is not None and fuel_per_ton > benchmark["typical_fuel_ratio"] * 2.0:
            flags.append("Fuel usage anomalous")

        return LayerResult(
            passed=(len(flags) == 0),
            penalty=(-30 if flags else 0),
            flags=flags,
            details={
                "energy_per_ton": float(energy_per_ton),
                "fuel_per_ton": float(fuel_per_ton),
                "pct_deviation_from_midpoint": float(pct_deviation_from_midpoint),
            },
        )
    except Exception as exc:
        return LayerResult(
            passed=False,
            penalty=-30,
            flags=[f"Validation error: {exc}"],
            details={
                "energy_per_ton": 0.0,
                "fuel_per_ton": 0.0,
                "pct_deviation_from_midpoint": 0.0,
            },
        )


# CBAM physical floor check to detect thermodynamically impossible declarations.
def check_physical_constraints(data: CarbonInput) -> LayerResult:
    try:
        data.validate_types()
        benchmark: Dict[str, float] = INDUSTRY_BENCHMARKS[data.industry]
        expected_minimum: float = data.production * benchmark["min_physical_energy"]
        deficit_kwh: float = max(0.0, expected_minimum - data.electricity)

        flags: List[str] = []
        if data.electricity < expected_minimum:
            flags.append("Physically impossible: violates thermodynamic minimum")

        return LayerResult(
            passed=(len(flags) == 0),
            penalty=(-40 if flags else 0),
            flags=flags,
            details={
                "expected_minimum": float(expected_minimum),
                "actual_electricity": float(data.electricity),
                "deficit_kwh": float(deficit_kwh),
            },
        )
    except Exception as exc:
        return LayerResult(
            passed=False,
            penalty=-40,
            flags=[f"Validation error: {exc}"],
            details={
                "expected_minimum": 0.0,
                "actual_electricity": float(getattr(data, "electricity", 0.0) or 0.0),
                "deficit_kwh": 0.0,
            },
        )


# CBAM behavioral integrity check for repetitive or abrupt reporting patterns.
def check_behavioral_patterns(data: CarbonInput, history: List[CarbonInput]) -> LayerResult:
    try:
        data.validate_types()
        for item in history:
            item.validate_types()

        benchmark: Dict[str, float] = INDUSTRY_BENCHMARKS[data.industry]
        flags: List[str] = []

        prior_same_count: int = sum(1 for h in history if abs(h.electricity - data.electricity) < 1e-9)
        if prior_same_count >= 2:
            flags.append("Repeated identical values")

        values: List[float] = [h.electricity for h in history] + [data.electricity]
        variance: float = pstdev(values) if len(values) >= 2 else 0.0
        if variance < 0.01:
            flags.append("Zero variance across submissions")

        pct_change_from_last: float = 0.0
        if history:
            last_val: float = history[-1].electricity
            if last_val > 0:
                pct_change_from_last = abs(data.electricity - last_val) / last_val
            elif data.electricity > 0:
                pct_change_from_last = 1.0

            if pct_change_from_last > benchmark["max_single_jump_pct"]:
                flags.append("Unrealistic jump from last submission")

        return LayerResult(
            passed=(len(flags) == 0),
            penalty=(-20 if flags else 0),
            flags=flags,
            details={
                "variance": float(variance),
                "pct_change_from_last": float(pct_change_from_last),
                "history_count": int(len(history)),
            },
        )
    except Exception as exc:
        return LayerResult(
            passed=False,
            penalty=-20,
            flags=[f"Validation error: {exc}"],
            details={
                "variance": 0.0,
                "pct_change_from_last": 0.0,
                "history_count": int(len(history)),
            },
        )


# CBAM evidence presence check to nudge document-backed submissions.
def check_evidence(data: CarbonInput) -> LayerResult:
    try:
        data.validate_types()
        flags: List[str] = []
        evidence_boost: bool = False
        penalty: int = 0

        if not data.evidence_provided:
            flags.append("No supporting documents")
            penalty = -10
        else:
            evidence_boost = True
            penalty = 5

        return LayerResult(
            passed=(len(flags) == 0),
            penalty=penalty,
            flags=flags,
            details={"evidence_boost": evidence_boost},
        )
    except Exception as exc:
        return LayerResult(
            passed=False,
            penalty=-10,
            flags=[f"Validation error: {exc}"],
            details={"evidence_boost": False},
        )


# CBAM scoring synthesizer that converts multi-layer outcomes into one enforcement score.
def compute_score(results: List[LayerResult]) -> Dict[str, Any]:
    layer_names: List[str] = ["consistency", "physical", "behavioral", "evidence"]
    try:
        normalized: List[LayerResult] = results[:4]
        while len(normalized) < 4:
            normalized.append(
                LayerResult(
                    passed=False,
                    penalty=-20,
                    flags=["Validation error: Missing layer result"],
                    details={},
                )
            )

        total_penalty: int = sum(int(r.penalty) for r in normalized)
        final_score: int = max(0, min(100, 100 + total_penalty))

        risk_level: str
        if final_score >= 80:
            risk_level = "Low"
        elif final_score >= 50:
            risk_level = "Medium"
        else:
            risk_level = "High"

        all_flags: List[str] = [flag for r in normalized for flag in r.flags]
        breakdown: Dict[str, str] = {
            layer_names[i]: ("pass" if normalized[i].passed else "fail") for i in range(4)
        }
        layer_details: Dict[str, Dict[str, Any]] = {
            layer_names[i]: dict(normalized[i].details) for i in range(4)
        }

        return {
            "score": int(final_score),
            "risk_level": risk_level,
            "all_flags": all_flags,
            "breakdown": breakdown,
            "layer_details": layer_details,
        }
    except Exception as exc:
        return {
            "score": 0,
            "risk_level": "High",
            "all_flags": [f"Validation error: {exc}"],
            "breakdown": {
                "consistency": "fail",
                "physical": "fail",
                "behavioral": "fail",
                "evidence": "fail",
            },
            "layer_details": {
                "consistency": {},
                "physical": {},
                "behavioral": {},
                "evidence": {},
            },
        }


# CBAM output assembler for UI, audit trail, and blockchain anchoring payload.
def build_output(data: CarbonInput, score_result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        score: int = int(score_result.get("score", 0))
        risk_level: str = str(score_result.get("risk_level", "High"))
        flags: List[str] = list(score_result.get("all_flags", []))
        breakdown: Dict[str, str] = dict(score_result.get("breakdown", {}))
        layer_details: Dict[str, Dict[str, Any]] = dict(score_result.get("layer_details", {}))

        if risk_level == "Low":
            cbam_risk_message = "Low risk: submission is unlikely to trigger EU default emission values"
            score_color = "green"
        elif risk_level == "Medium":
            cbam_risk_message = "Medium risk: submission may receive additional scrutiny under CBAM"
            score_color = "orange"
        else:
            cbam_risk_message = "High risk: EU may apply default emission values (3x levy)"
            score_color = "red"

        failed_layers: List[str] = [name for name, status in breakdown.items() if status == "fail"]
        if "physical" in failed_layers:
            suggestion = "Re-check meter calibration and production logs; current values violate physical minimums."
        elif "consistency" in failed_layers:
            suggestion = "Align declared energy/fuel with sector benchmark ranges and attach meter evidence."
        elif "behavioral" in failed_layers:
            suggestion = "Provide operational notes for abrupt changes and avoid repeated copy-forward values."
        elif "evidence" in failed_layers:
            suggestion = "Upload invoices, utility bills, and process records to strengthen trust score."
        else:
            suggestion = "Maintain current reporting discipline and continue attaching source documents."

        pct_deviation: float = float(
            layer_details.get("consistency", {}).get("pct_deviation_from_midpoint", 0.0)
        )

        warning_banner: str = (
            "CBAM trust engine detected anomalies that can trigger default levy treatment."
            if risk_level == "High"
            else "Submission has moderate risk signals; review before filing."
            if risk_level == "Medium"
            else "Submission appears internally consistent for CBAM trust checks."
        )

        evidence_nudge: str = (
            "Upload supporting documents to reduce CBAM audit risk."
            if not data.evidence_provided
            else ""
        )

        explanations: List[str] = [f"Detected issue: {flag}." for flag in flags]

        payload: str = json.dumps(asdict(data), sort_keys=True)
        data_hash: str = hashlib.sha256(payload.encode()).hexdigest()

        return {
            "score": score,
            "risk_level": risk_level,
            "cbam_risk_message": cbam_risk_message,
            "flags": flags,
            "breakdown": {
                "consistency": breakdown.get("consistency", "fail"),
                "physical": breakdown.get("physical", "fail"),
                "behavioral": breakdown.get("behavioral", "fail"),
                "evidence": breakdown.get("evidence", "fail"),
            },
            "ui_hooks": {
                "score_color": score_color,
                "warning_banner": warning_banner,
                "suggestion": suggestion,
                "pct_deviation": float(pct_deviation),
                "evidence_nudge": evidence_nudge,
            },
            "explanations": explanations,
            "blockchain_payload": {
                "data_hash": data_hash,
                "timestamp": data.timestamp,
                "score": score,
                "risk_level": risk_level,
            },
        }
    except Exception as exc:
        return {
            "score": 0,
            "risk_level": "High",
            "cbam_risk_message": "High risk: EU may apply default emission values (3x levy)",
            "flags": [f"Validation error: {exc}"],
            "breakdown": {
                "consistency": "fail",
                "physical": "fail",
                "behavioral": "fail",
                "evidence": "fail",
            },
            "ui_hooks": {
                "score_color": "red",
                "warning_banner": "Output builder failed; defaulting to highest risk handling.",
                "suggestion": "Retry with validated input payload.",
                "pct_deviation": 0.0,
                "evidence_nudge": "Upload supporting documents to reduce CBAM audit risk.",
            },
            "explanations": [f"Detected issue: Validation error: {exc}."],
            "blockchain_payload": {
                "data_hash": hashlib.sha256(b"{}").hexdigest(),
                "timestamp": datetime.now().isoformat(),
                "score": 0,
                "risk_level": "High",
            },
        }


# CBAM orchestration helper to run all four layers and build the final output safely.
def evaluate_submission(data: CarbonInput, history: List[CarbonInput]) -> Dict[str, Any]:
    try:
        consistency: LayerResult = check_consistency(data)
        physical: LayerResult = check_physical_constraints(data)
        behavioral: LayerResult = check_behavioral_patterns(data, history)
        evidence: LayerResult = check_evidence(data)
        score_result: Dict[str, Any] = compute_score([consistency, physical, behavioral, evidence])
        return build_output(data, score_result)
    except Exception as exc:
        fallback_score: Dict[str, Any] = {
            "score": 0,
            "risk_level": "High",
            "all_flags": [f"Validation error: {exc}"],
            "breakdown": {
                "consistency": "fail",
                "physical": "fail",
                "behavioral": "fail",
                "evidence": "fail",
            },
            "layer_details": {
                "consistency": {},
                "physical": {},
                "behavioral": {},
                "evidence": {},
            },
        }
        return build_output(data, fallback_score)


# CBAM demo runner showing suspicious, impossible, and clean submission outcomes.
def run_demo() -> None:
    try:
        history_case_1: List[CarbonInput] = [
            CarbonInput(production=980, electricity=350000, fuel=None, industry="steel", evidence_provided=True),
            CarbonInput(production=1005, electricity=355000, fuel=None, industry="steel", evidence_provided=True),
            CarbonInput(production=995, electricity=350000, fuel=None, industry="steel", evidence_provided=True),
        ]
        history_case_2: List[CarbonInput] = [
            CarbonInput(production=520, electricity=7200000, fuel=120.0, industry="aluminium", evidence_provided=True),
            CarbonInput(production=515, electricity=7200000, fuel=110.0, industry="aluminium", evidence_provided=True),
            CarbonInput(production=500, electricity=7000000, fuel=105.0, industry="aluminium", evidence_provided=True),
        ]
        history_case_3: List[CarbonInput] = [
            CarbonInput(production=210, electricity=3100000, fuel=510.0, industry="aluminium", evidence_provided=True),
            CarbonInput(production=205, electricity=3000000, fuel=505.0, industry="aluminium", evidence_provided=True),
            CarbonInput(production=198, electricity=2950000, fuel=495.0, industry="aluminium", evidence_provided=True),
        ]

        case_1 = CarbonInput(
            production=1000,
            electricity=100000,
            fuel=None,
            industry="steel",
            evidence_provided=False,
        )
        case_2 = CarbonInput(
            production=500,
            electricity=10000,
            fuel=None,
            industry="aluminium",
            evidence_provided=True,
        )
        case_3 = CarbonInput(
            production=200,
            electricity=90000,
            fuel=500.0,
            industry="aluminium",
            evidence_provided=True,
        )

        cases: List[tuple[str, CarbonInput, List[CarbonInput]]] = [
            ("SUSPICIOUS", case_1, history_case_1),
            ("PHYSICALLY IMPOSSIBLE", case_2, history_case_2),
            ("CLEAN", case_3, history_case_3),
        ]

        for idx, (label, payload, history) in enumerate(cases, start=1):
            output: Dict[str, Any] = evaluate_submission(payload, history)
            breakdown: Dict[str, str] = output.get("breakdown", {})
            data_hash: str = output.get("blockchain_payload", {}).get("data_hash", "")

            print(f"--- Case {idx}: {label} ---")
            print(f"Score:      {int(output.get('score', 0)):>3} / 100")
            print(f"Risk Level: {output.get('risk_level', 'High')}")
            print(f"CBAM Risk:  {output.get('cbam_risk_message', '')}")
            print(f"Flags:      {output.get('flags', [])}")
            print(f"Suggestion: {output.get('ui_hooks', {}).get('suggestion', '')}")
            print(f"Hash:       {data_hash[:16]}...")
            print(
                "Breakdown:  "
                f"consistency={breakdown.get('consistency', 'fail')} | "
                f"physical={breakdown.get('physical', 'fail')} | "
                f"behavioral={breakdown.get('behavioral', 'fail')} | "
                f"evidence={breakdown.get('evidence', 'fail')}"
            )
            print()

    except Exception as exc:
        print("--- Case Error: DEMO FAILURE ---")
        print(f"Score:        0 / 100")
        print("Risk Level: High")
        print("CBAM Risk:  High risk: EU may apply default emission values (3x levy)")
        print(f"Flags:      ['Validation error: {exc}']")
        print("Suggestion: Retry with validated input payload.")
        print(f"Hash:       {hashlib.sha256(b'{}').hexdigest()[:16]}...")
        print("Breakdown:  consistency=fail | physical=fail | behavioral=fail | evidence=fail")


if __name__ == "__main__":
    run_demo()
