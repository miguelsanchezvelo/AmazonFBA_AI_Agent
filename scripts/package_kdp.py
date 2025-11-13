from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


DEFAULT_FALLBACK_DIR = r"C:\Users\msvelo\Documents\private_msv\KDP_1"


@dataclass(frozen=True)
class Candidate:
    """Represents candidate source paths for a single asset.

    Attributes:
        name: The destination filename in the package.
        candidates: Possible source paths to try, in order.
    """

    name: str
    candidates: Tuple[Path, ...]


def ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist.

    Args:
        path: Directory path to create.
    """
    path.mkdir(parents=True, exist_ok=True)


def copy_first_existing(candidate: Candidate, dest_dir: Path) -> bool:
    """Copy the first existing candidate file into dest_dir.

    Args:
        candidate: Candidate object with destination name and source options.
        dest_dir: Destination directory to copy to.

    Returns:
        True if a file was copied, False if none of the candidates existed.
    """
    for src in candidate.candidates:
        if src.exists():
            shutil.copy2(str(src), str(dest_dir / candidate.name))
            return True
    return False


def zip_directory(src_dir: Path, zip_path: Path) -> None:
    """Zip directory contents into a zip file.

    Args:
        src_dir: Directory whose contents will be zipped.
        zip_path: Target zip file path.
    """
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in src_dir.iterdir():
            if item.is_file():
                zf.write(str(item), arcname=item.name)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(description="Assemble KDP package folder and zip it")
    parser.add_argument(
        "--dest",
        default="kdp_package_2025_2026",
        help="Destination package directory (default: kdp_package_2025_2026)",
    )
    parser.add_argument(
        "--fallback-dir",
        default=DEFAULT_FALLBACK_DIR,
        help="Fallback directory to look for metadata/text files if missing locally",
    )
    parser.add_argument(
        "--interior",
        default="scripts/kdp_agenda_scripts/output/interior_6x9_2025_2026_complete.pdf",
        help="Path to interior PDF",
    )
    parser.add_argument(
        "--cover",
        default="scripts/kdp_agenda_scripts/output/cover_fullwrap_6x9.pdf",
        help="Path to full-wrap cover PDF",
    )
    return parser


def main() -> None:
    """CLI entry point to assemble the KDP package.

    Steps:
      1) Create destination directory
      2) Copy interior and cover
      3) Copy metadata and listing text files, using fallback dir if not in CWD
      4) Zip the directory
    """
    args = build_parser().parse_args()
    cwd = Path.cwd()
    dest_dir = cwd / args.dest
    fallback_dir = Path(args.fallback_dir)

    # Reset destination dir
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    ensure_dir(dest_dir)

    # Required assets
    required = [
        Candidate("interior.pdf", (Path(args.interior),)),
        Candidate("cover_fullwrap.pdf", (Path(args.cover),)),
    ]

    missing: List[str] = []
    for cand in required:
        if not copy_first_existing(cand, dest_dir):
            missing.append(cand.name)

    # Optional/listing assets
    optional = [
        Candidate(
            "kdp_description_2025_2026.txt",
            (cwd / "kdp_description_2025_2026.txt", fallback_dir / "kdp_description_2025_2026.txt"),
        ),
        Candidate(
            "kdp_keywords_2025_2026.txt",
            (cwd / "kdp_keywords_2025_2026.txt", fallback_dir / "kdp_keywords_2025_2026.txt"),
        ),
        Candidate(
            "kdp_categories_2025_2026.txt",
            (cwd / "kdp_categories_2025_2026.txt", fallback_dir / "kdp_categories_2025_2026.txt"),
        ),
        Candidate(
            "metadata_2025_2026.yaml",
            (cwd / "metadata_2025_2026.yaml", fallback_dir / "metadata_2025_2026.yaml"),
        ),
    ]

    missing_optional: List[str] = []
    for cand in optional:
        if not copy_first_existing(cand, dest_dir):
            missing_optional.append(cand.name)

    # Zip
    zip_path = dest_dir.with_suffix(".zip")
    zip_directory(dest_dir, zip_path)

    print(f"Packaged: {dest_dir}")
    print(f"Zip: {zip_path}")
    if missing:
        print("Missing required:", ", ".join(missing))
    if missing_optional:
        print("Missing optional:", ", ".join(missing_optional))


if __name__ == "__main__":
    main()


