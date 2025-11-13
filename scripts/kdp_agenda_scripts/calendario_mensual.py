import argparse
import calendar
from dataclasses import dataclass
from typing import List, Tuple

from colorama import Fore, init as colorama_init
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


WEEKDAYS_EN = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


@dataclass
class Layout:
    """Layout constants for the rotated month grid.

    Coordinates are expressed in the rotated coordinate system (landscape content
    on a portrait page), where width' = page_height and height' = page_width.
    """

    page_w: float
    page_h: float
    # Increase margin to satisfy KDP inside/outside minimums and avoid flags
    margin: float = 36.0
    header_h: float = 38.0  # month title area (more room under title)
    dow_h: float = 26.0     # days-of-week header row (more separation)


def _rotated_page(c: canvas.Canvas, page_w: float, page_h: float) -> None:
    """Rotate the canvas 90 degrees to draw landscape content on portrait page."""
    c.saveState()
    c.translate(page_w, 0)
    c.rotate(90)


def _restore(c: canvas.Canvas) -> None:
    c.restoreState()


def _month_matrix(year: int, month: int, start_monday: bool) -> List[List[int]]:
    cal = calendar.Calendar(firstweekday=0 if start_monday else 6)
    # monthdayscalendar returns weeks as lists of ints (0 if outside month)
    return cal.monthdayscalendar(year, month)


def _draw_month(c: canvas.Canvas, year: int, month: int, *, start_monday: bool) -> None:
    page_w, page_h = A5  # portrait
    _rotated_page(c, page_w, page_h)

    # Now drawing with width' = page_h and height' = page_w
    L = Layout(page_w=page_h, page_h=page_w)

    # Background
    c.setFillColor(colors.white)
    c.rect(0, 0, L.page_w, L.page_h, stroke=0, fill=1)

    # Title (push inward from page edge to avoid KDP margin flags on odd pages)
    month_name = calendar.month_name[month].upper()
    c.setFillColor(colors.HexColor('#0B2239'))
    # Ensure Arial embedding for titles
    try:
        pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\\Windows\\Fonts\\arialbd.ttf"))
        title_font = "Arial-Bold"
    except Exception:
        title_font = "Helvetica-Bold"
    c.setFont(title_font, 18)
    title_inset = 16  # points moved inward from the top/left frame after rotation
    c.drawCentredString(L.page_w / 2.0, L.page_h - (L.margin + title_inset), f"{month_name} {year}")

    # Days-of-week header (extra inset on odd pages to avoid outer-margin flags)
    left = L.margin + 8
    right = L.page_w - L.margin
    top = L.page_h - (L.margin - 2) - L.header_h
    grid_top = top - L.dow_h
    bottom = L.margin

    cols = 7
    weeks = _month_matrix(year, month, start_monday)
    rows = len(weeks)
    cell_w = (right - left) / cols
    cell_h = (grid_top - bottom) / rows

    c.setStrokeColor(colors.HexColor('#A3B8D8'))
    c.setLineWidth(0.8)

    # Header labels (English)
    dows = WEEKDAYS_EN if start_monday else WEEKDAYS_EN[-1:] + WEEKDAYS_EN[:-1]
    try:
        pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\\Windows\\Fonts\\arialbd.ttf"))
        header_font = "Arial-Bold"
    except Exception:
        header_font = "Helvetica-Bold"
    c.setFont(header_font, 9)
    c.setFillColor(colors.HexColor('#2C3E55'))
    for i, name in enumerate(dows):
        x = left + i * cell_w + cell_w / 2.0
        # Move weekday names even closer to the grid
        c.drawCentredString(x, top + L.dow_h * 0.08, name)

    # Grid
    c.setLineWidth(1.0)
    for r in range(rows + 1):
        y = grid_top - r * cell_h
        c.line(left, y, right, y)
    for cidx in range(cols + 1):
        x = left + cidx * cell_w
        c.line(x, grid_top, x, bottom)

    # Day numbers
    try:
        pdfmetrics.registerFont(TTFont("Arial", r"C:\\Windows\\Fonts\\arial.ttf"))
        num_font = "Arial"
    except Exception:
        num_font = "Helvetica"
    c.setFont(num_font, 9)
    c.setFillColor(colors.HexColor('#2C3E55'))
    pad = 6
    for r, week in enumerate(weeks):
        for cidx, day in enumerate(week):
            if day == 0:
                continue
            x0 = left + cidx * cell_w
            y1 = grid_top - r * cell_h
            c.drawString(x0 + pad, y1 - pad - 9, str(day))

    _restore(c)


def generate_monthly_pdf(output_path: str, *, year: int, start_monday: bool = True, size: str = "a5") -> None:
    """Generate a monthly calendar PDF with one page per month.

    Pages are portrait, but each page draws a landscape-style grid rotated 90°
    so all pages mantienen orientación vertical (KDP-friendly).
    """
    pagesize = A5 if size == "a5" else (6 * 72.0, 9 * 72.0)
    c = canvas.Canvas(output_path, pagesize=pagesize)
    for month in range(1, 13):
        _draw_month(c, year, month, start_monday=start_monday)
        c.showPage()
    c.save()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Genera calendario mensual rotado en páginas A5 verticales")
    p.add_argument("--year", type=int, default=2025, help="Año a renderizar")
    p.add_argument("--output", type=str, default="monthly_calendar.pdf", help="Ruta de salida del PDF")
    p.add_argument("--start", type=str, default="monday", choices=["monday", "sunday"], help="Primer día de la semana")
    p.add_argument("--size", type=str, choices=["a5", "6x9"], default="a5", help="Tamaño de corte (afecta el tamaño de página)")
    return p


def main() -> None:
    colorama_init(autoreset=True)
    args = build_parser().parse_args()
    start_monday = args.start.lower() == "monday"
    generate_monthly_pdf(args.output, year=args.year, start_monday=start_monday, size=args.size)
    print(Fore.GREEN + f"Mensual generado: {args.output}")


if __name__ == "__main__":
    main()


