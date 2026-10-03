"""PDF net sheets.

client view: clean, seller-facing. Estimates are marked "EST.", disclaimer always included.
agent view:  everything in the client view plus the math, sources, warnings and assumptions.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import models
from .calculations.net_proceeds import NetSheet
from .money import fmt

INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5f6b7a")
RULE = colors.HexColor("#d5dae1")
ACCENT = colors.HexColor("#1d4e89")
EST_BG = colors.HexColor("#fff6db")
NET_BG = colors.HexColor("#eaf1fa")

CLIENT_DISCLAIMER = (
    "This is an ESTIMATE prepared for discussion purposes only. It is not a settlement statement, "
    "closing disclosure, or guarantee of proceeds. Actual payoffs, taxes, prorations, fees, and "
    "credits will be determined at closing and may differ from the figures shown. Items marked "
    "EST. are estimates; items marked ACTUAL are based on figures provided as of the date shown."
)
LISTING_NOTE = (
    "No purchase agreement exists yet. The sale price shown is hypothetical and used only to "
    "illustrate potential proceeds."
)


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=INK)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=10.5, textColor=MUTED),
        "title": ParagraphStyle("title", parent=base, fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=ACCENT),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3, textColor=ACCENT),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "bold": ParagraphStyle("bold", parent=base, fontName="Helvetica-Bold"),
        "boldright": ParagraphStyle("boldright", parent=base, fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "netlabel": ParagraphStyle("netlabel", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=16),
        "netvalue": ParagraphStyle("netvalue", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_RIGHT, textColor=ACCENT),
        "est": ParagraphStyle("est", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10.5, textColor=colors.HexColor("#8a4b00")),
        "act": ParagraphStyle("act", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10.5, textColor=colors.HexColor("#1e6b3a")),
        "warn": ParagraphStyle("warn", parent=base, fontSize=8.5, leading=11, textColor=colors.HexColor("#8a4b00")),
    }


def _esc(text) -> str:
    return (str(text or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fact(sheet: NetSheet, key: str) -> str:
    return (sheet.facts.get(key) or {}).get("value") or ""


def _fmt_date(text: str) -> str:
    try:
        d = models.parse_date(text)
    except ValueError:
        return text
    return d.strftime("%B %-d, %Y") if d else ""


def build_pdf(sheet: NetSheet, view: str = "client", generated: datetime | None = None) -> bytes:
    generated = generated or datetime.now()
    st = _styles()
    agent = view == "agent"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.8 * inch,
        title="Estimated Seller Net Sheet", author="Seller Net Sheet",
    )
    width = doc.width
    story = []

    title = "Estimated Seller Net Sheet"
    if agent:
        title += " — Agent Worksheet"
    story.append(Paragraph(title, st["title"]))
    story.append(Paragraph(
        f"Prepared {generated.strftime('%B %-d, %Y at %-I:%M %p')}"
        + (" · Listing estimate (no contract)" if sheet.mode == "listing" else ""), st["small"]))
    story.append(Spacer(1, 10))

    # Transaction information
    price_label = "Hypothetical sale price" if sheet.mode == "listing" else "Purchase price"
    info_rows = [
        ["Property", _esc(_fact(sheet, "property_address")) or "—"],
        ["Seller(s)", _esc(_fact(sheet, "sellers")) or "—"],
        [price_label, fmt(sheet.price)],
        ["Closing date", _fmt_date(_fact(sheet, "closing_date")) or "Not yet set"],
    ]
    poss = _fact(sheet, "possession_date")
    if poss and poss != _fact(sheet, "closing_date"):
        info_rows.append(["Possession date", _fmt_date(poss)])
    t = Table([[Paragraph(a, st["bold"]), Paragraph(b, st["base"])] for a, b in info_rows],
              colWidths=[1.6 * inch, width - 1.6 * inch])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    if sheet.mode == "listing":
        story.append(Spacer(1, 4))
        story.append(Paragraph(LISTING_NOTE, st["small"]))
    story.append(Spacer(1, 6))

    # Line items by section
    col = [width - 2.55 * inch, 0.8 * inch, 1.75 * inch]
    for key, name, lines in sheet.sections:
        rows = []
        styles = [
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for ln in lines:
            label = _esc(ln.label)
            if ln.provider:
                label += f' <font color="#5f6b7a" size="8">— {_esc(ln.provider)}</font>'
            if agent:
                details = [f"Source: {_esc(ln.source)}"] + [_esc(s) for s in ln.steps]
                details += [f'<font color="#8a4b00">{_esc(f)}</font>' for f in ln.flags]
                if ln.notes:
                    details.append(f"Note: {_esc(ln.notes)}")
                label += '<br/><font size="7.5" color="#5f6b7a">' + "<br/>".join(details) + "</font>"
            if ln.amount is None:
                marker, amount = "", "Not entered"
            else:
                marker = "EST." if ln.is_estimated else "ACTUAL"
                sign = "+ " if ln.kind == "credit" else "− "
                amount = sign + fmt(ln.amount)
            marker_style = st["est"] if marker == "EST." else st["act"]
            rows.append([Paragraph(label, st["base"]), Paragraph(marker, marker_style), Paragraph(amount, st["right"])])
            if ln.amount is not None and ln.is_estimated:
                styles.append(("BACKGROUND", (1, len(rows) - 1), (1, len(rows) - 1), EST_BG))
        table = Table(rows, colWidths=col)
        table.setStyle(TableStyle(styles))
        story.append(KeepTogether([Paragraph(name, st["h2"]), table]))

    # Summary
    story.append(Spacer(1, 12))
    summary = [
        [Paragraph(price_label, st["base"]), Paragraph(fmt(sheet.price), st["right"])],
        [Paragraph("Less seller expenses", st["base"]), Paragraph("− " + fmt(sheet.total_debits), st["right"])],
        [Paragraph("Less mortgage / lien payoffs", st["base"]), Paragraph("− " + fmt(sheet.total_payoffs), st["right"])],
        [Paragraph("Plus credits to seller", st["base"]), Paragraph("+ " + fmt(sheet.total_credits), st["right"])],
        [Paragraph("ESTIMATED NET PROCEEDS TO SELLER", st["netlabel"]), Paragraph(fmt(sheet.net, "—"), st["netvalue"])],
    ]
    s = Table(summary, colWidths=[width - 2.2 * inch, 2.2 * inch])
    s.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("BACKGROUND", (0, -1), (-1, -1), NET_BG),
        ("BOX", (0, -1), (-1, -1), 1.2, ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, -1), (-1, -1), 10), ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
    ]))
    story.append(KeepTogether([s]))

    if agent:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Review items, warnings & assumptions", st["h2"]))
        story.append(Paragraph(_esc(sheet.tax_pending_message), st["warn"]))
        for w in sheet.warnings:
            story.append(Paragraph("• " + _esc(w), st["warn"]))
        for i in sheet.info:
            story.append(Paragraph("• " + _esc(i), st["small"]))
        story.append(Paragraph(
            "• All figures use exact decimal arithmetic; each line is rounded to the cent (half up). "
            "Blank amounts are left out of totals, never estimated by the app.", st["small"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph(CLIENT_DISCLAIMER, st["small"]))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 0.45 * inch, f"Estimate only — not a settlement statement. Prepared {generated:%m/%d/%Y}.")
        canvas.drawRightString(letter[0] - doc.rightMargin, 0.45 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
