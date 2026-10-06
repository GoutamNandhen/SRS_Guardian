"""
SRS Guardian — Report Generation Service

Compiles document metadata, requirement classifications, deterministic quality scores,
detected issues, and human review decisions into exportable reports (HTML, CSV, PDF).
"""

from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from xhtml2pdf import pisa

from backend.app.models.document import Document, Requirement, Issue, Review
from backend.app.models.user_profile import UserProfile
from backend.app.nlp.ambiguity import analyze_ambiguity
from backend.app.nlp.readability import analyze_readability
from backend.app.nlp.scoring import score_document, score_requirement


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def build_report_data(document_id: int, db: Session) -> Dict[str, Any]:
    """
    Compiles complete document analysis and review status for report generation.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document with ID {document_id} not found")

    requirements: List[Requirement] = (
        db.query(Requirement)
        .filter(Requirement.document_id == document_id)
        .order_by(Requirement.id)
        .all()
    )

    all_issues: List[Issue] = (
        db.query(Issue)
        .join(Requirement)
        .filter(Requirement.document_id == document_id)
        .order_by(Issue.id)
        .all()
    )

    # Group issues by requirement ID
    issues_by_req: Dict[int, List[Issue]] = {}
    for issue in all_issues:
        issues_by_req.setdefault(issue.requirement_id, []).append(issue)

    # Aggregate document metrics
    functional_count = sum(
        1 for r in requirements if (r.classification_label or "").lower() == "functional"
    )
    non_functional_count = sum(
        1 for r in requirements if (r.classification_label or "").lower() == "non-functional"
    )

    # Quality scores: compute per-requirement scores and document summary
    scored_reqs = []
    for req in requirements:
        ambiguity_findings = analyze_ambiguity(req.text)
        readability_metrics = analyze_readability(req.text)

        req_issues = issues_by_req.get(req.id, [])
        dup_issue = next(
            (i for i in req_issues if i.type == "SEMANTIC_DUPLICATE"), None
        )
        is_dup = dup_issue is not None
        dup_info = None
        if dup_issue:
            try:
                dup_expl = json.loads(dup_issue.explanation_json)
                dup_info = {
                    "target_req_key": dup_expl.get("factors", {}).get("target_req_key"),
                    "similarity_score": dup_expl.get("factors", {}).get("similarity_score"),
                }
            except Exception:
                dup_info = None

        req_score = score_requirement(
            req_key=req.req_key,
            text=req.text,
            ambiguity_findings=ambiguity_findings,
            readability_metrics=readability_metrics,
            is_duplicate=is_dup,
            duplicate_info=dup_info,
            requirement_id=req.id,
        )
        scored_reqs.append(req_score)

    doc_summary_res = score_document(scored_reqs, document_id=doc.id)
    scores_by_req_id = {s.requirement_id: s for s in scored_reqs}

    # Count issues by severity, type, and status
    issues_by_type: Dict[str, int] = {}
    issues_by_severity: Dict[str, int] = {}
    issues_by_status: Dict[str, int] = {}
    reviewed_count = 0

    for issue in all_issues:
        issues_by_type[issue.type] = issues_by_type.get(issue.type, 0) + 1
        issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
        issues_by_status[issue.status] = issues_by_status.get(issue.status, 0) + 1
        if issue.status in ("accepted", "rejected", "reviewed", "edited"):
            reviewed_count += 1

    total_issues = len(all_issues)
    reviewed_pct = (
        round((reviewed_count / total_issues) * 100, 1) if total_issues > 0 else 100.0
    )

    # Format requirements list with their issues and scores
    formatted_requirements = []
    for req in requirements:
        req_score_obj = scores_by_req_id.get(req.id)
        quality_score = req_score_obj.overall_score if req_score_obj else 100.0
        sub_scores = (
            req_score_obj.sub_scores
            if req_score_obj and req_score_obj.sub_scores
            else {}
        )

        req_issues_list = []
        for issue in issues_by_req.get(req.id, []):
            try:
                expl_dict = json.loads(issue.explanation_json)
            except Exception:
                expl_dict = {
                    "human_explanation": issue.explanation_json,
                    "suggestion": "",
                }

            reviews_list = [
                {
                    "action": r.action,
                    "note": r.note or "",
                    "edited_text": r.edited_text or "",
                    "reviewed_at": r.reviewed_at.strftime("%Y-%m-%d %H:%M")
                    if r.reviewed_at
                    else "",
                }
                for r in issue.reviews
            ]

            req_issues_list.append(
                {
                    "id": issue.id,
                    "module": issue.module,
                    "type": issue.type,
                    "severity": issue.severity,
                    "status": issue.status,
                    "explanation": expl_dict,
                    "reviews": reviews_list,
                }
            )

        formatted_requirements.append(
            {
                "id": req.id,
                "req_key": req.req_key,
                "text": req.text,
                "classification_label": req.classification_label or "Unclassified",
                "classification_prob": req.classification_prob or 0.0,
                "quality_score": quality_score,
                "sub_scores": sub_scores,
                "issues": req_issues_list,
            }
        )

    summary = {
        "total_requirements": len(requirements),
        "functional_count": functional_count,
        "non_functional_count": non_functional_count,
        "mean_score": round(doc_summary_res.mean_score, 1) if doc_summary_res else 100.0,
        "median_score": round(doc_summary_res.median_score, 1) if doc_summary_res else 100.0,
        "min_score": round(doc_summary_res.min_score, 1) if doc_summary_res else 100.0,
        "max_score": round(doc_summary_res.max_score, 1) if doc_summary_res else 100.0,
        "score_distribution": (
            doc_summary_res.distribution
            if doc_summary_res
            else {"90-100": 0, "70-89": 0, "50-69": 0, "<50": 0}
        ),
        "worst_requirements": (
            doc_summary_res.worst_requirements if doc_summary_res else []
        ),
        "total_issues": total_issues,
        "reviewed_count": reviewed_count,
        "reviewed_percentage": reviewed_pct,
        "issues_by_type": issues_by_type,
        "issues_by_severity": issues_by_severity,

        "issues_by_status": issues_by_status,
    }

    user_prof = db.query(UserProfile).order_by(UserProfile.id.asc()).first()
    reviewer_profile = {
        "full_name": user_prof.full_name if (user_prof and user_prof.full_name) else "Not provided",
        "email": user_prof.email if (user_prof and user_prof.email) else "Not provided",
        "organization": user_prof.organization if (user_prof and user_prof.organization) else "Not provided",
        "role": user_prof.role if (user_prof and user_prof.role) else "Not provided",
        "phone": user_prof.phone if (user_prof and user_prof.phone) else "Not provided",
    }

    return {
        "document": {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            if doc.uploaded_at
            else "",
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "reviewer_profile": reviewer_profile,
        "summary": summary,
        "requirements": formatted_requirements,
        "raw_issues": all_issues,
    }


def generate_html_report(document_id: int, db: Session) -> str:
    """
    Renders the HTML report using Jinja2.
    """
    data = build_report_data(document_id, db)
    template = jinja_env.get_template("report.html")
    return template.render(**data)


def generate_csv_report(
    document_id: int, db: Session, csv_type: str = "requirements"
) -> str:
    """
    Generates CSV export.
    Supports:
      - csv_type == 'requirements': One row per requirement with score and summary.
      - csv_type == 'issues': One row per flagged issue with rule explanation and human review decision.
    """
    data = build_report_data(document_id, db)
    output = io.StringIO()
    writer = csv.writer(output)

    if csv_type.lower() == "issues":
        # One row per issue
        writer.writerow(
            [
                "issue_id",
                "req_key",
                "module",
                "rule_type",
                "severity",
                "status",
                "explanation",
                "suggestion",
                "reviewer_action",
                "reviewer_note",
                "requirement_text",
            ]
        )
        for req in data["requirements"]:
            for issue in req["issues"]:
                rev_action = (
                    issue["reviews"][0]["action"] if issue["reviews"] else ""
                )
                rev_note = issue["reviews"][0]["note"] if issue["reviews"] else ""
                writer.writerow(
                    [
                        issue["id"],
                        req["req_key"],
                        issue["module"],
                        issue["type"],
                        issue["severity"],
                        issue["status"],
                        issue["explanation"].get("human_explanation", ""),
                        issue["explanation"].get("suggestion", ""),
                        rev_action,
                        rev_note,
                        req["text"],
                    ]
                )
    else:
        # Default: one row per requirement
        writer.writerow(
            [
                "req_id",
                "req_key",
                "classification",
                "confidence",
                "quality_score",
                "clarity",
                "ambiguity",
                "testability",
                "readability",
                "structure",
                "consistency",
                "issues_count",
                "text",
            ]
        )
        for req in data["requirements"]:
            sub = req.get("sub_scores", {})
            writer.writerow(
                [
                    req["id"],
                    req["req_key"],
                    req["classification_label"],
                    f"{req['classification_prob']:.4f}",
                    req["quality_score"],
                    sub.get("clarity", 100.0),
                    sub.get("ambiguity", 100.0),
                    sub.get("testability", 100.0),
                    sub.get("readability", 100.0),
                    sub.get("structure", 100.0),
                    sub.get("consistency", 100.0),
                    len(req["issues"]),
                    req["text"],
                ]
            )

    return output.getvalue()


def generate_pdf_report(document_id: int, db: Session) -> bytes:
    """
    Renders HTML report and converts to PDF using xhtml2pdf.
    """
    html_content = generate_html_report(document_id, db)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=io.BytesIO(html_content.encode("utf-8")),
        dest=pdf_buffer,
        encoding="utf-8",
    )
    if pisa_status.err:
        raise RuntimeError("PDF generation failed in xhtml2pdf engine")

    return pdf_buffer.getvalue()
