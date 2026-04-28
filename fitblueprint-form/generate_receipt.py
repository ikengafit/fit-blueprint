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
    HRFlowable, KeepTogether, Image
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
        "notice":ParagraphStyle("notice",fontName="DM",   fontSize=7, leading=10,
                                textColor=MUTED, spaceAfter=3),
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
def make_hf(W, H, MARGIN):
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
            "iKengaFit  \u00b7  Washington, DC & Virtual  \u00b7  (202) 936-7657  \u00b7  "
            "ikengafit.com  \u00b7  david.clary@ikengafit.com")
        canvas.drawRightString(W - MARGIN, 0.34*inch, f"Page {doc.page}")
        canvas.restoreState()
    return draw

# ─── MAIN BUILD ───────────────────────────────────────────────────────────────
def build_receipt(submission: dict, output_path: str):
    s = S()
    W, H = letter
    MARGIN = 0.62 * inch
    COL    = W - 2 * MARGIN

    # Parse submission
    name    = submission.get("fullName",          "Client")
    email   = submission.get("email",             "")
    phone   = submission.get("phone",             "")
    loc     = submission.get("location",          "")
    pref          = submission.get("trainingPreference", "virtual")
    pkg_raw       = submission.get("recommendedPkg",     "")
    goal          = submission.get("primaryGoal",        "Not specified")
    level         = submission.get("fitnessLevel",       "Not specified")
    injury        = submission.get("injuries",           "None reported")
    iso           = submission.get("submittedAt",        datetime.now().isoformat())
    discount_code = (submission.get("discountCode",      "") or "").strip()

    try:
        dt       = datetime.fromisoformat(iso)
        svc_date = dt.strftime("%B %d, %Y")
        rec_no   = "IKF-" + dt.strftime("%Y%m%d%H%M")
    except Exception:
        svc_date = datetime.now().strftime("%B %d, %Y")
        rec_no   = "IKF-" + datetime.now().strftime("%Y%m%d%H%M")

    # Derive training modality from preference
    mode = "In-Person" if ("in-person" in pref.lower() or "in person" in pref.lower()) else "Virtual"

    # Fit Blueprint is always a fixed $100 service
    BASE_PRICE   = 100.00
    display_qty  = 1
    unit_price   = BASE_PRICE
    price        = BASE_PRICE
    discount_amt = 0.00
    if discount_code:
        # If a discount code was entered, record it — actual discount amount
        # can be adjusted here once codes/amounts are defined
        discount_code_display = discount_code.upper()
    else:
        discount_code_display = None
    total_paid = price - discount_amt

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
            Paragraph("(202) 936-7657  \u00b7  david.clary@ikengafit.com  \u00b7  ikengafit.com", s["body"]),
            Paragraph("<font color='#5A5754'>Provider tax identification available upon request from plan administrator.</font>", s["small"]),
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

    # No CPT codes — columns: Description | Qty | Unit Price | Total
    c1 = 3.68*inch; c3 = 0.46*inch; c4 = 0.96*inch; c5 = 1.04*inch

    svc_desc = (
        "<b>Comprehensive Fitness Assessment &amp; Individualized Exercise Prescription "
        "— iKengaFit Fit Blueprint Session</b><br/>"
        "<font size='7' color='#5A5754'>"
        "Single-session evaluation by David Clary, CSCS (NSCA), M.S. Clinical Exercise Science. "
        "Services rendered: "
        "(1) <b>Resting Measurements</b> — blood pressure, heart rate, grip strength; "
        "(2) <b>Body Composition</b> — InBody bioelectrical impedance + circumference (waist, hip, chest, arm, thigh); "
        "(3) <b>Functional Movement Screen (FMS)</b> — 7-pattern screen for limitations, asymmetries &amp; injury risk; "
        "(4) <b>Muscular Strength &amp; Endurance</b> — push test, core endurance holds, lower-body evaluation; "
        "(5) <b>Cardiovascular Assessment</b> — submaximal treadmill recovery test for aerobic capacity; "
        "(6) <b>Exercise Prescription</b> — personalized program based on findings, health history &amp; goals. "
        f"Modality: {mode}."
        "</font>"
    )

    svc = Table([
        [Paragraph("Description of Service",  s["label"]),
         Paragraph("Qty",                     s["label"]),
         Paragraph("Unit Price",              s["label"]),
         Paragraph("Total",                   s["label"])],
        [Paragraph(svc_desc, s["body"]),
         Paragraph(str(display_qty),          s["bold"]),
         Paragraph(f"${price:,.2f}",          s["bold"]),
         Paragraph(f"${price:,.2f}",          s["bold"])],
    ], colWidths=[c1, c3, c4, c5])
    svc.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), ROW_BG),
        ("LINEBELOW",   (0,0),(-1,0), 0.4, BORDER),
        ("LINEBELOW",   (0,1),(-1,1), 0.4, BORDER),
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",  (0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("ALIGN",       (1,0),(-1,-1),"RIGHT"),
    ]))
    story.append(svc)

    # Totals — columns aligned to c4+c5 of service table
    pad = c1 + c3
    totals_rows = [
        ["", Paragraph("Subtotal",          s["body"]),  Paragraph(f"${price:,.2f}",   s["body"])],
    ]
    discount_row_idx = None
    if discount_code_display:
        discount_label = f"Discount Code: <b>{discount_code_display}</b>"
        discount_val   = f"  -${discount_amt:,.2f}" if discount_amt else "  Applied"
        discount_row_idx = len(totals_rows)
        totals_rows.append(
            ["", Paragraph(discount_label + discount_val, s["small"]), ""]
        )
    totals_rows += [
        ["", Paragraph("<b>TOTAL PAID</b>",  s["bold"]),  Paragraph(f"<b>${total_paid:,.2f}</b>", s["bold"])],
        ["", Paragraph("Pmt Method",     s["small"]), Paragraph("Paid in Full",     s["small"])],
    ]
    totals = Table(totals_rows, colWidths=[pad, c4, c5])
    total_row = len(totals_rows) - 2  # TOTAL PAID row index
    ts_cmds = [
        ("LINEABOVE",    (1,total_row),(-1,total_row), 0.75, TEAL),
        ("LINEBELOW",    (1,total_row),(-1,total_row), 0.4,  BORDER),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1),5),
        ("RIGHTPADDING", (0,0),(-1,-1),5),
        ("TOPPADDING",   (0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("ALIGN",        (1,0),(-1,-1),"RIGHT"),
    ]
    if discount_row_idx is not None:
        ts_cmds.append(("SPAN", (1, discount_row_idx), (2, discount_row_idx)))
        ts_cmds.append(("ALIGN", (1, discount_row_idx), (2, discount_row_idx), "LEFT"))
    totals.setStyle(TableStyle(ts_cmds))
    story.append(totals)
    story.append(rule(TEAL, 0.6, space=3))

    # 4. CLINICAL DOCUMENTATION ────────────────────────────────────────────────
    clin = Table([
        [Paragraph("PROVIDER CREDENTIALS",        s["label"]),
         Paragraph("SERVICE CATEGORY",             s["label"]),
         Paragraph("CERTIFICATIONS / JURISDICTION", s["label"])],
        [Paragraph("David Clary, MS, CSCS, PN1<br/>"
                   "M.S. Clinical Exercise Science<br/>"
                   "Cert. Strength &amp; Conditioning Specialist (NSCA)<br/>"
                   "Precision Nutrition Coach, Level 1",  s["body"]),
         Paragraph("Comprehensive Fitness Assessment<br/>"
                   "Individualized Exercise Prescription<br/>"
                   "Preventive &amp; Corrective Health Services",   s["body"]),
         Paragraph("NSCA-CSCS  \u00b7  NASM-CPT<br/>"
                   "Precision Nutrition PN1<br/>"
                   "FMS Certified Practitioner<br/>"
                   "Jurisdiction: Washington, DC",        s["body"])],
        [Paragraph("CLIENT-REPORTED HEALTH GOAL",  s["label"]),
         Paragraph("FUNCTIONAL FITNESS LEVEL",     s["label"]),
         Paragraph("REPORTED LIMITATIONS / INJURIES", s["label"])],
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
    # Tighten spacing before clinical block when discount row adds extra height
    story.append(Spacer(1, 2 if discount_code_display else 4))
    story.append(KeepTogether([
        Paragraph("CLINICAL DOCUMENTATION FOR REIMBURSEMENT", s["h2"]),
        clin,
    ]))
    story.append(rule(space=3))

    # 5. REIMBURSEMENT GUIDANCE ────────────────────────────────────────────────
    story.append(Paragraph("REIMBURSEMENT GUIDANCE &amp; LETTER OF MEDICAL NECESSITY SUPPORT", s["h2"]))
    story.append(Paragraph(
        "<b>HSA / FSA / Employer Wellness:</b> Services may qualify for reimbursement when accompanied by a "
        "<b>Letter of Medical Necessity (LMN)</b> from a licensed physician citing the client\u2019s diagnosis "
        "and clinical rationale for supervised fitness assessment and corrective exercise prescription. "
        "Submit this itemized receipt with the LMN to your plan administrator or HSA/FSA provider. "
        "Eligibility is determined solely by your plan. iKengaFit does not guarantee reimbursement. "
        "Retain documentation for 7 years.",
        s["notice"]))
    story.append(rule(space=3))

    # 6. PROVIDER CERTIFICATION + SIGNATURE — wrapped in KeepTogether so it
    # never splits across pages regardless of content above it.
    sig_w  = 2.2 * inch
    date_w = 2.2 * inch
    gap = COL - sig_w - date_w

    # Signature image — scale to fit above the line naturally
    sig_img_path = Path(__file__).parent / "signature.png"
    # Display at ~1.4 inch wide, proportional height (205x71 px → ratio 0.346)
    sig_img_w = 1.4 * inch
    sig_img_h = sig_img_w * (71 / 205)

    sig_block = KeepTogether([
        Paragraph("PROVIDER CERTIFICATION", s["h2"]),
        Paragraph(
            "I certify that the services listed were rendered as described, that all "
            "information is accurate and complete, and that this receipt reflects "
            "actual charges for services provided to the named client.",
            s["notice"]),
        Spacer(1, 0.06*inch),
        # Signature image above the line
        Table(
            [[Image(str(sig_img_path), width=sig_img_w, height=sig_img_h),
              Spacer(gap, 1),
              Paragraph("", s["small"])]],
            colWidths=[sig_w, gap, date_w],
            style=[("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                   ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),2),
                   ("VALIGN",(0,0),(-1,-1),"BOTTOM")]),
        # Signature lines
        Table(
            [[HRFlowable(width=sig_w, thickness=0.75, color=DARK),
              Spacer(gap, 1),
              HRFlowable(width=date_w, thickness=0.75, color=DARK)],
             [Paragraph("David Clary, MS, CSCS, PN1", s["small"]),
              Spacer(gap, 1),
              Paragraph(svc_date, s["small"])],
             [Paragraph("<font color='#8A9090'>Provider Signature</font>", s["label"]),
              Spacer(gap, 1),
              Paragraph("<font color='#8A9090'>Date</font>", s["label"])]],
            colWidths=[sig_w, gap, date_w],
            style=[("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                   ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]),
    ])
    story.append(sig_block)

    # ── BUILD ──────────────────────────────────────────────────────────────────
    hf = make_hf(W, H, MARGIN)

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        title="iKengaFit Personal Training Receipt",
        author="iKengaFit",
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.38*inch, bottomMargin=0.48*inch,
    )
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print(f"Receipt saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_receipt.py <submission.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    build_receipt(data, sys.argv[2])
