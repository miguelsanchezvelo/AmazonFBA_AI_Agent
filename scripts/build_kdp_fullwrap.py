from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Tuple

from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader


INCH = 72.0


@dataclass(frozen=True)
class TrimSize:
    """Represents a KDP trim size in inches and points.

    Attributes:
        width_in: Width in inches.
        height_in: Height in inches.
    """

    width_in: float
    height_in: float

    @property
    def width_pt(self) -> float:
        return self.width_in * INCH

    @property
    def height_pt(self) -> float:
        return self.height_in * INCH


TRIM_SIZES = {
    "6x9": TrimSize(6.0, 9.0),
}


def compute_spine_inches(page_count: int, paper: str) -> float:
    """Compute spine width in inches per KDP guidance.

    Args:
        page_count: Total number of pages in the interior PDF.
        paper: Paper type key; supported: 'white', 'cream', 'color'.

    Returns:
        Spine width in inches.
    """
    paper = paper.lower()
    if paper == "white":
        per_page = 0.002252
    elif paper == "cream":
        per_page = 0.0025
    elif paper == "color":
        per_page = 0.002347
    else:
        raise ValueError(f"Unsupported paper type: {paper}")
    return page_count * per_page


def draw_fullwrap_cover(
    output_pdf: str,
    *,
    trim: TrimSize,
    spine_in: float,
    front_image_path: str,
    bleed: bool = False,
    background_color: colors.Color | None = colors.white,
    spine_color: colors.Color | None = colors.HexColor("#CCCCCC"),
) -> Tuple[float, float, float]:
    """Render a simple full-wrap cover with blank back and provided front image.

    - Back: solid background color
    - Spine: solid spine color, no text
    - Front: front_image scaled to fit trim area (covering), centered

    Args:
        output_pdf: Destination path for the generated PDF.
        trim: Trim size.
        spine_in: Spine width in inches.
        front_image_path: Path to the front cover image (PNG/JPG).
        bleed: If True, adds 0.125" bleed on outer edges.
        background_color: Back cover background color.
        spine_color: Spine fill color.

    Returns:
        Tuple of (total_width_pt, total_height_pt, spine_pt).
    """
    # KDP recommends 0.125" bleed for all sides on cover
    bleed_in = 0.125 if bleed else 0.0
    spine_pt = spine_in * INCH
    # Total wrap dimensions (no barcode area reserved here; KDP places it if needed)
    total_w_in = trim.width_in * 2 + spine_in + bleed_in * 2
    total_h_in = trim.height_in + bleed_in * 2
    total_w_pt = total_w_in * INCH
    total_h_pt = total_h_in * INCH

    c = canvas.Canvas(output_pdf, pagesize=(total_w_pt, total_h_pt))

    # Background
    if background_color is not None:
        c.setFillColor(background_color)
        c.rect(0, 0, total_w_pt, total_h_pt, stroke=0, fill=1)

    # Regions (from left to right): back | spine | front
    back_x = 0.0
    back_w = trim.width_pt + bleed_in * INCH

    spine_x = back_x + back_w
    spine_w = spine_pt

    front_x = spine_x + spine_w
    front_w = trim.width_pt + bleed_in * INCH

    # Spine block
    if spine_color is not None:
        c.setFillColor(spine_color)
        c.rect(spine_x, 0, spine_w, total_h_pt, stroke=0, fill=1)

    # Draw front image to cover the front area while preserving aspect ratio
    img = ImageReader(front_image_path)
    img_w, img_h = img.getSize()
    target_w = front_w
    target_h = total_h_pt  # include bleed in height if any
    # Scale to cover: choose scale so that image fully covers area
    scale = max(target_w / img_w, target_h / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale
    # Center inside front area
    dx = front_x + (target_w - draw_w) / 2.0
    dy = (target_h - draw_h) / 2.0
    c.drawImage(img, dx, dy, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')

    c.showPage()
    c.save()
    return total_w_pt, total_h_pt, spine_pt


def count_pages(pdf_path: str) -> int:
    """Return total page count of a PDF file.

    Args:
        pdf_path: Path to PDF.

    Returns:
        Number of pages.
    """
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build KDP full-wrap cover for 6x9 agenda")
    parser.add_argument("--interior", required=True, help="Path to final interior PDF to compute spine")
    parser.add_argument("--front-image", required=True, help="Path to front cover image (PNG/JPG)")
    parser.add_argument("--trim", choices=list(TRIM_SIZES.keys()), default="6x9", help="Trim size")
    parser.add_argument("--paper", choices=["white", "cream", "color"], default="white", help="Paper type for spine calc")
    parser.add_argument("--bleed", action="store_true", help="Include 0.125\" bleed on all outer edges")
    parser.add_argument("--output", default="scripts/kdp_agenda_scripts/output/cover_fullwrap_6x9.pdf", help="Output cover PDF path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    trim = TRIM_SIZES[args.trim]
    pages = count_pages(args.interior)
    spine_in = compute_spine_inches(pages, args.paper)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    total_w_pt, total_h_pt, spine_pt = draw_fullwrap_cover(
        args.output,
        trim=trim,
        spine_in=spine_in,
        front_image_path=args.front_image,
        bleed=args.bleed,
    )
    print(f"Cover generated: {args.output}")
    print(f"Pages: {pages}, Spine: {spine_in:.4f} in ({spine_pt:.1f} pt)")
    print(f"Total: {total_w_pt/INCH:.3f} x {total_h_pt/INCH:.3f} in")


if __name__ == "__main__":
    main()


