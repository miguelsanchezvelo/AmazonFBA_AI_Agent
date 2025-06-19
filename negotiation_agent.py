"""Automated email negotiation agent for supplier communications."""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import smtplib
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
from typing import List, Tuple, Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - library might be missing
    OpenAI = None  # type: ignore

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

KEYWORDS = [
    "quotation",
    "moq",
    "pricing",
    "price",
    "shipping",
    "sample",
    "payment",
    "terms",
]

LOG_PATH = os.path.join("logs", "email_negotiation_log.txt")


def decode(value: str | bytes | None) -> str:
    """Return decoded string value."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode()
        except Exception:
            return value.decode("utf-8", "ignore")
    return str(value)


def parse_email(msg: email.message.Message) -> Tuple[str, str, str]:
    """Extract ``(subject, sender, body)`` from an email message."""

    raw_subject = msg.get("Subject", "")
    parts = decode_header(raw_subject)
    subject = "".join(decode(p[0]) for p in parts)
    sender = parseaddr(msg.get("From", ""))[1]

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                body_bytes = part.get_payload(decode=True)
                body += decode(body_bytes)
                break
    else:
        body = decode(msg.get_payload(decode=True))

    return subject, sender, body.strip()


def analyse_email(
    client: OpenAI,
    model: str,
    sender: str,
    subject: str,
    body: str,
) -> Tuple[str, bool, str]:
    """Return ``(summary, reply_needed, reply_text)`` using OpenAI."""

    system = (
        "You are an assistant for an Amazon FBA seller. "
        "Summarize the supplier email and indicate if a reply is required. "
        "If a reply is required, draft a short professional response. "
        "Respond in JSON with keys 'summary', 'reply_needed' and 'reply'."
    )
    user = f"From: {sender}\nSubject: {subject}\n\n{body}"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
    except Exception as exc:  # pragma: no cover - network
        raise RuntimeError(f"OpenAI API error: {exc}") from exc

    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
        summary = data.get("summary", "")
        reply_needed = bool(data.get("reply_needed"))
        reply_text = data.get("reply", "")
    except json.JSONDecodeError:
        summary = content
        reply_needed = False
        reply_text = ""
    return summary, reply_needed, reply_text


def send_reply(
    email_addr: str,
    password: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """Send an email reply via SMTP."""

    msg = EmailMessage()
    msg["From"] = email_addr
    msg["To"] = recipient
    msg["Subject"] = f"Re: {subject}"
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(email_addr, password)
        smtp.send_message(msg)


def log_entry(
    sender: str,
    subject: str,
    body: str,
    summary: str,
    reply_needed: bool,
    reply: str,
) -> None:
    """Append an entry to the log file."""

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"FROM: {sender}\n")
        f.write(f"SUBJECT: {subject}\n")
        f.write("BODY:\n" + body + "\n")
        f.write("SUMMARY: " + summary + "\n")
        f.write(f"REPLY_NEEDED: {reply_needed}\n")
        if reply:
            f.write("REPLY:\n" + reply + "\n")
        f.write("-" * 40 + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Process supplier emails and draft or send replies"
    )
    parser.add_argument(
        "--auto-reply",
        action="store_true",
        help="Automatically send replies instead of printing drafts",
    )
    args = parser.parse_args(argv)

    load_dotenv()

    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    auto_reply = args.auto_reply or os.getenv("AUTO_REPLY", "false").lower() in {"1", "true", "yes"}
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4")

    if not email_addr or not password:
        print("EMAIL_ADDRESS or EMAIL_PASSWORD not configured.")
        return

    openai_ok = bool(api_key and OpenAI)
    client = None
    if openai_ok:
        try:
            client = OpenAI(api_key=api_key)
        except Exception as exc:  # pragma: no cover - network
            print(f"OpenAI initialization failed: {exc}")
            openai_ok = False

    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(email_addr, password)
        imap.select("INBOX")
    except Exception as exc:
        print(f"Failed to connect to IMAP: {exc}")
        return

    status, data = imap.search(None, "UNSEEN")
    if status != "OK":
        print("Failed to search mailbox.")
        imap.logout()
        return

    ids = data[0].split()
    processed: List[Tuple[str, str]] = []
    replies: List[str] = []

    for num in ids:
        status, fetched = imap.fetch(num, "(RFC822)")
        if status != "OK" or not fetched:
            continue
        msg = email.message_from_bytes(fetched[0][1])
        subject, sender, body = parse_email(msg)
        text = (subject + "\n" + body).lower()
        if not any(k in text for k in KEYWORDS):
            continue

        summary = body[:120]
        reply_needed = False
        reply_text = ""

        if openai_ok and client:
            try:
                summary, reply_needed, reply_text = analyse_email(
                    client, model, sender, subject, body
                )
            except Exception as exc:  # pragma: no cover - network
                print(f"OpenAI error for email from {sender}: {exc}")
                openai_ok = False

        log_entry(sender, subject, body, summary, reply_needed, reply_text)
        processed.append((sender, subject))

        if reply_needed and reply_text:
            if auto_reply and openai_ok:
                try:
                    send_reply(email_addr, password, sender, subject, reply_text)
                    replies.append(sender)
                except Exception as exc:  # pragma: no cover - network
                    print(f"Failed to send reply to {sender}: {exc}")
            else:
                print(f"Draft reply for {sender}:\n{reply_text}\n")

    imap.logout()

    print("Processed emails:")
    for sender, subj in processed:
        sent = sender in replies
        status_str = "reply sent" if sent else "logged"
        print(f" - {sender} | {subj} ({status_str})")
    if not processed:
        print("No new supplier emails found.")


if __name__ == "__main__":
    main()
