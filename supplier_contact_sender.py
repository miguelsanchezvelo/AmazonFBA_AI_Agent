"""Send supplier contact emails and log interactions."""

import csv
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, List

from dotenv import load_dotenv

CONTACT_DIR = os.path.join("data", "supplier_contacts")
LOG_CSV = os.path.join("data", "supplier_contact_log.csv")

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@example.com")
EMAIL_TO = os.getenv("EMAIL_TO", "supplier@example.com")
TEST_MODE = os.getenv("TEST_MODE", "1") == "1" or not all(
    [SMTP_SERVER, SMTP_USER, SMTP_PASSWORD]
)


def list_contact_files() -> List[str]:
    if not os.path.isdir(CONTACT_DIR):
        return []
    return [
        os.path.join(CONTACT_DIR, f)
        for f in os.listdir(CONTACT_DIR)
        if f.lower().endswith(".txt")
    ]


def parse_contact_file(path: str) -> Dict[str, str]:
    asin = ""
    title = ""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines[:5]:  # look for asin and title in first lines
        if line.lower().startswith("asin:"):
            asin = line.split(":", 1)[1].strip()
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
    if not asin:
        base = os.path.basename(path)
        asin = base.split("_")[0]
    if not title:
        title = os.path.basename(path).rsplit(".", 1)[0]
    message = "\n".join(lines)
    return {"asin": asin, "title": title, "message": message}


def load_log() -> List[Dict[str, str]]:
    if not os.path.exists(LOG_CSV):
        return []
    with open(LOG_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_log(rows: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(LOG_CSV), exist_ok=True)
    with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ASIN",
                "Title",
                "Date Sent",
                "Email Sent To",
                "Status",
                "Response Date",
                "Notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def send_email(subject: str, body: str) -> None:
    if TEST_MODE:
        print(f"[TEST MODE] Would send email to {EMAIL_TO} with subject '{subject}'")
        return
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as exc:
        print(f"Error sending email: {exc}")


def process_files() -> None:
    files = list_contact_files()
    if not files:
        print(f"No contact files found in '{CONTACT_DIR}'.")
        return
    log_rows = load_log()
    existing_asins = {r["ASIN"] for r in log_rows}
    for path in files:
        data = parse_contact_file(path)
        asin = data["asin"]
        if asin in existing_asins:
            continue
        title = data["title"]
        send_email(f"Supplier inquiry for {asin}", data["message"])
        now = datetime.utcnow().strftime("%Y-%m-%d")
        log_rows.append(
            {
                "ASIN": asin,
                "Title": title,
                "Date Sent": now,
                "Email Sent To": EMAIL_TO,
                "Status": "sent" if not TEST_MODE else "pending",
                "Response Date": "",
                "Notes": "",
            }
        )
    save_log(log_rows)
    print(f"Logged {len(log_rows)} contacts to {LOG_CSV}")


if __name__ == "__main__":
    process_files()
