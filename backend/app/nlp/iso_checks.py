"""
Selected Machine-Checkable Checks Based on ISO/IEC/IEEE 29148.

NOTE (Rule 10): SRS Guardian does NOT claim full ISO compliance or certification.
This module evaluates selected machine-checkable requirements characteristics:
1. ISO_SINGULAR: Exactly one requirement per statement.
2. ISO_UNAMBIGUOUS: Absence of subjective, vague, or non-normative terms (reuses Phase 5).
3. ISO_VERIFIABLE: Presence of measurable/quantifiable thresholds or testable criteria.
4. ISO_COMPLETE: Syntactic completeness (subject/actor + modal + action + object).
5. ISO_CONSISTENT: Document-wide uniform terminology (detects actor/action drift).
6. ISO_TRACEABLE: Persistent explicit identifier and source lineage.
7. ISO_STRUCTURE: Conformance to standardized syntax (e.g., EARS template).
"""

from dataclasses import dataclass, field
import re
from typing import Any
import spacy

from backend.app.nlp.ambiguity import Finding, TextSpan, ExplanationFactor, analyze_ambiguity
from backend.app.nlp.ears import analyze_ears, EarsResult
from backend.app.nlp.numeric_constraints import extract_constraints

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


# Standard measurable performance terms requiring quantitative thresholds
PERFORMANCE_TERMS = {
    "quickly", "fast", "rapidly", "slow", "efficiently", "effectively",
    "instant", "instantly", "high capacity", "low latency", "minimal delay",
    "high availability", "scalable", "maximum speed", "minimum throughput"
}

# Common synonym groups for terminology consistency checks
SYNONYM_GROUPS = [
    {"user", "customer", "client", "account holder", "end-user"},
    {"reset", "recover", "restore", "retrieve"},
    {"system", "application", "platform", "software", "service"},
    {"display", "show", "present", "render"},
    {"remove", "delete", "erase", "purge"},
]


@dataclass
class IsoCheckItem:
    check_id: str
    characteristic: str
    status: str  # "passed", "warning", "failed"
    score_deduction: float
    explanation: str
    suggestion: str | None = None
    spans: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "characteristic": self.characteristic,
            "status": self.status,
            "score_deduction": self.score_deduction,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "spans": self.spans,
        }


@dataclass
class RequirementIsoReport:
    req_key: str
    text: str
    ears_result: EarsResult
    checks: list[IsoCheckItem]
    total_iso_deductions: float
    conformance_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "req_key": self.req_key,
            "text": self.text,
            "ears_result": self.ears_result.to_dict(),
            "checks": [c.to_dict() for c in self.checks],
            "total_iso_deductions": self.total_iso_deductions,
            "conformance_summary": self.conformance_summary,
        }


def check_singular(text: str, doc: Any = None) -> IsoCheckItem:
    """
    ISO-SINGULAR: Evaluates if requirement contains multiple conjoined requirements or actions.
    """
    if doc is None:
        doc = nlp(text)

    # 1. Multiple normative modal verbs ("shall ... and shall ...", "must ... and must ...")
    modals = [tok for tok in doc if tok.text.lower() in ("shall", "must", "should", "will")]
    if len(modals) > 1:
        spans = [{"start": tok.idx, "end": tok.idx + len(tok.text), "text": tok.text} for tok in modals]
        return IsoCheckItem(
            check_id="ISO_SINGULAR",
            characteristic="Singular",
            status="failed",
            score_deduction=10.0,
            explanation=f"Multiple modal verbs ({', '.join(m.text for m in modals)}) detected. The requirement appears to contain multiple distinct obligations.",
            suggestion="Split into separate, single-purpose requirements (one 'shall' or 'must' per statement).",
            spans=spans,
        )

    # 2. Conjunction joining two distinct verbs
    for token in doc:
        if token.pos_ == "CCONJ" and token.text.lower() in ("and", "or"):
            head = token.head
            # Check if coordinating two predicate verbs
            conj_verbs = [
                child for child in head.children
                if child.dep_ == "conj" and child.pos_ == "VERB"
            ]
            if head.pos_ == "VERB" and conj_verbs:
                span_text = f"{head.text} {token.text} {conj_verbs[0].text}"
                start_idx = min(head.idx, conj_verbs[0].idx)
                end_idx = max(head.idx + len(head.text), conj_verbs[0].idx + len(conj_verbs[0].text))
                return IsoCheckItem(
                    check_id="ISO_SINGULAR",
                    characteristic="Singular",
                    status="failed",
                    score_deduction=10.0,
                    explanation=f"Conjoined distinct action verbs detected ('{span_text}'). Violates requirement singularity.",
                    suggestion="Separate the compound actions into individual requirement statements.",
                    spans=[{"start": start_idx, "end": end_idx, "text": span_text}],
                )

    return IsoCheckItem(
        check_id="ISO_SINGULAR",
        characteristic="Singular",
        status="passed",
        score_deduction=0.0,
        explanation="Statement specifies a single atomic requirement action.",
    )


def check_unambiguous(text: str, ambiguity_findings: list[Finding] | None = None) -> IsoCheckItem:
    """
    ISO-UNAMBIGUOUS: Evaluates clarity and lack of subjective/ambiguous vocabulary.
    Reuses findings from Phase 5.
    """
    if ambiguity_findings is None:
        ambiguity_findings = analyze_ambiguity(text)

    if not ambiguity_findings:
        return IsoCheckItem(
            check_id="ISO_UNAMBIGUOUS",
            characteristic="Unambiguous",
            status="passed",
            score_deduction=0.0,
            explanation="No subjective or vague terminology detected.",
        )

    # Filter critical or notable ambiguity findings
    weak_terms = [f for f in ambiguity_findings if f.rule_id == "CHECK_A_WEAK_TERM"]
    weak_modals = [f for f in ambiguity_findings if f.rule_id == "CHECK_B_WEAK_MODAL"]
    vague_pronouns = [f for f in ambiguity_findings if f.rule_id == "CHECK_D_VAGUE_PRONOUN"]

    all_spans = []
    for f in ambiguity_findings:
        for s in f.spans:
            all_spans.append({"start": s.start, "end": s.end, "text": s.text})

    reasons: list[str] = []
    if weak_terms:
        reasons.append(f"subjective vocabulary ({', '.join(f.spans[0].text for f in weak_terms if f.spans)})")
    if weak_modals:
        reasons.append(f"non-normative modal verb ({', '.join(f.spans[0].text for f in weak_modals if f.spans)})")
    if vague_pronouns:
        reasons.append("vague pronoun reference")

    reason_str = "; ".join(reasons) if reasons else "ambiguous phrasing detected"
    return IsoCheckItem(
        check_id="ISO_UNAMBIGUOUS",
        characteristic="Unambiguous",
        status="failed" if weak_terms or weak_modals else "warning",
        score_deduction=15.0 if weak_terms else (10.0 if weak_modals else 5.0),
        explanation=f"Potential ambiguity detected: {reason_str}.",
        suggestion="Replace subjective modifiers with measurable criteria and use normative 'shall' or 'must'.",
        spans=all_spans,
    )


def check_verifiable(text: str) -> IsoCheckItem:
    """
    ISO-VERIFIABLE: Evaluates if requirement contains measurable acceptance criteria or testable conditions.
    """
    lower = text.lower()

    # Check for subjective performance terms lacking numerical thresholds
    found_perf_terms: list[str] = []
    for term in PERFORMANCE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            found_perf_terms.append(term)

    # Check for quantitative constraints
    constraints = extract_constraints(text)

    # Check for any numbers with units
    has_quantity = bool(re.search(r"\b\d+(\.\d+)?\s*(ms|seconds?|minutes?|hours?|characters?|bytes?|kb|mb|gb|%|percent)\b", lower))

    if found_perf_terms and not constraints and not has_quantity:
        spans = []
        for term in found_perf_terms:
            m = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
            if m:
                spans.append({"start": m.start(), "end": m.end(), "text": m.group(0)})
        return IsoCheckItem(
            check_id="ISO_VERIFIABLE",
            characteristic="Verifiable",
            status="failed",
            score_deduction=15.0,
            explanation=f"Performance modifier '{', '.join(found_perf_terms)}' lacks a measurable acceptance criterion (e.g. exact response time in ms/seconds).",
            suggestion="Specify explicit numeric thresholds and units (e.g., 'respond within 2.0 seconds').",
            spans=spans,
        )

    if constraints or has_quantity:
        return IsoCheckItem(
            check_id="ISO_VERIFIABLE",
            characteristic="Verifiable",
            status="passed",
            score_deduction=0.0,
            explanation="Contains explicit quantitative constraint or measurable unit suitable for automated verification.",
        )

    # Pure functional capability (e.g. "The system shall allow users to reset password")
    # This is functionally verifiable via test case inspection.
    return IsoCheckItem(
        check_id="ISO_VERIFIABLE",
        characteristic="Verifiable",
        status="passed",
        score_deduction=0.0,
        explanation="Specifies a functional capability verifiable via pass/fail demonstration or test inspection.",
    )


def check_complete(text: str, doc: Any = None) -> IsoCheckItem:
    """
    ISO-COMPLETE: Evaluates syntactic presence of Actor, Modal Verb, Main Action Verb, and Target/Object.
    """
    if doc is None:
        doc = nlp(text)
    subjects = [tok for tok in doc if tok.dep_ in ("nsubj", "nsubjpass")]
    aux_modals = [tok for tok in doc if tok.dep_ in ("aux", "auxpass") and tok.text.lower() in ("shall", "must", "should", "will", "may", "can")]
    root_verbs = [tok for tok in doc if tok.pos_ == "VERB" or tok.dep_ == "ROOT"]
    objects = [tok for tok in doc if tok.dep_ in ("dobj", "pobj", "attr", "ccomp", "xcomp")]

    missing_parts = []
    if not subjects:
        missing_parts.append("Subject/Actor")
    if not aux_modals:
        missing_parts.append("Modal Verb")
    if not root_verbs:
        missing_parts.append("Action Verb")
    if not objects and len(doc) > 4:
        missing_parts.append("Object/Target")

    if missing_parts:
        return IsoCheckItem(
            check_id="ISO_COMPLETE",
            characteristic="Complete",
            status="failed",
            score_deduction=10.0,
            explanation=f"Syntactically incomplete requirement statement: missing {', '.join(missing_parts)}.",
            suggestion="Rewrite ensuring all syntactic elements (Actor, Modal 'shall', Action Verb, Target) are present.",
        )

    return IsoCheckItem(
        check_id="ISO_COMPLETE",
        characteristic="Complete",
        status="passed",
        score_deduction=0.0,
        explanation="Syntactically complete statement with defined Subject, Modal, Action, and Object.",
    )


# Compiled regex patterns for synonym groups
SYNONYM_PATTERNS = [
    {word: re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in group}
    for group in SYNONYM_GROUPS
]


def build_synonym_index(
    all_reqs: list[dict[str, Any]],
) -> tuple[dict[Any, dict[int, list[str]]], dict[int, dict[str, list[dict[str, Any]]]]]:
    """Pre-indexes synonym occurrences across all requirements in O(N) time.

    Returns:
        req_matches: map of req_id -> {group_idx: [words_found_in_req]}
        doc_usage: map of group_idx -> {word: [req_dict, ...]}
    """
    req_matches: dict[Any, dict[int, list[str]]] = {}
    doc_usage: dict[int, dict[str, list[dict[str, Any]]]] = {
        g_idx: {} for g_idx in range(len(SYNONYM_GROUPS))
    }

    for req in all_reqs:
        r_id = req.get("id", req.get("req_key", id(req)))
        r_text = req.get("text", "")
        req_matches[r_id] = {}

        for g_idx, patterns in enumerate(SYNONYM_PATTERNS):
            matched = [word for word, pat in patterns.items() if pat.search(r_text)]
            if matched:
                req_matches[r_id][g_idx] = matched
                for w in matched:
                    doc_usage[g_idx].setdefault(w, []).append(req)

    return req_matches, doc_usage


def check_consistent(
    req_dict: dict[str, Any],
    all_reqs: list[dict[str, Any]],
    synonym_index: tuple | None = None,
) -> IsoCheckItem:
    """
    ISO-CONSISTENT: Checks for terminology drift across the document.
    Detects when different synonyms are used across requirements to refer to the same concept.
    """
    if synonym_index is None:
        synonym_index = build_synonym_index(all_reqs)

    req_matches, doc_usage = synonym_index
    r_id = req_dict.get("id", req_dict.get("req_key", id(req_dict)))
    current_matches = req_matches.get(r_id, {})

    inconsistencies: list[str] = []
    spans: list[dict[str, Any]] = []

    for g_idx, matched_words in current_matches.items():
        primary_word = matched_words[0]
        # Check if other requirements used a different word from this same synonym group
        for other_word, other_reqs in doc_usage[g_idx].items():
            if other_word not in matched_words:
                # Find the first other requirement that isn't this requirement
                other_req = next((r for r in other_reqs if r.get("id") != req_dict.get("id")), None)
                if other_req:
                    # Find span in current requirement
                    pat = SYNONYM_PATTERNS[g_idx][primary_word]
                    m = pat.search(req_dict.get("text", ""))
                    if m and not any(s["text"].lower() == primary_word.lower() for s in spans):
                        spans.append({"start": m.start(), "end": m.end(), "text": m.group(0)})
                    note = f"'{primary_word}' in {req_dict.get('req_key', 'this req')} vs '{other_word}' in {other_req.get('req_key', 'another req')}"
                    if note not in inconsistencies:
                        inconsistencies.append(note)

    if inconsistencies:
        return IsoCheckItem(
            check_id="ISO_CONSISTENT",
            characteristic="Consistent",
            status="warning",
            score_deduction=10.0,
            explanation=f"Potential terminology inconsistency detected across document: {'; '.join(inconsistencies[:2])}.",
            suggestion="Standardize vocabulary across requirements so identical concepts and actors share uniform naming.",
            spans=spans,
        )

    return IsoCheckItem(
        check_id="ISO_CONSISTENT",
        characteristic="Consistent",
        status="passed",
        score_deduction=0.0,
        explanation="Terminology is consistent with the rest of the document.",
    )


def check_traceable(req_dict: dict[str, Any]) -> IsoCheckItem:
    """
    ISO-TRACEABLE: Checks for unique persistent requirement key and source lineage.
    """
    req_key = req_dict.get("req_key", "")
    source_layer = req_dict.get("source_layer", "")

    # Check for standard structured identifier pattern (REQ-001, FR-01, etc.)
    has_standard_id = bool(re.match(r"^(REQ|FR|NFR|R|SR|BR)[-_.]?\d+", req_key, re.IGNORECASE))

    if not has_standard_id and not req_key:
        return IsoCheckItem(
            check_id="ISO_TRACEABLE",
            characteristic="Traceable",
            status="failed",
            score_deduction=5.0,
            explanation="Requirement lacks an explicit persistent identifier for configuration control and traceability.",
            suggestion="Assign an explicit unique identifier such as 'REQ-001' or 'FR-101'.",
        )

    return IsoCheckItem(
        check_id="ISO_TRACEABLE",
        characteristic="Traceable",
        status="passed",
        score_deduction=0.0,
        explanation=f"Explicit identifier '{req_key}' identified via extraction layer '{source_layer or 'explicit_id'}'.",
    )


def check_structure(text: str, ears_result: EarsResult | None = None) -> IsoCheckItem:
    """
    ISO-STRUCTURE: Checks conformance to structured requirements syntax (EARS template).
    """
    if ears_result is None:
        ears_result = analyze_ears(text)

    if ears_result.is_valid_ears:
        return IsoCheckItem(
            check_id="ISO_STRUCTURE",
            characteristic="Conforming Structure",
            status="passed",
            score_deduction=0.0,
            explanation=f"Conforms to structured EARS template ({ears_result.pattern.replace('_', ' ').title()}).",
        )

    if ears_result.pattern != "non_conforming":
        return IsoCheckItem(
            check_id="ISO_STRUCTURE",
            characteristic="Conforming Structure",
            status="warning",
            score_deduction=5.0,
            explanation=f"Matches {ears_result.pattern.replace('_', ' ')} syntax, but contains non-normative or missing elements: {', '.join(ears_result.missing_elements)}.",
            suggestion=ears_result.suggestion,
        )

    return IsoCheckItem(
        check_id="ISO_STRUCTURE",
        characteristic="Conforming Structure",
        status="failed",
        score_deduction=5.0,
        explanation="Does not follow a recognized EARS structured syntax pattern.",
        suggestion=ears_result.suggestion or "Restructure as: 'The <system> shall <response>'",
    )


def analyze_iso_checks(
    req_dict: dict[str, Any],
    all_reqs: list[dict[str, Any]] | None = None,
    ambiguity_findings: list[Finding] | None = None,
    synonym_index: tuple | None = None,
    doc: Any = None,
) -> RequirementIsoReport:
    """
    Runs all 7 machine-checkable ISO 29148 checks on a requirement.
    """
    text = req_dict["text"]
    req_key = req_dict.get("req_key", "REQ")
    if all_reqs is None:
        all_reqs = [req_dict]

    if doc is None:
        doc = nlp(text)

    ears_result = analyze_ears(text)

    c_singular = check_singular(text, doc=doc)
    c_unambiguous = check_unambiguous(text, ambiguity_findings)
    c_verifiable = check_verifiable(text)
    c_complete = check_complete(text, doc=doc)
    c_consistent = check_consistent(req_dict, all_reqs, synonym_index=synonym_index)
    c_traceable = check_traceable(req_dict)
    c_structure = check_structure(text, ears_result)

    checks = [
        c_singular,
        c_unambiguous,
        c_verifiable,
        c_complete,
        c_consistent,
        c_traceable,
        c_structure,
    ]

    total_deductions = sum(c.score_deduction for c in checks)

    passed_count = sum(1 for c in checks if c.status == "passed")
    warning_count = sum(1 for c in checks if c.status == "warning")
    failed_count = sum(1 for c in checks if c.status == "failed")

    summary = f"{passed_count}/7 passed, {warning_count} warnings, {failed_count} potential issues"

    return RequirementIsoReport(
        req_key=req_key,
        text=text,
        ears_result=ears_result,
        checks=checks,
        total_iso_deductions=round(total_deductions, 1),
        conformance_summary=summary,
    )


def batch_analyze_iso_checks(
    req_dicts: list[dict[str, Any]],
    all_reqs: list[dict[str, Any]] | None = None,
    ambiguity_findings_map: dict[Any, list[Finding]] | None = None,
) -> list[RequirementIsoReport]:
    """Batched ISO checks across multiple requirements using nlp.pipe for high throughput."""
    if not req_dicts:
        return []
    if all_reqs is None:
        all_reqs = req_dicts
    if ambiguity_findings_map is None:
        ambiguity_findings_map = {}

    synonym_index = build_synonym_index(all_reqs)
    texts = [r.get("text", "") for r in req_dicts]
    pipe_kwargs = {"batch_size": 256}
    if nlp.has_pipe("ner"):
        pipe_kwargs["disable"] = ["ner"]

    docs = list(nlp.pipe(texts, **pipe_kwargs))
    reports = []
    for r, d in zip(req_dicts, docs):
        r_id = r.get("id", r.get("req_key"))
        amb_f = ambiguity_findings_map.get(r_id) or ambiguity_findings_map.get(r.get("req_key"))
        report = analyze_iso_checks(
            r,
            all_reqs=all_reqs,
            ambiguity_findings=amb_f,
            synonym_index=synonym_index,
            doc=d,
        )
        reports.append(report)
    return reports
