"""Software Requirements Specification (SRS) as a PDF document, built with ReportLab."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .models import CATEGORY_CHOICES, FUNCTIONAL, NON_FUNCTIONAL

NAVY = colors.HexColor("#111a2c")
ACCENT = colors.HexColor("#2f6bd8")
MUTED = colors.HexColor("#667085")
BORDER = colors.HexColor("#d9dee6")
SOFT = colors.HexColor("#f4f6f9")
PRIORITY_COLORS = {"high": colors.HexColor("#c4372f"), "medium": colors.HexColor("#b7791f"),
                   "low": colors.HexColor("#12805c")}

base = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=30,
                            textColor=NAVY, alignment=TA_LEFT, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=11, textColor=MUTED, spaceAfter=16),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=15,
                         textColor=NAVY, spaceBefore=14, spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                         textColor=ACCENT, spaceBefore=10, spaceAfter=6),
    "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13.5),
    "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8.5, leading=11.5, textColor=MUTED),
    "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=9, leading=12.5),
    "label": ParagraphStyle("label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8,
                            leading=11, textColor=MUTED),
    "req": ParagraphStyle("req", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
                          leading=14, textColor=NAVY),
}


def _p(text, style="body"):
    return Paragraph(escape(text or "").replace("\n", "<br/>"), STYLES[style])


def _requirement_block(r):
    color = PRIORITY_COLORS.get(r["priority"], MUTED).hexval()[2:]
    header = Paragraph(f'{escape(r["code"])} &nbsp; {escape(r["title"])} &nbsp; '
                       f'<font size="8" color="#{color}">[{r["priority_display"].upper()}]</font>', STYLES["req"])
    rows = [[_p("Description", "label"), _p(r["description"], "cell")]]
    if r["req_type"] == FUNCTIONAL:
        if r["actor"]:
            rows.append([_p("Actor", "label"), _p(r["actor"], "cell")])
        if r["module"]:
            rows.append([_p("Module", "label"), _p(r["module"], "cell")])
    else:
        rows.append([_p("Category", "label"), _p(r["category_display"], "cell")])
    if r["criteria_list"]:
        rows.append([_p("Acceptance criteria", "label"),
                     Paragraph("<br/>".join(f"• {escape(c)}" for c in r["criteria_list"]), STYLES["cell"])])
    if r["needs_confirmation"]:
        rows.append([_p("Status", "label"), _p("Proposed target – to be confirmed by the stakeholders", "cell")])
    table = Table(rows, colWidths=[34 * mm, None])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return KeepTogether([header, Spacer(0, 3), table, Spacer(0, 10)])


def build_srs_pdf(project, requirements):
    buffer = BytesIO()
    generated_on = timezone.localtime().strftime("%d/%m/%Y %H:%M")

    def decorate(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BORDER)
        canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 11 * mm, f"Software Requirements Specification — {project.title}"[:110])
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.drawString(18 * mm, 10 * mm, f"Generated with Smart UML on {generated_on}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=20 * mm, bottomMargin=18 * mm,
                            title=f"SRS - {project.title}", author="Smart UML")
    functional = [r for r in requirements if r["req_type"] == FUNCTIONAL]
    non_functional = [r for r in requirements if r["req_type"] == NON_FUNCTIONAL]

    story = [
        _p("Software Requirements Specification", "subtitle"),
        Paragraph(escape(project.title), STYLES["title"]),
        _p(f"Version of {generated_on}", "small"),
        Spacer(0, 10),
        _p("1. Project description", "h1"),
        _p(project.description or "No description provided."),
    ]

    summary = [["", "Total", "High", "Medium", "Low"]]
    for label, items in (("Functional requirements", functional), ("Non-functional requirements", non_functional)):
        summary.append([label, len(items)] + [sum(1 for r in items if r["priority"] == p) for p in ("high", "medium", "low")])
    table = Table(summary, colWidths=[70 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [_p("2. Summary", "h1"), table]

    story.append(_p("3. Functional requirements", "h1"))
    story += [_requirement_block(r) for r in functional] or [_p("No functional requirement yet.", "small")]

    story.append(_p("4. Non-functional requirements", "h1"))
    if not non_functional:
        story.append(_p("No non-functional requirement yet.", "small"))
    for category, label in CATEGORY_CHOICES:
        items = [r for r in non_functional if r["category"] == category]
        if items:
            story.append(_p(label, "h2"))
            story += [_requirement_block(r) for r in items]

    if any(r["needs_confirmation"] for r in non_functional):
        story += [Spacer(0, 6), _p("Requirements marked “Proposed target – to be confirmed” contain values suggested "
                                   "during the analysis; they must be validated by the stakeholders.", "small")]

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
