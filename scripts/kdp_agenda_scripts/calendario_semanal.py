from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import calendar
import os
from datetime import date, timedelta
import argparse
import csv
import json
from typing import Iterator, List, Tuple, Optional
from dataclasses import dataclass
from colorama import Fore, Style, init as colorama_init


# ======================== CONFIG ========================
# Cambiar a orientación vertical (portrait)
PAGE_WIDTH, PAGE_HEIGHT = A5
TOP_MARGIN = 36
BOTTOM_MARGIN = 36
# Increase margins to satisfy KDP minimums (>=0.375" inside, >=0.25" outside)
SIDE_MARGIN = 36

NAVY = colors.HexColor("#002147")
SUNDAY_BG = colors.HexColor("#E0ECFA")
SATURDAY_BG = colors.HexColor("#F5F8FC")
SUNDAY_TEXT = colors.white
SATURDAY_TEXT = NAVY

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "weekly_agenda_2025.pdf")

# Fonts
try:
    # Prefer system fonts for embedding
    pdfmetrics.registerFont(TTFont("Arial", r"C:\\Windows\\Fonts\\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\\Windows\\Fonts\\arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\\Windows\\Fonts\\ariali.ttf"))
    FONT_NAME = "Arial"
    TITLE_FONT = "Arial-Bold"
    ITALIC_FONT = "Arial-Italic"
except Exception:
    # Fallback to built-ins
    FONT_NAME = "Helvetica"
TITLE_FONT = "Helvetica-Bold"
    ITALIC_FONT = "Helvetica-Oblique"

YEAR = 2025


# ======================== QUOTES & MUSIC ========================
QUOTES = [
    ("Without music, life would be a mistake.", "Friedrich Nietzsche"),
    ("Music expresses that which cannot be put into words.", "Victor Hugo"),
    ("Where words fail, music speaks.", "Hans Christian Andersen"),
    ("One good thing about music, when it hits you, you feel no pain.", "Bob Marley"),
    ("Music can change the world because it can change people.", "Bono"),
    ("After silence, that which comes nearest to expressing the inexpressible is music.", "Aldous Huxley"),
    ("Music is the shorthand of emotion.", "Leo Tolstoy"),
    ("Music is the strongest form of magic.", "Marilyn Manson"),
]

MUSIC_RECS = [
    ("No Surprises", "Radiohead"),
    ("Exit Music (For a Film)", "Radiohead"),
    ("Clair de Lune", "Claude Debussy"),
    ("Nuvole Bianche", "Ludovico Einaudi"),
    ("Come Together", "The Beatles"),
    ("Here Comes the Sun", "The Beatles"),
    ("Nocturne Op.9 No.2", "Chopin"),
    ("Gymnopedie No.1", "Erik Satie"),
    ("Time", "Hans Zimmer"),
    ("Experience", "Ludovico Einaudi"),
    ("So What", "Miles Davis"),
    ("Reckoner", "Radiohead"),
]

# Varying intros for the weekly music recommendation
MUSIC_INTROS = [
    "A tune to light up your week",
    "Soundtrack for your week",
    "Set the tone this week with",
    "Your weekly spark",
    "A sonic pick for the days ahead",
    "Press play and begin",
    "A classic to revisit",
    "A record for focus and flow",
    "An album to unwind to",
    "Let this lead your week",
    "Vibes for the journey",
    "Music to kick things off",
    "Turn this on and get moving",
    "A gentle push to start the week",
    "Fuel for thought and focus",
    "Something timeless for your days",
    "A spark for your mornings",
    "Evening companion for unwinding",
    "A soundtrack for deep work",
    "Mood-setter for the week ahead",
    "Play this while planning",
    "A groove to keep you going",
    "Rhythms for clear thinking",
    "Quiet confidence in album form",
    "A modern classic to revisit",
    "An easy lift for any day",
    "Something bright and spacious",
    "For rainy mornings and sunny afternoons",
    "A comforting listen for busy weeks",
    "Textured, patient, and rewarding",
    "Minimal, melodic, memorable",
    "For focus, flow, and calm",
    "A record that reveals itself",
    "Crisp, warm, and human",
    "Energy without the rush",
    "Lean in and let it play",
    "A pulse to organize your day",
    "Unfussy, honest, enduring",
    "Headphones on, world off",
    "A soundtrack for quiet ambition",
    "Take five and press play",
    "Play it loud, think softly",
    "A gentle nudge toward momentum",
    "Steady rhythms, steady progress",
    "A favorite for long stretches",
    "Let this one breathe in the background",
    "Warmth for colder minutes",
    "A measured stride in album form",
    "Soft edges, sharp ideas",
    "Keep this close this week",
]


# ======================== MUSIC TYPES & API ========================
@dataclass(frozen=True)
class MusicRecommendation:
    """A single weekly music recommendation.

    Attributes:
        intro: Short intro phrase preceding the song name.
        song: Song title (or album/track label).
        artist: Artist or composer name.
    """
    intro: str
    song: str
    artist: str


def get_default_music_recommendation(week_index: int, year: int) -> MusicRecommendation:
    """Return a deterministic, built-in music recommendation.

    The content is selected from the static lists in this module and must not
    change, but the selection mechanism can rotate by week/year.
    """
    song, artist = MUSIC_RECS[week_index % len(MUSIC_RECS)]
    intro = MUSIC_INTROS[(year * 100 + week_index) % len(MUSIC_INTROS)]
    return MusicRecommendation(intro=intro, song=song, artist=artist)


def build_default_music_schedule(year: int, weeks_total: int) -> List[MusicRecommendation]:
    """Build a default recommendation schedule for all weeks of a year."""
    return [get_default_music_recommendation(i, year) for i in range(weeks_total)]


def load_music_schedule_json(path: str) -> List[MusicRecommendation]:
    """Load a weekly music schedule from a JSON file.

    The JSON should be an array of objects with ``intro``, ``song``, ``artist``.
    """
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)
    schedule: List[MusicRecommendation] = []
    for it in items:
        schedule.append(MusicRecommendation(intro=str(it["intro"]), song=str(it["song"]), artist=str(it["artist"])) )
    return schedule


def load_music_schedule_csv(path: str) -> List[MusicRecommendation]:
    """Load a weekly music schedule from a CSV file.

    Expected columns: ``intro,song,artist``. Extra columns are ignored.
    """
    schedule: List[MusicRecommendation] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schedule.append(MusicRecommendation(intro=str(row.get("intro", "")), song=str(row.get("song", "")), artist=str(row.get("artist", ""))))
    return schedule


def export_music_schedule_json(path: str, year: int, spans: List[Tuple[date, date]], schedule: List[MusicRecommendation]) -> None:
    """Export a weekly schedule as JSON with dates."""
    out = []
    for idx, ((d_start, d_end), rec) in enumerate(zip(spans, schedule)):
        out.append({
            "index": idx,
            "iso_week": (d_start.isocalendar()[1]),
            "start": d_start.isoformat(),
            "end": d_end.isoformat(),
            "intro": rec.intro,
            "song": rec.song,
            "artist": rec.artist,
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"year": year, "weeks": out}, f, indent=2)


def export_music_schedule_csv(path: str, spans: List[Tuple[date, date]], schedule: List[MusicRecommendation]) -> None:
    """Export a weekly schedule as CSV with dates."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "iso_week", "start", "end", "intro", "song", "artist"])
        for idx, ((d_start, d_end), rec) in enumerate(zip(spans, schedule)):
            writer.writerow([idx, d_start.isocalendar()[1], d_start.isoformat(), d_end.isoformat(), rec.intro, rec.song, rec.artist])


# ======================== WEEK UTILS ========================
def weeks_in_year(year: int) -> Iterator[Tuple[date, date]]:
    """Yield (monday, sunday) tuples covering all weeks of the year.

    Weeks are Monday..Sunday. The first week starts on the Monday on/before Jan 1,
    and the last week ends on the Sunday on/after Dec 31, so the agenda covers
    any spillover days from adjacent years.
    """
    jan1 = date(year, 1, 1)
    dec31 = date(year, 12, 31)
    start = jan1 - timedelta(days=(jan1.weekday()))  # Monday <= Jan1
    end = dec31 + timedelta(days=(6 - dec31.weekday()))  # Sunday >= Dec31
    cur = start
    while cur <= end:
        yield cur, cur + timedelta(days=6)
        cur += timedelta(days=7)


# ======================== DRAWING ========================
def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if not current:
            current = w
            continue
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_w: float, *, font: str, size: int, line_gap: float, max_lines: Optional[int] = None) -> int:
    lines = _wrap_text(text, font, size, max_w)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_gap, line)
    return len(lines)


def draw_week_spread(c: canvas.Canvas, week_idx: int, d_start: date, d_end: date, music: MusicRecommendation, quote_override: Optional[Tuple[str, str]] = None) -> None:
    """Draw two pages for a full week: left (Mon-Thu), right (Fri-Sun + notes).

    The music recommendation is passed explicitly for modularity.
    """

    # Common header text
    iso_week = d_start.isocalendar()[1]
    header_text = f"Week {iso_week}  —  {d_start.strftime('%b %d')} – {d_end.strftime('%b %d, %Y')}"

    # Choose quote and music for this week
    if quote_override is not None:
        q_text, q_author = quote_override
    else:
    q_text, q_author = QUOTES[week_idx % len(QUOTES)]
    intro = music.intro
    song = music.song
    artist = music.artist

    # -------- Left page (Mon..Thu) --------
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, header_text)

    # Shared vertical rhythm so Monday aligns with Friday and Thu with Notes
    y_hdr = PAGE_HEIGHT - TOP_MARGIN
    top_offset_base = 56
    y_start_left = PAGE_HEIGHT - TOP_MARGIN - top_offset_base
    usable_h_total = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - top_offset_base
    day_box_h_right = usable_h_total * 0.58 / 3.0
    notes_box_h = usable_h_total - day_box_h_right * 3.0
    # Left side: 4 boxes must equal height of right 3 boxes
    day_box_h_left = max(24.0, (day_box_h_right * 3.0) / 4.0)
    box_w = PAGE_WIDTH - 2 * SIDE_MARGIN

    # Quote block centered between header and Monday box top (mirrors music block)
    if q_author and str(q_author).strip():
    quote_line = f"“{q_text}” — {q_author}"
    else:
        quote_line = f"“{q_text}” — Anonymous"
    qb_x = SIDE_MARGIN
    qb_w = PAGE_WIDTH - 2 * SIDE_MARGIN
    inner_pad = 6
    quote_font = FONT_NAME
    quote_size = 10
    quote_line_gap = quote_size + 2
    q_lines = _wrap_text(quote_line, quote_font, quote_size, qb_w - 2 * inner_pad)
    qb_h = 8 + len(q_lines) * quote_line_gap + 6
    mid_gap = (y_hdr + y_start_left) / 2.0
    qb_y = min(y_start_left - 6 - qb_h, mid_gap - qb_h / 2.0)

    # Draw the four day boxes with unified height
    for i in range(4):
        day_dt = d_start + timedelta(days=i)
        y_top = y_start_left - i * day_box_h_left
        draw_day_box(c, day_dt, SIDE_MARGIN, y_top - day_box_h_left, box_w, day_box_h_left)

    # Draw quote text (no border)
    c.setFont(quote_font, quote_size)
    c.setFillColor(colors.black)
    text_x = qb_x + inner_pad
    text_y = qb_y + qb_h - inner_pad - 2
    _draw_wrapped(c, quote_line, text_x, text_y, qb_w - 2 * inner_pad, font=quote_font, size=quote_size, line_gap=quote_line_gap, max_lines=None)

    c.showPage()  # move to right page of the spread

    # -------- Right page (Fri..Sun + Notes + Mini month) --------
    c.setFont(TITLE_FONT, 14)
    c.setFillColor(NAVY)
    c.drawString(SIDE_MARGIN, PAGE_HEIGHT - TOP_MARGIN, header_text)

    # Music recommendation box (right page only) – compute dynamic height with styled parts
    mb_x = SIDE_MARGIN
    mb_w = PAGE_WIDTH - 2 * SIDE_MARGIN
    gap_x = 8  # spacing used later near the notes box
    m_pad = 6
    music_size = 10
    music_gap = music_size + 2

    intro_text = f"{intro}: "
    song_text = song
    by_text = f" by {artist}"
    intro_font = TITLE_FONT            # bold
    song_font = ITALIC_FONT            # italic
    by_font = TITLE_FONT               # bold

    available_w = mb_w - 2 * m_pad
    intro_w = pdfmetrics.stringWidth(intro_text, intro_font, music_size)
    song_w = pdfmetrics.stringWidth(song_text, song_font, music_size)
    by_w = pdfmetrics.stringWidth(by_text, by_font, music_size)

    single_line = intro_w + song_w + by_w <= available_w
    if single_line:
        music_lines_count = 1
    else:
        song_wrapped = _wrap_text(song_text, song_font, music_size, available_w)
        song_wrapped = song_wrapped[:2]
        music_lines_count = 1 + len(song_wrapped) + 1  # intro + song lines + by line
    mb_h = 8 + music_lines_count * music_gap + 4
    # Center the music text between page title and top of Friday box
    y_hdr = PAGE_HEIGHT - TOP_MARGIN
    top_offset_base = 56
    y_fri_top = PAGE_HEIGHT - TOP_MARGIN - top_offset_base
    mid_music = (y_hdr + y_fri_top) / 2.0
    mb_y = mid_music - mb_h / 2.0
    # Draw music text with styles: intro (bold), song (italic), by artist (bold)
    # Center horizontally within mb_x..mb_x+mb_w
    text_y_m = mb_y + mb_h - m_pad - 2
    c.setFillColor(NAVY)
    center_x = mb_x + mb_w / 2.0
    if single_line:
        # Center the full composed line
        total_w = intro_w + song_w + by_w
        start_x = center_x - total_w / 2.0
        c.setFont(intro_font, music_size)
        c.drawString(start_x, text_y_m, intro_text)
        c.setFont(song_font, music_size)
        c.drawString(start_x + intro_w, text_y_m, song_text)
        c.setFont(by_font, music_size)
        c.drawString(start_x + intro_w + song_w, text_y_m, by_text)
    else:
        # Line 1: intro centered
        c.setFont(intro_font, music_size)
        intro_x = center_x - intro_w / 2.0
        c.drawString(intro_x, text_y_m, intro_text)
        # Wrapped song lines, each centered
        y_cursor = text_y_m - music_gap
        song_wrapped = _wrap_text(song_text, song_font, music_size, available_w)
        song_wrapped = song_wrapped[:2]
        for part in song_wrapped:
            part_w = pdfmetrics.stringWidth(part, song_font, music_size)
            c.setFont(song_font, music_size)
            c.drawString(center_x - part_w / 2.0, y_cursor, part)
            y_cursor -= music_gap
        # Last line: by artist centered
        by_w2 = pdfmetrics.stringWidth(by_text, by_font, music_size)
        c.setFont(by_font, music_size)
        c.drawString(center_x - by_w2 / 2.0, y_cursor, by_text)

    # 3 stacked boxes for Fri..Sun then big Notes
    # Start Friday boxes at fixed offset from header; the music block is centered in that gap
    top_offset = top_offset_base
    usable_h_right = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - top_offset
    day_box_h = usable_h_total * 0.58 / 3.0  # match computation used on left
    notes_box_h = usable_h_right - day_box_h * 3  # remaining to notes
    box_w_right = PAGE_WIDTH - 2 * SIDE_MARGIN

    for i in range(3):
        day_dt = d_start + timedelta(days=4 + i)
        y_top = PAGE_HEIGHT - TOP_MARGIN - top_offset - i * day_box_h
        draw_day_box(c, day_dt, SIDE_MARGIN, y_top - day_box_h, box_w_right, day_box_h)

    # Notes box and mini month aligned horizontally and split 50/50
    y_notes_top = PAGE_HEIGHT - TOP_MARGIN - top_offset - 3 * day_box_h
    # Choose month from the middle day of the week
    mid_dt = d_start + timedelta(days=3)
    full_w = box_w_right
    w_notes = (full_w - gap_x) / 2.0
    mini_w = full_w - w_notes - gap_x  # same as w_notes
    # Slightly smaller than notes height so it can sit comfortably centered
    mini_h = notes_box_h * 0.8
    # Draw notes on the left half
    draw_notes_box(c, SIDE_MARGIN, y_notes_top - notes_box_h, w_notes, notes_box_h, title="Notes")
    # Mini calendar on the right half
    mini_x = SIDE_MARGIN + w_notes + gap_x
    # Place lower within the notes area to maximize clearance above
    mini_y = y_notes_top - notes_box_h + 10
    draw_mini_month(c, mid_dt.year, mid_dt.month, mini_x, mini_y, mini_w, mini_h, highlight_week_range=(d_start, d_end))

    c.showPage()


def draw_day_box(c: canvas.Canvas, day_dt: date, x: float, y: float, w: float, h: float) -> None:
    # Background for weekends as light pill behind date text area only
    weekday = day_dt.weekday()  # Mon=0..Sun=6
    # Border box
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=0)

    # Header line
    name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday]
    header = f"{name}  {day_dt.strftime('%b %d')}"

    c.setFont(TITLE_FONT, 11)
    c.setFillColor(NAVY)
    c.drawString(x + 6, y + h - 12, header)

    # Weekend highlight pill behind date text
    if weekday in (5, 6):
        text_w = pdfmetrics.stringWidth(header, TITLE_FONT, 11)
        pill_w = text_w + 10
        pill_h = 12
        pill_x = x + 4
        pill_y = y + h - 16
        c.setFillColor(SATURDAY_BG if weekday == 5 else SUNDAY_BG)
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 3, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.setFont(TITLE_FONT, 11)
        c.drawString(x + 6, y + h - 12, header)

    # Ruled lines for writing (fewer lines, more spacing)
    c.setStrokeColor(colors.HexColor("#D9E2EF"))
    c.setLineWidth(0.4)
    top = y + h - 26
    bottom = y + 12
    line_gap = 11.0
    yy = top
    while yy > bottom:
        c.line(x + 6, yy, x + w - 6, yy)
        yy -= line_gap


def draw_notes_box(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str = "Notes") -> None:
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=0)
    c.setFont(TITLE_FONT, 11)
    c.setFillColor(NAVY)
    c.drawString(x + 6, y + h - 12, title)
    # Lines
    c.setStrokeColor(colors.HexColor("#D9E2EF"))
    c.setLineWidth(0.4)
    top = y + h - 20
    bottom = y + 8
    # Match line spacing with day boxes
    line_gap = 11.0
    yy = top
    while yy > bottom:
        c.line(x + 6, yy, x + w - 6, yy)
        yy -= line_gap


# Mini monthly calendar (compact)
def draw_mini_month(c: canvas.Canvas, year: int, month: int, x: float, y: float, w: float, h: float, highlight_week_range: Tuple[date, date] | None = None) -> None:
    """Draw a compact month calendar into the rectangle (x,y,w,h).

    (x, y) is bottom-left. Uses 7 columns x 6 rows grid with a tiny header.
    """
    # Dynamic sizing based on available height
    title_font_size = max(11.0, min(16.0, h * 0.11))
    weekday_font_size = max(8.0, min(12.0, h * 0.075))
    num_font_size = max(9.0, min(13.0, h * 0.095))

    # Header: Month name centered
    title_h = title_font_size + 6
    # Increase separation to avoid any visual tightness
    title_sep = max(10.0, title_font_size * 0.85)  # extra spacing between title and weekday header
    c.setFont(TITLE_FONT, title_font_size)
    c.setFillColor(NAVY)
    month_name = calendar.month_name[month]
    c.drawCentredString(x + w / 2.0, y + h - title_h + 3, f"{month_name} {year}")

    # Weekday header
    weekdays = ["M", "T", "W", "T", "F", "S", "S"]
    grid_h = h - title_h - title_sep - 6
    cell_w = w / 7.0
    cell_h = grid_h / 7.0  # 1 row for weekday header + 6 weeks

    c.setFont(FONT_NAME, weekday_font_size)
    c.setFillColor(colors.black)
    header_y = y + h - title_h - title_sep
    for i, wd in enumerate(weekdays):
        c.drawCentredString(x + i * cell_w + cell_w / 2.0, header_y, wd)

    # Weeks data (always 6 rows)
    weeks = calendar.monthcalendar(year, month)
    while len(weeks) < 6:
        weeks.append([0, 0, 0, 0, 0, 0, 0])

    # Optional: highlight current week row
    if highlight_week_range is not None:
        start_h, end_h = highlight_week_range
        c.setFillColor(colors.HexColor("#EDF3FE"))
        for row_idx, week in enumerate(weeks):
            # If any valid day in this row intersects the highlight range
            intersects = False
            for wd, d in enumerate(week):
                if d == 0:
                    continue
                dt = date(year, month, d)
                if start_h <= dt <= end_h:
                    intersects = True
                    break
            if intersects:
                # fill behind the 7 day cells
                row_y = header_y - cell_h + 2 - row_idx * cell_h
                c.roundRect(x + 1, row_y - 2, w - 2, cell_h - 2, 3, stroke=0, fill=1)

    # Draw numbers
    c.setFont(FONT_NAME, num_font_size)
    y0 = header_y - cell_h + 2
    for row_idx in range(6):
        week = weeks[row_idx]
        yy = y0 - row_idx * cell_h
        for wd, day in enumerate(week):
            if day == 0:
                continue
            cx = x + wd * cell_w + cell_w / 2.0
            day_str = f"{day:02}"
            # Weekend coloring; Sunday with light pill, Saturday navy text
            if wd == 6:
                ascent = pdfmetrics.getAscent(FONT_NAME) * num_font_size / 1000.0
                descent = abs(pdfmetrics.getDescent(FONT_NAME)) * num_font_size / 1000.0
                text_w = pdfmetrics.stringWidth(day_str, FONT_NAME, num_font_size)
                pad_x = 0.26 * num_font_size
                pad_y = 0.22 * num_font_size
                rect_w = text_w + 2 * pad_x
                rect_h = ascent + descent + 2 * pad_y
                rect_x = cx - rect_w / 2.0
                rect_y = yy - descent
                c.setFillColor(SUNDAY_BG)
                c.roundRect(rect_x, rect_y, rect_w, rect_h, 0.22 * num_font_size, stroke=0, fill=1)
                c.setFillColor(SUNDAY_TEXT)
            elif wd == 5:
                c.setFillColor(SATURDAY_TEXT)
            else:
                c.setFillColor(colors.black)
            c.drawCentredString(cx, yy, day_str)

# ======================== MAIN ========================

def main() -> None:
    """Generate the weekly agenda PDF with optional music schedule I/O."""
    colorama_init(autoreset=True)
    global YEAR, OUTPUT_FILE
    parser = argparse.ArgumentParser(description="Generate weekly agenda PDF (KDP)")
    parser.add_argument("--year", type=int, default=YEAR, help="Year to render (default: 2025)")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="Output PDF path")
    parser.add_argument("--load-music-json", type=str, default="", help="Optional JSON schedule to load (intro/song/artist)")
    parser.add_argument("--load-music-csv", type=str, default="", help="Optional CSV schedule to load (intro,song,artist)")
    parser.add_argument("--genre", type=str, default="", help="Optional genre name to select a profile from music_profiles/<genre>.json|csv")
    parser.add_argument("--music-profile-json", type=str, default="", help="Explicit music profile JSON path (overrides --genre)")
    parser.add_argument("--music-profile-csv", type=str, default="", help="Explicit music profile CSV path (overrides --genre)")
    parser.add_argument("--export-music-json", type=str, default="", help="Export default music schedule JSON")
    parser.add_argument("--export-music-csv", type=str, default="", help="Export default music schedule CSV")
    parser.add_argument("--auto", action="store_true", help="Non-interactive mode (placeholder flag)")
    args = parser.parse_args()

    YEAR = args.year
    OUTPUT_FILE = args.output

    spans = list(weeks_in_year(YEAR))

    # Load or build schedule
    schedule: Optional[List[MusicRecommendation]] = None
    # Highest precedence: explicit load flags
    if args.load_music_json:
        schedule = load_music_schedule_json(args.load_music_json)
    elif args.load_music_csv:
        schedule = load_music_schedule_csv(args.load_music_csv)
    # Next: explicit profile paths
    elif args.music_profile_json:
        schedule = load_music_schedule_json(args.music_profile_json)
    elif args.music_profile_csv:
        schedule = load_music_schedule_csv(args.music_profile_csv)
    # Next: genre lookup under music_profiles/
    elif args.genre:
        prof_dir = os.path.join(SCRIPT_DIR, "music_profiles")
        json_p = os.path.join(prof_dir, f"{args.genre}.json")
        csv_p = os.path.join(prof_dir, f"{args.genre}.csv")
        if os.path.exists(json_p):
            schedule = load_music_schedule_json(json_p)
        elif os.path.exists(csv_p):
            schedule = load_music_schedule_csv(csv_p)
    if schedule is None:
        schedule = build_default_music_schedule(YEAR, len(spans))

    # Export if requested
    if args.export_music_json:
        export_music_schedule_json(args.export_music_json, YEAR, spans, schedule)
    if args.export_music_csv:
        export_music_schedule_csv(args.export_music_csv, spans, schedule)

    c = canvas.Canvas(OUTPUT_FILE, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    for week_idx, (d_start, d_end) in enumerate(spans):
        rec = schedule[week_idx] if week_idx < len(schedule) else get_default_music_recommendation(week_idx, YEAR)
        draw_week_spread(c, week_idx, d_start, d_end, rec)
    c.save()
    print(Fore.GREEN + f"Weekly agenda generated: {OUTPUT_FILE}" + Style.RESET_ALL)


if __name__ == "__main__":
    main()


