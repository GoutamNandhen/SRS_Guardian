from dataclasses import dataclass, field
from pathlib import Path
import statistics
from typing import Any
import yaml

from backend.app.nlp.ambiguity import Finding
from backend.app.nlp.readability import ReadabilityMetrics

CONFIG_PATH = Path("backend/app/nlp/rules/score_weights.yaml")

_SCORE_WEIGHTS_CACHE: dict[str, Any] | None = None


def load_score_weights() -> dict[str, Any]:
    """Loads and caches the score weights configuration from YAML."""
    global _SCORE_WEIGHTS_CACHE
    if _SCORE_WEIGHTS_CACHE is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Score weights config not found at {CONFIG_PATH}")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _SCORE_WEIGHTS_CACHE = yaml.safe_load(f)
    return _SCORE_WEIGHTS_CACHE


@dataclass
class WaterfallStep:
    step_number: int
    step_name: str
    rule_id: str | None
    deduction: float
    current_score: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "rule_id": self.rule_id,
            "deduction": round(self.deduction, 1),
            "current_score": round(self.current_score, 1),
            "explanation": self.explanation,
        }


@dataclass
class RequirementQualityScore:
    req_key: str
    text: str
    overall_score: float
    sub_scores: dict[str, float]
    waterfall: list[WaterfallStep]
    issues_count: int
    penalties_applied: list[dict[str, Any]]
    requirement_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "req_key": self.req_key,
            "text": self.text,
            "overall_score": round(self.overall_score, 1),
            "sub_scores": {k: round(v, 1) for k, v in self.sub_scores.items()},
            "waterfall": [w.to_dict() for w in self.waterfall],
            "issues_count": self.issues_count,
            "penalties_applied": self.penalties_applied,
        }


@dataclass
class DocumentQualitySummary:
    total_requirements: int
    mean_score: float
    median_score: float
    min_score: float
    max_score: float
    distribution: dict[str, int]
    worst_requirements: list[dict[str, Any]]
    issue_counts: dict[str, int]
    requirement_scores: list[RequirementQualityScore]
    document_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "total_requirements": self.total_requirements,
            "mean_score": round(self.mean_score, 1),
            "median_score": round(self.median_score, 1),
            "min_score": round(self.min_score, 1),
            "max_score": round(self.max_score, 1),
            "distribution": self.distribution,
            "worst_requirements": self.worst_requirements,
            "issue_counts": self.issue_counts,
            "requirements": [r.to_dict() for r in self.requirement_scores],
        }


def score_requirement(
    req_key: str,
    text: str,
    ambiguity_findings: list[Finding] | None = None,
    readability_metrics: ReadabilityMetrics | None = None,
    is_duplicate: bool = False,
    duplicate_info: dict[str, Any] | None = None,
    contradiction_findings: list[dict[str, Any]] | None = None,
    requirement_id: int | None = None,
) -> RequirementQualityScore:
    """Calculates deterministic quality score, sub-scores, and waterfall trace for a requirement."""
    config = load_score_weights()
    base_score = float(config.get("base_score", 100.0))
    penalties_cfg = config.get("penalties", {})
    thresholds = config.get("readability_thresholds", {})

    current_score = base_score
    waterfall: list[WaterfallStep] = [
        WaterfallStep(
            step_number=0,
            step_name="Base Score",
            rule_id=None,
            deduction=0.0,
            current_score=base_score,
            explanation="Initial baseline score for a clean requirement",
        )
    ]

    sub_scores = {
        "clarity": 100.0,
        "ambiguity": 100.0,
        "testability": 100.0,
        "readability": 100.0,
        "structure": 100.0,
        "consistency": 100.0,
    }

    step_number = 0
    penalties_applied: list[dict[str, Any]] = []

    # 1. Apply Phase 5 Ambiguity penalties
    if ambiguity_findings:
        for finding in ambiguity_findings:
            rule_id = finding.rule_id
            cfg = penalties_cfg.get(rule_id)
            if not cfg:
                continue

            deduction = float(cfg.get("deduction", 10.0))
            current_score = max(0.0, current_score - deduction)
            step_number += 1

            matched_spans = ", ".join(f"'{s.text}'" for s in finding.spans)
            step_name = f"{cfg.get('name', rule_id)} ({matched_spans})" if matched_spans else cfg.get("name", rule_id)
            explanation = finding.human_explanation

            waterfall.append(
                WaterfallStep(
                    step_number=step_number,
                    step_name=step_name,
                    rule_id=rule_id,
                    deduction=deduction,
                    current_score=current_score,
                    explanation=explanation,
                )
            )

            penalties_applied.append(
                {
                    "rule_id": rule_id,
                    "name": cfg.get("name", rule_id),
                    "deduction": deduction,
                    "matched_text": matched_spans,
                }
            )

            # Update specific sub-scores
            if rule_id == "CHECK_A_WEAK_TERM":
                sub_scores["ambiguity"] = max(0.0, sub_scores["ambiguity"] - 35.0)
                sub_scores["clarity"] = max(0.0, sub_scores["clarity"] - 30.0)
                sub_scores["testability"] = max(0.0, sub_scores["testability"] - 30.0)
            elif rule_id == "CHECK_B_WEAK_MODAL":
                sub_scores["ambiguity"] = max(0.0, sub_scores["ambiguity"] - 35.0)
                sub_scores["testability"] = max(0.0, sub_scores["testability"] - 30.0)
            elif rule_id == "CHECK_C_MISSING_METRIC":
                sub_scores["ambiguity"] = max(0.0, sub_scores["ambiguity"] - 30.0)
                sub_scores["testability"] = max(0.0, sub_scores["testability"] - 40.0)
            elif rule_id == "CHECK_D_VAGUE_PRONOUN":
                sub_scores["clarity"] = max(0.0, sub_scores["clarity"] - 25.0)
            elif rule_id == "CHECK_E_COMPOUND_REQ":
                sub_scores["structure"] = max(0.0, sub_scores["structure"] - 40.0)
            elif rule_id == "CHECK_F_PASSIVE_VOICE":
                sub_scores["structure"] = max(0.0, sub_scores["structure"] - 35.0)
                sub_scores["clarity"] = max(0.0, sub_scores["clarity"] - 20.0)

    # 2. Readability threshold penalties
    if readability_metrics:
        fog_max = float(thresholds.get("gunning_fog_max", 14.0))
        passive_max = float(thresholds.get("passive_ratio_max", 0.40))

        if readability_metrics.gunning_fog > fog_max:
            cfg = penalties_cfg.get("READABILITY_HIGH_GUNNING_FOG", {})
            deduction = float(cfg.get("deduction", 10.0))
            current_score = max(0.0, current_score - deduction)
            step_number += 1
            waterfall.append(
                WaterfallStep(
                    step_number=step_number,
                    step_name=f"High Gunning Fog Index ({readability_metrics.gunning_fog:.1f} > {fog_max:.1f})",
                    rule_id="READABILITY_HIGH_GUNNING_FOG",
                    deduction=deduction,
                    current_score=current_score,
                    explanation="Overly complex linguistic syntax increases reader misinterpretation.",
                )
            )
            sub_scores["readability"] = max(0.0, sub_scores["readability"] - 30.0)
            sub_scores["clarity"] = max(0.0, sub_scores["clarity"] - 20.0)

        if readability_metrics.passive_voice_ratio > passive_max:
            cfg = penalties_cfg.get("READABILITY_HIGH_PASSIVE", {})
            deduction = float(cfg.get("deduction", 5.0))
            current_score = max(0.0, current_score - deduction)
            step_number += 1
            waterfall.append(
                WaterfallStep(
                    step_number=step_number,
                    step_name=f"High Passive Voice Ratio ({readability_metrics.passive_voice_ratio * 100:.0f}% > {passive_max * 100:.0f}%)",
                    rule_id="READABILITY_HIGH_PASSIVE",
                    deduction=deduction,
                    current_score=current_score,
                    explanation="Excessive passive constructions reduce operational clarity.",
                )
            )
            sub_scores["readability"] = max(0.0, sub_scores["readability"] - 20.0)
            sub_scores["structure"] = max(0.0, sub_scores["structure"] - 20.0)

        # Baseline readability sub-score tuning
        if readability_metrics.flesch_reading_ease < 50.0:
            sub_scores["readability"] = max(0.0, sub_scores["readability"] - 25.0)
        if readability_metrics.word_count > float(thresholds.get("max_recommended_words", 35)):
            sub_scores["readability"] = max(0.0, sub_scores["readability"] - 20.0)

    # 3. Duplicate penalty (Phase 6)
    if is_duplicate:
        cfg = penalties_cfg.get("SEMANTIC_DUPLICATE", {})
        deduction = float(cfg.get("deduction", 15.0))
        current_score = max(0.0, current_score - deduction)
        step_number += 1
        dup_target = duplicate_info.get("target_req_key", "another requirement") if duplicate_info else "another requirement"
        sim_pct = f"{duplicate_info.get('similarity_score', 0.8) * 100:.1f}%" if duplicate_info else ">= 80%"
        waterfall.append(
            WaterfallStep(
                step_number=step_number,
                step_name=f"Potential Semantic Duplicate ({dup_target}, sim {sim_pct})",
                rule_id="SEMANTIC_DUPLICATE",
                deduction=deduction,
                current_score=current_score,
                explanation=f"Requirement is semantically redundant with {dup_target}.",
            )
        )
        sub_scores["consistency"] = max(0.0, sub_scores["consistency"] - 50.0)
        penalties_applied.append(
            {
                "rule_id": "SEMANTIC_DUPLICATE",
                "name": "Potential Semantic Duplicate",
                "deduction": deduction,
                "matched_text": dup_target,
            }
        )

    # 4. Contradiction penalties (Phase 12)
    if contradiction_findings:
        cfg = penalties_cfg.get("POTENTIAL_CONTRADICTION", {})
        deduction = float(cfg.get("deduction", 25.0))
        for cf in contradiction_findings:
            current_score = max(0.0, current_score - deduction)
            step_number += 1
            target_key = cf.get("target_req_key", "another requirement")
            reason = cf.get("reason", "Conflicting requirement logic")
            waterfall.append(
                WaterfallStep(
                    step_number=step_number,
                    step_name=f"Potential Contradiction ({target_key})",
                    rule_id="POTENTIAL_CONTRADICTION",
                    deduction=deduction,
                    current_score=current_score,
                    explanation=f"Requirement logically contradicts {target_key}: {reason}",
                )
            )
            sub_scores["consistency"] = max(0.0, sub_scores["consistency"] - 60.0)
            sub_scores["testability"] = max(0.0, sub_scores["testability"] - 30.0)
            penalties_applied.append(
                {
                    "rule_id": "POTENTIAL_CONTRADICTION",
                    "name": "Potential Contradiction",
                    "deduction": deduction,
                    "matched_text": target_key,
                }
            )

    # Clamp and finalize
    final_overall = max(0.0, min(100.0, current_score))
    final_subscores = {k: max(0.0, min(100.0, v)) for k, v in sub_scores.items()}

    return RequirementQualityScore(
        requirement_id=requirement_id,
        req_key=req_key,
        text=text,
        overall_score=final_overall,
        sub_scores=final_subscores,
        waterfall=waterfall,
        issues_count=len(penalties_applied),
        penalties_applied=penalties_applied,
    )


def score_document(
    requirement_scores: list[RequirementQualityScore],
    document_id: int | None = None,
) -> DocumentQualitySummary:
    """Aggregates individual requirement scores into document-level metrics and distributions."""
    n = len(requirement_scores)
    if n == 0:
        return DocumentQualitySummary(
            document_id=document_id,
            total_requirements=0,
            mean_score=0.0,
            median_score=0.0,
            min_score=0.0,
            max_score=0.0,
            distribution={"90-100": 0, "70-89": 0, "50-69": 0, "<50": 0},
            worst_requirements=[],
            issue_counts={},
            requirement_scores=[],
        )

    scores = [r.overall_score for r in requirement_scores]
    mean_score = statistics.mean(scores)
    median_score = statistics.median(scores)
    min_score = min(scores)
    max_score = max(scores)

    # Score distribution bins
    distribution = {
        "90-100": sum(1 for s in scores if s >= 90.0),
        "70-89": sum(1 for s in scores if 70.0 <= s < 90.0),
        "50-69": sum(1 for s in scores if 50.0 <= s < 70.0),
        "<50": sum(1 for s in scores if s < 50.0),
    }

    # Rank worst requirements (lowest overall score first)
    sorted_reqs = sorted(requirement_scores, key=lambda r: r.overall_score)
    worst_reqs = [
        {
            "requirement_id": r.requirement_id,
            "req_key": r.req_key,
            "overall_score": round(r.overall_score, 1),
            "issues_count": r.issues_count,
            "text": r.text,
        }
        for r in sorted_reqs[:5]
    ]

    # Aggregate issue counts by rule_id
    issue_counts: dict[str, int] = {}
    for r in requirement_scores:
        for p in r.penalties_applied:
            rid = p["rule_id"]
            issue_counts[rid] = issue_counts.get(rid, 0) + 1

    return DocumentQualitySummary(
        document_id=document_id,
        total_requirements=n,
        mean_score=mean_score,
        median_score=median_score,
        min_score=min_score,
        max_score=max_score,
        distribution=distribution,
        worst_requirements=worst_reqs,
        issue_counts=issue_counts,
        requirement_scores=requirement_scores,
    )
