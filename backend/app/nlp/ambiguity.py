from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
import spacy
import yaml

# Path to weak terms configuration
WEAK_TERMS_PATH = Path("backend/app/nlp/rules/weak_terms.yaml")

# Load spaCy pipeline
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


@dataclass
class TextSpan:
    start: int
    end: int
    text: str
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "weight": self.weight,
        }


@dataclass
class ExplanationFactor:
    name: str
    contribution: float
    direction: str  # "negative" or "positive"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "contribution": self.contribution,
            "direction": self.direction,
        }


@dataclass
class Finding:
    finding_id: str
    module: str
    method: str
    rule_id: str
    spans: list[TextSpan]
    factors: list[ExplanationFactor]
    human_explanation: str
    suggestion: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "module": self.module,
            "method": self.method,
            "rule_id": self.rule_id,
            "spans": [s.to_dict() for s in self.spans],
            "factors": [f.to_dict() for f in self.factors],
            "human_explanation": self.human_explanation,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


def load_weak_terms() -> dict[str, dict[str, dict[str, str]]]:
    if WEAK_TERMS_PATH.exists():
        with open(WEAK_TERMS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_WEAK_TERMS_CONFIG = load_weak_terms()


def check_a_weak_terms(text: str) -> list[Finding]:
    """CHECK A: Subjective / vague terms from weak_terms.yaml."""
    findings: list[Finding] = []
    idx = 1

    for category, terms in _WEAK_TERMS_CONFIG.items():
        for term, data in terms.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                span = TextSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                    weight=1.0,
                )
                findings.append(
                    Finding(
                        finding_id=f"AMB-A-{idx:03d}",
                        module="ambiguity",
                        method="rule_based",
                        rule_id="CHECK_A_WEAK_TERM",
                        spans=[span],
                        factors=[
                            ExplanationFactor(
                                name=f"weak_term_{category}",
                                contribution=1.0,
                                direction="negative",
                            )
                        ],
                        human_explanation=data.get(
                            "explanation",
                            f"The term '{match.group(0)}' is subjective.",
                        ),
                        suggestion=data.get(
                            "suggestion",
                            "Replace with an exact quantified requirement.",
                        ),
                        confidence=0.95,
                    )
                )
                idx += 1

    return findings


def check_b_weak_modals(text: str) -> list[Finding]:
    """CHECK B: Weak modal verbs (should, may, could, might)."""
    weak_modals = {
        "should": "desire or recommendation rather than a binding requirement",
        "may": "optional permission rather than an obligation",
        "could": "capability possibility rather than a mandatory requirement",
        "might": "speculative possibility rather than a binding requirement",
    }

    findings: list[Finding] = []
    idx = 1

    for modal, reason in weak_modals.items():
        pattern = re.compile(rf"\b{modal}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            span = TextSpan(
                start=match.start(),
                end=match.end(),
                text=match.group(0),
                weight=1.0,
            )
            findings.append(
                Finding(
                    finding_id=f"AMB-B-{idx:03d}",
                    module="ambiguity",
                    method="rule_based",
                    rule_id="CHECK_B_WEAK_MODAL",
                    spans=[span],
                    factors=[
                        ExplanationFactor(
                            name="weak_modal_verb",
                            contribution=1.0,
                            direction="negative",
                        )
                    ],
                    human_explanation=f"Weak modal verb '{match.group(0)}' conveys a {reason}.",
                    suggestion="Replace with 'shall' for system commitments or 'must' for user constraints.",
                    confidence=0.95,
                )
            )
            idx += 1

    return findings


def check_c_missing_metrics(text: str, doc: Any = None) -> list[Finding]:
    """CHECK C: Missing measurable criterion when referring to measurable concepts."""
    if doc is None:
        doc = nlp(text)

    measurable_concepts = {
        "time": "response or latency time",
        "speed": "processing speed or rate",
        "size": "data or payload size",
        "count": "quantity of items",
        "capacity": "system capacity or storage",
        "frequency": "recurrence interval",
        "availability": "uptime percentage",
        "latency": "network or execution latency",
        "bandwidth": "throughput limit",
    }

    # Check if document contains any numeric value or unit
    has_numeric = False
    for token in doc:
        if token.like_num or token.pos_ == "NUM":
            has_numeric = True
            break
        if token.ent_type_ in ("CARDINAL", "QUANTITY", "TIME", "PERCENT"):
            has_numeric = True
            break

    findings: list[Finding] = []
    if not has_numeric:
        idx = 1
        for concept, desc in measurable_concepts.items():
            pattern = re.compile(rf"\b{concept}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                span = TextSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                    weight=0.85,
                )
                findings.append(
                    Finding(
                        finding_id=f"AMB-C-{idx:03d}",
                        module="ambiguity",
                        method="rule_based",
                        rule_id="CHECK_C_MISSING_METRIC",
                        spans=[span],
                        factors=[
                            ExplanationFactor(
                                name="unquantified_concept",
                                contribution=0.85,
                                direction="negative",
                            )
                        ],
                        human_explanation=f"The requirement references {desc} ('{match.group(0)}') but lacks a quantified numeric threshold or unit.",
                        suggestion=f"Specify an exact numeric threshold and unit for {concept} (e.g. 'within 2 seconds', '99.9% uptime').",
                        confidence=0.85,
                    )
                )
                idx += 1

    return findings


def check_d_vague_pronouns(text: str, doc: Any = None) -> list[Finding]:
    """CHECK D: Vague pronoun reference as subject without preceding antecedent."""
    if doc is None:
        doc = nlp(text)

    findings: list[Finding] = []
    idx = 1

    vague_pronouns = {"it", "this", "that", "they"}
    for token in doc:
        if token.lower_ in vague_pronouns and token.dep_ in (
            "nsubj",
            "nsubjpass",
        ):
            # Check if any explicit NOUN or PROPN precedes this token in the sentence
            has_prior_noun = any(
                t.pos_ in ("NOUN", "PROPN") for t in token.sent[: token.i]
            )

            if not has_prior_noun:
                start_char = token.idx
                end_char = token.idx + len(token.text)
                span = TextSpan(
                    start=start_char,
                    end=end_char,
                    text=token.text,
                    weight=0.8,
                )
                findings.append(
                    Finding(
                        finding_id=f"AMB-D-{idx:03d}",
                        module="ambiguity",
                        method="rule_based",
                        rule_id="CHECK_D_VAGUE_PRONOUN",
                        spans=[span],
                        factors=[
                            ExplanationFactor(
                                name="vague_subject_pronoun",
                                contribution=0.8,
                                direction="negative",
                            )
                        ],
                        human_explanation=f"The pronoun '{token.text}' is used as a subject without an explicit antecedent noun in the sentence.",
                        suggestion=f"Replace '{token.text}' with the specific actor or component name.",
                        confidence=0.80,
                    )
                )
                idx += 1

    return findings


def check_e_compound_requirements(
    text: str, doc: Any = None
) -> list[Finding]:
    """CHECK E: Compound requirement (multiple modal clauses or coordinate action verbs)."""
    if doc is None:
        doc = nlp(text)

    findings: list[Finding] = []
    idx = 1

    # Check 1: Multiple modal auxiliary obligations in one requirement
    modal_tokens = [
        t for t in doc if t.lower_ in ("shall", "must") and t.pos_ in ("AUX", "VERB")
    ]
    if len(modal_tokens) > 1:
        spans = [
            TextSpan(
                start=t.idx, end=t.idx + len(t.text), text=t.text, weight=0.85
            )
            for t in modal_tokens
        ]
        findings.append(
            Finding(
                finding_id=f"AMB-E-{idx:03d}",
                module="ambiguity",
                method="rule_based",
                rule_id="CHECK_E_COMPOUND_MODALS",
                spans=spans,
                factors=[
                    ExplanationFactor(
                        name="multiple_normative_modals",
                        contribution=0.85,
                        direction="negative",
                    )
                ],
                human_explanation=f"Requirement contains {len(modal_tokens)} distinct modal commitments ('{', '.join(t.text for t in modal_tokens)}'), violating atomicity.",
                suggestion="Split into individual, single-obligation requirements.",
                confidence=0.85,
            )
        )
        idx += 1

    # Check 2: Coordinating conjunction joining distinct action verbs (e.g. 'shall notify ... and log ...')
    for token in doc:
        if token.dep_ == "conj" and token.pos_ == "VERB" and token.head.pos_ == "VERB":
            # Find the coordinating conjunction token (e.g., 'and', 'or')
            cc_tokens = [c for c in token.children if c.dep_ == "cc"] or [
                c for c in token.head.children if c.dep_ == "cc"
            ]
            cc_text = cc_tokens[0].text if cc_tokens else "and"

            span = TextSpan(
                start=token.idx,
                end=token.idx + len(token.text),
                text=token.text,
                weight=0.75,
            )
            findings.append(
                Finding(
                    finding_id=f"AMB-E-{idx:03d}",
                    module="ambiguity",
                    method="rule_based",
                    rule_id="CHECK_E_COMPOUND_ACTIONS",
                    spans=[span],
                    factors=[
                        ExplanationFactor(
                            name="coordinated_actions",
                            contribution=0.75,
                            direction="negative",
                        )
                    ],
                    human_explanation=f"Requirement combines multiple distinct action verbs ('{token.head.text}' {cc_text} '{token.text}').",
                    suggestion="Separate into individual atomic requirements for each distinct operation.",
                    confidence=0.75,
                )
            )
            idx += 1
            break

    return findings


def check_f_passive_voice(text: str, doc: Any = None) -> list[Finding]:
    """CHECK F: Passive voice without an explicit actor."""
    if doc is None:
        doc = nlp(text)

    findings: list[Finding] = []
    idx = 1

    for token in doc:
        if token.dep_ == "nsubjpass":
            head_verb = token.head
            # Look for an agent preposition ("by <actor>")
            has_agent = False
            for child in head_verb.children:
                if child.dep_ == "agent":
                    has_agent = True
                    break
                if child.lower_ == "by" and child.dep_ == "prep":
                    has_agent = True
                    break

            if not has_agent:
                span = TextSpan(
                    start=head_verb.idx,
                    end=head_verb.idx + len(head_verb.text),
                    text=head_verb.text,
                    weight=0.85,
                )
                findings.append(
                    Finding(
                        finding_id=f"AMB-F-{idx:03d}",
                        module="ambiguity",
                        method="rule_based",
                        rule_id="CHECK_F_PASSIVE_VOICE",
                        spans=[span],
                        factors=[
                            ExplanationFactor(
                                name="passive_voice_no_actor",
                                contribution=0.85,
                                direction="negative",
                            )
                        ],
                        human_explanation=f"Passive construction ('{head_verb.text}') omits the responsible actor or system.",
                        suggestion=f"Rephrase actively: 'The <actor/system> shall {head_verb.lemma_} <object>'.",
                        confidence=0.85,
                    )
                )
                idx += 1

    return findings


def analyze_ambiguity(text: str) -> list[Finding]:
    """Runs all ambiguity checks on the provided requirement text."""
    doc = nlp(text)
    all_findings: list[Finding] = []

    all_findings.extend(check_a_weak_terms(text))
    all_findings.extend(check_b_weak_modals(text))
    all_findings.extend(check_c_missing_metrics(text, doc))
    all_findings.extend(check_d_vague_pronouns(text, doc))
    all_findings.extend(check_e_compound_requirements(text, doc))
    all_findings.extend(check_f_passive_voice(text, doc))

    return all_findings
