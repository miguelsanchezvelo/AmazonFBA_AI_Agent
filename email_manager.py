"""Automatic supplier email manager for Amazon FBA."""

from __future__ import annotations

import argparse
import csv
import email
import imaplib
import json
import os
import re
import smtplib
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional
    OpenAI = None  # type: ignore

CONFIG_PATH = "config.json"
CSV_PATH = os.path.join("data", "supplier_offers.csv")
HANDLED_FOLDER = "FBA_Handled"
KEYWORDS = ["quotation", "offer", "moq"]
GENERIC_REPLY = (
    "Thank you for the information. We will review your offer and contact you soon."
)


def load_config() -> Dict[str, str]:
    """Load optional configuration from ``config.json``."""

    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_setting(config: Dict[str, str], name: str, default: str | None = None) -> str | None:
    """Return environment or config value for ``name``."""

    return os.getenv(name) or config.get(name.lower()) or config.get(name) or default


def _decode(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode()
        except Exception:
            return value.decode("utf-8", "ignore")
    return str(value)


def parse_email(msg: email.message.Message) -> Tuple[str, str, str, str, str]:
    """Return ``(subject, sender, body, msg_id, date)``."""

    raw_subject = msg.get("Subject", "")
    parts = decode_header(raw_subject)
    subject = "".join(_decode(p[0]) for p in parts)
    sender = parseaddr(msg.get("From", ""))[1]
    msg_id = msg.get("Message-ID", "")
    date = msg.get("Date", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not part.get("Content-Disposition"):
                body_bytes = part.get_payload(decode=True)
                body += _decode(body_bytes)
                break
    else:
        body = _decode(msg.get_payload(decode=True))

    return subject, sender, body.strip(), msg_id, date


def ensure_folder(imap: imaplib.IMAP4_SSL, name: str) -> None:
    """Create IMAP folder ``name`` if it does not exist."""

    code, _ = imap.list()
    if code != "OK":
        return
    folders = [line.split()[-1].decode() for line in _]
    if name not in folders:
        imap.create(name)


def move_to_folder(imap: imaplib.IMAP4_SSL, msg_id: bytes, folder: str) -> None:
    """Move ``msg_id`` to ``folder``."""

    imap.copy(msg_id, folder)
    imap.store(msg_id, "+FLAGS", "\\Deleted")


def extract_offer_regex(text: str) -> Tuple[str, str, str, str]:
    """Extract offer details using regular expressions."""

    price = ""
    moq = ""
    lead = ""
    product = ""

    m = re.search(r"(?:unit price|price)[^\d]*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        price = m.group(1)
    m = re.search(r"(?:MOQ|minimum order)[^\d]*(\d+)", text, re.I)
    if m:
        moq = m.group(1)
    m = re.search(r"lead time[^\d]*(\d+\s*(?:days|weeks|months)?)", text, re.I)
    if m:
        lead = m.group(1)
    m = re.search(r"product[:\s]*([\w\s-]+)", text, re.I)
    if m:
        product = m.group(1).strip()
    return product, price, moq, lead


def extract_offer_ai(client: OpenAI, model: str, text: str) -> Tuple[str, str, str, str]:
    """Use OpenAI to extract offer details."""

    prompt = (
        "Extract unit price, MOQ, lead time and product name from the following email. "
        "Respond in JSON with keys product, price, moq and lead_time. If a value is missing, use an empty string.\n\n"
        + text
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
        return (
            data.get("product", ""),
            data.get("price", ""),
            data.get("moq", ""),
            data.get("lead_time", ""),
        )
    except json.JSONDecodeError:
        return extract_offer_regex(text)


def write_offer_row(row: Iterable[str]) -> None:
    """Append row to ``supplier_offers.csv``."""

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "Sender",
                "Product",
                "Price",
                "MOQ",
                "LeadTime",
                "EmailSubject",
                "Date",
                "RawContent",
            ])
        writer.writerow(list(row))


def send_reply(email_addr: str, password: str, smtp_server: str, smtp_port: int, recipient: str, subject: str, body: str) -> None:
    """Send an email via SMTP."""

    msg = EmailMessage()
    msg["From"] = email_addr
    msg["To"] = recipient
    msg["Subject"] = f"Re: {subject}"
    msg.set_content(body)

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(email_addr, password)
        smtp.send_message(msg)


def generate_reply(client: Optional[OpenAI], model: str, sender: str, subject: str, body: str) -> str:
    """Return reply text using OpenAI or default."""

    if not client:
        return GENERIC_REPLY
    prompt = (
        "You are an Amazon FBA seller. Craft a short professional reply confirming interest, "
        "asking any necessary follow-up questions."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"From: {sender}\nSubject: {subject}\n\n{body}"},
        ],
    )
    return resp.choices[0].message.content.strip()


def process_inbox(dry_run: bool = False) -> None:
    """Process supplier emails from the inbox."""

    load_dotenv()
    config = load_config()

    email_addr = get_setting(config, "EMAIL_ADDRESS")
    password = get_setting(config, "EMAIL_PASSWORD")
    smtp_server = get_setting(config, "SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(get_setting(config, "SMTP_PORT", "587") or 587)
    imap_server = get_setting(config, "IMAP_SERVER", "imap.gmail.com")

    supplier_domains = get_setting(config, "SUPPLIER_DOMAINS", "") or ""
    domains = [d.strip().lower() for d in supplier_domains.split(",") if d.strip()]

    if not email_addr or not password:
        print("Missing email credentials. Skipping.")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    client: Optional[OpenAI] = None
    if api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
        except Exception:
            client = None

    try:
        imap = imaplib.IMAP4_SSL(imap_server)
        imap.login(email_addr, password)
        imap.select("INBOX")
    except Exception as exc:
        print(f"IMAP connection failed: {exc}")
        return

    ensure_folder(imap, HANDLED_FOLDER)

    status, data = imap.search(None, "UNSEEN")
    if status != "OK":
        print("Failed to search mailbox.")
        imap.logout()
        return

    ids = data[0].split()
    processed = 0
    replied = 0
    skipped = 0

    for num in ids:
        status, fetched = imap.fetch(num, "(RFC822)")
        if status != "OK" or not fetched:
            continue
        msg = email.message_from_bytes(fetched[0][1])
        subject, sender, body, msg_id, date = parse_email(msg)
        if not any(k in subject.lower() for k in KEYWORDS):
            skipped += 1
            continue
        domain = sender.split("@")[-1].lower()
        if domains and domain not in domains and not msg.get("In-Reply-To"):
            skipped += 1
            continue

        product, price, moq, lead = extract_offer_ai(client, model, body) if client else extract_offer_regex(body)
        write_offer_row([sender, product, price, moq, lead, subject, date, body.replace("\n", " ")])
        processed += 1

        reply_text = generate_reply(client, model, sender, subject, body)
        if dry_run:
            print(f"Would reply to {sender}: {reply_text}\n")
        else:
            try:
                send_reply(email_addr, password, smtp_server, smtp_port, sender, subject, reply_text)
                replied += 1
            except Exception as exc:
                print(f"Failed to send reply to {sender}: {exc}")

        if not dry_run:
            move_to_folder(imap, num, HANDLED_FOLDER)

    if not dry_run:
        imap.expunge()
    imap.logout()

    print(f"{processed + skipped} emails processed, {replied} replied, {skipped} skipped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage supplier emails")
    parser.add_argument("--dry-run", action="store_true", help="Only list actions without sending replies")
    args = parser.parse_args()
    process_inbox(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
