"""Email management utilities for supplier communications."""

from __future__ import annotations

import email
import imaplib
import json
import os
import smtplib
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Dict, List, Tuple

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

LOG_PATH = os.path.join("logs", "email_threads.json")


def _decode(value: str | bytes | None) -> str:
    """Return decoded string value."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode()
        except Exception:
            return value.decode("utf-8", "ignore")
    return str(value)


def parse_email(msg: email.message.Message) -> Tuple[str, str, str, str]:
    """Return ``(subject, sender, body, msg_id)``."""

    raw_subject = msg.get("Subject", "")
    parts = decode_header(raw_subject)
    subject = "".join(_decode(p[0]) for p in parts)
    sender = parseaddr(msg.get("From", ""))[1]
    msg_id = msg.get("Message-ID", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                body_bytes = part.get_payload(decode=True)
                body += _decode(body_bytes)
                break
    else:
        body = _decode(msg.get_payload(decode=True))

    return subject, sender, body.strip(), msg_id


def load_threads() -> Dict[str, List[Dict[str, str]]]:
    if not os.path.exists(LOG_PATH):
        return {}
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_threads(threads: Dict[str, List[Dict[str, str]]]) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(threads, f, indent=2)


def is_supplier_reply(msg: email.message.Message, my_email: str) -> bool:
    """Return True if the message looks like a supplier response."""

    sender = parseaddr(msg.get("From", ""))[1]
    if sender.lower() == my_email.lower():
        return False
    subject = _decode(msg.get("Subject", "")).lower()
    return subject.startswith("re:") or bool(msg.get("In-Reply-To"))


def analyse_email(
    client: OpenAI,
    model: str,
    sender: str,
    subject: str,
    body: str,
) -> Tuple[str, bool, str]:
    """Return ``(summary, reply_needed, reply)`` using OpenAI."""

    system = (
        "You assist an Amazon FBA seller. "
        "Summarize the supplier email and state if a reply is required. "
        "If a reply is required, draft a short professional response. "
        "Respond in JSON using keys 'summary', 'reply_needed' and 'reply'."
    )
    user = f"From: {sender}\nSubject: {subject}\n\n{body}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
        return data.get("summary", ""), bool(data.get("reply_needed")), data.get("reply", "")
    except json.JSONDecodeError:
        return content, False, ""


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


def process_inbox() -> None:
    """Process unread inbox messages."""

    load_dotenv()

    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    auto_reply = os.getenv("AUTO_REPLY", "false").lower() in {"1", "true", "yes"}
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

    threads = load_threads()

    for num in data[0].split():
        status, fetched = imap.fetch(num, "(RFC822)")
        if status != "OK" or not fetched:
            continue
        msg = email.message_from_bytes(fetched[0][1])
        if not is_supplier_reply(msg, email_addr):
            continue

        subject, sender, body, msg_id = parse_email(msg)
        thread_id = msg.get("In-Reply-To") or msg_id
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

        entry = {
            "from": sender,
            "subject": subject,
            "body": body,
            "summary": summary,
            "reply": reply_text if reply_needed else "",
        }
        threads.setdefault(thread_id, []).append(entry)

        if reply_needed and reply_text:
            if auto_reply and openai_ok:
                try:
                    send_reply(email_addr, password, sender, subject, reply_text)
                    entry["sent_reply"] = True
                except Exception as exc:  # pragma: no cover - network
                    print(f"Failed to send reply to {sender}: {exc}")
                    entry["sent_reply"] = False
            else:
                print(f"Draft reply for {sender}:\n{reply_text}\n")
                entry["sent_reply"] = False

    save_threads(threads)
    imap.logout()


if __name__ == "__main__":
    process_inbox()
