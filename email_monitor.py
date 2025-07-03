"""Monitor supplier replies via IMAP and log extracted quotes."""

from __future__ import annotations

import argparse
import csv
import email
import imaplib
import os
import re
import time
from email.header import decode_header
from email.utils import parseaddr
from typing import Dict, List, Tuple

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

LOG_FILE = "log.txt"
DEFAULT_OUTPUT = os.path.join("data", "email_monitor_results.csv")


def log(msg: str) -> None:
    """Append timestamped ``msg`` to ``log.txt``."""

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def _decode(val: str | bytes | None) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        try:
            return val.decode()
        except Exception:
            return val.decode("utf-8", "ignore")
    return str(val)


def parse_email(msg: email.message.Message) -> Tuple[str, str, str, List[str]]:
    """Return ``(subject, sender, body, attachments)`` for ``msg``."""

    parts = decode_header(msg.get("Subject", ""))
    subject = "".join(_decode(p[0]) for p in parts)
    sender = parseaddr(msg.get("From", ""))[1]

    body = ""
    attachments: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = part.get("Content-Disposition", "")
            if part.get_content_type() == "text/plain" and "attachment" not in disp:
                body_bytes = part.get_payload(decode=True)
                body += _decode(body_bytes)
            elif "attachment" in disp:
                name = part.get_filename()
                if name:
                    attachments.append(_decode(name))
    else:
        body = _decode(msg.get_payload(decode=True))

    return subject, sender, safe_strip(body), attachments


ASIN_RE = re.compile(r"\bB0[A-Z0-9]{7}\b")
PRICE_RE = re.compile(r"(?:unit price|price)[^\d]*(\d+(?:\.\d+)?)", re.I)
MOQ_RE = re.compile(r"(?:MOQ|minimum order)[^\d]*(\d+)", re.I)
LEAD_RE = re.compile(r"lead time[^\d]*(\d+\s*(?:days|weeks|months)?)", re.I)


def extract_info(text: str) -> Tuple[str, str, str, str]:
    """Return ``(asin, price, moq, lead)`` extracted from ``text``."""

    asin = ""
    price = ""
    moq = ""
    lead = ""

    m = ASIN_RE.search(text)
    if m:
        asin = m.group(0)
    m = PRICE_RE.search(text)
    if m:
        price = m.group(1)
    m = MOQ_RE.search(text)
    if m:
        moq = m.group(1)
    m = LEAD_RE.search(text)
    if m:
        lead = m.group(1)
    return asin, price, moq, lead


def save_rows(rows: List[Dict[str, str]], path: str) -> None:
    """Append ``rows`` to CSV at ``path``."""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ASIN",
                "Sender",
                "Subject",
                "Body Summary",
                "MOQ",
                "Price Per Unit",
                "Lead Time",
                "Attachments",
            ],
        )
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def is_reply(msg: email.message.Message, subject: str) -> bool:
    """Return True if the email appears to be a reply."""

    if msg.get("In-Reply-To"):
        return True
    return subject.lower().startswith("re:")


def process_inbox(unread_only: bool, output: str) -> None:
    """Connect to IMAP server and process supplier replies."""

    load_dotenv()
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD") or os.getenv("APP_PASSWORD")
    server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))

    if not email_addr or not password:
        log("email_monitor: missing email credentials")
        print("EMAIL_ADDRESS or EMAIL_PASSWORD not configured.")
        return

    try:
        imap = imaplib.IMAP4_SSL(server, port)
        imap.login(email_addr, password)
        imap.select("INBOX")
        log("email_monitor: connected to IMAP")
    except Exception as exc:
        log(f"email_monitor: connection failed {exc}")
        print(f"Failed to connect: {exc}")
        return

    criteria = "UNSEEN" if unread_only else "ALL"
    status, data = imap.search(None, criteria)
    if status != "OK":
        log("email_monitor: search failed")
        imap.logout()
        return

    ids = data[0].split()
    if not ids:
        log("email_monitor: no emails found")
        imap.logout()
        return

    rows: List[Dict[str, str]] = []

    for num in ids:
        try:
            status, fetched = imap.fetch(num, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            msg = email.message_from_bytes(fetched[0][1])
            subject, sender, body, attachments = parse_email(msg)
            if not is_reply(msg, subject):
                continue
            asin, price, moq, lead = extract_info(subject + " " + body)
            summary = " ".join(body.splitlines())[:200]
            rows.append(
                {
                    "ASIN": asin,
                    "Sender": sender,
                    "Subject": subject,
                    "Body Summary": summary,
                    "MOQ": moq,
                    "Price Per Unit": price,
                    "Lead Time": lead,
                    "Attachments": ",".join(attachments),
                }
            )
            imap.store(num, "+FLAGS", "\\Seen")
            log(f"email_monitor: processed email {num.decode()} from {sender}")
        except Exception as exc:  # pragma: no cover - network/issues
            log(f"email_monitor: failed processing {num.decode()}: {exc}")

    imap.logout()

    if not rows:
        log("email_monitor: no supplier replies found")
        print("No supplier replies found.")
        return

    save_rows(rows, output)
    log(f"email_monitor: saved {len(rows)} rows to {output}")
    print(f"Saved {len(rows)} rows to {output}")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Monitor supplier email replies")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--unread-only",
        dest="unread_only",
        action="store_true",
        help="Process only unread emails (default)",
    )
    group.add_argument(
        "--all",
        dest="unread_only",
        action="store_false",
        help="Process all emails",
    )
    parser.set_defaults(unread_only=True)
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, help="Where to save extracted CSV"
    )
    args = parser.parse_args(argv)

    process_inbox(args.unread_only, args.output)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()

def safe_strip(val):
    return val.strip() if isinstance(val, str) else ''
