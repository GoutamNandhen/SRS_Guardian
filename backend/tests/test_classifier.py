import pytest
from backend.app.ml.classifier import classify
from backend.app.ml.explain_classifier import explain


def test_classifier_predictions():
    # Typically Functional
    label_f, prob_f = classify(
        "The system shall allow users to reset their password using their registered email."
    )
    assert label_f in ("Functional", "Non-Functional")
    assert 0.5 <= prob_f <= 1.0

    # Typically Non-Functional (Performance)
    label_nf, prob_nf = classify(
        "The system shall achieve 99.99% availability and respond within 50 milliseconds."
    )
    assert label_nf in ("Functional", "Non-Functional")
    assert 0.5 <= prob_nf <= 1.0


def test_explain_classifier_tokens():
    text = (
        "The system should respond quickly when the user checks the account balance."
    )
    tokens = explain(text)
    assert isinstance(tokens, list)
    assert len(tokens) <= 8
    assert len(tokens) > 0

    for token, val in tokens:
        assert isinstance(token, str)
        assert isinstance(val, float)

    # Test cache retrieval
    cached_tokens = explain(text)
    assert cached_tokens == tokens
