#!/usr/bin/env python3
"""
iKengaFit — Insurance Reimbursement Receipt Generator
Produces a single-page PDF receipt suitable for HSA/FSA/insurance reimbursement.
Usage: python3 generate_receipt.py <submission.json> <output.pdf>
"""

import sys, json, urllib.request
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─── FONTS ─────────────────────────────────────────────────────────────────────
FONT_DIR = Path("/tmp/fonts")
FONT_DIR.mkdir(exist_ok=True)

def dl_font(name, url):
    p = FONT_DIR / name
    if not p.exists():
        urllib.request.urlretrieve(url, p)
    return str(p)

reg = dl_font("DMSans.ttf",
    "https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf")
pdfmetrics.registerFont(TTFont("DM",   reg))
pdfmetrics.registerFont(TTFont("DM-B", reg))

# ─── COLORS ────────────────────────────────────────────────────────────────────
TEAL   = HexColor("#028381")
DARK   = HexColor("#151414")
ROW_BG = HexColor("#EEE9E2")
LABEL  = HexColor("#2E2C29")   # near-black — survives fax/photocopy
MUTED  = HexColor("#5A5754")
BORDER = HexColor("#C8C4BC")

# ─── STYLES (compact) ──────────────────────────────────────────────────────────
def S():
    return {
        "h2":    ParagraphStyle("h2",    fontName="DM-B", fontSize=7.5, leading=10,
                                textColor=DARK, spaceBefore=6, spaceAfter=3),
        "body":  ParagraphStyle("body",  fontName="DM",   fontSize=8.5, leading=12,
                                textColor=DARK, spaceAfter=1),
        "bold":  ParagraphStyle("bold",  fontName="DM-B", fontSize=8.5, leading=12,
                                textColor=DARK, spaceAfter=1),
        "small": ParagraphStyle("small", fontName="DM",   fontSize=7.5, leading=10,
                                textColor=MUTED, spaceAfter=1),
        "label": ParagraphStyle("label", fontName="DM-B", fontSize=6.5, leading=9,
                                textColor=LABEL, spaceAfter=1),
        "notice":ParagraphStyle("notice",fontName="DM",   fontSize=7.5, leading=11,
                                textColor=MUTED, spaceAfter=5),
    }

# ─── PACKAGE MAP ───────────────────────────────────────────────────────────────
PACKAGES = {
    "6":  {"virtual": 270,  "in-person": 600,  "sessions": 6,  "weeks": "2-3 weeks"},
    "12": {"virtual": 600,  "in-person": 1080, "sessions": 12, "weeks": "4-6 weeks"},
    "24": {"virtual": 1080, "in-person": 1920, "sessions": 24, "weeks": "8-12 weeks"},
}

def parse_package(pkg_str, pref):
    import re
    pkg_lower = (pkg_str or "").lower()
    mode = "In-Person" if ("in-person" in (pref or "").lower()
                           or "in person" in (pref or "").lower()) else "Virtual"
    key  = "in-person" if mode == "In-Person" else "virtual"
    for n, info in PACKAGES.items():
        if (f"{n}-session" in pkg_lower or f"{n} session" in pkg_lower
                or f"{n}-sess" in pkg_lower):
            return info["sessions"], info[key], info["weeks"], mode
    prices = re.findall(r'\$(\d+)', pkg_str or "")
    return "—", int(prices[-1]) if prices else 0, "—", mode

def rule(color=BORDER, thickness=0.4, space=4):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceBefore=space, spaceAfter=space)

# ─── HEADER / FOOTER ──────────────────────────────────────────────────────────
def make_hf(W, H, MARGIN, total_ref):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(TEAL)
        canvas.rect(0, H - 0.34*inch, W, 0.34*inch, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(MARGIN, H - 0.24*inch, "iKengaFit")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN + 62, H - 0.24*inch, "Personal Training")
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawRightString(W - MARGIN, H - 0.24*inch, "ITEMIZED SERVICE RECEIPT")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 0.52*inch, W - MARGIN, 0.52*inch)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 0.34*inch,
            "iKengaFit  \u00b7  Washington, DC & Virtual  \u00b7  "
            "ikengafit.com  \u00b7  david.clary@ikengafit.com")
        total = total_ref[0] or ""
        suffix = f" of {total}" if total else ""
        canvas.drawRightString(W - MARGIN, 0.34*inch, f"Page {doc.page}{suffix}")
        canvas.restoreState()
    return draw

# ─── MAIN BUILD ───────────────────────────────────────────────────────────────
def build_receipt(submission: dict, output_path: str):
    s = S()
    W, H = letter
    MARGIN = 0.72 * inch
    COL    = W - 2 * MARGIN

    # Parse submission
    name    = submission.get("fullName",          "Client")
    email   = submission.get("email",             "")
    phone   = submission.get("phone",             "")
    loc     = submission.get("location",          "")
    pref    = submission.get("trainingPreference","virtual")
    pkg_raw = submission.get("recommendedPkg",    "")
    goal    = submission.get("primaryGoal",       "Not specified")
    level   = submission.get("fitnessLevel",      "Not specified")
    injury  = submission.get("injuries",          "None reported")
    iso     = submission.get("submittedAt",       datetime.now().isoformat())

    try:
        dt       = datetime.fromisoformat(iso)
        svc_date = dt.strftime("%B %d, %Y")
        rec_no   = "IKF-" + dt.strftime("%Y%m%d%H%M")
    except Exception:
        svc_date = datetime.now().strftime("%B %d, %Y")
        rec_no   = "IKF-" + datetime.now().strftime("%Y%m%d%H%M")

    sessions, price, weeks, mode = parse_package(pkg_raw, pref)
    unit_price = round(price / sessions, 2) if isinstance(sessions, int) and sessions else 0

    # ── Story ──────────────────────────────────────────────────────────────────
    story = []
    half  = COL / 2
    third = COL / 3
    qtr   = COL / 4

    # 1. PROVIDER / CLIENT ─────────────────────────────────────────────────────
    def col_list(items):
        """Render a list of Paragraph items stacked vertically inside a table cell."""
        return items

    pc = Table([[
        col_list([
            Paragraph("SERVICE PROVIDER", s["label"]),
            Paragraph("<b>iKengaFit</b>", s["body"]),
            Paragraph("David Clary, MS, CSCS, PN1", s["body"]),
            Paragraph("1140 3rd St NE, Washington, DC 20002", s["body"]),
            Paragraph("david.clary@ikengafit.com  \u00b7  ikengafit.com", s["body"]),
            Paragraph("<font color='#CC2200'><b>EIN: [REQUIRED — add before sending]</b></font>", s["small"]),
            Paragraph("<font color='#CC2200'><b>NPI: [REQUIRED — add before sending]</b></font>", s["small"]),
        ]),
        col_list([
            Paragraph("CLIENT / PATIENT", s["label"]),
            Paragraph(f"<b>{name}</b>", s["body"]),
            Paragraph(email,  s["body"]),
            Paragraph(phone,  s["body"]),
            Paragraph(loc,    s["body"]),
            Paragraph("",     s["small"]),
            Paragraph("",     s["small"]),
        ]),
    ]], colWidths=[half, half])
    pc.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(pc)
    story.append(rule())

    # 2. RECEIPT META ──────────────────────────────────────────────────────────
    meta = Table(
        [[Paragraph("RECEIPT NO.",       s["label"]),
          Paragraph("DATE OF ISSUE",     s["label"]),
          Paragraph("DATE OF SERVICE",   s["label"]),
          Paragraph("MODALITY",          s["label"])],
         [Paragraph(f"<b>{rec_no}</b>",  s["body"]),
          Paragraph(svc_date,            s["body"]),
          Paragraph(svc_date,            s["body"]),
          Paragraph(f"<b>{mode}</b>",    s["body"])]],
        colWidths=[qtr]*4
    )
    meta.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),1),
        ("BOTTOMPADDING",(0,0),(-1,-1),1),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.08*inch))

    # 3. ITEMIZED SERVICES ─────────────────────────────────────────────────────
    story.append(Paragraph("ITEMIZED SERVICES", s["h2"]))

    c1 = 2.68*inch; c2 = 1.0*inch; c3 = 0.46*inch; c4 = 0.82*inch; c5 = 0.97*inch
    # verify: 2.9+0.78+0.46+0.82+0.97 = 5.93 < 6.56 (COL at 0.72 margin) — fine

    svc = Table([
        [Paragraph("Description of Service",  s["label"]),
         Paragraph("CPT Code",                s["label"]),
         Paragraph("Qty",                     s["label"]),
         Paragraph("Unit Price",              s["label"]),
         Paragraph("Total",                   s["label"])],
        [Paragraph(
            "<b>Individualized Personal Training Program</b><br/>"
            f"<font size='7' color='#5A5754'>"
            f"Prescribed exercise program supervised by a Certified Strength &amp; "
            f"Conditioning Specialist (CSCS). Includes fitness assessment, individualized "
            f"exercise prescription, and progress monitoring. "
            f"Modality: {mode}. Duration: {weeks}, min. 2x/week."
            f"</font>", s["body"]),
         Paragraph("97110 / 97150",  s["small"]),   # separated with slash
         Paragraph(str(sessions),     s["bold"]),
         Paragraph(f"${unit_price:,.2f}", s["bold"]),
         Paragraph(f"${price:,.2f}",      s["bold"])],
    ], colWidths=[c1, c2, c3, c4, c5])
    svc.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), ROW_BG),
        ("LINEBELOW",   (0,0),(-1,0), 0.4, BORDER),
        ("LINEBELOW",   (0,1),(-1,1), 0.4, BORDER),
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",  (0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("ALIGN",       (2,0),(-1,-1),"RIGHT"),
    ]))
    story.append(svc)

    # Totals — columns aligned exactly to c4+c5 of service table
    pad = c1 + c2 + c3
    totals = Table([
        ["", Paragraph("Subtotal",          s["body"]),  Paragraph(f"${price:,.2f}",   s["body"])],
        ["", Paragraph("<b>TOTAL PAID</b>",  s["bold"]),  Paragraph(f"<b>${price:,.2f}</b>", s["bold"])],
        ["", Paragraph("Pmt Method",     s["small"]), Paragraph("Paid in Full",     s["small"])],
    ], colWidths=[pad, c4, c5])
    totals.setStyle(TableStyle([
        ("LINEABOVE",    (1,2),(-1,2), 0.75, TEAL),
        ("LINEBELOW",    (1,2),(-1,2), 0.4,  BORDER),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1),5),
        ("RIGHTPADDING", (0,0),(-1,-1),5),
        ("TOPPADDING",   (0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("ALIGN",        (1,0),(-1,-1),"RIGHT"),
    ]))
    story.append(totals)
    story.append(rule(TEAL, 0.6, space=3))

    # 4. CLINICAL DOCUMENTATION ────────────────────────────────────────────────
    clin = Table([
        [Paragraph("PROVIDER CREDENTIALS",        s["label"]),
         Paragraph("SERVICE CATEGORY",             s["label"]),
         Paragraph("NPI / CERTIFICATION",          s["label"])],
        [Paragraph("David Clary, MS, CSCS, PN1<br/>"
                   "Cert. Strength &amp; Conditioning Specialist<br/>"
                   "Precision Nutrition Level 1",  s["body"]),
         Paragraph("Therapeutic Exercise (97110)<br/>"
                   "Therapeutic Activities (97150)<br/>"
                   "Preventive Health Services",   s["body"]),
         Paragraph("<font color='#CC2200'><b>[REQUIRED — add NPI]</b></font><br/>"
                   "NSCA-CSCS Certified<br/>"
                   "Jurisdiction: DC",             s["body"])],
        [Paragraph("CLIENT-REPORTED HEALTH GOAL",  s["label"]),
         Paragraph("FUNCTIONAL FITNESS LEVEL",     s["label"]),
         Paragraph("REPORTED LIMITATIONS",         s["label"])],
        [Paragraph(goal,   s["body"]),
         Paragraph(level,  s["body"]),
         Paragraph(injury, s["body"])],
    ], colWidths=[third, third, third])
    clin.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), HexColor("#028381")),
        ("TEXTCOLOR",   (0,0),(-1,0), white),
        ("BACKGROUND",  (0,2),(-1,2), HexColor("#028381")),
        ("TEXTCOLOR",   (0,2),(-1,2), white),
        ("GRID",        (0,0),(-1,-1), 0.3, BORDER),
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",  (0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(KeepTogether([
        Paragraph("CLINICAL DOCUMENTATION FOR REIMBURSEMENT", s["h2"]),
        clin,
    ]))
    story.append(rule(space=3))

    # 5. REIMBURSEMENT GUIDANCE ────────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("REIMBURSEMENT GUIDANCE", s["h2"]),
        Paragraph(
            "<b>HSA / FSA:</b> Personal training may be reimbursable when prescribed as "
            "medically necessary by a licensed physician. Submit this receipt plus a "
            "<b>Letter of Medical Necessity (LMN)</b> to your HSA/FSA administrator. "
            "The LMN must include your diagnosis, clinical rationale, and recommended "
            "frequency and duration of treatment.",
            s["notice"]),
        Paragraph(
            "<b>Employer Wellness / Medicare Advantage:</b> Many plans reimburse fitness "
            "expenses. Submit this receipt with your member ID and check your plan\u2019s "
            "Evidence of Coverage for eligible categories and annual limits.",
            s["notice"]),
        Paragraph(
            "<b>Important:</b> Eligibility is determined solely by your plan administrator. "
            "iKengaFit does not guarantee reimbursement. Retain all documentation for 7 years.",
            s["notice"]),
    ]))
    story.append(rule(space=3))

    # 6. PROVIDER CERTIFICATION + SIGNATURE ────────────────────────────────────
    sig_w  = 2.2*inch
    date_w = 2.2*inch

    story.append(KeepTogether([
        Paragraph("PROVIDER CERTIFICATION", s["h2"]),
        Paragraph(
            "I certify that the services listed were rendered as described, that all "
            "information is accurate and complete, and that this receipt reflects actual "
            "charges for services provided to the named client.",
            s["notice"]),
        Spacer(1, 0.14*inch),
        Table([[
            Table([
                [HRFlowable(width=sig_w, thickness=0.75, color=DARK)],
                [Paragraph("David Clary, MS, CSCS, PN1", s["small"])],
                [Paragraph("Provider Signature", s["label"])],
            ], colWidths=[sig_w + 0.3*inch],
               style=[("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                      ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]),
            Table([
                [HRFlowable(width=date_w, thickness=0.75, color=DARK)],
                [Paragraph(svc_date, s["small"])],
                [Paragraph("Date", s["label"])],
            ], colWidths=[date_w + 0.3*inch],
               style=[("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                      ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]),
        ]], colWidths=[COL*0.55, COL*0.45],
           style=[("VALIGN",(0,0),(-1,-1),"TOP"),
                  ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                  ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]),
    ]))

    # ── TWO-PASS BUILD for "Page X of Y" ──────────────────────────────────────
    from io import BytesIO
    total_ref = [None]

    def _count_pass():
        buf = BytesIO()
        tmp = SimpleDocTemplate(buf, pagesize=letter,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=0.54*inch, bottomMargin=0.68*inch)
        tmp.build(story[:])
        total_ref[0] = tmp.page

    _count_pass()
    hf = make_hf(W, H, MARGIN, total_ref)

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        title="iKengaFit Personal Training Receipt",
        author="iKengaFit",
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.54*inch, bottomMargin=0.68*inch,
    )
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print(f"Receipt saved: {output_path}  ({total_ref[0]} page(s))")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_receipt.py <submission.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    build_receipt(data, sys.argv[2])
