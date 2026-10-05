"""SRS Guardian - LLM Service Module.

Single entry point for all LLM calls in the system (Rule 6).
Restricted strictly to:
1. AI Rewrite Suggestions
2. Gherkin Test Scenario Generation

Enforces:
- Global on/off switch (settings.LLM_ENABLED)
- Deterministic SHA-256 disk caching to prevent recomputation and API costs (Rule 7)
- Graceful offline fallback when disabled or when network is unavailable
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/cache")
LLM_CACHE_PATH = CACHE_DIR / "llm_cache.json"

_CACHE: dict[str, Any] | None = None
_CLIENT = None


def _get_cache() -> dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if LLM_CACHE_PATH.exists():
            try:
                with open(LLM_CACHE_PATH, "r", encoding="utf-8") as f:
                    _CACHE = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load LLM cache: {e}. Starting fresh.")
                _CACHE = {}
        else:
            _CACHE = {}
    return _CACHE


def _save_cache() -> None:
    global _CACHE
    if _CACHE is not None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(LLM_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(_CACHE, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save LLM cache to disk: {e}")


def _compute_cache_key(task: str, text: str, extra: str = "") -> str:
    payload = f"{task}:{settings.LLM_MODEL}:{text.strip().lower()}:{extra}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in settings or environment.")
        from google import genai
        _CLIENT = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _CLIENT


def suggest_rewrite(
    requirement_text: str,
    issues: list[dict[str, Any]] | None = None,
    ears_pattern: str | None = None,
) -> dict[str, Any]:
    """Generates an AI rewrite suggestion for a flagged requirement statement.

    Adheres to EARS guidelines and resolves identified quality/ambiguity issues.
    Returns structured suggestion with rationale and change notes.
    """
    if not settings.LLM_ENABLED:
        return {
            "enabled": False,
            "cached": False,
            "original_text": requirement_text,
            "suggested_text": None,
            "rationale": "LLM service is currently disabled. Enable LLM_ENABLED in configuration to generate rewrite suggestions.",
            "changes_made": [],
            "conforms_to_ears": False,
            "error": None,
        }

    issues_summary = ""
    if issues:
        issues_summary = "Detected issues to fix:\n" + "\n".join(
            f"- [{i.get('rule_id', 'ISSUE')}]: {i.get('human_explanation', '')}" for i in issues
        )

    ears_hint = f"Target EARS Pattern: {ears_pattern}" if ears_pattern else "Follow standard EARS structure (e.g., 'The <system> shall <action>')."

    cache_key = _compute_cache_key("rewrite", requirement_text, f"{ears_pattern}:{len(issues or [])}")
    cache = _get_cache()
    if cache_key in cache:
        cached_entry = cache[cache_key]
        return {
            "enabled": True,
            "cached": True,
            "original_text": requirement_text,
            "suggested_text": cached_entry.get("suggested_text"),
            "rationale": cached_entry.get("rationale"),
            "changes_made": cached_entry.get("changes_made", []),
            "conforms_to_ears": cached_entry.get("conforms_to_ears", True),
            "error": None,
        }

    prompt = f"""You are a professional requirements engineer specializing in ISO/IEC/IEEE 29148 and EARS (Easy Approach to Requirements Syntax).
Rewrite the following requirement to resolve its quality, ambiguity, or structural defects while strictly preserving its original engineering intent.

Requirement:
"{requirement_text}"

{issues_summary}
{ears_hint}

Instructions:
1. Provide a concise, clear, unambiguous rewrite.
2. Use active voice and normative modal ("shall").
3. Include specific measurable criteria or placeholders (e.g. "[within 2.0 seconds]") where metrics were vague.
4. Avoid subjective terms (e.g. "quickly", "user-friendly").
5. Return ONLY a valid JSON object with the following keys:
{{
  "suggested_text": "...",
  "rationale": "...",
  "changes_made": ["...", "..."],
  "conforms_to_ears": true
}}
"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.LLM_MODEL,
            contents=prompt,
        )
        raw_text = response.text.strip()
        # Handle markdown code blocks in LLM response if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)
        result = {
            "enabled": True,
            "cached": False,
            "original_text": requirement_text,
            "suggested_text": data.get("suggested_text"),
            "rationale": data.get("rationale"),
            "changes_made": data.get("changes_made", []),
            "conforms_to_ears": data.get("conforms_to_ears", True),
            "error": None,
        }

        # Cache valid response to disk
        cache[cache_key] = {
            "suggested_text": result["suggested_text"],
            "rationale": result["rationale"],
            "changes_made": result["changes_made"],
            "conforms_to_ears": result["conforms_to_ears"],
        }
        _save_cache()
        return result

    except Exception as e:
        logger.error(f"Gemini API call failed for rewrite suggestion: {e}")
        return {
            "enabled": True,
            "cached": False,
            "original_text": requirement_text,
            "suggested_text": None,
            "rationale": None,
            "changes_made": [],
            "conforms_to_ears": False,
            "error": f"LLM generation failed: {type(e).__name__}: {str(e)}",
        }


def generate_gherkin(
    requirement_text: str,
    classification_label: str | None = None,
    requirement_id: int | None = None,
) -> dict[str, Any]:
    """Generates standard Gherkin (Given/When/Then) test scenarios for a requirement.

    Transforms requirement statements into verifiable acceptance criteria.
    """
    if not settings.LLM_ENABLED:
        return {
            "enabled": False,
            "cached": False,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
            "gherkin_scenarios": None,
            "error": "LLM service is currently disabled. Enable LLM_ENABLED in configuration to generate Gherkin scenarios.",
        }

    cache_key = _compute_cache_key("gherkin", requirement_text, str(classification_label or ""))
    cache = _get_cache()
    if cache_key in cache:
        return {
            "enabled": True,
            "cached": True,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
            "gherkin_scenarios": cache[cache_key].get("gherkin_scenarios"),
            "error": None,
        }

    prompt = f"""You are a QA automation and requirements verification engineer.
Convert the following software requirement into 1 to 2 standard, highly testable Gherkin acceptance test scenarios.

Requirement ({classification_label or 'Functional'}):
"{requirement_text}"

Instructions:
1. Use standard Gherkin format:
Feature: <Feature Name>
  Scenario: <Positive or primary happy path>
    Given <initial context or precondition>
    When <action or event occurs>
    Then <verifiable outcome or response>

  Scenario: <Negative or edge case condition>
    Given ...
    When ...
    Then ...
2. Return ONLY the plain Gherkin text. Do not wrap in markdown quotes or preamble.
"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.LLM_MODEL,
            contents=prompt,
        )
        scenarios = response.text.strip()
        # Clean any markdown fences if model returned them
        if scenarios.startswith("```gherkin"):
            scenarios = scenarios[10:]
        elif scenarios.startswith("```"):
            scenarios = scenarios[3:]
        if scenarios.endswith("```"):
            scenarios = scenarios[:-3]
        scenarios = scenarios.strip()

        result = {
            "enabled": True,
            "cached": False,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
            "gherkin_scenarios": scenarios,
            "error": None,
        }

        # Cache to disk
        cache[cache_key] = {"gherkin_scenarios": scenarios}
        _save_cache()
        return result

    except Exception as e:
        logger.error(f"Gemini API call failed for Gherkin generation: {e}")
        return {
            "enabled": True,
            "cached": False,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
            "gherkin_scenarios": None,
            "error": f"LLM generation failed: {type(e).__name__}: {str(e)}",
        }
