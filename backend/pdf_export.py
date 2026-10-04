"""PDF export of a DocuGuide answer: steps, documents, sources and what is still unconfirmed.

Rendered on the server from the structured answer (not a screenshot), so the text is selectable,
links work and the Romanian letters (ă î â ș ț) are correct: DejaVu Sans is bundled in backend/fonts.
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
GREEN = colors.HexColor("#087e6c")
DARK = colors.HexColor("#1d2b25")
GREY = colors.HexColor("#5f6f67")
LINE = colors.HexColor("#d5e3dc")
AMBER_BG = colors.HexColor("#fff4e0")
AMBER = colors.HexColor("#7a5a14")

_FONTS_READY = False

STATUS_LABEL = {"required": "Obligatoriu", "possible": "Posibil", "recommended": "Recomandat", "unknown": "Neconfirmat"}


def _register_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont("Body", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Italic", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")
    _FONTS_READY = True


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="Body", textColor=DARK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=18, leading=23, textColor=DARK, spaceAfter=3),
        "meta": ParagraphStyle("meta", fontSize=8.5, leading=12, textColor=GREY, **{k: v for k, v in base.items() if k not in ("textColor",)}),
        "summary": ParagraphStyle("summary", fontSize=10.5, leading=15, spaceBefore=6, spaceAfter=4, **base),
        "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=GREEN, spaceBefore=14, spaceAfter=6),
        "stepTitle": ParagraphStyle("stepTitle", fontName="Body-Bold", fontSize=10.5, leading=14, textColor=DARK),
        "body": ParagraphStyle("body", fontSize=9.5, leading=13.5, **base),
        "small": ParagraphStyle("small", fontSize=8.5, leading=12, textColor=GREY, **{k: v for k, v in base.items() if k not in ("textColor",)}),
        "quote": ParagraphStyle("quote", fontName="Body-Italic", fontSize=8, leading=11, textColor=GREY, leftIndent=8, spaceBefore=2),
        "warn": ParagraphStyle("warn", fontSize=9, leading=13, textColor=AMBER, fontName="Body"),
        "bullet": ParagraphStyle("bullet", fontSize=9, leading=12.5, leftIndent=10, bulletIndent=0, bulletFontName="Body", **base),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def _link(url: str, label: str | None = None) -> str:
    url = escape(url or "", {'"': "&quot;"})
    return f'<link href="{url}" color="#087e6c">{escape(label or url)}</link>'


def _profile_lines(card: dict | None, profile: dict) -> list[str]:
    """The user's answers in words (question: answer), using the guide's own labels."""
    lines: list[str] = []
    for q in (card or {}).get("questions", []):
        raw = (profile or {}).get(q["key"])
        if raw in (None, "", "unknown", []):
            continue
        vals = raw if isinstance(raw, list) else [raw]
        labels = []
        for v in vals:
            key = str(v).split(":")[0].strip()
            opt = next((o for o in q["options"] if o["value"] == key), None)
            if opt and key != "unknown":
                labels.append(opt["label"])
        if labels:
            lines.append(f"{q['ask'].rstrip('?')}: {', '.join(labels)}")
    return lines


def _on_page(canvas, doc, generated: str) -> None:
    canvas.saveState()
    w, h = A4
    canvas.setFont("Body-Bold", 9)
    canvas.setFillColor(GREEN)
    canvas.drawString(18 * mm, h - 11 * mm, "DocuGuide")
    canvas.setFont("Body", 8)
    canvas.setFillColor(GREY)
    canvas.drawRightString(w - 18 * mm, h - 11 * mm, generated)
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, h - 13 * mm, w - 18 * mm, h - 13 * mm)
    canvas.line(18 * mm, 14 * mm, w - 18 * mm, 14 * mm)
    canvas.drawString(18 * mm, 9.5 * mm, "Informativ. Verifică cerințele actuale la instituția responsabilă.")
    canvas.drawRightString(w - 18 * mm, 9.5 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def build_pdf(payload: dict, card: dict | None = None, now: datetime | None = None) -> bytes:
    """payload = {question, data (the answer as shown), checked (document names ticked by the user)}"""
    _register_fonts()
    st = _styles()
    data = payload.get("data") or {}
    answer = data.get("answer") or {}
    sources = data.get("sources") or []
    card_info = data.get("card") or {}
    checked = set(payload.get("checked") or [])
    now = now or datetime.now()
    generated = now.strftime("%d.%m.%Y, %H:%M")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
        title=card_info.get("title") or "Ghid DocuGuide", author="DocuGuide", subject="Documente și pași, cu surse oficiale",
    )
    story: list = []

    # ---- title block ----
    story.append(_p(card_info.get("title") or "Ghid DocuGuide", st["title"]))
    if payload.get("question"):
        story.append(Paragraph(f"<b>Întrebarea ta:</b> {escape(payload['question'])}", st["meta"]))
    for line in _profile_lines(card, data.get("profile") or {}):
        story.append(Paragraph(f"<b>Răspunsul tău —</b> {escape(line)}", st["meta"]))
    story.append(Paragraph(f"Generat la {generated}", st["meta"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=6, spaceAfter=2))
    if answer.get("summary"):
        story.append(_p(answer["summary"], st["summary"]))
    if not card_info:
        story.append(Paragraph(
            "Acest ghid a fost generat automat din surse oficiale găsite și nu este un ghid verificat manual. "
            "Verifică fiecare element la sursa indicată.", st["warn"]))

    # ---- alerts / visible notes (everything except the "unconfirmed" list) ----
    warnings = answer.get("warnings") or []
    unconfirmed = [w.split(":", 1)[1].strip() for w in warnings if w.startswith("Neconfirmat în surse:")]
    notes = [w for w in warnings if not w.startswith("Neconfirmat în surse:")]
    if notes:
        rows = [[Paragraph(escape(n), st["warn"])] for n in notes]
        t = Table(rows, colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), AMBER_BG), ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story += [Spacer(1, 6), t]

    # ---- steps ----
    steps = answer.get("steps") or []
    if steps:
        story.append(_p("Pași de urmat", st["h2"]))
        for i, s in enumerate(steps, 1):
            tick = " ✓" if s.get("check") == "confirmed" else ""
            block = [Paragraph(f"{i}. {escape(s.get('title', ''))}<font color='#087e6c'>{tick}</font>", st["stepTitle"])]
            if s.get("description"):
                block.append(_p(s["description"], st["body"]))
            meta = []
            if s.get("applies") == "yes":
                meta.append("Se aplică în cazul tău")
            if s.get("applies") == "maybe" and s.get("condition_text"):
                meta.append(f"Doar dacă {s['condition_text']}")
            if s.get("where"):
                meta.append(f"Unde: {s['where']}")
            if s.get("cost"):
                meta.append(f"Cost: {s['cost']}")
            if s.get("duration"):
                meta.append(f"Durată: {s['duration']}")
            if s.get("depends_on_step"):
                meta.append(f"După pasul {s['depends_on_step']}")
            if meta:
                block.append(_p("  ·  ".join(meta), st["small"]))
            for q in (s.get("quotes") or ([s["quote"]] if s.get("quote") else []))[:3]:
                block.append(_p(f"„{q}”", st["quote"]))
            if s.get("link"):
                block.append(Paragraph(_link(s["link"], "Pagina oficială"), st["small"]))
            block.append(Spacer(1, 7))
            story.append(KeepTogether(block))

    # ---- documents (checklist) ----
    documents = answer.get("documents") or []
    if documents:
        done = sum(1 for d in documents if d.get("name") in checked)
        story.append(_p(f"Documente de pregătit ({done}/{len(documents)} pregătite)", st["h2"]))
        rows = []
        for d in documents:
            mark = "☑" if d.get("name") in checked else "☐"
            parts = [Paragraph(f"<b>{escape(d.get('name', ''))}</b> "
                               f"<font color='#5f6f67' size='8'>— {STATUS_LABEL.get(d.get('status'), '')}"
                               f"{' ✓' if d.get('check') == 'confirmed' else ''}</font>", st["body"])]
            if d.get("applies") == "yes":
                parts.append(_p("Se aplică în cazul tău", st["small"]))
            elif d.get("applies") == "maybe" and d.get("condition_text"):
                parts.append(_p(f"Doar dacă {d['condition_text']}", st["small"]))
            if d.get("where_to_get"):
                parts.append(_p(f"Unde: {d['where_to_get']}", st["small"]))
            if d.get("quote"):
                parts.append(_p(f"„{d['quote']}”", st["quote"]))
            rows.append([Paragraph(mark, ParagraphStyle("box", fontName="Body", fontSize=13, leading=14, textColor=GREEN)), parts])
        t = Table(rows, colWidths=[9 * mm, doc.width - 9 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        story.append(t)

    # ---- passages (search-path answers without a structured guide) ----
    extracts = answer.get("extracts") or []
    if extracts:
        story.append(_p("Fragmente din sursele oficiale", st["h2"]))
        for e in extracts:
            story.append(KeepTogether([_p(e.get("text", "")[:900], st["quote"]),
                                       Paragraph(_link(e.get("url", ""), e.get("source") or e.get("url")), st["small"]),
                                       Spacer(1, 6)]))

    # ---- what is not confirmed ----
    if unconfirmed:
        story.append(_p("Ce nu este confirmat în surse", st["h2"]))
        story.append(Paragraph("Verifică aceste puncte direct la instituție înainte de a te baza pe ghid.", st["small"]))
        for u in unconfirmed:
            story.append(Paragraph(escape(u), st["bullet"], bulletText="•"))

    # ---- sources ----
    if sources:
        story.append(_p("Surse oficiale", st["h2"]))
        for s in sources:
            story.append(Paragraph(
                f"<b>[{s.get('id')}]</b> {escape(s.get('organization', ''))} — {escape(s.get('title', ''))}<br/>"
                f"{_link(s.get('url', ''))}", st["bullet"]))
            story.append(Spacer(1, 3))

    # ---- verification footer ----
    if card_info:
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
        story.append(Paragraph(
            f"Ghid verificat: {escape(str(card_info.get('confirmed', '')))} elemente confirmate pe paginile oficiale "
            f"la {generated}. Ultima verificare manuală: {escape(str(card_info.get('last_verified', '')))}.", st["small"]))

    doc.build(story, onFirstPage=lambda c, d: _on_page(c, d, generated), onLaterPages=lambda c, d: _on_page(c, d, generated))
    return buf.getvalue()
