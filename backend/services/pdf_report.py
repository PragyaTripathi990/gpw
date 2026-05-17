"""
PDF Report Generator for LexGuard
Generates a professional downloadable risk report.
"""
import io
from html import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from backend.services.analysis_enrichment import enrich_analysis


def _cell_text(value: object) -> str:
    """Normalize table cell values to plain strings."""
    return "" if value is None else str(value)


def _paragraph_text(value: object) -> str:
    """Escape dynamic text so ReportLab markup stays valid."""
    return escape(_cell_text(value), quote=False).replace("\n", "<br/>")


def generate_pdf_report(analysis: dict) -> bytes:
    """Generate a PDF report from analysis results."""
    analysis = enrich_analysis(analysis)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=HexColor('#6B21A8'))
    heading_style = ParagraphStyle('H2', parent=styles['Heading2'], textColor=HexColor('#1E1E1E'))
    body_style = styles['BodyText']
    risk_style = ParagraphStyle('Risk', parent=styles['BodyText'], textColor=HexColor('#DC2626'), fontSize=11)
    safe_style = ParagraphStyle('Safe', parent=styles['BodyText'], textColor=HexColor('#16A34A'), fontSize=11)

    elements = []

    # Title
    elements.append(Paragraph("LEXGUARD Contract Risk Report", title_style))
    elements.append(Spacer(1, 12))

    # Summary table
    grade = analysis.get("risk_grade", "?")
    score = analysis.get("overall_risk_score", 0)
    rec = analysis.get("recommendation", "")
    summary_data = [
        ["Document Type", _cell_text(analysis.get("document_type", "Unknown"))],
        ["Total Clauses", str(analysis.get("total_clauses", 0))],
        ["Overall Risk Score", f"{score}/10"],
        ["Risk Grade", _cell_text(grade)],
        ["Recommendation", _cell_text(rec)],
        ["Critical Issues", str(analysis.get("critical_issues", 0))],
        ["Warnings", str(analysis.get("warnings_count", 0))],
        ["Safe Clauses", str(analysis.get("safe_count", 0))],
    ]
    t = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#F3F4F6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#D1D5DB')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    summary_text = _cell_text(analysis.get("executive_summary", "No summary available."))
    # Truncate very long summaries
    if len(summary_text) > 2000:
        summary_text = summary_text[:2000] + "..."
    elements.append(Paragraph(_paragraph_text(summary_text), body_style))
    elements.append(Spacer(1, 20))

    # Risk Summary
    risk_summary = analysis.get("risk_summary", {})
    top_red_flags = analysis.get("top_red_flags", [])
    if risk_summary:
        elements.append(Paragraph("Risk Snapshot", heading_style))
        elements.append(Paragraph(_paragraph_text(risk_summary.get("headline", "")), body_style))
        elements.append(Spacer(1, 8))
        dominant_themes = risk_summary.get("dominant_themes", [])
        if dominant_themes:
            theme_text = ", ".join(dominant_themes)
            elements.append(Paragraph(_paragraph_text(f"Dominant themes: {theme_text}"), body_style))
            elements.append(Spacer(1, 12))

    if top_red_flags:
        elements.append(Paragraph("Top Red Flags", heading_style))
        elements.append(Spacer(1, 10))
        for flag in top_red_flags[:5]:
            title = (
                f"{flag.get('severity', 'HIGH')} — {flag.get('label', 'Contract Risk')}"
                f" (Clause {flag.get('clause_number', '?')}: {flag.get('clause_title', 'Unknown')})"
            )
            elements.append(Paragraph(f"<b>{_paragraph_text(title)}</b>", risk_style))
            elements.append(Paragraph(_paragraph_text(flag.get("why_it_matters", "")), body_style))
            elements.append(Spacer(1, 10))
        elements.append(Spacer(1, 8))

    # Clause Analysis
    elements.append(Paragraph("Clause-by-Clause Analysis", heading_style))
    elements.append(Spacer(1, 10))

    clause_results = analysis.get("clause_results", [])
    if not clause_results:
        elements.append(Paragraph("No clause-level findings were available for this analysis.", body_style))
        elements.append(Spacer(1, 12))

    for cr in clause_results:
        clause = cr.get("clause", {})
        verdict = cr.get("verdict", {})
        rs = verdict.get("risk_score", 5) if isinstance(verdict, dict) else 5
        style_to_use = risk_style if rs >= 5 else safe_style

        title = f"{clause.get('clause_number', '?')}. {clause.get('title', 'Unknown')} — Risk: {rs}/10"
        elements.append(Paragraph(f"<b>{_paragraph_text(title)}</b>", style_to_use))
        
        plain = verdict.get("plain_english", "") if isinstance(verdict, dict) else ""
        if plain:
            elements.append(Paragraph(_paragraph_text(plain), body_style))
        
        fix = verdict.get("suggested_fix", "") if isinstance(verdict, dict) else ""
        if fix and fix != "N/A":
            elements.append(
                Paragraph(f"<i>Suggested fix: {_paragraph_text(fix)}</i>", body_style)
            )
        
        elements.append(Spacer(1, 12))

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Generated by LexGuard — AI Contract Intelligence System", 
                               ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=HexColor('#9CA3AF'))))

    doc.build(elements)
    return buffer.getvalue()
