from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import calendar
import os
from datetime import date, timedelta
import argparse
import time
from colorama import Fore, Style, init as colorama_init
from typing import Dict, List
import json

# ======================== CONFIGURACIÓN ========================
# Keep layout metrics in landscape coordinates
PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)
TOP_MARGIN = 15
BOTTOM_MARGIN = 15
SIDE_MARGIN = 25
ROW_GAP = 6
COL_GAP = 14
# Hacer la distribución más simétrica reduciendo desplazamientos adicionales
GLOBAL_VOFFSET = 0
SECOND_ROW_VSHIFT = 0
NAVY = colors.HexColor("#002147")
LIGHT_BLUE = colors.HexColor("#A9C6EA")
# Estilos de resaltado
SUNDAY_BG = colors.HexColor("#E0ECFA")
SATURDAY_BG = colors.HexColor("#F5F8FC")
SUNDAY_TEXT = colors.white
SATURDAY_TEXT = NAVY
# Guardar siempre en la misma carpeta del script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "annual_calendar_2025_expanded.pdf")

# Fuente: registrar Arial para incrustación correcta
try:
    pdfmetrics.registerFont(TTFont("Arial", r"C:\\Windows\\Fonts\\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\\Windows\\Fonts\\arialbd.ttf"))
    FONT_NAME = "Arial"
    TITLE_FONT_NAME = "Arial-Bold"
except Exception:
    FONT_NAME = "Helvetica"
    TITLE_FONT_NAME = "Helvetica-Bold"
DAY_FONT_SIZE = 9
YEAR_TITLE_FONT_SIZE = 18
YEAR_HEADER_SPACE = 0
# Side year label fine-tuning
YEAR_SIDE_EDGE_INSET = 2   # distance from outer edge in points
YEAR_SIDE_Y_OFFSET = 32    # shift toward first row of months (positive moves up)

month_name = calendar.month_name
YEAR = 2025
SIZE = "a5"  # default; can be overridden by CLI

# ======================== FESTIVOS OCCIDENTE (GENÉRICOS) ========================
def western_easter_date(year: int) -> date:
    """Compute western Easter Sunday date for a given year.

    Args:
        year: Gregorian year.

    Returns:
        The `date` of Easter Sunday for the given year.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = 1 + ((h + l - 7 * m + 114) % 31)
    return date(year, month, day)


def build_western_holidays(year: int) -> Dict[date, str]:
    """Build a minimal set of western holidays for the given year.

    Args:
        year: Gregorian year.

    Returns:
        Mapping from `date` to holiday label.
    """
    easter = western_easter_date(year)
    holidays = {
        date(year, 1, 1): "New Year's Day",
        easter - timedelta(days=2): "Good Friday",
        easter + timedelta(days=1): "Easter Monday",
        date(year, 5, 1): "International Workers' Day (May Day)",
        date(year, 11, 1): "All Saints' Day",
        date(year, 12, 25): "Christmas Day",
        date(year, 12, 31): "New Year's Eve",
    }
    return holidays


HOLIDAYS = build_western_holidays(YEAR)
HOLIDAY_RECT_VOFFSET = 1.5  # subir el recuadro para centrar mejor respecto al texto
PILL_RADIUS = 3.0
SUNDAY_PAD_X = 3.0
SUNDAY_PAD_Y = 1.4
SATURDAY_PAD_X = 2.4
SATURDAY_PAD_Y = 1.2

# ======================== GENERADOR DE CALENDARIO ========================
def draw_annual_calendar(c: canvas.Canvas, *, show_legend: bool = True) -> None:
    """Draw the 12-month annual calendar across two portrait pages.

    Internally, the layout math uses landscape coordinates (PAGE_WIDTH/HEIGHT),
    but we rotate the canvas +90° on each page so the content appears rotated
    within a portrait page. This keeps a uniform portrait orientation for KDP.

    Args:
        c: ReportLab canvas to draw into.
        show_legend: If True, prints the holiday legend at the bottom.
    """
    layout = [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12]
    ]

    for page_months in layout:
        # Rotate landscape content into a portrait page
        c.saveState()
        # Portrait A5 page size (width, height) is A5; rotate around origin then translate
        portrait_w, portrait_h = (A5 if SIZE == "a5" else (6 * 72.0, 9 * 72.0))
        c.translate(portrait_w, 0)
        c.rotate(90)

        # Draw side year label on each spread
        draw_year_side_label(c)
        for idx, month in enumerate(page_months):
            # Distribución en horizontal: 3 columnas x 2 filas
            row_idx = idx // 3
            col_idx = idx % 3
            draw_month_box(c, month, col_idx, row_idx)
        if show_legend:
            draw_holiday_legend(c, page_months)
        c.restoreState()
        c.showPage()


def draw_month_box(c: canvas.Canvas, month: int, col_idx: int, row_idx: int) -> None:
    """Draw a single month box at the given grid position.

    Args:
        c: ReportLab canvas.
        month: Month number in 1..12.
        col_idx: Column index (0..2).
        row_idx: Row index (0..1).
    """
    # Área base del mes (3 columnas x 2 filas en apaisado) con espacios entre cajas
    box_w = (PAGE_WIDTH - 2 * SIDE_MARGIN - 2 * COL_GAP) / 3
    # Reserve extra 20pt for legend clearance at bottom of each page
    box_h = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - ROW_GAP - 20) / 2
    x0 = SIDE_MARGIN + col_idx * (box_w + COL_GAP)
    # Desplazar bloques: mantener margen superior seguro en la primera fila
    # Para la segunda fila, subimos 1/3 del espacio entre filas + desplazamiento adicional
    y_offset_row = 0 if row_idx == 0 else (ROW_GAP * (2/3) + SECOND_ROW_VSHIFT)
    y0 = PAGE_HEIGHT - TOP_MARGIN - YEAR_HEADER_SPACE - GLOBAL_VOFFSET - row_idx * (box_h + ROW_GAP) + y_offset_row
    if row_idx == 0:
        # Añadir holgura adicional para aumentar separación del encabezado/año (pág. 9 y 141)
        y0 -= 18

    # Título
    c.setFont(TITLE_FONT_NAME, 13)
    c.setFillColor(NAVY)
    title = f"{month_name[month]}"
    # Separar más el título del encabezado de días
    c.drawCentredString(x0 + box_w / 2, y0 - 8, title)

    # Días de la semana
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cell_w = box_w / 7
    header_h = 48  # espacio para título + encabezados
    bottom_padding = 10
    available_h = max(12, box_h - header_h - bottom_padding)
    cell_h = available_h / 6  # 6 filas fijas para alinear meses
    c.setFont(FONT_NAME, 8)
    c.setFillColor(colors.black)
    for i, wd in enumerate(weekdays):
        c.drawString(x0 + i * cell_w + 1, y0 - 28, wd)

    # Días numéricos con cuadrícula fija de 6 semanas
    weeks = calendar.monthcalendar(YEAR, month)  # lista de semanas (valores 0 si fuera de mes)
    # Siempre usar exactamente 6 filas para alinear
    while len(weeks) < 6:
        weeks.append([0, 0, 0, 0, 0, 0, 0])
    y_start = y0 - header_h
    c.setFont(FONT_NAME, DAY_FONT_SIZE)
    for row_idx_weeks in range(6):
        week = weeks[row_idx_weeks]
        y = y_start - row_idx_weeks * cell_h
        for wd, day in enumerate(week):
            if day == 0:
                continue
            x_left = x0 + wd * cell_w + 1
            cx = x0 + wd * cell_w + (cell_w / 2.0)
            day_str = f"{day:02}"
            # Fondo para domingos: resaltar sólo detrás del número (píldora)
            if wd == 6:
                font_size = DAY_FONT_SIZE
                ascent = pdfmetrics.getAscent(FONT_NAME) * font_size / 1000.0
                descent = abs(pdfmetrics.getDescent(FONT_NAME)) * font_size / 1000.0
                text_w = pdfmetrics.stringWidth(day_str, FONT_NAME, font_size)
                rect_w = text_w + 2 * SUNDAY_PAD_X
                rect_h = ascent + descent + 2 * SUNDAY_PAD_Y
                rect_x = cx - (rect_w / 2.0)
                rect_y = y - (descent + SUNDAY_PAD_Y)
                c.setFillColor(SUNDAY_BG)
                c.roundRect(rect_x, rect_y, rect_w, rect_h, PILL_RADIUS, stroke=0, fill=1)

            # Fondo para sábados: píldora suave
            if wd == 5:
                font_size = DAY_FONT_SIZE
                ascent = pdfmetrics.getAscent(FONT_NAME) * font_size / 1000.0
                descent = abs(pdfmetrics.getDescent(FONT_NAME)) * font_size / 1000.0
                text_w = pdfmetrics.stringWidth(day_str, FONT_NAME, font_size)
                rect_w = text_w + 2 * SATURDAY_PAD_X
                rect_h = ascent + descent + 2 * SATURDAY_PAD_Y
                rect_x = cx - (rect_w / 2.0)
                rect_y = y - (descent + SATURDAY_PAD_Y)
                c.setFillColor(SATURDAY_BG)
                c.roundRect(rect_x, rect_y, rect_w, rect_h, PILL_RADIUS, stroke=0, fill=1)

            # Resaltar festivos: dibujar un recuadro centrado respecto al texto
            current_dt = date(YEAR, month, day)
            if current_dt in HOLIDAYS:
                font_size = DAY_FONT_SIZE
                ascent = pdfmetrics.getAscent(FONT_NAME) * font_size / 1000.0
                descent = abs(pdfmetrics.getDescent(FONT_NAME)) * font_size / 1000.0
                text_w = pdfmetrics.stringWidth(day_str, FONT_NAME, font_size)
                pad = 2.0
                rect_w = text_w + 2 * pad
                rect_h = ascent + descent + 2 * pad
                rect_x = cx - (rect_w / 2.0)
                rect_y = y - (descent + pad) + HOLIDAY_RECT_VOFFSET
                c.setStrokeColor(NAVY)
                c.setLineWidth(0.8)
                c.rect(rect_x, rect_y, rect_w, rect_h, stroke=1, fill=0)

            # Color del número para contraste
            if wd == 6:  # Sunday
                c.setFillColor(SUNDAY_TEXT)
            elif wd == 5:  # Saturday
                c.setFillColor(SATURDAY_TEXT)
            else:
                c.setFillColor(colors.black)
            c.drawCentredString(cx, y, day_str)

    # Línea inferior
    # Sin línea inferior para un look más limpio

# ======================== CABECERA DE AÑO ========================
def draw_year_header(c: canvas.Canvas) -> None:
    """Draw the year header centered at the top of the rotated (landscape) area."""
    c.setFont(TITLE_FONT_NAME, YEAR_TITLE_FONT_SIZE)
    c.setFillColor(NAVY)
    year_text = str(YEAR)
    # Colocar el año centrado verticalmente en el margen superior
    top_y = PAGE_HEIGHT - TOP_MARGIN
    header_y = top_y - YEAR_HEADER_SPACE / 2.0
    c.drawCentredString(PAGE_WIDTH / 2.0, header_y, year_text)


def draw_year_side_label(c: canvas.Canvas) -> None:
    """Draw a tall year label along the outer edge (portrait right side after rotation)."""
    c.saveState()
    c.setFillColor(NAVY)
    # After rotation, outer edge is at x = PAGE_WIDTH - SIDE_MARGIN
    # Place the year very close to the outer edge and nudge toward the first row
    x = PAGE_WIDTH - YEAR_SIDE_EDGE_INSET
    y = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / 2.0 + YEAR_SIDE_Y_OFFSET
    c.translate(x, y)
    # Rotate so text reads upright when page is viewed vertically
    c.rotate(270)
    # Larger size to fill the side whitespace
    c.setFont(TITLE_FONT_NAME, 34)
    c.drawCentredString(0, 0, str(YEAR))
    c.restoreState()

# ======================== LEYENDA ========================
def draw_holiday_legend(c: canvas.Canvas, months_on_page: List[int]) -> None:
    """Draw holiday legend filtered to the months present on this rotated page."""
    # Filtrar festivos por los meses mostrados en esta página
    page_holidays = [(d, name) for d, name in HOLIDAYS.items() if d.month in months_on_page]
    if not page_holidays:
        return
    # Orden cronológico
    page_holidays.sort(key=lambda x: x[0])
    parts = [f"{name} ({d.strftime('%b %d')})" for d, name in page_holidays]
    legend_text = "Holidays: " + ", ".join(parts)
    # Place legend safely within margins (avoid KDP flags) and wrap to multiple lines
    c.setFillColor(NAVY)
    margin_x = SIDE_MARGIN + 12
    # Move legend closer to the calendars while staying inside safe area
    y = BOTTOM_MARGIN + 18
    safe_w = max(60.0, PAGE_WIDTH - 2 * SIDE_MARGIN - 24)
    font_size = 7.5
    # Wrap text to safe width
    def wrap(text: str) -> list[str]:
        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if not cur:
                cur = w
                continue
            if pdfmetrics.stringWidth(test, FONT_NAME, font_size) <= safe_w:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    lines = wrap(legend_text)
    c.setFont(FONT_NAME, font_size)
    line_gap = font_size + 2
    for i, line in enumerate(lines):
        c.drawString(margin_x, y + i * line_gap, line)


# ======================== UTIL ========================
def save_metadata_json(path: str, metadata: Dict) -> None:
    """Save metadata to a JSON file.

    Args:
        path: Output JSON path.
        metadata: Serializable dictionary to save.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

# ======================== SEPARADORES DE COLUMNAS ========================
# (Separadores eliminados a petición del usuario)
# ======================== EJECUCIÓN ========================

def main() -> None:
    """CLI entrypoint to generate the annual calendar PDF.

    Supports custom year/output and optional JSON metadata export.
    """
    colorama_init(autoreset=True)
    global YEAR, OUTPUT_FILE, HOLIDAYS, SECOND_ROW_VSHIFT
    parser = argparse.ArgumentParser(description="Generate annual calendar PDF for KDP")
    parser.add_argument("--year", type=int, default=YEAR, help="Year to render (default: 2025)")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="Output PDF path")
    parser.add_argument("--second-row-vshift", type=float, default=SECOND_ROW_VSHIFT, help="Extra vertical shift for row 2 (points)")
    parser.add_argument("--no-legend", action="store_true", help="Do not print the holiday legend")
    parser.add_argument("--export-json", type=str, default="", help="Optional path to export metadata JSON")
    parser.add_argument("--size", type=str, choices=["a5", "6x9"], default="a5", help="Trim size (affects page size)")
    parser.add_argument("--auto", action="store_true", help="Enable non-interactive mode (no effect, for consistency)")
    args = parser.parse_args()

    start = time.time()
    print(Fore.CYAN + "[KDP] Generating annual calendar…")

    # Actualizar configuración global según argumentos
    YEAR = args.year
    OUTPUT_FILE = args.output
    SECOND_ROW_VSHIFT = args.second_row_vshift
    global SIZE
    SIZE = args.size
    HOLIDAYS = build_western_holidays(YEAR)

    # Always create a portrait A5 page; rotate content per page
    pagesize = A5 if args.size == "a5" else (6 * 72.0, 9 * 72.0)
    c = canvas.Canvas(OUTPUT_FILE, pagesize=pagesize)
    draw_annual_calendar(c, show_legend=(not args.no_legend))
    c.save()

    elapsed = time.time() - start
    print(Fore.GREEN + f"Calendario anual expandido generado: {OUTPUT_FILE}" + Style.RESET_ALL)
    print(Fore.YELLOW + f"Duración: {elapsed:.2f}s")

    if args.export_json:
        metadata = {
            "year": YEAR,
            "output_pdf": OUTPUT_FILE,
            "pages": 2,
            "months_per_page": [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        save_metadata_json(args.export_json, metadata)
        print(Fore.CYAN + f"Metadata JSON saved: {args.export_json}")


if __name__ == "__main__":
    main()
