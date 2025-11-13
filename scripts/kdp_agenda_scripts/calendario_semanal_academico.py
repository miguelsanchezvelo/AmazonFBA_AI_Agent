from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from typing import Iterator, Tuple, List, Optional
import os

from colorama import Fore, Style, init as colorama_init
from reportlab.pdfgen import canvas
import csv

# Reuse styles, page size, and drawing functions from the 2025 weekly agenda
from scripts.kdp_agenda_scripts import calendario_semanal as weekmod


def parse_iso(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def week_spans_covering(start: date, end: date) -> Iterator[Tuple[date, date]]:
    """Yield Monday..Sunday week spans that cover [start, end] inclusive."""
    # First Monday on/before start
    cur = start - timedelta(days=start.weekday())
    # Last Sunday on/after end
    last = end + timedelta(days=(6 - end.weekday()))
    while cur <= last:
        yield cur, cur + timedelta(days=6)
        cur += timedelta(days=7)


def _load_unique_quotes(path: str) -> List[Tuple[str, str]]:
    """Load unique quotes from CSV with columns: quote,author.

    This loader is robust to commas inside the quote text by taking the last
    column as the author and joining all preceding columns as the quote text.

    Args:
        path: CSV file path.

    Returns:
        List of (quote, author) tuples.
    """
    out: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # Skip header if present
            if len(row) >= 2 and row[0].strip().lower() == "quote" and row[-1].strip().lower() == "author":
                continue
            if len(row) == 1:
                q = row[0].strip()
                a = ""
            else:
                a = row[-1].strip()
                q = ",".join(col.strip() for col in row[:-1]).strip()
            if q:
                out.append((q, a))
    return out


def _load_unique_music(path: str) -> List[weekmod.MusicRecommendation]:
    """Load unique music from CSV with columns: intro,song,artist

    Args:
        path: CSV file path.

    Returns:
        List of MusicRecommendation entries.
    """
    out: List[weekmod.MusicRecommendation] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            intro = str(row.get("intro", "")).strip()
            song = str(row.get("song", "")).strip()
            artist = str(row.get("artist", "")).strip()
            if song and artist:
                if not intro:
                    intro = weekmod.MUSIC_INTROS[len(out) % len(weekmod.MUSIC_INTROS)]
                out.append(weekmod.MusicRecommendation(intro=intro, song=song, artist=artist))
    return out


def main() -> None:
    colorama_init(autoreset=True)
    parser = argparse.ArgumentParser(description="Generate academic weekly agenda PDF for a custom date range")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--size",
        choices=["a5", "6x9"],
        default="a5",
        help="Trim size: 'a5' (default) or '6x9' inches",
    )
    parser.add_argument("--quotes-csv", type=str, default="", help="CSV path with unique quotes: quote,author")
    parser.add_argument("--music-csv", type=str, default="", help="CSV path with unique music: intro,song,artist")
    # Default to project root weekly filename style
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    default_out = os.path.join(root_dir, "weekly_agenda_2025_2026.pdf")
    parser.add_argument("--output", default=default_out, help="Output PDF path")
    args = parser.parse_args()

    start = parse_iso(args.start)
    end = parse_iso(args.end)
    if end < start:
        raise SystemExit("End date must be >= start date")

    print(Fore.CYAN + f"[KDP] Generating academic weekly agenda: {start} → {end} ({args.size})")

    # Adjust base page size in the imported weekly module
    if args.size == "6x9":
        weekmod.PAGE_WIDTH = 6 * 72  # 432 pt
        weekmod.PAGE_HEIGHT = 9 * 72  # 648 pt

    # Load unique datasets if provided
    quotes: Optional[List[Tuple[str, str]]] = None
    music_list: Optional[List[weekmod.MusicRecommendation]] = None
    if args.quotes_csv:
        quotes = _load_unique_quotes(args.quotes_csv)
    if args.music_csv:
        music_list = _load_unique_music(args.music_csv)

    # Prepare uniqueness enforcement
    used_songs: set[str] = set()
    used_quotes: set[str] = set()
    synth_music_counter = 1
    synth_quote_counter = 1

    # Simple fallback quote templates to guarantee uniqueness if needed
    quote_templates: List[str] = [
        "Small steps every day lead to big changes.",
        "Plan with purpose, act with clarity.",
        "Consistency compounds into excellence.",
        "Focus turns time into progress.",
        "Begin where you are; use what you have.",
        "Direction is better than speed.",
        "Little by little becomes a lot.",
        "Energy flows where attention goes.",
        "Discipline is a form of self-respect.",
        "Clarity creates momentum.",
        "Show up, even on the small days.",
        "Your calendar is your blueprint.",
        "Progress over perfection.",
        "What gets scheduled gets done.",
        "Build the week you want to live.",
        "Focus on the next right thing.",
        "Routine is a powerful decision-saver.",
        "Momentum starts with a single task.",
        "Protect your peak hours.",
        "Finish the day with intention.",
    ]

    c = canvas.Canvas(args.output, pagesize=(weekmod.PAGE_WIDTH, weekmod.PAGE_HEIGHT))
    week_idx = 0
    for d_start, d_end in week_spans_covering(start, end):
        if d_end < start or d_start > end:
            continue
        # Select music: prefer CSV unique list if available
        if music_list is not None and week_idx < len(music_list):
            rec = music_list[week_idx]
        else:
            rec = weekmod.get_default_music_recommendation(week_idx, d_start.year)
        # Enforce music uniqueness by song title; if repeated, search next unused in defaults
        if rec.song in used_songs:
            # try to find an unused from defaults
            found = False
            for offset in range(len(weekmod.MUSIC_RECS)):
                cand_song, cand_artist = weekmod.MUSIC_RECS[(week_idx + offset) % len(weekmod.MUSIC_RECS)]
                if cand_song not in used_songs:
                    rec = weekmod.MusicRecommendation(
                        intro=rec.intro or weekmod.MUSIC_INTROS[(d_start.year * 100 + week_idx) % len(weekmod.MUSIC_INTROS)],
                        song=cand_song,
                        artist=cand_artist,
                    )
                    found = True
                    break
            if not found:
                # synthesize unique fallback
                rec = weekmod.MusicRecommendation(
                    intro=rec.intro or weekmod.MUSIC_INTROS[(d_start.year * 100 + week_idx) % len(weekmod.MUSIC_INTROS)],
                    song=f"Focus Track {synth_music_counter:02d}",
                    artist="Studio Ensemble",
                )
                synth_music_counter += 1
        used_songs.add(rec.song)

        # Select quote: prefer CSV unique list if available
        if quotes is not None and week_idx < len(quotes):
            quote_tuple = quotes[week_idx]
        else:
            base_q, base_a = weekmod.QUOTES[week_idx % len(weekmod.QUOTES)]
            quote_tuple = (base_q, base_a)
        # Enforce quote uniqueness by text; if repeated, pull next template or synthesize
        if quote_tuple[0] in used_quotes:
            # try from templates
            if synth_quote_counter <= len(quote_templates):
                q_text = quote_templates[synth_quote_counter - 1]
                q_author = ""
                synth_quote_counter += 1
                quote_tuple = (q_text, q_author)
            else:
                quote_tuple = (f"Keep going — Week {week_idx+1}", "")
        used_quotes.add(quote_tuple[0])

        weekmod.draw_week_spread(c, week_idx, d_start, d_end, rec, quote_override=quote_tuple)
        week_idx += 1
    c.save()
    print(Fore.GREEN + f"Academic weekly agenda generated: {args.output}" + Style.RESET_ALL)


if __name__ == "__main__":
    main()


