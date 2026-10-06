"""SRS Guardian - Numeric Constraint Extraction and Conflict Detection Engine.

Mechanism 1 of Phase 12 (Contradiction Detection).
Extracts structured 5-tuples: (entity, attribute, comparator, value, unit)
from requirement statements and detects logical/mathematical interval conflicts.
Deterministic, explainable, and requires zero ML/LLM inference.
"""

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

import spacy
from spacy.language import Language

_NLP: Language | None = None


def get_spacy_nlp() -> Language:
    """Lazily loads and caches the spaCy model."""
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            _NLP = spacy.blank("en")
            if "sentencizer" not in _NLP.pipe_names:
                _NLP.add_pipe("sentencizer")
    return _NLP


@dataclass
class NumericConstraint:
    """Represents an extracted quantitative requirement constraint."""
    entity: str
    attribute: str
    comparator: str  # '>=', '<=', '==', '>', '<', '!=', 'between'
    value: float
    value_max: float | None = None  # Populated when comparator is 'between'
    unit: str = ""
    normalized_value: float = 0.0
    normalized_value_max: float | None = None
    normalized_unit: str = ""
    raw_span: str = ""
    char_start: int = 0
    char_end: int = 0
    req_key: str | None = None
    requirement_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def range_display(self) -> str:
        """User-friendly mathematical range representation."""
        if self.comparator == "==":
            return f"exactly {self.value:g} {self.unit}"
        elif self.comparator == ">=":
            return f"[{self.value:g}, inf) {self.unit}"
        elif self.comparator == ">":
            return f"({self.value:g}, inf) {self.unit}"
        elif self.comparator == "<=":
            return f"(-inf, {self.value:g}] {self.unit}"
        elif self.comparator == "<":
            return f"(-inf, {self.value:g}) {self.unit}"
        elif self.comparator == "!=":
            return f"!= {self.value:g} {self.unit}"
        elif self.comparator == "between" and self.value_max is not None:
            return f"[{self.value:g}, {self.value_max:g}] {self.unit}"
        return f"{self.comparator} {self.value:g} {self.unit}"


@dataclass
class NumericConflictFinding:
    """Represents a potential numeric contradiction between two requirements."""
    finding_id: str
    req_key_1: str
    req_key_2: str
    requirement_id_1: int | None
    requirement_id_2: int | None
    constraint_1: NumericConstraint
    constraint_2: NumericConstraint
    module: str = "contradiction"
    rule_id: str = "NUMERIC_CONSTRAINT_CONFLICT"
    severity: str = "critical"
    confidence: float = 1.0  # Deterministic mathematical rule
    human_explanation: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "module": self.module,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "confidence": self.confidence,
            "req_key_1": self.req_key_1,
            "req_key_2": self.req_key_2,
            "requirement_id_1": self.requirement_id_1,
            "requirement_id_2": self.requirement_id_2,
            "constraint_1": self.constraint_1.to_dict(),
            "constraint_2": self.constraint_2.to_dict(),
            "human_explanation": self.human_explanation,
            "suggestion": self.suggestion,
        }


# Unit normalization map: maps variant units to canonical units and conversion multipliers
UNIT_CONVERSIONS = {
    # Characters / Length
    "character": ("characters", 1.0, "length"),
    "characters": ("characters", 1.0, "length"),
    "char": ("characters", 1.0, "length"),
    "chars": ("characters", 1.0, "length"),
    "letter": ("characters", 1.0, "length"),
    "letters": ("characters", 1.0, "length"),
    "digit": ("characters", 1.0, "length"),
    "digits": ("characters", 1.0, "length"),

    # Time / Latency
    "millisecond": ("seconds", 0.001, "latency"),
    "milliseconds": ("seconds", 0.001, "latency"),
    "ms": ("seconds", 0.001, "latency"),
    "second": ("seconds", 1.0, "latency"),
    "seconds": ("seconds", 1.0, "latency"),
    "sec": ("seconds", 1.0, "latency"),
    "s": ("seconds", 1.0, "latency"),
    "minute": ("seconds", 60.0, "duration"),
    "minutes": ("seconds", 60.0, "duration"),
    "min": ("seconds", 60.0, "duration"),
    "hour": ("seconds", 3600.0, "duration"),
    "hours": ("seconds", 3600.0, "duration"),
    "hr": ("seconds", 3600.0, "duration"),
    "hrs": ("seconds", 3600.0, "duration"),
    "day": ("seconds", 86400.0, "duration"),
    "days": ("seconds", 86400.0, "duration"),

    # Size / Memory
    "byte": ("mb", 1.0 / (1024 * 1024), "size"),
    "bytes": ("mb", 1.0 / (1024 * 1024), "size"),
    "b": ("mb", 1.0 / (1024 * 1024), "size"),
    "kb": ("mb", 1.0 / 1024.0, "size"),
    "kilobyte": ("mb", 1.0 / 1024.0, "size"),
    "kilobytes": ("mb", 1.0 / 1024.0, "size"),
    "mb": ("mb", 1.0, "size"),
    "megabyte": ("mb", 1.0, "size"),
    "megabytes": ("mb", 1.0, "size"),
    "gb": ("mb", 1024.0, "size"),
    "gigabyte": ("mb", 1024.0, "size"),
    "gigabytes": ("mb", 1024.0, "size"),

    # Concurrency / Capacity
    "user": ("users", 1.0, "capacity"),
    "users": ("users", 1.0, "capacity"),
    "session": ("users", 1.0, "capacity"),
    "sessions": ("users", 1.0, "capacity"),
    "connection": ("users", 1.0, "capacity"),
    "connections": ("users", 1.0, "capacity"),
    "request": ("requests", 1.0, "throughput"),
    "requests": ("requests", 1.0, "throughput"),
    "transaction": ("requests", 1.0, "throughput"),
    "transactions": ("requests", 1.0, "throughput"),
    "retry": ("retries", 1.0, "count"),
    "retries": ("retries", 1.0, "count"),
    "attempt": ("retries", 1.0, "count"),
    "attempts": ("retries", 1.0, "count"),

    # Percentage
    "%": ("%", 1.0, "ratio"),
    "percent": ("%", 1.0, "ratio"),
    "percentage": ("%", 1.0, "ratio"),
}

# Regex patterns for extracting numeric constraints
COMPARATOR_PATTERNS = [
    # Between X and Y
    (
        r"(?i)\bbetween\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "between",
    ),
    (
        r"(?i)\bfrom\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "between",
    ),
    # Greater than or equal (>=)
    (
        r"(?i)\b(?:at\s+least|no\s+less\s+than|minimum\s+of|greater\s+than\s+or\s+equal\s+to|>=\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        ">=",
    ),
    # Less than or equal (<=)
    (
        r"(?i)\b(?:at\s+most|no\s+more\s+than|maximum\s+of|less\s+than\s+or\s+equal\s+to|within|up\s+to|not\s+exceed|<=\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "<=",
    ),
    # Exactly (==)
    (
        r"(?i)\b(?:exactly|equal\s+to|precisely|==\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "==",
    ),
    # Strictly greater (>)
    (
        r"(?i)\b(?:greater\s+than|more\s+than|exceeding|over|>\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        ">",
    ),
    # Strictly less (<)
    (
        r"(?i)\b(?:less\s+than|fewer\s+than|under|<\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "<",
    ),
    # Not equal (!=)
    (
        r"(?i)\b(?:not\s+equal\s+to|different\s+from|!=\s*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b",
        "!=",
    ),
]


def extract_entity_from_text(text: str, match_start: int, nlp: Language) -> str:
    """Extracts the subject or domain entity governing the constraint using spaCy."""
    doc = nlp(text)
    
    # 1. Look for noun chunks that occur before or govern the match
    candidates = []
    for chunk in doc.noun_chunks:
        # Avoid generic pronouns
        clean_text = chunk.lemma_.lower().strip()
        if clean_text in ("it", "this", "that", "system", "the system"):
            continue
        # If the chunk precedes the match
        if chunk.end_char <= match_start + 10:
            candidates.append(chunk.text.lower().strip())

    if candidates:
        # Return the most specific preceding noun phrase
        # E.g. "password", "file upload", "response time"
        best = candidates[-1]
        for stop in ("the ", "a ", "an "):
            if best.startswith(stop):
                best = best[len(stop):]
        return best

    # 2. Fallback: inspect subject of the root verb
    for token in doc:
        if token.dep_ in ("nsubj", "nsubjpass") and token.lemma_.lower() not in ("system", "it"):
            # Include compound nouns e.g. "response time"
            compounds = [w.text.lower() for w in token.lefts if w.dep_ == "compound"]
            compounds.append(token.text.lower())
            return " ".join(compounds)

    # 3. Default to "system" if nothing specific found
    return "system"


def extract_constraints(
    text: str,
    req_key: str | None = None,
    requirement_id: int | None = None,
) -> list[NumericConstraint]:
    """Extracts all numeric constraints from a single requirement statement."""
    nlp = get_spacy_nlp()
    constraints: list[NumericConstraint] = []
    
    # Clean requirement ID prefix if present for clean entity parsing
    clean_text = text
    id_match = re.match(r"^(?:REQ|FR|NFR|BR|UC)?[-_ ]?\d+[:.]?\s*", text, flags=re.IGNORECASE)
    offset_adjustment = 0
    if id_match:
        offset_adjustment = id_match.end()
        clean_text = text[offset_adjustment:]

    for pattern, comparator in COMPARATOR_PATTERNS:
        for match in re.finditer(pattern, clean_text):
            groups = match.groups()
            raw_span = match.group(0).strip()
            char_start = match.start() + offset_adjustment
            char_end = match.end() + offset_adjustment

            val1 = float(groups[0])
            val2 = None
            unit_str = ""

            if comparator == "between":
                val2 = float(groups[1])
                if len(groups) > 2 and groups[2]:
                    unit_str = groups[2].lower()
            else:
                if len(groups) > 1 and groups[1]:
                    unit_str = groups[1].lower()

            # If unit wasn't captured in the regex match, look immediately after
            if not unit_str:
                after_match = clean_text[match.end(): match.end() + 25]
                unit_search = re.match(r"^\s*([a-zA-Z%]+)", after_match)
                if unit_search:
                    unit_str = unit_search.group(1).lower()

            # Normalize unit and calculate normalized values
            conv_info = UNIT_CONVERSIONS.get(unit_str)
            if conv_info:
                norm_unit, multiplier, inferred_attr = conv_info
                norm_val = val1 * multiplier
                norm_val2 = val2 * multiplier if val2 is not None else None
            else:
                norm_unit = unit_str
                norm_val = val1
                norm_val2 = val2
                inferred_attr = "quantity"

            entity = extract_entity_from_text(clean_text, match.start(), nlp)

            # Refine attribute based on entity
            attribute = inferred_attr
            if "time" in entity or "latency" in entity or "delay" in entity:
                attribute = "latency"
            elif "size" in entity or "length" in entity:
                attribute = "size" if norm_unit == "mb" else "length"

            constraints.append(
                NumericConstraint(
                    entity=entity,
                    attribute=attribute,
                    comparator=comparator,
                    value=val1,
                    value_max=val2,
                    unit=unit_str or norm_unit,
                    normalized_value=norm_val,
                    normalized_value_max=norm_val2,
                    normalized_unit=norm_unit,
                    raw_span=raw_span,
                    char_start=char_start,
                    char_end=char_end,
                    req_key=req_key,
                    requirement_id=requirement_id,
                )
            )

    return constraints


def get_constraint_interval(c: NumericConstraint) -> tuple[float, float, bool, bool]:
    """Returns interval (low, high, include_low, include_high) using normalized values."""
    comp = c.comparator
    v = c.normalized_value

    if comp == ">=":
        return (v, math.inf, True, False)
    elif comp == ">":
        return (v, math.inf, False, False)
    elif comp == "<=":
        return (-math.inf, v, False, True)
    elif comp == "<":
        return (-math.inf, v, False, False)
    elif comp == "==":
        return (v, v, True, True)
    elif comp == "between" and c.normalized_value_max is not None:
        return (v, c.normalized_value_max, True, True)
    elif comp == "!=":
        # Special representation: low = high = v with open flags
        return (v, v, False, False)

    return (-math.inf, math.inf, False, False)


def intervals_conflict(c1: NumericConstraint, c2: NumericConstraint) -> tuple[bool, str]:
    """Evaluates whether two numeric constraints have an empty interval intersection."""
    # Discrete exclusion (!=) handling
    if c1.comparator == "!=" and c2.comparator == "==":
        if math.isclose(c1.normalized_value, c2.normalized_value, rel_tol=1e-5):
            return True, f"Value cannot simultaneously equal and not equal {c1.normalized_value:g}."
        return False, ""
    if c2.comparator == "!=" and c1.comparator == "==":
        if math.isclose(c1.normalized_value, c2.normalized_value, rel_tol=1e-5):
            return True, f"Value cannot simultaneously equal and not equal {c1.normalized_value:g}."
        return False, ""

    l1, h1, inc_l1, inc_h1 = get_constraint_interval(c1)
    l2, h2, inc_l2, inc_h2 = get_constraint_interval(c2)

    # Case 1: Interval 1 strictly below Interval 2
    if h1 < l2:
        return True, f"Upper bound of {c1.range_display} is strictly below lower bound of {c2.range_display}."
    if h2 < l1:
        return True, f"Upper bound of {c2.range_display} is strictly below lower bound of {c1.range_display}."

    # Case 2: Boundaries touch at a single point (h1 == l2 or h2 == l1)
    if math.isclose(h1, l2, rel_tol=1e-5):
        if not (inc_h1 and inc_l2):
            return True, f"Ranges touch at {h1:g} but at least one boundary excludes the point."
    if math.isclose(h2, l1, rel_tol=1e-5):
        if not (inc_h2 and inc_l1):
            return True, f"Ranges touch at {h2:g} but at least one boundary excludes the point."

    return False, ""


def are_entities_compatible(e1: str, e2: str) -> bool:
    """Checks if two entity strings refer to the same domain concept."""
    e1_clean = e1.lower().strip()
    e2_clean = e2.lower().strip()

    if e1_clean == e2_clean:
        return True

    # Substring match (e.g. "password" in "user password")
    if e1_clean in e2_clean or e2_clean in e1_clean:
        return True

    # Token lemma intersection
    tokens1 = set(re.findall(r"\w+", e1_clean))
    tokens2 = set(re.findall(r"\w+", e2_clean))
    common = tokens1.intersection(tokens2)
    # Exclude trivial words
    common.difference_update({"the", "a", "an", "system", "user"})
    if common:
        return True

    return False


def detect_numeric_conflicts(
    requirements: list[dict[str, Any]],
) -> list[NumericConflictFinding]:
    """Detects all numeric constraint conflicts across requirement statements.

    Args:
        requirements: List of dicts with keys: 'id', 'req_key', 'text'.

    Returns:
        List of NumericConflictFinding objects representing POTENTIAL contradictions.
    """
    # 1. Extract constraints for each requirement
    req_constraints: dict[str, list[NumericConstraint]] = {}
    for r in requirements:
        req_key = r.get("req_key", str(r.get("id", "")))
        req_id = r.get("id")
        text = r.get("text", "")
        c_list = extract_constraints(text, req_key=req_key, requirement_id=req_id)
        if c_list:
            req_constraints[req_key] = c_list

    findings: list[NumericConflictFinding] = []
    keys = list(req_constraints.keys())

    # 2. Cross-compare constraints between distinct requirements
    for i in range(len(keys)):
        k1 = keys[i]
        c_list_1 = req_constraints[k1]

        for j in range(i + 1, len(keys)):
            k2 = keys[j]
            c_list_2 = req_constraints[k2]

            for c1 in c_list_1:
                for c2 in c_list_2:
                    # Units must normalize to the same dimension
                    if c1.normalized_unit != c2.normalized_unit:
                        continue

                    # Entity and attribute must be compatible
                    if not are_entities_compatible(c1.entity, c2.entity):
                        continue

                    # Check mathematical interval conflict
                    has_conflict, math_reason = intervals_conflict(c1, c2)
                    if has_conflict:
                        finding_id = f"NUMERIC_CONFLICT_{k1}_{k2}_{c1.attribute}"
                        explanation = (
                            f"POTENTIAL contradiction: Requirement {k1} specifies '{c1.entity}' "
                            f"must be {c1.range_display}, whereas Requirement {k2} specifies "
                            f"{c2.range_display}. These constraints cannot be simultaneously satisfied "
                            f"({math_reason})."
                        )
                        suggestion = (
                            f"Reconcile the quantitative constraints on '{c1.entity}' between "
                            f"{k1} and {k2} with project stakeholders to establish a consistent threshold."
                        )

                        findings.append(
                            NumericConflictFinding(
                                finding_id=finding_id,
                                req_key_1=k1,
                                req_key_2=k2,
                                requirement_id_1=c1.requirement_id,
                                requirement_id_2=c2.requirement_id,
                                constraint_1=c1,
                                constraint_2=c2,
                                human_explanation=explanation,
                                suggestion=suggestion,
                            )
                        )

    return findings
