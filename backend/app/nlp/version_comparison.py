"""SRS Guardian - Version Comparison & Semantic Diffing Engine.

Phase 15C: Tier 3.
Compares two versions of an SRS document:
1. Aligns requirements across versions using composite matching (exact ID + embedding similarity).
2. Classifies each requirement as added, removed, modified, or unchanged.
3. Computes text diffs, quality score deltas (Score_v2 - Score_v1), and issue lifecycles (resolved vs newly introduced issues).
"""

import difflib
from typing import Any
import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.document import Document, Requirement
from backend.app.ml.embeddings import encode
from backend.app.nlp.scoring import score_requirement
from backend.app.nlp.ambiguity import analyze_ambiguity


def compute_text_diff(text1: str, text2: str) -> str:
    """Produces a clean unified inline difference between two requirement texts."""
    words1 = text1.split()
    words2 = text2.split()
    matcher = difflib.SequenceMatcher(None, words1, words2)
    diff_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            diff_parts.append(" ".join(words1[i1:i2]))
        elif tag == "delete":
            diff_parts.append(f"[-{' '.join(words1[i1:i2])}-]")
        elif tag == "insert":
            diff_parts.append(f"[+{' '.join(words2[j1:j2])}+]")
        elif tag == "replace":
            diff_parts.append(f"[-{' '.join(words1[i1:i2])}-] [+{' '.join(words2[j1:j2])}+]")
    return " ".join(diff_parts)


def compare_document_versions(
    doc1_id: int,
    doc2_id: int,
    db: Session,
    similarity_threshold: float = 0.70,
) -> dict[str, Any]:
    """Compares two SRS documents or document versions."""
    doc1 = db.query(Document).filter(Document.id == doc1_id).first()
    doc2 = db.query(Document).filter(Document.id == doc2_id).first()

    if not doc1:
        raise ValueError(f"Document {doc1_id} not found")
    if not doc2:
        raise ValueError(f"Document {doc2_id} not found")

    reqs1 = db.query(Requirement).filter(Requirement.document_id == doc1_id).all()
    reqs2 = db.query(Requirement).filter(Requirement.document_id == doc2_id).all()

    # Pre-score requirements if not already scored
    def get_req_score(req: Requirement) -> float:
        findings = analyze_ambiguity(req.text)
        res = score_requirement(
            req_key=req.req_key or "REQ",
            text=req.text,
            ambiguity_findings=findings,
        )
        return round(res.overall_score, 1)

    scores1 = {r.id: get_req_score(r) for r in reqs1}
    scores2 = {r.id: get_req_score(r) for r in reqs2}

    def get_req_issues(req: Requirement) -> list[dict[str, str]]:
        res = []
        for issue in req.issues:
            if issue.status != "rejected":
                rule_id = issue.type or getattr(issue, "rule_id", "ISSUE")
                human_exp = ""
                if issue.explanation_json:
                    try:
                        import json
                        exp_data = json.loads(issue.explanation_json) if isinstance(issue.explanation_json, str) else issue.explanation_json
                        human_exp = exp_data.get("human_explanation", "")
                    except Exception:
                        human_exp = f"Defect detected by {rule_id}"
                res.append({
                    "rule_id": rule_id,
                    "severity": issue.severity,
                    "human_explanation": human_exp or f"Defect ({rule_id})",
                })
        return res

    issues1 = {r.id: get_req_issues(r) for r in reqs1}
    issues2 = {r.id: get_req_issues(r) for r in reqs2}

    # Step 1: Exact req_key matching
    matched_pairs: list[tuple[Requirement, Requirement, float]] = []
    unmatched_1: list[Requirement] = []
    unmatched_2: list[Requirement] = list(reqs2)

    reqs2_by_key = {r.req_key.strip().upper(): r for r in reqs2 if r.req_key}

    for r1 in reqs1:
        key1 = (r1.req_key or "").strip().upper()
        if key1 and key1 in reqs2_by_key:
            target_r2 = reqs2_by_key[key1]
            if target_r2 in unmatched_2:
                # Text similarity
                emb1 = encode([r1.text])[0]
                emb2 = encode([target_r2.text])[0]
                sim = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-9))
                matched_pairs.append((r1, target_r2, round(sim, 3)))
                unmatched_2.remove(target_r2)
                continue
        unmatched_1.append(r1)

    # Step 2: Semantic embedding matching for remaining unmatched requirements
    if unmatched_1 and unmatched_2:
        texts1 = [r.text for r in unmatched_1]
        texts2 = [r.text for r in unmatched_2]
        embs1 = encode(texts1)
        embs2 = encode(texts2)

        # Compute cosine similarity matrix
        sim_matrix = np.dot(embs1, embs2.T) / (
            np.linalg.norm(embs1, axis=1, keepdims=True) * np.linalg.norm(embs2, axis=1, keepdims=True).T + 1e-9
        )

        still_unmatched_1 = []
        for i, r1 in enumerate(unmatched_1):
            best_j = int(np.argmax(sim_matrix[i]))
            best_sim = float(sim_matrix[i, best_j])
            if best_sim >= similarity_threshold and unmatched_2[best_j] in unmatched_2:
                matched_r2 = unmatched_2[best_j]
                matched_pairs.append((r1, matched_r2, round(best_sim, 3)))
                # Prevent reuse
                sim_matrix[:, best_j] = -1.0
            else:
                still_unmatched_1.append(r1)
        unmatched_1 = still_unmatched_1
        # Filter unmatched_2 by removing those in matched_pairs
        matched_r2_ids = {p[1].id for p in matched_pairs}
        unmatched_2 = [r for r in reqs2 if r.id not in matched_r2_ids]

    # Step 3: Classify items
    comparison_items: list[dict[str, Any]] = []
    total_resolved = 0
    total_new = 0

    # Process Matched Pairs (Unchanged or Modified)
    for r1, r2, sim in matched_pairs:
        s1 = scores1.get(r1.id, 100.0)
        s2 = scores2.get(r2.id, 100.0)
        delta = round(s2 - s1, 1)

        iss1 = issues1.get(r1.id, [])
        iss2 = issues2.get(r2.id, [])
        iss1_rules = {i["rule_id"] for i in iss1}
        iss2_rules = {i["rule_id"] for i in iss2}

        resolved = [i for i in iss1 if i["rule_id"] not in iss2_rules]
        new_issues = [i for i in iss2 if i["rule_id"] not in iss1_rules]
        persistent = [i for i in iss2 if i["rule_id"] in iss1_rules]

        total_resolved += len(resolved)
        total_new += len(new_issues)

        is_identical = r1.text.strip() == r2.text.strip()
        status_label = "unchanged" if is_identical else "modified"
        diff_str = None if is_identical else compute_text_diff(r1.text, r2.text)

        comparison_items.append({
            "status": status_label,
            "req_key": r2.req_key or r1.req_key or "REQ",
            "text_v1": r1.text,
            "text_v2": r2.text,
            "score_v1": s1,
            "score_v2": s2,
            "score_delta": delta,
            "similarity": sim,
            "diff_text": diff_str,
            "resolved_issues": resolved,
            "new_issues": new_issues,
            "persistent_issues": persistent,
        })

    # Process Removed Requirements (present in doc1 only)
    for r1 in unmatched_1:
        s1 = scores1.get(r1.id, 100.0)
        iss1 = issues1.get(r1.id, [])
        total_resolved += len(iss1)
        comparison_items.append({
            "status": "removed",
            "req_key": r1.req_key or "REQ",
            "text_v1": r1.text,
            "text_v2": None,
            "score_v1": s1,
            "score_v2": None,
            "score_delta": None,
            "similarity": 0.0,
            "diff_text": f"[-{r1.text}-]",
            "resolved_issues": iss1,
            "new_issues": [],
            "persistent_issues": [],
        })

    # Process Added Requirements (present in doc2 only)
    for r2 in unmatched_2:
        s2 = scores2.get(r2.id, 100.0)
        iss2 = issues2.get(r2.id, [])
        total_new += len(iss2)
        comparison_items.append({
            "status": "added",
            "req_key": r2.req_key or "REQ",
            "text_v1": None,
            "text_v2": r2.text,
            "score_v1": None,
            "score_v2": s2,
            "score_delta": None,
            "similarity": 0.0,
            "diff_text": f"[+{r2.text}+]",
            "resolved_issues": [],
            "new_issues": iss2,
            "persistent_issues": [],
        })

    # Sort items: modified first, then added, then removed, then unchanged
    status_order = {"modified": 0, "added": 1, "removed": 2, "unchanged": 3}
    comparison_items.sort(key=lambda x: (status_order.get(x["status"], 4), x["req_key"]))

    # Summary metrics
    added_count = sum(1 for x in comparison_items if x["status"] == "added")
    removed_count = sum(1 for x in comparison_items if x["status"] == "removed")
    modified_count = sum(1 for x in comparison_items if x["status"] == "modified")
    unchanged_count = sum(1 for x in comparison_items if x["status"] == "unchanged")

    avg_v1 = round(float(np.mean(list(scores1.values()))), 1) if scores1 else 100.0
    avg_v2 = round(float(np.mean(list(scores2.values()))), 1) if scores2 else 100.0
    overall_delta = round(avg_v2 - avg_v1, 1)

    return {
        "doc1_id": doc1_id,
        "doc1_filename": doc1.filename,
        "doc2_id": doc2_id,
        "doc2_filename": doc2.filename,
        "total_v1": len(reqs1),
        "total_v2": len(reqs2),
        "added_count": added_count,
        "removed_count": removed_count,
        "modified_count": modified_count,
        "unchanged_count": unchanged_count,
        "avg_score_v1": avg_v1,
        "avg_score_v2": avg_v2,
        "score_delta": overall_delta,
        "total_resolved_issues": total_resolved,
        "total_new_issues": total_new,
        "items": comparison_items,
    }
