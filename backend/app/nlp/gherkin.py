"""SRS Guardian - Rule-Based Gherkin Test Skeleton Generator.

Phase 15A: Tier 3.
Transforms natural language software requirements into executable Given/When/Then
Gherkin test skeletons.

Strategy:
1. Rule-Based (Primary): Inspects EARS pattern (Event-driven, State-driven, Unwanted,
   Optional feature, Ubiquitous, Complex) from `backend.app.nlp.ears`.
   Directly maps extracted clauses to Given/When/Then steps without calling any LLM.
2. Fallback: If requirement does not conform to EARS:
   - If LLM is enabled (settings.LLM_ENABLED): delegates to `backend.app.services.llm.generate_gherkin`.
   - If LLM is disabled: produces a deterministic structured fallback skeleton.

This guarantees 100% offline, zero-cost, deterministic test skeleton generation.
"""

import re
from typing import Any
from backend.app.core.config import settings
from backend.app.nlp.ears import analyze_ears, EarsResult


def _capitalize_clause(clause: str) -> str:
    """Capitalizes the first character of a clause if lowercase."""
    if not clause:
        return ""
    c = clause.strip()
    return c[0].upper() + c[1:] if len(c) > 1 else c.upper()


def _format_scenario_name(text: str, max_words: int = 8) -> str:
    """Creates a concise scenario title from text."""
    words = re.findall(r"\w+", text)
    if not words:
        return "Verify system behavior"
    title_words = words[:max_words]
    return " ".join(title_words).capitalize()


def generate_gherkin_from_ears(ears: EarsResult, requirement_text: str) -> str:
    """Generates standard Given/When/Then Gherkin syntax from parsed EARS elements."""
    system = ears.system or "the system"
    response = ears.response or "perform the intended function"
    modal = ears.modal or "shall"

    # Inline system name (e.g. "the system" rather than "The system" mid-sentence)
    if system.startswith("The ") or system.startswith("the "):
        sys_inline = "the " + system[4:]
    elif system.startswith("A ") or system.startswith("a "):
        sys_inline = "a " + system[2:]
    else:
        sys_inline = system

    # Feature title based on system
    feature_title = f"{system.title()} Verification"

    if ears.pattern == "event_driven" and ears.trigger:
        scenario_title = f"Handle trigger - {_format_scenario_name(ears.trigger)}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS Event-Driven Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given {sys_inline} is operational and in ready state\n"
            f"    When {_capitalize_clause(ears.trigger)}\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    elif ears.pattern == "state_driven" and ears.state:
        scenario_title = f"Operate while in state - {_format_scenario_name(ears.state)}"
        state_clause = ears.state.strip()
        state_repr = state_clause if state_clause.lower().startswith("in ") else f"in state: {state_clause}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS State-Driven Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given {sys_inline} is active and {state_repr}\n"
            f"    When a functional request or event occurs\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    elif ears.pattern == "unwanted_behavior" and ears.condition:
        scenario_title = f"Mitigate condition - {_format_scenario_name(ears.condition)}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS Unwanted Behavior Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given {sys_inline} is operating\n"
            f"    When {_capitalize_clause(ears.condition)}\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    elif ears.pattern == "optional_feature" and ears.feature:
        scenario_title = f"Execute optional feature - {_format_scenario_name(ears.feature)}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS Optional Feature Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given feature '{ears.feature}' is enabled\n"
            f"    When the user or caller invokes {sys_inline}\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    elif ears.pattern == "complex":
        precondition_parts = []
        if ears.state:
            precondition_parts.append(f"in state: {ears.state}")
        if ears.feature:
            precondition_parts.append(f"with feature '{ears.feature}' enabled")
        precondition_str = " and ".join(precondition_parts) if precondition_parts else "operational"

        event_trigger = ears.trigger or ears.condition or "an authorized event is triggered"
        scenario_title = f"Complex condition response - {_format_scenario_name(event_trigger)}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS Complex Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given {sys_inline} is {precondition_str}\n"
            f"    When {_capitalize_clause(event_trigger)}\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    elif ears.pattern == "ubiquitous":
        scenario_title = f"Standard system behavior - {_format_scenario_name(response)}"
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Derived via EARS Ubiquitous Pattern (Rule-Based)\n"
            f"  Scenario: {scenario_title}\n"
            f"    Given {sys_inline} is initialized and ready\n"
            f"    When the function is requested by an authorized user\n"
            f"    Then {sys_inline} {modal} {response}\n"
        )
    else:
        # Fallback template
        gherkin = (
            f"Feature: {feature_title}\n"
            f"  # Structured Fallback Skeleton\n"
            f"  Scenario: Satisfy requirement statement\n"
            f"    Given {sys_inline} is initialized\n"
            f"    When the operational workflow is executed\n"
            f"    Then {sys_inline} shall satisfy: {requirement_text.strip()}\n"
        )

    return gherkin.strip()


def generate_gherkin_skeleton(
    requirement_text: str,
    classification_label: str | None = None,
    requirement_id: int | None = None,
) -> dict[str, Any]:
    """Generates Given/When/Then acceptance criteria skeletons.

    Prioritizes deterministic rule-based synthesis via EARS patterns.
    Falls back to LLM generation only when EARS pattern is non-conforming
    and LLM_ENABLED is True.
    """
    clean_text = requirement_text.strip()
    ears_result = analyze_ears(clean_text)

    # If requirement conforms to one of the 6 EARS templates
    if ears_result.pattern != "non_conforming" and (ears_result.system or ears_result.response):
        scenarios = generate_gherkin_from_ears(ears_result, clean_text)
        return {
            "enabled": True,
            "cached": False,
            "source": "ears_rule",
            "ears_pattern": ears_result.pattern,
            "requirement_id": requirement_id,
            "requirement_text": clean_text,
            "gherkin_scenarios": scenarios,
            "error": None,
        }

    # If non-conforming and LLM is enabled, attempt LLM generation
    if settings.LLM_ENABLED:
        try:
            from backend.app.services.llm import generate_gherkin as llm_generate
            llm_res = llm_generate(
                requirement_text=clean_text,
                classification_label=classification_label,
                requirement_id=requirement_id,
            )
            if llm_res.get("gherkin_scenarios"):
                return {
                    "enabled": True,
                    "cached": llm_res.get("cached", False),
                    "source": "llm",
                    "ears_pattern": ears_result.pattern,
                    "requirement_id": requirement_id,
                    "requirement_text": clean_text,
                    "gherkin_scenarios": llm_res.get("gherkin_scenarios"),
                    "error": None,
                }
        except Exception as e:
            # Log and fall back to rule-based fallback skeleton
            pass

    # Deterministic rule-based fallback skeleton when non-conforming and LLM is disabled or failed
    fallback_scenarios = generate_gherkin_from_ears(ears_result, clean_text)
    return {
        "enabled": True,
        "cached": False,
        "source": "fallback_rule",
        "ears_pattern": ears_result.pattern,
        "requirement_id": requirement_id,
        "requirement_text": clean_text,
        "gherkin_scenarios": fallback_scenarios,
        "error": None,
    }
