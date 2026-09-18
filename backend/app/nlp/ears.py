"""
EARS (Easy Approach to Requirements Syntax) Validation Engine.

Rule-based matching against the standard EARS patterns:
1. Ubiquitous:       THE <system> SHALL <response>
2. Event-driven:     WHEN <trigger>, THE <system> SHALL <response>
3. State-driven:     WHILE <state>, THE <system> SHALL <response>
4. Unwanted:         IF <condition>, THEN THE <system> SHALL <response>
5. Optional feature: WHERE <feature>, THE <system> SHALL <response>
6. Complex:          Combinations of preconditions (e.g. WHILE <state>, WHEN <trigger>, ...)

NOTE: An EARS match does NOT imply that the requirement is logically correct or complete.
It evaluates conformance to structured natural language syntax.
"""

from dataclasses import dataclass, field
import re
from typing import Any
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


# Modal verb patterns
NORMATIVE_MODALS = {"shall", "must"}
WEAK_MODALS = {"should", "may", "could", "might", "can"}
ALL_MODALS = NORMATIVE_MODALS.union(WEAK_MODALS)


@dataclass
class EarsResult:
    pattern: str  # "ubiquitous", "event_driven", "state_driven", "unwanted_behavior", "optional_feature", "complex", "non_conforming"
    is_valid_ears: bool
    trigger: str | None = None
    state: str | None = None
    feature: str | None = None
    condition: str | None = None
    system: str | None = None
    modal: str | None = None
    response: str | None = None
    missing_elements: list[str] = field(default_factory=list)
    explanation: str = ""
    suggestion: str | None = None
    matched_template: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "is_valid_ears": self.is_valid_ears,
            "trigger": self.trigger,
            "state": self.state,
            "feature": self.feature,
            "condition": self.condition,
            "system": self.system,
            "modal": self.modal,
            "response": self.response,
            "missing_elements": self.missing_elements,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "matched_template": self.matched_template,
        }


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip().strip(",").strip(".").strip()
    return cleaned if cleaned else None


def analyze_ears(text: str) -> EarsResult:
    """
    Analyzes a requirement string against EARS syntax patterns.
    """
    stripped = text.strip().rstrip(".")
    if not stripped:
        return EarsResult(
            pattern="non_conforming",
            is_valid_ears=False,
            missing_elements=["text"],
            explanation="Requirement text is empty.",
            suggestion="Specify a complete requirement following an EARS template.",
        )

    # 1. Regex check for standard modal clause: <system> (shall|must|should|may|can) <response>
    modal_regex = re.compile(
        r"^(.*?)\b(shall|must|should|may|could|might|can)\b\s+(.*)$",
        re.IGNORECASE,
    )

    # 2. Check for leading clauses: WHEN, WHILE, IF, WHERE
    # Preconditions can occur at the beginning
    trigger: str | None = None
    state: str | None = None
    condition: str | None = None
    feature: str | None = None

    working_text = stripped

    # Check for prefix clauses
    # Complex pattern check (multiple prefix keywords)
    prefix_types: list[str] = []

    # WHILE <state>
    while_match = re.search(r"^\s*while\s+([^,]+?)(?:,\s*|\s+(?=when\b|if\b|where\b|the\b))", working_text, re.IGNORECASE)
    if while_match:
        state = _clean(while_match.group(1))
        prefix_types.append("state")
        working_text = working_text[while_match.end():].strip()

    # WHERE <feature>
    where_match = re.search(r"^\s*where\s+([^,]+?)(?:,\s*|\s+(?=when\b|if\b|while\b|the\b))", working_text, re.IGNORECASE)
    if where_match:
        feature = _clean(where_match.group(1))
        prefix_types.append("feature")
        working_text = working_text[where_match.end():].strip()

    # WHEN <trigger>
    when_match = re.search(r"^\s*when\s+([^,]+?)(?:,\s*|\s+(?=if\b|the\b))", working_text, re.IGNORECASE)
    if when_match:
        trigger = _clean(when_match.group(1))
        prefix_types.append("trigger")
        working_text = working_text[when_match.end():].strip()

    # IF <condition> [, THEN]
    if_match = re.search(r"^\s*if\s+([^,]+?)(?:,\s*then\s+|\s+then\s+|,\s*|\s+(?=the\b))", working_text, re.IGNORECASE)
    if if_match:
        condition = _clean(if_match.group(1))
        prefix_types.append("condition")
        working_text = working_text[if_match.end():].strip()

    # If no prefix matched at start, check for trailing WHEN / WHILE / IF / WHERE clauses
    # e.g. "The system shall respond quickly when the user checks the account balance"
    if not prefix_types:
        trailing_when = re.search(r"\bwhen\s+(.+)$", working_text, re.IGNORECASE)
        if trailing_when:
            trigger = _clean(trailing_when.group(1))
            prefix_types.append("trigger")
            working_text = working_text[:trailing_when.start()].strip()

        trailing_while = re.search(r"\bwhile\s+(.+)$", working_text, re.IGNORECASE)
        if trailing_while and not trigger:
            state = _clean(trailing_while.group(1))
            prefix_types.append("state")
            working_text = working_text[:trailing_while.start()].strip()

        trailing_if = re.search(r"\bif\s+(.+)$", working_text, re.IGNORECASE)
        if trailing_if and not trigger and not state:
            condition = _clean(trailing_if.group(1))
            prefix_types.append("condition")
            working_text = working_text[:trailing_if.start()].strip()

    # Now parse the system + modal + response in the main clause
    # Remove leading "then " if leftover
    if working_text.lower().startswith("then "):
        working_text = working_text[5:].strip()

    m_match = modal_regex.match(working_text)

    system: str | None = None
    modal: str | None = None
    response: str | None = None
    missing_elements: list[str] = []

    if m_match:
        system = _clean(m_match.group(1))
        modal = m_match.group(2).lower()
        response = _clean(m_match.group(3))
    else:
        # Fall back to spaCy dependency parse to extract subject, aux, and predicate
        doc = nlp(working_text)
        subjs = [token for token in doc if token.dep_ in ("nsubj", "nsubjpass")]
        auxs = [token for token in doc if token.dep_ in ("aux", "auxpass") and token.text.lower() in ALL_MODALS]

        if subjs:
            system = _clean(doc[:subjs[0].i + 1].text)
        if auxs:
            modal = auxs[0].text.lower()
            response = _clean(doc[auxs[0].i + 1:].text)
        elif subjs:
            response = _clean(doc[subjs[0].i + 1:].text)

    # Check for missing elements in the core clause
    if not system:
        missing_elements.append("system")
    if not modal:
        missing_elements.append("modal")
    elif modal not in NORMATIVE_MODALS:
        missing_elements.append("normative_modal")
    if not response:
        missing_elements.append("response")

    # Determine Pattern Name
    pattern: str = "non_conforming"
    matched_template: str | None = None
    is_valid_ears: bool = False

    num_prefixes = len(prefix_types)

    if num_prefixes > 1:
        pattern = "complex"
        matched_template = "While <state>, When <trigger>, The <system> shall <response>"
    elif num_prefixes == 1:
        p_type = prefix_types[0]
        if p_type == "trigger":
            pattern = "event_driven"
            matched_template = "When <trigger>, The <system> shall <response>"
        elif p_type == "state":
            pattern = "state_driven"
            matched_template = "While <state>, The <system> shall <response>"
        elif p_type == "condition":
            pattern = "unwanted_behavior"
            matched_template = "If <condition>, then The <system> shall <response>"
        elif p_type == "feature":
            pattern = "optional_feature"
            matched_template = "Where <feature>, The <system> shall <response>"
    else:
        # No prefix clauses
        if system and modal and response:
            pattern = "ubiquitous"
            matched_template = "The <system> shall <response>"
        else:
            pattern = "non_conforming"

    # Strict EARS validity: must have system, normative modal ('shall' or 'must'), and response
    has_core_elements = bool(system and response and (modal in NORMATIVE_MODALS))
    is_valid_ears = (pattern != "non_conforming") and has_core_elements

    # Construct Explanation and Suggestions
    explanation_parts: list[str] = []
    suggestion: str | None = None

    if pattern == "ubiquitous":
        explanation_parts.append(f"Matches EARS Ubiquitous pattern: active under all operational conditions.")
    elif pattern == "event_driven":
        explanation_parts.append(f"Matches EARS Event-driven pattern with trigger '{trigger}'.")
    elif pattern == "state_driven":
        explanation_parts.append(f"Matches EARS State-driven pattern with state '{state}'.")
    elif pattern == "unwanted_behavior":
        explanation_parts.append(f"Matches EARS Unwanted behavior pattern with condition '{condition}'.")
    elif pattern == "optional_feature":
        explanation_parts.append(f"Matches EARS Optional feature pattern with feature '{feature}'.")
    elif pattern == "complex":
        explanation_parts.append(f"Matches EARS Complex pattern combining multiple pre-conditions.")
    else:
        explanation_parts.append("Does not conform to any standard EARS syntactic pattern.")

    if missing_elements:
        missing_desc = ", ".join(f"'{m}'" for m in missing_elements)
        explanation_parts.append(f"Structural elements missing or non-normative: {missing_desc}.")

        # Generate recommendation
        if "normative_modal" in missing_elements:
            suggestion = f"Replace weak modal '{modal}' with normative 'shall' or 'must'."
        elif "system" in missing_elements:
            suggestion = "Specify an explicit target system or actor (e.g. 'The system shall...')."
        elif "modal" in missing_elements:
            suggestion = "Add a normative modal verb ('shall' or 'must')."
        else:
            suggestion = f"Restructure using EARS template: {matched_template or 'The <system> shall <response>'}"

    explanation = " ".join(explanation_parts)

    return EarsResult(
        pattern=pattern,
        is_valid_ears=is_valid_ears,
        trigger=trigger,
        state=state,
        feature=feature,
        condition=condition,
        system=system,
        modal=modal,
        response=response,
        missing_elements=missing_elements,
        explanation=explanation,
        suggestion=suggestion,
        matched_template=matched_template,
    )
