import pytest
from backend.app.nlp.readability import analyze_readability, ReadabilityMetrics


def test_readability_metrics_structure():
    text = (
        "The system shall allow users to reset their password using their registered email address."
    )
    metrics = analyze_readability(text)

    assert isinstance(metrics, ReadabilityMetrics)
    assert metrics.word_count > 5
    assert metrics.clause_count >= 1
    assert metrics.max_nesting_depth >= 1
    assert 0.0 <= metrics.passive_voice_ratio <= 1.0
    assert isinstance(metrics.flesch_reading_ease, float)
    assert isinstance(metrics.gunning_fog, float)

    d = metrics.to_dict()
    assert "word_count" in d
    assert "clause_count" in d
    assert "max_nesting_depth" in d
    assert "passive_voice_ratio" in d
    assert "flesch_reading_ease" in d
    assert "gunning_fog" in d


def test_readability_passive_voice_detection():
    # Active
    active_text = "The administrator creates the security policy."
    active_metrics = analyze_readability(active_text)
    assert active_metrics.passive_voice_ratio == 0.0

    # Passive
    passive_text = "The security policy is created by the system."
    passive_metrics = analyze_readability(passive_text)
    assert passive_metrics.passive_voice_ratio > 0.0
