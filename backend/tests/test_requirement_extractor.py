import pytest
from backend.app.nlp.requirement_extractor import extract_requirements, Requirement


def test_id_labelled_document():
    doc = """
ONLINE BANKING SYSTEM
REQ-001: The system should respond quickly when the user checks the account balance.
REQ-002: The system shall allow users to reset their password using their registered email.
REQ-003: Users must recover forgotten passwords using their registered email address.
REQ-004: The password must contain at least 8 characters.
REQ-005: The password must contain exactly 6 characters.
REQ-006: The system shall allow users to download their transaction history.
"""
    reqs = extract_requirements(doc)
    assert len(reqs) == 6
    assert all(r.source_layer == "layer_1_explicit_id" for r in reqs)
    assert all(r.confidence == 0.95 for r in reqs)
    assert reqs[0].req_id == "REQ-001"
    assert reqs[5].req_id == "REQ-006"
    assert "ONLINE BANKING SYSTEM" not in [r.text for r in reqs]


def test_bullet_list_in_functional_section():
    doc = """
# 2.0 Functional Requirements
Here are the core system capabilities:
- The system shall notify administrators upon failed authentication attempts.
- The platform must log all transaction attempts securely.
* Users should receive confirmation emails after registration.

# 3.0 Miscellaneous Notes
- Lunch schedule is 12pm.
"""
    reqs = extract_requirements(doc)
    assert len(reqs) >= 3
    # Items under Functional Requirements should be captured as structural cues
    structural_reqs = [r for r in reqs if r.source_layer == "layer_2_structural_cue"]
    assert len(structural_reqs) == 3
    assert all(r.confidence == 0.85 for r in structural_reqs)
    assert any("notify administrators" in r.text for r in structural_reqs)
    assert any("log all transaction" in r.text for r in structural_reqs)
    assert any("confirmation emails" in r.text for r in structural_reqs)
    # The note under miscellaneous should not be captured as a structural requirement
    assert not any("Lunch schedule" in r.text for r in reqs)


def test_prose_document_modal_verbs():
    doc = """
Project Overview
This document outlines the core architecture of the gateway.

The payment gateway shall validate all inbound API requests against signature keys.
Furthermore, the user must provide a one-time password before confirming wire transfers.
The service will archive completed transactions after 90 days.
General information about our company history and founders is available online.
"""
    reqs = extract_requirements(doc)
    assert len(reqs) == 3
    assert all(r.source_layer == "layer_3_modal_verb" for r in reqs)
    assert all(r.confidence == 0.70 for r in reqs)
    assert any("validate all inbound API requests" in r.text for r in reqs)
    assert any("provide a one-time password" in r.text for r in reqs)
    assert any("archive completed transactions" in r.text for r in reqs)
    # General descriptive prose should not be included
    assert not any("company history" in r.text for r in reqs)


def test_toc_and_captions_excluded():
    doc = """
Table of Contents
1. Introduction .................... 1
2. System Scope .................... 3
3. Functional Requirements ......... 5
4. Appendix ........................ 9

Figure 1: High level network architecture diagram.
Table 2: Database schema specifications.

Short.
Hi.

3. Functional Requirements
REQ-101: The system shall encrypt all data in transit using TLS 1.3.
"""
    reqs = extract_requirements(doc)
    # Only REQ-101 must be extracted
    assert len(reqs) == 1
    assert reqs[0].req_id == "REQ-101"
    assert "TLS 1.3" in reqs[0].text
    # Check that TOC lines, captions, and short sentences were excluded
    all_texts = [r.text for r in reqs]
    assert not any("Introduction" in t for t in all_texts)
    assert not any("Architecture diagram" in t for t in all_texts)
    assert not any("Short" in t for t in all_texts)


def test_fallback_layer():
    doc = """
System description notes.
The application provides user authentication capabilities.
The database stores customer profile settings securely.
"""
    reqs = extract_requirements(doc)
    assert len(reqs) > 0
    assert all(r.source_layer == "layer_4_fallback" for r in reqs)
    assert all(r.confidence == 0.40 for r in reqs)
