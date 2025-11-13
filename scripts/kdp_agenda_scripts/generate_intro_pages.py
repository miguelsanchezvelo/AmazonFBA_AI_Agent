from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import calendar
import os
import argparse
import time
from colorama import Fore, Style, init as colorama_init


# ======================== CONFIG ========================
PAGE_WIDTH, PAGE_HEIGHT = A5
# Default margins; will be overridden for 6x9 to satisfy KDP
TOP_MARGIN = 24
BOTTOM_MARGIN = 20
SIDE_MARGIN = 22

NAVY = colors.HexColor("#002147")
LINE_COLOR = colors.HexColor("#D9E2EF")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "intro_sections_2025.pdf")

# Supported page sizes
SIZE_MAP = {
    "a5": A5,
    "6x9": (6 * 72.0, 9 * 72.0),
}

try:
    # Prefer system TrueType fonts to ensure proper embedding
    pdfmetrics.registerFont(TTFont("Arial", r"C:\\Windows\\Fonts\\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\\Windows\\Fonts\\arialbd.ttf"))
    FONT_NAME = "Arial"
    TITLE_FONT = "Arial-Bold"
except Exception:
    FONT_NAME = "Helvetica"
    TITLE_FONT = "Helvetica-Bold"

YEAR = 2025
month_name = calendar.month_name


# ======================== UTILS ========================
def draw_lined_box(c: canvas.Canvas, x: float, y: float, w: float, h: float, *, title: str, line_gap: float = 11.0) -> None:
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=0)
    c.setFont(TITLE_FONT, 11)
    c.setFillColor(NAVY)
    c.drawString(x + 6, y + h - 12, title)
    # Lined area
    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(0.4)
    top = y + h - 20
    bottom = y + 8
    yy = top
    while yy > bottom:
        c.line(x + 6, yy, x + w - 6, yy)
        yy -= line_gap



def draw_field(c: canvas.Canvas, label: str, x: float, y: float, w: float, *, line_y_offset: float = -16, label_font: int = 9) -> None:
    c.setFont(TITLE_FONT, label_font)
    c.setFillColor(NAVY)
    c.drawString(x, y, label)
    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(0.6)
    c.line(x, y + line_y_offset, x + w, y + line_y_offset)


# ======================== PAGES ========================
def draw_owner_info_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 15)
    c.setFillColor(NAVY)
    c.drawCentredString(PAGE_WIDTH / 2.0, PAGE_HEIGHT - TOP_MARGIN, "This Agenda Belongs To")

    x = SIDE_MARGIN
    y = PAGE_HEIGHT - TOP_MARGIN - 32
    w = PAGE_WIDTH - 2 * SIDE_MARGIN
    h = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 60
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y - h, w, h, 5, stroke=1, fill=0)

    # Two columns inside
    pad = 10
    col_gap = 14
    col_w = (w - pad * 2 - col_gap) / 2.0
    left_x = x + pad
    right_x = left_x + col_w + col_gap
    cur_y = y - 12

    # Left column fields
    draw_field(c, "Name", left_x, cur_y, col_w)
    cur_y -= 40
    draw_field(c, "Email", left_x, cur_y, col_w)
    cur_y -= 40
    draw_field(c, "Phone", left_x, cur_y, col_w)
    cur_y -= 40
    draw_field(c, "Address", left_x, cur_y, col_w)
    cur_y -= 40
    draw_field(c, "City / Postal Code", left_x, cur_y, col_w)

    # Right column fields
    cur_y_right = y - 12
    draw_field(c, "Country", right_x, cur_y_right, col_w)
    cur_y_right -= 34
    draw_field(c, "Emergency Contact (Name)", right_x, cur_y_right, col_w)
    cur_y_right -= 34
    draw_field(c, "Emergency Phone", right_x, cur_y_right, col_w)
    cur_y_right -= 34
    draw_field(c, "If found, please contact", right_x, cur_y_right, col_w)

    # Bottom lined notes for preferences/allergies
    lined_h = 84
    draw_lined_box(c, x + 8, y - h + 12, w - 16, lined_h, title="Notes")



def draw_goals_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Yearly Goals")

    grid_gap = 10
    box_w = (PAGE_WIDTH - 2 * SIDE_MARGIN - grid_gap) / 2.0
    box_h = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 24 - grid_gap) / 2.0
    titles = ["Personal", "Health", "Work / Study", "Other"]
    for i, title in enumerate(titles):
        row = i // 2
        col = i % 2
        x = SIDE_MARGIN + col * (box_w + grid_gap)
        y_top = PAGE_HEIGHT - TOP_MARGIN - 24 - row * (box_h + grid_gap)
        draw_lined_box(c, x, y_top - box_h, box_w, box_h, title=title)



def draw_important_dates_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Important Dates / Birthdays")

    cols = 2
    rows = 6
    gap_x = 10
    gap_y = 8
    grid_w = PAGE_WIDTH - 2 * SIDE_MARGIN
    col_w = (grid_w - (cols - 1) * gap_x) / cols
    grid_h = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 28
    row_h = (grid_h - (rows - 1) * gap_y) / rows

    m = 1
    for r in range(rows):
        for cidx in range(cols):
            x = SIDE_MARGIN + cidx * (col_w + gap_x)
            y_top = PAGE_HEIGHT - TOP_MARGIN - 24 - r * (row_h + gap_y)
            # small box with a few lines
            c.setStrokeColor(NAVY)
            c.setLineWidth(0.8)
            c.roundRect(x, y_top - row_h, col_w, row_h, 3, stroke=1, fill=0)
            c.setFont(TITLE_FONT, 10)
            c.setFillColor(NAVY)
            c.drawString(x + 6, y_top - 12, month_name[m])
            # lines
            c.setStrokeColor(LINE_COLOR)
            c.setLineWidth(0.4)
            top = y_top - 20
            bottom = y_top - row_h + 8
            yy = top
            while yy > bottom:
                c.line(x + 6, yy, x + col_w - 6, yy)
                yy -= 11.0
            m += 1
            if m > 12:
                break
        if m > 12:
            break



def draw_contacts_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Contacts")

    # Table header
    left = SIDE_MARGIN
    right = PAGE_WIDTH - SIDE_MARGIN
    top = PAGE_HEIGHT - TOP_MARGIN - 26
    # column widths
    name_w = (right - left) * 0.42
    phone_w = (right - left) * 0.26
    email_w = (right - left) - name_w - phone_w
    x_name = left
    x_phone = left + name_w
    x_email = x_phone + phone_w

    c.setFont(TITLE_FONT, 10)
    c.setFillColor(NAVY)
    c.drawString(x_name + 4, top + 8, "Name")
    c.drawString(x_phone + 4, top + 8, "Phone")
    c.drawString(x_email + 4, top + 8, "Email")

    # vertical separators
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.6)
    c.line(x_phone, top - (PAGE_HEIGHT - BOTTOM_MARGIN - 12), x_phone, BOTTOM_MARGIN + 12)  # won't be visible; just anchors

    # rows
    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(0.6)
    row_top = top
    row_bottom = BOTTOM_MARGIN + 12
    row_gap = 14
    y = row_top
    while y > row_bottom:
        c.line(left, y, right, y)
        y -= row_gap
    # outer border
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(left, row_bottom, right - left, row_top - row_bottom, 4, stroke=1, fill=0)
    # vertical lines on the box
    c.line(x_phone, row_bottom, x_phone, row_top)
    c.line(x_email, row_bottom, x_email, row_top)



def draw_quarterly_goals_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Quarterly Goals")

    grid_gap = 10
    box_w = (PAGE_WIDTH - 2 * SIDE_MARGIN - grid_gap) / 2.0
    box_h = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 24 - grid_gap) / 2.0
    titles = ["Q1", "Q2", "Q3", "Q4"]
    for i, title in enumerate(titles):
        row = i // 2
        col = i % 2
        x = SIDE_MARGIN + col * (box_w + grid_gap)
        y_top = PAGE_HEIGHT - TOP_MARGIN - 24 - row * (box_h + grid_gap)
        draw_lined_box(c, x, y_top - box_h, box_w, box_h, title=title)



def draw_birthdays_gifts_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Birthdays & Gifts")

    left = SIDE_MARGIN
    right = PAGE_WIDTH - SIDE_MARGIN
    top = PAGE_HEIGHT - TOP_MARGIN - 26

    # columns: Name | Date | Idea
    name_w = (right - left) * 0.54
    date_w = (right - left) * 0.16
    idea_w = (right - left) - name_w - date_w
    x_name = left
    x_date = left + name_w
    x_idea = x_date + date_w

    c.setFont(TITLE_FONT, 10)
    c.setFillColor(NAVY)
    c.drawString(x_name + 4, top + 8, "Name")
    c.drawString(x_date + 4, top + 8, "Date")
    c.drawString(x_idea + 4, top + 8, "Gift Idea")

    row_bottom = BOTTOM_MARGIN + 12
    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(0.6)
    y = top
    row_gap = 14
    while y > row_bottom:
        c.line(left, y, right, y)
        y -= row_gap
    c.line(left, row_bottom, right, row_bottom)

    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(left, row_bottom, right - left, top - row_bottom, 4, stroke=1, fill=0)
    c.line(x_date, row_bottom, x_date, top)
    c.line(x_idea, row_bottom, x_idea, top)



def draw_month_budget_page(c: canvas.Canvas) -> None:
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, "Monthly Budget")

    # Left: inputs
    left_w = (PAGE_WIDTH - 2 * SIDE_MARGIN - 10) * 0.5
    x_left = SIDE_MARGIN
    y_top = PAGE_HEIGHT - TOP_MARGIN - 24

    # Sections
    sections = [
        ("Income", 6),
        ("Fixed Expenses", 8),
        ("Variable Expenses", 8),
    ]

    yy = y_top
    for title, lines in sections:
        draw_lined_box(c, x_left, yy - 120, left_w, 120, title=title, line_gap=12)
        yy -= 120 + 10

    # Right: summary box
    x_right = x_left + left_w + 10
    w_right = PAGE_WIDTH - SIDE_MARGIN - x_right
    draw_lined_box(c, x_right, BOTTOM_MARGIN + 40, w_right, y_top - (BOTTOM_MARGIN + 40), title="Summary (Savings, Notes)", line_gap=12)


# ======================== MAIN ========================

def main() -> None:
    colorama_init(autoreset=True)
    global YEAR, OUTPUT_PATH
    parser = argparse.ArgumentParser(description="Generate KDP intro pages PDF")
    parser.add_argument("--year", type=int, default=YEAR, help="Year label (for headers where applicable)")
    parser.add_argument("--output", type=str, default=OUTPUT_PATH, help="Output PDF path")
    parser.add_argument(
        "--size",
        type=str,
        choices=["a5", "6x9"],
        default="a5",
        help="Trim size for pages (default: a5)",
    )
    parser.add_argument("--auto", action="store_true", help="Non-interactive mode (consistency flag)")
    args = parser.parse_args()

    start = time.time()
    print(Fore.CYAN + "[KDP] Generating intro pages…")

    YEAR = args.year
    OUTPUT_PATH = args.output

    # Resolve page size
    pagesize = SIZE_MAP.get(args.size, A5)
    # Update globals used by drawing functions
    global PAGE_WIDTH, PAGE_HEIGHT, TOP_MARGIN, BOTTOM_MARGIN, SIDE_MARGIN
    PAGE_WIDTH, PAGE_HEIGHT = pagesize
    # Enforce KDP-safe margins for 6x9
    if args.size == "6x9":
        TOP_MARGIN = 36  # 0.5"
        BOTTOM_MARGIN = 36
        SIDE_MARGIN = 36  # >= 0.375" on both sides

    c = canvas.Canvas(OUTPUT_PATH, pagesize=pagesize)

    # 1) Owner info page
    draw_owner_info_page(c)
    c.showPage()

    # 2) Yearly goals (4 boxes)
    draw_goals_page(c)
    c.showPage()

    # 2b) Quarterly goals (Q1..Q4)
    draw_quarterly_goals_page(c)
    c.showPage()

    # 3) Important dates / Birthdays (12 small boxes)
    draw_important_dates_page(c)
    c.showPage()

    # 4) Contacts page
    draw_contacts_page(c)
    c.showPage()

    # 5) Birthdays & Gifts list
    draw_birthdays_gifts_page(c)
    c.showPage()

    # 6) Monthly Budget template
    draw_month_budget_page(c)
    c.showPage()

    c.save()
    elapsed = time.time() - start
    print(Fore.GREEN + f"PDF generado: {OUTPUT_PATH}" + Style.RESET_ALL)
    print(Fore.YELLOW + f"Duración: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
