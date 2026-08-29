"""Server-side branded PDF decision report (reportlab)."""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

NAVY = colors.HexColor("#1A365D")
STAMP = colors.HexColor("#C05621")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")
PASS = colors.HexColor("#1E4620")
FAIL = colors.HexColor("#A50E0E")
REVIEW = colors.HexColor("#8B5A00")

STAMP_COLOR = {"BID": PASS, "BID WITH CONDITIONS": STAMP, "NO-BID": FAIL}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("BPTitle", fontName="Times-Bold", fontSize=22, textColor=NAVY, spaceAfter=2))
    ss.add(ParagraphStyle("BPMeta", fontName="Courier", fontSize=8.5, textColor=MUTED, spaceAfter=1))
    ss.add(ParagraphStyle("BPH", fontName="Times-Bold", fontSize=13, textColor=NAVY, spaceBefore=12, spaceAfter=4))
    ss.add(ParagraphStyle("BPBody", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13))
    ss.add(ParagraphStyle("BPItem", fontName="Helvetica", fontSize=9, textColor=INK, leading=12, leftIndent=8))
    ss.add(ParagraphStyle("BPDisc", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED, leading=11, spaceBefore=10))
    return ss


def build_report(analysis, decision, requirements, risks, actions):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm, title="BidPilot Analysis Report")
    S = _styles()
    E = []

    E.append(Paragraph("BidPilot &mdash; Pre-Bid Analysis", S["BPTitle"]))
    E.append(Paragraph("Know before you bid &middot; Decision support (not legal advice)", S["BPMeta"]))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    E.append(Spacer(1, 8))

    E.append(Paragraph(analysis.get("tender_name", ""), S["BPH"]))
    E.append(Paragraph(f"Company: {analysis.get('company_name', '')}", S["BPBody"]))
    d = decision or {}
    date = (analysis.get("created_at") or "")[:10]
    E.append(Paragraph(f"Analysis date: {date}", S["BPMeta"]))
    E.append(Spacer(1, 10))

    # Decision stamp box
    outcome = d.get("outcome", "—")
    stamp_c = STAMP_COLOR.get(outcome, STAMP)
    stamp_tbl = Table([[Paragraph(f"<b>{outcome}</b>", ParagraphStyle("st", fontName="Times-Bold", fontSize=16, textColor=stamp_c, alignment=1))]], colWidths=[110 * mm])
    stamp_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, stamp_c), ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    E.append(stamp_tbl)
    E.append(Spacer(1, 8))

    # Scores
    score_data = [
        ["Readiness", "Eligibility", "Compliance", "Technical", "Risk"],
        [f"{d.get('readiness_score','—')}%", f"{d.get('eligibility','—')}%", f"{d.get('compliance','—')}%",
         f"{d.get('technical','—')}%", f"{d.get('risk','—')}%"],
    ]
    st = Table(score_data, colWidths=[34 * mm] * 5)
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, 1), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
    ]))
    E.append(st)
    E.append(Spacer(1, 6))
    E.append(Paragraph("<b>Recommendation:</b> " + (d.get("recommendation", "") or ""), S["BPBody"]))

    def _list(title, items, fmt):
        E.append(Paragraph(f"{title} ({len(items)})", S["BPH"]))
        if not items:
            E.append(Paragraph("None.", S["BPItem"]))
        for it in items:
            E.append(Paragraph("&bull; " + fmt(it), S["BPItem"]))

    blockers = [r for r in requirements if r.get("status") == "FAIL"]
    reviews = [r for r in requirements if r.get("status") == "NEEDS_REVIEW"]
    passes = [r for r in requirements if r.get("status") == "PASS"]

    def req_fmt(r):
        src = r.get("evidence_source_document") or "no source"
        pg = r.get("source_page") or r.get("evidence_source_page")
        return f"<b>{r.get('name','')}</b> &mdash; {r.get('tender_requirement','') or r.get('description','')} <font color='#4B5563'>[{src}{', p.'+str(pg) if pg else ''}]</font>"

    _list("Blockers", blockers, req_fmt)
    _list("Needs review", reviews, req_fmt)
    _list("Satisfied", passes, req_fmt)

    _list("Commercial &amp; project risks", risks,
          lambda r: f"<b>[{r.get('severity','')}] {r.get('title','')}</b> &mdash; {r.get('concern','')} <font color='#4B5563'>[Tender p.{r.get('source_page','?')}]</font>")

    _list("Action plan", actions,
          lambda a: f"<b>[{a.get('priority','')}]</b> {a.get('title','')} &mdash; {a.get('reason','')}")

    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    E.append(Paragraph(
        "BidPilot provides decision support based on uploaded information. Final tender and legal "
        "decisions remain with your team. BidPilot does not provide legal advice or guarantee tender eligibility.",
        S["BPDisc"]))
    E.append(Paragraph(f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} by BidPilot", S["BPMeta"]))

    doc.build(E)
    buf.seek(0)
    return buf.read()


def build_portfolio_report(recommendation, conflicts, capacity, objective_label):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm, title="BidPilot Portfolio Report")
    S = _styles()
    E = []
    E.append(Paragraph("BidPilot &mdash; Portfolio Recommendation", S["BPTitle"]))
    E.append(Paragraph(f"Objective: {objective_label} &middot; Decision support (not legal advice)", S["BPMeta"]))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    E.append(Spacer(1, 8))

    def _bucket(title, items, color):
        E.append(Paragraph(f"{title} ({len(items)})", S["BPH"]))
        if not items:
            E.append(Paragraph("None.", S["BPItem"])); return
        for o in items:
            val = f" &middot; ₹{o['value_cr']} Cr" if o.get("value_cr") is not None else ""
            E.append(Paragraph(f"<b><font color='{color}'>{o['name']}</font></b> &mdash; {o.get('qualification_fit',0)}% fit, {o.get('risk','')} risk{val}", S["BPItem"]))
            if o.get("note"):
                E.append(Paragraph(f"<font color='#4B5563'>{o['note']}</font>", S["BPItem"]))

    _bucket("Pursue", recommendation.get("pursue", []), "#1E4620")
    _bucket("Watch / Conditional", recommendation.get("watch", []), "#8B5A00")
    _bucket("Defer / Skip", recommendation.get("defer", []), "#A50E0E")

    E.append(Paragraph("Resource conflicts", S["BPH"]))
    if not conflicts:
        E.append(Paragraph("None detected.", S["BPItem"]))
    for c in conflicts:
        E.append(Paragraph(f"&bull; {c['message']}", S["BPItem"]))

    E.append(Paragraph("Assumptions &amp; capacity", S["BPH"]))
    p = capacity.get("people", {}); f = capacity.get("finance", {})
    E.append(Paragraph(f"Estimators {p.get('estimators',0)} &middot; Bid managers {p.get('bid_managers',0)} &middot; "
                       f"Engineers {p.get('engineers',0)} &middot; PMs {p.get('project_managers',0)} &middot; "
                       f"Specialist engineers {p.get('specialist_engineers',0)}", S["BPItem"]))
    E.append(Paragraph(f"Working capital ₹{f.get('working_capital_cr',0)} Cr &middot; Bid-security capacity ₹{f.get('bid_security_capacity_cr',0)} Cr", S["BPItem"]))
    for eq in capacity.get("equipment", []):
        E.append(Paragraph(f"{eq.get('name')}: {max(0,(eq.get('total',0)-eq.get('committed',0)))} available", S["BPItem"]))

    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    E.append(Paragraph("Portfolio recommendations are modeled from configured capacity and opportunity resource "
                       "profiles (some values are AI-inferred assumptions). They are decision support, not guaranteed "
                       "outcomes. Final decisions remain with your team.", S["BPDisc"]))
    E.append(Paragraph(f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} by BidPilot", S["BPMeta"]))
    doc.build(E)
    buf.seek(0)
    return buf.read()
