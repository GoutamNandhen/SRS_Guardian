"""
SRS Guardian — Review Reports API Router (Phase 18).

Provides dedicated endpoints for Explainable Visual Review data and Comprehensive Exports:
- GET /api/documents/{id}/review-report
- GET /api/documents/{id}/review-report/annotated-pdf
- GET /api/documents/{id}/review-report/pdf
- GET /api/documents/{id}/review-report/docx
"""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import Document
from backend.app.schemas.review_report import DocumentReviewReportResponse
from backend.app.services.review_report import (
    build_review_report_data,
    generate_annotated_srs_pdf,
    generate_comprehensive_pdf_report,
    generate_comprehensive_docx_report,
)

router = APIRouter(prefix="/documents", tags=["review-reports"])


def _validate_analyzed_doc(document_id: int, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    if not doc.requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document with ID {document_id} has not been analyzed yet. Run analysis first.",
        )
    return doc


@router.get(
    "/{document_id}/review-report",
    response_model=DocumentReviewReportResponse,
    summary="Get explainable visual review report data with finding location spans and confidence",
)
def get_review_report_data_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
):
    _validate_analyzed_doc(document_id, db)
    try:
        report_dict = build_review_report_data(document_id, db)
        return DocumentReviewReportResponse(
            document_id=report_dict["document"]["id"],
            filename=report_dict["document"]["filename"],
            file_type=report_dict["document"]["file_type"],
            page_count=report_dict["document"]["page_count"],
            uploaded_at=report_dict["document"]["uploaded_at"],
            status=report_dict["document"]["status"],
            cleaned_text=report_dict["document"]["cleaned_text"],
            raw_text=report_dict["document"].get("raw_text"),
            total_requirements=report_dict["total_requirements"],
            total_findings=report_dict["total_findings"],
            overall_status=report_dict.get("overall_status", "ACCEPTABLE"),
            quality_summary=report_dict["quality_summary"],
            findings_by_severity=report_dict["findings_by_severity"],
            findings_by_module=report_dict["findings_by_module"],
            findings_by_confidence=report_dict["findings_by_confidence"],
            executive_summary_table=report_dict.get("executive_summary_table", []),
            requirements=report_dict["requirements"],
            all_findings=report_dict["all_findings"],
            system_evaluation=report_dict.get("system_eval"),
            shap_attributions=report_dict.get("shap_attributions"),
            dynamic_conclusion=report_dict.get("dynamic_conclusion"),
        )
    except Exception as e:
        logger.error(f"Error compiling review report for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate review report: {str(e)}",
        )


@router.get(
    "/{document_id}/review-report/annotated-pdf",
    summary="Export Annotated SRS PDF with visual highlights and audit legend",
)
def get_annotated_srs_pdf_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
):
    doc = _validate_analyzed_doc(document_id, db)
    clean_stem = Path(doc.filename).stem
    try:
        pdf_bytes = generate_annotated_srs_pdf(document_id, db)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_stem}_annotated_srs.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"Error generating annotated PDF for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate annotated PDF: {str(e)}",
        )


@router.get(
    "/{document_id}/review-report/pdf",
    summary="Export Comprehensive 19-Section Analysis Report in PDF format",
)
def get_comprehensive_pdf_report_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
):
    doc = _validate_analyzed_doc(document_id, db)
    clean_stem = Path(doc.filename).stem
    try:
        pdf_bytes = generate_comprehensive_pdf_report(document_id, db)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_stem}_comprehensive_report.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"Error generating comprehensive PDF report for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate comprehensive PDF report: {str(e)}",
        )


@router.get(
    "/{document_id}/review-report/docx",
    summary="Export Comprehensive 19-Section Analysis Report in Microsoft Word (.docx) format",
)
def get_comprehensive_docx_report_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
):
    doc = _validate_analyzed_doc(document_id, db)
    clean_stem = Path(doc.filename).stem
    try:
        docx_bytes = generate_comprehensive_docx_report(document_id, db)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_stem}_comprehensive_report.docx"'
            },
        )
    except Exception as e:
        logger.error(f"Error generating DOCX report for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate DOCX report: {str(e)}",
        )
