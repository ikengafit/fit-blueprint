"""
generate_client_pdf.py
Generates a 7-page client-facing PDF mirroring the iKengaFit PPTX deck.
ReportLab canvas: origin (0,0) = BOTTOM-LEFT. All y coords are measured from bottom.
"""
import sys, json, os
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

# ─── FONTS ────────────────────────────────────────────────────────────────────
FONT_DIR = Path("/tmp/fonts")
def _reg(name, path):
    try:
        pdfmetrics.registerFont(TTFont(name, str(path))); return True
    except Exception:
        return False

if _reg("DM",  FONT_DIR/"DMSans-Regular.ttf") and _reg("DM-B", FONT_DIR/"DMSans-Bold.ttf"):
    R, B = "DM", "DM-B"
else:
    R, B = "Helvetica", "Helvetica-Bold"

# ─── COLORS ───────────────────────────────────────────────────────────────────
TEAL      = HexColor("#028381")
TEAL_DK   = HexColor("#01605F")
CRIMSON   = HexColor("#8A2C0E")
DARK      = HexColor("#151414")
CREAM     = HexColor("#F5F1EB")
GRAY_DK   = HexColor("#1E1E1E")
GRAY_LT   = HexColor("#E8E4DD")
MUTED     = HexColor("#767574")
AA        = HexColor("#AAAAAA")          # light grey text
PEACH     = HexColor("#FFCAB0")
TEAL_LT   = HexColor("#CCE8E8")
D8EC      = HexColor("#D8ECEB")
CCCC      = HexColor("#CCCCCC")

# ─── PAGE ─────────────────────────────────────────────────────────────────────
W, H = LETTER   # 612 × 792 pt
M    = 0.5 * inch

HERE      = Path(__file__).parent
LOGO_PATH = HERE / "public" / "logo_form.jpg"
LOGO_AR   = 1742 / 614        # width / height
LOGO_H    = 0.38 * inch
LOGO_W    = LOGO_H * LOGO_AR

# ─── LOW-LEVEL HELPERS ────────────────────────────────────────────────────────

def fill_rect(c, x, y, w, h, color):
    """Draw filled rectangle. y = bottom of rect (ReportLab convention)."""
    c.setFillColor(color)
    c.rect(x, y, w, h, fill=1, stroke=0)

def stroke_rect(c, x, y, w, h, color, lw=0.8):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.rect(x, y, w, h, fill=0, stroke=1)

def hline(c, x, y, w, color=CRIMSON, lw=2.5):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(x, y, x + w, y)

def txt(c, s, x, y, size=10, color=white, bold=False, align="left", maxw=None):
    """Single-line text. y = baseline."""
    c.setFillColor(color)
    c.setFont(B if bold else R, size)
    if align == "center" and maxw:
        c.drawCentredString(x + maxw/2, y, s)
    elif align == "right" and maxw:
        c.drawRightString(x + maxw, y, s)
    else:
        c.drawString(x, y, s)

def lbl(c, s, x, y, color=TEAL, size=7):
    """Small all-caps tracking label."""
    c.setFillColor(color)
    c.setFont(B, size)
    c.drawString(x, y, s.upper())

def logo_tr(c):
    """Logo in top-right corner of page."""
    if LOGO_PATH.exists():
        x = W - M - LOGO_W
        y = H - M - LOGO_H
        c.drawImage(str(LOGO_PATH), x, y, width=LOGO_W, height=LOGO_H,
                    preserveAspectRatio=True, mask="auto")

def logo_at(c, x, y, h=None):
    if LOGO_PATH.exists():
        _h = h or LOGO_H
        _w = _h * LOGO_AR
        c.drawImage(str(LOGO_PATH), x, y, width=_w, height=_h,
                    preserveAspectRatio=True, mask="auto")

def wrap_lines(c, text, max_w, size, bold):
    """Word-wrap text into list of lines fitting max_w."""
    font = B if bold else R
    c.setFont(font, size)
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def wtext(c, text, x, y_top, max_w, size=10, color=white, bold=False,
          leading=None, max_lines=None):
    """
    Wrapped text. y_top = TOP of the text block (descends downward).
    Returns total height used.
    """
    _lead = leading or (size * 1.38)
    lines = wrap_lines(c, text, max_w, size, bold)
    if max_lines:
        lines = lines[:max_lines]
    c.setFillColor(color)
    c.setFont(B if bold else R, size)
    for i, line in enumerate(lines):
        baseline = y_top - (i + 0.85) * _lead
        c.drawString(x, baseline, line)
    return len(lines) * _lead

# ─── PAGE 1 — COVER ───────────────────────────────────────────────────────────
def p1_cover(c, data):
    name = data.get("clientName") or data.get("fullName", "Client")

    fill_rect(c, 0, 0, W, H, DARK)
    # Teal left accent bar
    fill_rect(c, 0, 0, 0.18*inch, H, TEAL)

    # Logo top-right
    logo_tr(c)

    # Small label near top
    lbl(c, "Personalized Fitness Coaching", M, H - M - 0.02*inch, TEAL, 7)

    # Hero headline — vertically centered between logo area and crimson box
    # Crimson box top: M + 1.35*inch = ~1.85 inch from bottom
    # Logo/label area bottom: H - M - 0.5*inch = ~11.0 inch from bottom
    # Total content block height: headline(2 lines ~1.1") + tagline(0.55") + rule + subtitle = ~2.0"
    # Center of available zone = (1.85 + 11.0) / 2 = 6.43" from bottom
    # Place hero_top so center of 2" block = 6.43" → hero_top = 6.43 + 1.0 = 7.43"
    # But LETTER H = 11" so in pts: H = 792, inch = 72pts
    # hero_top_pt = 7.43 * 72 = 535 pts from bottom
    # Vertically center the content block in the page
    # Available zone: top of crimson box at M+1.35*inch=~1.85" to label at H-M-0.1*inch=~10.9"
    # Block height approx: 2 headline lines (62pt each) + tagline (15pt) + rule + subtitle
    #   = 1.25" + 0.22" + 0.22" + 0.14" + 0.20" = ~2.0"
    # Vertical center = (1.85 + 10.9) / 2 = 6.38"; place top of block at center + half_height
    # hero_top (baseline of first line) ≈ 6.38 + 1.0 = 7.38" but in pts = 7.38*72 = 531
    # H = 792pt. Hero block center should be ~50% = 396pt from bottom.
    # Content block from hero_top down to subtitle: ~2.0 inches = 144pt
    # So hero_top should be at ~396 + 72 = 468pt, which is H*0.59
    # But that always looks low visually. PPTX cover has hero just slightly above center.
    # Set hero_top to H * 0.64 so the content group straddles the visual center.
    hero_top = H * 0.64   # ~507pt from bottom = ~3.96" from top on 11" page

    c.setFillColor(white)
    c.setFont(B, 44)
    c.drawString(M, hero_top,              "YOUR COACHING")
    c.drawString(M, hero_top - 0.62*inch,  "PACKAGE PROPOSAL")

    # Tagline
    tag_y = hero_top - 1.08*inch
    c.setFillColor(TEAL)
    c.setFont(R, 15)
    c.drawString(M, tag_y, "Find Your Place of Strength™")

    # Crimson rule
    hline(c, M, tag_y - 0.22*inch, 2.5*inch, CRIMSON, 2.5)

    # Subtitle
    c.setFillColor(AA)
    c.setFont(R, 10)
    c.drawString(M, tag_y - 0.46*inch,
        f"Prepared exclusively for {name} following your iKengaFit Fitness Assessment")

    # Bottom crimson box (bottom-right)
    bW, bH = 2.55*inch, 1.35*inch
    bX = W - M - bW
    bY = M
    fill_rect(c, bX, bY, bW, bH, CRIMSON)
    c.setFillColor(white)
    c.setFont(B, 11)
    c.drawCentredString(bX + bW/2, bY + bH - 0.36*inch, "Washington, DC")
    c.drawCentredString(bX + bW/2, bY + bH - 0.58*inch, "& Virtual Nationwide")
    c.setFillColor(PEACH)
    c.setFont(R, 10)
    c.drawCentredString(bX + bW/2, bY + 0.22*inch, "ikengafit.com")

    # iKengaFit wordmark bottom-left
    c.setFillColor(white)
    c.setFont(B, 15)
    c.drawString(M, M + 0.22*inch, "iKengaFit")


# ─── PAGE 2 — TRAINER ─────────────────────────────────────────────────────────
def p2_trainer(c, data):
    fill_rect(c, 0, 0, W, H, CREAM)

    # Teal header bar at top
    hH = 1.1*inch
    fill_rect(c, 0, H - hH, W, hH, TEAL)
    logo_tr(c)
    lbl(c, "About iKengaFit", M, H - 0.3*inch, white, 7)
    c.setFillColor(white)
    c.setFont(B, 22)
    c.drawString(M, H - hH + 0.22*inch, "Your Trainer & Credentials")

    # Content starts below header — card fills most of the page height
    ct = H - hH - 0.25*inch   # content top
    lW = 4.3*inch

    # ── Right dark credential card — sized to fill page bottom to content top ──
    cX = M + lW + 0.25*inch
    cW = W - cX - M              # fits to right margin
    # Card goes from near-bottom to content top, with enough bottom padding
    cY = M
    cH = ct - cY - 0.1*inch
    fill_rect(c, cX, cY, cW, cH + 0.3*inch, DARK)  # +0.3" extra to avoid clipping footer

    ci = 0.16*inch
    inner_w = cW - ci * 2        # text width inside card padding

    lbl(c, "Meet Your Trainer", cX+ci, cY+cH-0.22*inch, TEAL, 7)
    c.setFillColor(white)
    c.setFont(B, 22)
    c.drawString(cX+ci, cY+cH-0.52*inch, "David Clary")
    c.setFillColor(TEAL)
    c.setFont(R, 11)
    c.drawString(cX+ci, cY+cH-0.76*inch, "MS, CSCS, Pn1")
    hline(c, cX+ci, cY+cH-0.98*inch, 1.3*inch, CRIMSON, 2)

    creds = [
        ("M.S.",  "Clinical Exercise Science — Liberty University"),
        ("B.S.",  "Human Performance — Howard University"),
        ("CSCS",  "Certified Strength & Conditioning Specialist"),
        ("Pn1",   "Precision Nutrition Coach, Level 1"),
        ("ACE",   "Nationally Certified Personal Trainer"),
        ("Bio.",  "Dartfish Biomechanical Analysis Technician"),
    ]
    # Distribute 6 credentials across the available vertical space
    # Leave room at bottom for footer line
    cred_top = cY + cH - 1.18*inch
    cred_bot = cY + 0.55*inch    # enough room above footer line at cY+0.14
    cred_step = (cred_top - cred_bot) / max(len(creds)-1, 1)
    for i, (abbr, desc) in enumerate(creds):
        ry = cred_top - i * cred_step
        c.setFillColor(TEAL)
        c.setFont(B, 9)
        c.drawString(cX+ci, ry, abbr)
        desc_x  = cX + ci + 0.52*inch
        desc_w  = inner_w - 0.52*inch
        wtext(c, desc, desc_x, ry + 0.02*inch, desc_w,
              size=9, color=CCCC, leading=12, max_lines=1)

    c.setFillColor(MUTED)
    c.setFont(R, 8)
    c.drawString(cX+ci, cY + 0.14*inch, "Human Performance Expert  ·  DMV Area")

    # ── Left column — fills matching height to card ──
    c.setFillColor(TEAL)
    c.setFont(B, 14)
    c.drawString(M, ct - 0.05*inch, "Who We Are")
    hline(c, M, ct - 0.28*inch, 1.1*inch, CRIMSON, 2)

    wtext(c, ("iKengaFit is a Washington, DC-based personal training and coaching "
              "practice serving clients in-person in the NOMA area and virtually "
              "nationwide. Every program is built around you — your goals, your "
              "schedule, your life."),
          M, ct - 0.44*inch, lW, size=10, color=DARK, leading=15)

    # Quote box
    qH = 0.54*inch
    qY = ct - 1.62*inch          # bottom of quote box
    fill_rect(c, M, qY, lW, qH, TEAL_DK)
    c.setFillColor(white)
    c.setFont(B, 10.5)
    c.drawString(M + 0.14*inch, qY + qH - 0.22*inch,
                 '"Grab YOUR health by the horns."')

    c.setFillColor(DARK)
    c.setFont(R, 10)
    c.drawString(M, qY - 0.28*inch, "In-person: Washington, DC (NOMA area)")
    c.drawString(M, qY - 0.48*inch, "Virtually nationwide")

    # Additional info block to fill left column space
    info_top = qY - 0.74*inch
    lbl(c, "Our Approach", M, info_top, TEAL, 7)
    hline(c, M, info_top - 0.18*inch, 1.0*inch, TEAL, 0.6)
    wtext(c, ("We combine evidence-based exercise programming with personalized "
              "coaching to build programs you'll actually stick with. No fluff — "
              "just science-backed training designed around your body and goals."),
          M, info_top - 0.34*inch, lW, size=10, color=DARK, leading=15)

    # Services list
    svc_top = info_top - 1.52*inch
    lbl(c, "Services", M, svc_top, TEAL, 7)
    hline(c, M, svc_top - 0.18*inch, 0.6*inch, TEAL, 0.6)
    services = ["Standard Session Packages",
                "Elite Monthly Coaching (Precision & Signature)",
                "Virtual & In-Person Training",
                "Nutrition & Habit Coaching (Elite)"]
    for i, svc in enumerate(services):
        c.setFillColor(DARK)
        c.setFont(R, 9.5)
        c.drawString(M + 0.12*inch, svc_top - 0.38*inch - i*0.28*inch, f"•  {svc}")


# ─── PAGE 3 — WHERE YOU ARE TODAY ─────────────────────────────────────────────
def p3_assessment(c, data):
    name = data.get("clientName") or data.get("fullName", "Client")
    fill_rect(c, 0, 0, W, H, DARK)
    fill_rect(c, 0, 0, 0.18*inch, H, TEAL)
    logo_tr(c)

    lbl(c, "Your Fitness Assessment Recap", M, H-M-0.02*inch, AA, 7)
    c.setFillColor(white)
    c.setFont(B, 28)
    c.drawString(M, H-M-0.48*inch, "Where You Are Today")
    hline(c, M, H-M-0.68*inch, 1.8*inch, CRIMSON, 2)
    c.setFillColor(AA)
    c.setFont(R, 10)
    c.drawString(M, H-M-0.86*inch, f"Assessment summary for {name}:")

    boxes = [
        ("Primary Goal",        data.get("primaryGoal",     "[Not specified]")),
        ("Fitness Level",       data.get("fitnessLevel",    "[Not specified]")),
        ("Training History",    data.get("trainingHistory", "[Not specified]")),
        ("Availability",        data.get("availability",    "[Not specified]")),
        ("Key Focus Areas",     data.get("focusAreas",      "[Not specified]")),
        ("Recommended Package", data.get("recommendedPkg",  "To be determined")),
    ]

    # Grid: 3 cols × 2 rows — fix row height so boxes fill page without excess space
    grid_top = H - M - 1.04*inch
    grid_bot = M
    grid_h   = grid_top - grid_bot
    row_gap  = 0.14*inch
    # Fixed row height: content area fits label + ~3 lines of text + padding
    row_h    = (grid_h - row_gap) / 2

    avail_w  = W - M - 0.22*inch - M
    col_gap  = 0.12*inch
    col_w    = (avail_w - 2*col_gap) / 3

    for idx, (lbl_txt, val) in enumerate(boxes):
        col = idx % 3
        row = idx // 3
        bx  = M + col*(col_w + col_gap)
        # row 0 = top row, row 1 = bottom row
        by  = grid_top - (row+1)*row_h - row*row_gap

        fill_rect(c, bx, by, col_w, row_h, GRAY_DK)
        stroke_rect(c, bx, by, col_w, row_h, TEAL, 0.8)

        val_str = str(val) if val else "—"
        max_lines = int((row_h - 0.5*inch) / 18)
        # Place content starting at 65% down from box top (creates visual centering)
        # Box top = by + row_h, so content_top_baseline = by + row_h - row_h*0.22
        content_y = by + row_h - 0.22*inch   # just below top of box = top padding

        lbl(c, lbl_txt, bx+0.14*inch, content_y, TEAL, 7)
        wtext(c, val_str, bx+0.14*inch, content_y - 0.22*inch,
              col_w - 0.28*inch, size=13, color=white, bold=True,
              leading=18, max_lines=max_lines)


# ─── PAGE 4 — BENEFITS ────────────────────────────────────────────────────────
def p4_benefits(c, data):
    fill_rect(c, 0, 0, W, H, DARK)
    fill_rect(c, 0, 0, 0.18*inch, H, TEAL)
    logo_tr(c)

    lbl(c, "What You Get With Every Package", M, H-M-0.02*inch, AA, 7)
    c.setFillColor(white)
    c.setFont(B, 28)
    c.drawString(M, H-M-0.48*inch, "Built for You. Built to Perform.")
    hline(c, M, H-M-0.68*inch, 1.8*inch, CRIMSON, 2)

    bens = [
        ("01", "Customized Workouts",
         "Every session is designed around your goals, movement patterns, and "
         "fitness level — no cookie-cutter plans."),
        ("02", "Expert Coaching & Feedback",
         "Real-time instruction from a CSCS-certified trainer with an M.S. in "
         "Clinical Exercise Science."),
        ("03", "Virtual or In-Person",
         "Train in-person in Washington, DC (NOMA area) or virtually from "
         "anywhere in the country — same quality."),
        ("04", "Performance Tracking",
         "App access to track goals and metrics so you can measure and "
         "visualize your progress over time."),
        ("05", "Flexible Payment",
         "One-time package purchases with no monthly commitment. "
         "Split-payment available on 12- and 24-session packages."),
        ("06", "A Clear Path Forward",
         "Standard packages are a strong starting point — many clients upgrade "
         "to Elite Coaching after their first package."),
    ]

    # 2-col × 3-row grid — use tighter row height so content fills page evenly
    # Each item: number (18pt) + title (12pt) + ~3 lines body (9.5pt) ≈ 1.4 inch
    # Give each row a fixed 1.55 inch with thin dividers
    grid_top = H - M - 0.88*inch
    grid_bot = M + 0.1*inch
    grid_h   = grid_top - grid_bot
    row_h    = grid_h / 3   # 3 rows

    avail_w  = W - M - 0.22*inch - M
    col_gap  = 0.4*inch
    col_w    = (avail_w - col_gap) / 2

    for i, (num, title, body) in enumerate(bens):
        col = i % 2
        row = i // 2
        bx  = M + col*(col_w + col_gap)
        # row 0 = top, row 2 = bottom
        by  = grid_top - (row+1)*row_h

        # Anchor content at top of row area with minimal top padding
        item_top = by + row_h - 0.18*inch

        # Number
        c.setFillColor(TEAL)
        c.setFont(B, 18)
        c.drawString(bx, item_top - 0.26*inch, num)

        # Title
        c.setFillColor(white)
        c.setFont(B, 12)
        c.drawString(bx + 0.48*inch, item_top - 0.24*inch, title)

        # Body — up to 3 lines
        wtext(c, body, bx + 0.48*inch, item_top - 0.48*inch,
              col_w - 0.48*inch, size=9.5, color=AA, leading=13.5, max_lines=3)

        # Subtle divider between rows (not after last row)
        if row < 2:
            hline(c, bx, by + 0.06*inch, col_w, HexColor("#2A2A2A"), 0.4)


# ─── PAGE 5 — COMPARISON TABLE ────────────────────────────────────────────────
def p5_comparison(c, data):
    fill_rect(c, 0, 0, W, H, CREAM)

    hH = 1.0*inch
    fill_rect(c, 0, H-hH, W, hH, DARK)
    logo_tr(c)
    lbl(c, "Coaching Comparison", M, H-0.28*inch, TEAL, 7)
    c.setFillColor(white)
    c.setFont(B, 20)
    c.drawString(M, H-hH+0.22*inch, "Standard Coaching vs. Elite Coaching")

    tL = M; tR = W - M; tW = tR - tL
    cWs = [tW*0.26, tW*0.26, tW*0.24, tW*0.24]
    cXs = [tL,
           tL+cWs[0],
           tL+cWs[0]+cWs[1],
           tL+cWs[0]+cWs[1]+cWs[2]]

    # Column header row
    tHY  = H - hH - 0.44*inch   # bottom of header row
    tHH  = 0.38*inch
    fill_rect(c, tL, tHY, tW, tHH, TEAL)
    hdrs = ["Feature", "Standard Coaching",
            "Elite — Precision (2x/wk)", "Elite — Signature (3x/wk)"]
    for i, h in enumerate(hdrs):
        c.setFillColor(white)
        c.setFont(B, 8)
        bl = tHY + tHH/2 - 4
        if i == 0:
            c.drawString(cXs[i]+0.08*inch, bl, h)
        else:
            c.drawCentredString(cXs[i]+cWs[i]/2, bl, h)

    rows = [
        ("Coaching Model",        "Session-based",  "Monthly program", "Monthly program"),
        ("Personalized Plan",     "[YES]",           "[YES]",           "[YES]"),
        ("Ongoing Accountability","[NO]",            "[YES]",           "[YES]"),
        ("Weekly Check-Ins",      "[NO]",            "[YES]",           "[YES]"),
        ("Habit & Nutrition",     "[NO]",            "[YES]",           "[YES]"),
        ("Progress Reviews",      "[NO]",            "[YES]",           "[YES]"),
        ("Application Required",  "Not required",   "Required",        "Required"),
        ("Schedule Flexibility",  "High",           "Moderate",        "Moderate"),
        ("Investment",            "From $270",      "$1,000/mo",       "$1,500/mo"),
    ]

    tDB  = M + 0.28*inch
    avail_rh = tHY - tDB
    rH   = avail_rh / len(rows)

    for ri, row in enumerate(rows):
        ry = tHY - (ri+1)*rH
        bg = GRAY_LT if ri % 2 == 0 else CREAM
        fill_rect(c, tL, ry, tW, rH, bg)
        fill_rect(c, cXs[1], ry, cWs[1], rH, D8EC)

        for ci, cell in enumerate(row):
            is_yes = cell == "[YES]"
            is_no  = cell == "[NO]"
            disp   = ("✓" if is_yes else ("✗" if is_no else cell))

            # Use ASCII fallbacks since DM Sans may lack ✓/✗
            if is_yes: disp = "YES"
            if is_no:  disp = "—"

            cell_color = (TEAL_DK  if is_yes and ci == 1 else
                          HexColor("#5A9EA0") if is_yes else
                          MUTED    if is_no else
                          DARK)
            fsize = 9 if ci == 0 else 10
            c.setFillColor(cell_color)
            c.setFont(B if (is_yes and ci == 1) else R, fsize)
            bl = ry + rH/2 - fsize*0.35
            if ci == 0:
                c.drawString(cXs[ci]+0.08*inch, bl, disp)
            else:
                c.drawCentredString(cXs[ci]+cWs[ci]/2, bl, disp)

    c.setFillColor(DARK)
    c.setFont(R, 8)
    c.drawString(tL, M+0.08*inch,
                 "Elite Coaching requires an application and a 3-month minimum commitment.")


# ─── PAGE 6 — PRICING ─────────────────────────────────────────────────────────
def p6_pricing(c, data):
    import qrcode as qrc
    fill_rect(c, 0, 0, W, H, TEAL)
    fill_rect(c, 0, 0, 0.18*inch, H, TEAL_DK)
    logo_tr(c)

    lbl(c, "Pricing & Next Steps", M, H-M-0.02*inch, white, 7)
    c.setFillColor(white)
    c.setFont(B, 26)
    c.drawString(M, H-M-0.48*inch, "Ready to Start? Let's Get to Work.")
    hline(c, M, H-M-0.68*inch, 2.4*inch, CRIMSON, 2.5)

    STD_URL  = "https://www.ikengafit.com/standardcoaching"
    ELIT_URL = "https://www.ikengafit.com/elitecoaching"

    def make_qr(url, path):
        if not os.path.exists(path):
            qrc.make(url, box_size=6, border=2).save(path)
    make_qr(STD_URL,  "/tmp/qr_std_pdf.png")
    make_qr(ELIT_URL, "/tmp/qr_elite_pdf.png")

    packages = [
        ("6 Sessions",  "$270",   "$600",   "2–3 wks  ·  Min 2x/week"),
        ("12 Sessions", "$600",   "$1,080", "4–6 wks  ·  Min 2x/week"),
        ("24 Sessions", "$1,080", "$1,920", "8–12 wks  ·  Min 2x/week"),
    ]

    # Bottom elite crimson bar
    cta_h = 1.25*inch
    cta_y = M
    fill_rect(c, M, cta_y, W-2*M, cta_h, CRIMSON)

    eq = 0.85*inch
    eq_x = W - M - eq - 0.18*inch
    eq_y = cta_y + (cta_h - eq)/2
    if os.path.exists("/tmp/qr_elite_pdf.png"):
        c.drawImage("/tmp/qr_elite_pdf.png", eq_x, eq_y, width=eq, height=eq)

    c.setFillColor(white)
    c.setFont(B, 14)
    c.drawString(M+0.2*inch, cta_y+cta_h-0.3*inch, "Interested in Elite Coaching?")
    wtext(c, "Apply at ikengafit.com/elitecoaching — Precision 2x/wk $1,000/mo  ·  Signature 3x/wk $1,500/mo",
          M+0.2*inch, cta_y+cta_h-0.54*inch, eq_x-M-0.4*inch,
          size=9, color=PEACH, leading=13)
    c.setFillColor(DARK)
    c.setFont(B, 9)
    c.drawString(M+0.2*inch, cta_y+0.2*inch, "Scan to Apply  →")

    # Package cards
    cards_top = H - M - 0.88*inch
    cards_bot = cta_y + cta_h + 0.14*inch
    card_h    = cards_top - cards_bot
    avail_w   = W - 2*M
    col_gap   = 0.18*inch
    card_w    = (avail_w - 2*col_gap) / 3
    # QR size scales to fill the majority of remaining card space after pricing info
    info_h = 1.28*inch   # space used by name + weeks + divider + price labels + prices
    qr_size = min(card_h - info_h - 0.5*inch, card_w - 0.3*inch)

    for i, (pkg, virt, ip, weeks) in enumerate(packages):
        cx = M + i*(card_w+col_gap)
        cy = cards_bot

        fill_rect(c, cx, cy, card_w, card_h, TEAL_DK)

        # Package name
        c.setFillColor(white)
        c.setFont(B, 13)
        c.drawString(cx+0.15*inch, cy+card_h-0.3*inch, pkg)

        # Weeks
        c.setFillColor(TEAL_LT)
        c.setFont(R, 8)
        c.drawString(cx+0.15*inch, cy+card_h-0.5*inch, weeks)

        # Thin divider
        fill_rect(c, cx+0.15*inch, cy+card_h-0.66*inch,
                  card_w-0.3*inch, 0.015*inch, HexColor("#035E5D"))

        # Prices — virtual left, in-person right
        half_w = (card_w - 0.3*inch)/2 - 0.05*inch

        lbl(c, "VIRTUAL",  cx+0.15*inch,      cy+card_h-0.84*inch, TEAL_LT, 7)
        lbl(c, "IN-PERSON", cx+0.2*inch+half_w, cy+card_h-0.84*inch, PEACH,  7)

        c.setFillColor(white)
        c.setFont(B, 20)
        c.drawString(cx+0.15*inch,       cy+card_h-1.14*inch, virt)
        c.drawString(cx+0.2*inch+half_w, cy+card_h-1.14*inch, ip)

        # QR code — centered horizontally, vertically fills the gap between price and bottom
        qr_x = cx + (card_w - qr_size)/2
        # Place QR so there's equal space above and below it in the remaining area
        qr_area_top = cy + card_h - 1.28*inch   # just below price info
        qr_area_bot = cy + 0.36*inch             # above "Tap to Book" label
        qr_y = qr_area_bot + (qr_area_top - qr_area_bot - qr_size) / 2
        if os.path.exists("/tmp/qr_std_pdf.png"):
            c.drawImage("/tmp/qr_std_pdf.png", qr_x, qr_y,
                        width=qr_size, height=qr_size)

        # Tap to Book — white text for contrast
        c.setFillColor(white)
        c.setFont(R, 7.5)
        c.drawCentredString(cx+card_w/2, cy+0.2*inch, "Tap to Book")


# ─── PAGE 7 — CLOSING ─────────────────────────────────────────────────────────
def p7_closing(c, data):
    fill_rect(c, 0, 0, W, H, TEAL)

    # Dark left panel
    pW = 3.75*inch
    fill_rect(c, 0, 0, pW, H, DARK)

    lx = M; lw = pW - M - 0.2*inch

    # Left panel — distribute content evenly top to bottom
    # iKengaFit wordmark near top
    c.setFillColor(white)
    c.setFont(B, 24)
    c.drawString(lx, H - 1.0*inch, "iKengaFit")
    hline(c, lx, H-1.22*inch, 1.5*inch, CRIMSON, 2.5)
    c.setFillColor(TEAL)
    c.setFont(R, 12)
    c.drawString(lx, H-1.44*inch, "Find Your Place of Strength™")

    # Trainer info — place in upper-middle
    c.setFillColor(AA)
    c.setFont(R, 10)
    c.drawString(lx, H-2.6*inch, "David Clary, MS, CSCS, Pn1")
    c.drawString(lx, H-2.82*inch, "Personal Trainer & Coach")

    # Contact block — middle
    lbl(c, "Contact & Links", lx, H-3.6*inch, TEAL, 7)
    hline(c, lx, H-3.78*inch, lw, TEAL, 0.8)
    links = ["ikengafit.com",
             "ikengafit.com/standardcoaching",
             "Washington, DC & Virtual"]
    for i, lnk in enumerate(links):
        c.setFillColor(TEAL)
        c.setFont(R, 10)
        c.drawString(lx, H-3.98*inch - i*0.34*inch, lnk)

    # Logo bottom-left
    logo_at(c, lx, M+0.1*inch)

    # ── Right teal panel ──
    rx = pW + M
    rw = W - rx - M

    lbl(c, "Your Next Step", rx, H-M-0.02*inch, TEAL_DK, 7)

    c.setFillColor(white)
    c.setFont(B, 28)
    c.drawString(rx, H-M-0.48*inch, "Let's Build")
    c.drawString(rx, H-M-0.9*inch,  "Your Strongest Self.")

    hline(c, rx, H-M-1.1*inch, 2.2*inch, CRIMSON, 2.5)

    wtext(c, ("Your assessment is complete. Your program is ready to be built. "
              "The next step is yours — select a package, book your sessions, "
              "and let's get to work."),
          rx, H-M-1.3*inch, rw, size=11, color=white, leading=17)

    # Steps section to fill the large gap in the right panel
    steps_top = H - M - 2.0*inch
    lbl(c, "Your Next Steps", rx, steps_top, TEAL_DK, 7)
    hline(c, rx, steps_top - 0.18*inch, rw, HexColor("#026E6C"), 0.6)
    steps = [
        ("01", "Review your package options below"),
        ("02", "Scan or click to book your sessions"),
        ("03", "Complete onboarding in the iKengaFit app"),
        ("04", "Show up and get to work!"),
    ]
    for i, (num, step_text) in enumerate(steps):
        sy = steps_top - 0.46*inch - i * 0.52*inch
        c.setFillColor(TEAL_DK)
        c.setFont(B, 11)
        c.drawString(rx, sy, num)
        c.setFillColor(white)
        c.setFont(R, 10.5)
        c.drawString(rx + 0.4*inch, sy, step_text)

    # BOOK button
    btn_h = 0.58*inch
    btn_y = M + 1.55*inch
    fill_rect(c, rx, btn_y, rw, btn_h, CRIMSON)
    c.setFillColor(white)
    c.setFont(B, 12)
    c.drawCentredString(rx+rw/2, btn_y+btn_h/2-0.08*inch, "BOOK YOUR PACKAGE  →")

    # Free week banner
    fw_h = 0.42*inch
    fw_y = M + 0.88*inch
    fill_rect(c, rx, fw_y, rw, fw_h, DARK)  # dark box for contrast on teal bg
    c.setFillColor(TEAL)
    c.setFont(B, 8.5)
    c.drawString(rx+0.12*inch, fw_y+fw_h-0.2*inch,
                 "Try 1 FREE Week of the Elite Performance System in the iKengaFit App")

    # Footer note
    c.setFillColor(DARK)
    c.setFont(R, 8.5)
    c.drawString(rx, M+0.14*inch,
                 "Questions? Visit ikengafit.com or book a free Fitness Assessment.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def build_client_pdf(submission: dict, output_path: str):
    c = Canvas(str(output_path), pagesize=LETTER)
    c.setTitle("iKengaFit Fit Blueprint — Personalized Coaching Proposal")
    c.setAuthor("iKengaFit")

    pages = [p1_cover, p2_trainer, p3_assessment,
             p4_benefits, p5_comparison, p6_pricing, p7_closing]
    for i, fn in enumerate(pages):
        fn(c, submission)
        if i < len(pages)-1:
            c.showPage()

    c.save()
    print(f"Client PDF saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_client_pdf.py <submission.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        sub = json.load(f)
    build_client_pdf(sub, sys.argv[2])
