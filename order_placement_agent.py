import csv
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, List

from dotenv import load_dotenv

PRODUCT_CSV = os.path.join("data", "supplier_selection_results.csv")
MESSAGES_DIR = "supplier_messages"
LOG_FILE = "order_log.txt"


def parse_int(val: str | None) -> int:
    if val is None:
        return 0
    m = re.search(r"\d+", str(val))
    return int(m.group()) if m else 0


def parse_float(val: str | None) -> float:
    if val is None:
        return 0.0
    m = re.search(r"\d+\.\d+|\d+", str(val))
    return float(m.group()) if m else 0.0


def load_products(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        print(f"Input file '{path}' not found.")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_message(asin: str) -> str | None:
    path = os.path.join(MESSAGES_DIR, f"{asin}.txt")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_email(text: str) -> str | None:
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else None


def log_action(action: str, asin: str, note: str = "") -> None:
    timestamp = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {action} | {asin} | {note}\n")


def send_email(
    smtp_server: str,
    smtp_port: int,
    email_addr: str,
    password: str,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_addr
    msg["To"] = to_addr
    msg.set_content(body)
    with smtplib.SMTP(smtp_server, smtp_port) as s:
        s.starttls()
        s.login(email_addr, password)
        s.send_message(msg)


def main() -> None:
    load_dotenv()
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not email_addr or not password:
        print("Missing email credentials in .env. Exiting.")
        return

    products = load_products(PRODUCT_CSV)
    if not products:
        return

    ordered: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    for row in products:
        asin = row.get("asin", "").strip()
        title = row.get("title", "").strip()
        units = parse_int(row.get("units_to_order") or row.get("Units"))
        total_cost = parse_float(row.get("total_cost"))
        roi = parse_float(row.get("roi"))
        demand = row.get("demand") or row.get("demand_level") or ""

        if units <= 0:
            continue

        msg_text = load_message(asin)
        if not msg_text:
            print(f"⚠️ No supplier message found for {asin}. Skipping.")
            log_action("missing_message", asin)
            skipped.append(asin)
            continue

        supplier_email = extract_email(msg_text) or "Unknown"
        print("\n" + "-" * 60)
        print(f"ASIN: {asin}")
        print(f"Title: {title}")
        print(f"Units: {units}")
        print(f"Total Cost: ${total_cost:.2f}")
        print(f"Supplier Email: {supplier_email}")
        print("Message:\n" + msg_text)
        print(
            f"Justification: Demand {demand} and ROI {roi:.2f} make this product a suitable investment."
        )
        print(f"Contacting supplier extracted from message: {supplier_email}")
        choice = input("Send this order request email? [y/N] ").strip().lower()
        if choice != "y":
            print("Skipped.")
            log_action("skipped", asin)
            skipped.append(asin)
            continue

        try:
            send_email(
                smtp_server,
                smtp_port,
                email_addr,
                password,
                supplier_email,
                f"Purchase Order Request for {asin}",
                msg_text,
            )
            print("Email sent.")
            log_action("sent", asin, supplier_email)
            ordered.append(asin)
        except Exception as exc:
            print(f"Error sending email for {asin}: {exc}")
            log_action("error", asin, str(exc))
            errors.append(asin)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"Ordered: {', '.join(ordered) if ordered else 'None'}")
    print(f"Skipped: {', '.join(skipped) if skipped else 'None'}")
    if errors:
        print(f"Errors: {', '.join(errors)}")
    print(f"Log written to {LOG_FILE}")


if __name__ == "__main__":
    main()
