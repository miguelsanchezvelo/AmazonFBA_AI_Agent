#!/usr/bin/env python3
"""Reset all generated pipeline outputs and logs."""

import os
import glob
import shutil

DATA_DIR = "data"
MSG_DIR = "supplier_messages"
EMAIL_DIR = "email_logs"
LOGS_DIR = "logs"
LOG_FILE = "log.txt"


def safe_remove(path: str) -> None:
    """Remove a file if it exists."""
    if os.path.isfile(path) or os.path.islink(path):
        try:
            os.remove(path)
            print(f"Deleted {path}")
        except Exception as exc:  # pragma: no cover - permissions
            print(f"Could not delete {path}: {exc}")


def safe_rmtree(path: str) -> None:
    """Remove a directory and its contents if it exists."""
    if os.path.isdir(path):
        try:
            shutil.rmtree(path)
            print(f"Removed {path}/")
        except Exception as exc:  # pragma: no cover - permissions
            print(f"Could not remove {path}: {exc}")


def reset() -> None:
    """Delete pipeline outputs and logs."""
    pattern = os.path.join(DATA_DIR, "*.csv")
    for fname in glob.glob(pattern):
        if os.path.basename(fname).startswith("mock_"):
            continue
        safe_remove(fname)

    for folder in (MSG_DIR, EMAIL_DIR, LOGS_DIR):
        safe_rmtree(folder)

    safe_remove(LOG_FILE)


def main() -> None:
    reset()


if __name__ == "__main__":
    main()
