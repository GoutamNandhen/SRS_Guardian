import pytest
from backend.app.nlp.ambiguity import (
    check_a_weak_terms,
    check_b_weak_modals,
    check_c_missing_metrics,
    check_d_vague_pronouns,
    check_e_compound_requirements,
    check_f_passive_voice,
    analyze_ambiguity,
)


def test_check_a_weak_terms():
    # Positive case: contains subjective speed term "quickly"
    findings_pos = check_a_weak_terms(
        "The system should respond quickly to customer requests."
    )
    assert len(findings_pos) >= 1
    assert any(
        f.rule_id == "CHECK_A_WEAK_TERM" and f.spans[0].text == "quickly"
        for f in findings_pos
    )

    # Negative case: unambiguous quantified statement
    findings_neg = check_a_weak_terms(
        "The system shall respond within 200 ms to customer requests."
    )
    assert len(findings_neg) == 0


def test_check_b_weak_modals():
    # Positive case: weak modal "should" and "may"
    findings_pos = check_b_weak_modals(
        "The application should allow login and users may skip 2FA."
    )
    assert len(findings_pos) == 2
    rule_ids = [f.rule_id for f in findings_pos]
    assert all(r == "CHECK_B_WEAK_MODAL" for r in rule_ids)
    modals = [f.spans[0].text.lower() for f in findings_pos]
    assert "should" in modals
    assert "may" in modals

    # Negative case: normative modals "shall" and "must"
    findings_neg = check_b_weak_modals(
        "The system shall authenticate the user and the user must provide a password."
    )
    assert len(findings_neg) == 0


def test_check_c_missing_metrics():
    # Positive case: mentions measurable concept "time" without any number
    findings_pos = check_c_missing_metrics(
        "The system shall minimize transaction latency and processing time."
    )
    assert len(findings_pos) >= 1
    concepts = [f.spans[0].text.lower() for f in findings_pos]
    assert "time" in concepts or "latency" in concepts

    # Negative case: mentions time with explicit metric threshold
    findings_neg = check_c_missing_metrics(
        "The system shall maintain a response time under 500 ms."
    )
    assert len(findings_neg) == 0


def test_check_d_vague_pronouns():
    # Positive case: "It" as subject without antecedent noun
    findings_pos = check_d_vague_pronouns(
        "It shall backup the database every night."
    )
    assert len(findings_pos) >= 1
    assert findings_pos[0].rule_id == "CHECK_D_VAGUE_PRONOUN"
    assert findings_pos[0].spans[0].text == "It"

    # Negative case: Clear actor subject
    findings_neg = check_d_vague_pronouns(
        "The database service shall backup customer tables every night."
    )
    assert len(findings_neg) == 0


def test_check_e_compound_requirements():
    # Positive case 1: Multiple normative modals ("shall" and "must")
    findings_pos_modals = check_e_compound_requirements(
        "The system shall encrypt data and administrators must review logs."
    )
    assert any(
        f.rule_id == "CHECK_E_COMPOUND_MODALS" for f in findings_pos_modals
    )

    # Positive case 2: Coordinated action verbs
    findings_pos_actions = check_e_compound_requirements(
        "The system shall notify the administrator and terminate the session."
    )
    assert any(
        f.rule_id == "CHECK_E_COMPOUND_ACTIONS" for f in findings_pos_actions
    )

    # Negative case: Single action and single modal
    findings_neg = check_e_compound_requirements(
        "The system shall notify the administrator upon failed authentication."
    )
    assert len(findings_neg) == 0


def test_check_f_passive_voice():
    # Positive case: Passive construction without actor
    findings_pos = check_f_passive_voice(
        "The user password was changed during maintenance."
    )
    assert len(findings_pos) >= 1
    assert findings_pos[0].rule_id == "CHECK_F_PASSIVE_VOICE"
    assert findings_pos[0].spans[0].text.lower() == "changed"

    # Negative case: Passive with explicit agent ("by the administrator") or active voice
    findings_neg = check_f_passive_voice(
        "The user password was changed by the administrator."
    )
    assert len(findings_neg) == 0


def test_unified_explanation_schema_contract():
    findings = analyze_ambiguity(
        "The system should respond quickly when the user checks account balance."
    )
    assert len(findings) >= 2  # weak modal "should" + weak term "quickly"

    for f in findings:
        d = f.to_dict()
        assert "finding_id" in d
        assert d["module"] == "ambiguity"
        assert d["method"] == "rule_based"
        assert "rule_id" in d
        assert isinstance(d["spans"], list)
        assert len(d["spans"]) > 0
        assert "start" in d["spans"][0]
        assert "end" in d["spans"][0]
        assert "text" in d["spans"][0]
        assert "factors" in d["factors"][0] or len(d["factors"]) > 0
        assert "human_explanation" in d
        assert "suggestion" in d
        assert 0.0 <= d["confidence"] <= 1.0
