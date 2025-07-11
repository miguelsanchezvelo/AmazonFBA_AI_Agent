"""Send purchase order requests to suppliers via email."""

from __future__ import annotations

import csv
import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import datetime
from email.message import EmailMessage
from importlib.util import find_spec
from typing import Dict, List, Tuple
import argparse
from mock_data import get_mock_asins

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore

REQUIRED_PACKAGES = {
    "yagmail": "yagmail",
    "dotenv": "python-dotenv",
    "pandas": "pandas",
    "openai": "openai",
}


def _missing_packages() -> List[str]:
    missing = []
    for mod, pkg in REQUIRED_PACKAGES.items():
        if find_spec(mod) is None:
            missing.append(pkg)
    return missing


MISSING_PKGS = _missing_packages()


def install_packages(pkgs: List[str]) -> None:
    """Install the given pip packages."""

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *pkgs])
    except Exception as exc:  # pragma: no cover - network/permission issues
        print(f"Failed to install packages {pkgs}: {exc}")


def ensure_dependencies(auto: bool) -> None:
    """Ensure all required packages are installed."""

    if not MISSING_PKGS:
        return

    if auto or not sys.stdin.isatty():
        print(f"Installing missing packages: {', '.join(MISSING_PKGS)}")
        install_packages(MISSING_PKGS)
        return

    print(f"The following packages are required: {', '.join(MISSING_PKGS)}")
    choice = input("Install them now? [Y/n] ").strip().lower()
    if choice in ("", "y", "yes"):
        install_packages(MISSING_PKGS)

PRODUCT_CSV = os.path.join("data", "supplier_selection_results.csv")
MESSAGES_DIR = "supplier_messages"
LOG_CSV = os.path.join("data", "order_placement_log.csv")
TMP_DIR = os.path.join("data", "edited_messages")
CONFIG_JSON = "config.json"
CONFIRM_LOG = os.path.join("logs", "order_confirmation_log.txt")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

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


def parse_bool(val: str) -> bool:
    """Return ``True`` unless ``val`` looks like a false value."""
    return str(val).strip().lower() not in {"0", "false", "no", "n"}


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


def load_credentials() -> Tuple[str | None, str | None, str, int]:
    load_dotenv()
    config: Dict[str, str] = {}
    if os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

    def get(name: str, default: str | None = None) -> str | None:
        return os.getenv(name) or config.get(name.lower()) or config.get(name) or default

    email_addr = get("EMAIL_ADDRESS")
    password = get("EMAIL_PASSWORD")
    smtp_server = get("SMTP_SERVER", "smtp.gmail.com") or "smtp.gmail.com"
    smtp_port = int(get("SMTP_PORT", "587") or 587)
    return email_addr, password, smtp_server, smtp_port


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_row(action: str, asin: str, units: int, recipient: str, message: str) -> None:
    os.makedirs(os.path.dirname(LOG_CSV), exist_ok=True)
    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "action", "asin", "units", "recipient", "message"],
        )
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "asin": asin,
                "units": units,
                "recipient": recipient,
                "message": message,
            }
        )


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------

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
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(email_addr, password)
        smtp.send_message(msg)


# ---------------------------------------------------------------------------
# Interactive workflow
# ---------------------------------------------------------------------------

def edit_message(original: str, asin: str, auto: bool) -> str:
    if auto:
        return original

    choice = input("Edit message before sending? [y/N] ").strip().lower()
    if choice != "y":
        return original

    print("Enter new message. Finish with a single '.' on a line:")
    lines: List[str] = []
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    new_msg = "\n".join(lines).strip()
    if not new_msg:
        return original

    os.makedirs(TMP_DIR, exist_ok=True)
    fname = os.path.join(TMP_DIR, f"{asin}_{int(datetime.utcnow().timestamp())}.txt")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(new_msg)
    print(f"Edited message saved to {fname}")
    log_row("edited", asin, 0, "", fname)
    return new_msg


def process_orders(
    auto: bool = False,
    email_addr: str | None = None,
    password: str | None = None,
    smtp_server: str | None = None,
    smtp_port: int | None = None,
) -> None:
    env_email, env_pass, env_server, env_port = load_credentials()
    email_addr = email_addr or env_email
    password = password or env_pass
    smtp_server = smtp_server or env_server
    smtp_port = smtp_port or env_port

    if not email_addr and not auto and sys.stdin.isatty():
        email_addr = input("Email address: ").strip()
    if not password and not auto and sys.stdin.isatty():
        password = input("Email password or token: ").strip()
    if not smtp_server and not auto and sys.stdin.isatty():
        default = env_server
        prompt = f"SMTP server hostname [{default}]: "
        smtp_server = input(prompt).strip() or default
    if smtp_port is None and not auto and sys.stdin.isatty():
        default = str(env_port)
        val = input(f"SMTP server port [{default}]: ").strip() or default
        try:
            smtp_port = int(val)
        except ValueError:
            smtp_port = env_port

    if not email_addr or not password:
        print("Missing email credentials. Exiting.")
        return

    products = load_products(PRODUCT_CSV)
    if not products:
        return

    for row in products:
        asin = row.get("asin", "").strip()
        title = row.get("title", "").strip()
        units = parse_int(row.get("units_to_order") or row.get("Units"))
        total_cost = parse_float(row.get("total_cost"))

        if units <= 0:
            continue

        message = load_message(asin)
        if not message:
            print(f"⚠️ Supplier message for {asin} missing.")
            log_row("missing_message", asin, units, "", "")
            continue

        supplier_email = extract_email(message) or ""

        print("-" * 60)
        print(f"ASIN: {asin}")
        print(f"Title: {title}")
        print(f"Units to order: {units}")
        print(f"Total cost: ${total_cost:.2f}")
        print(f"Supplier email: {supplier_email}")
        print("Message:\n" + message)
        if not auto:
            choice = input("Contact this supplier? [Y/n] ").strip().lower()
            if choice == "n":
                print("Skipped.")
                log_row("skipped", asin, units, supplier_email, "")
                continue

        msg_body = edit_message(message, asin, auto)

        if not auto:
            confirm = input("Send email now? [Y/n] ").strip().lower()
            if confirm == "n":
                print("Send cancelled.")
                log_row("cancelled", asin, units, supplier_email, msg_body)
                continue

        attempts = 0
        while attempts < 3:
            try:
                send_email(
                    smtp_server,
                    smtp_port,
                    email_addr,
                    password,
                    supplier_email,
                    f"Purchase Order Request for {asin}",
                    msg_body,
                )
                print("Email sent.")
                log_row("sent", asin, units, supplier_email, msg_body)
                break
            except Exception as exc:
                attempts += 1
                print(f"Error sending email: {exc}")
                log_row("error", asin, units, supplier_email, str(exc))
                if attempts >= 3:
                    print("Giving up on this email.")
                    break
                if auto:
                    break
                retry = input("Retry sending? [y/N] ").strip().lower()
                if retry != "y":
                    break


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Return parsed command line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Send purchase order emails to suppliers using files generated by the"
            " FBA pipeline. Requires 'data/supplier_selection_results.csv' and"
            " message files in 'supplier_messages/'."
        )
    )
    parser.add_argument("--email", help="Email address used to send orders")
    parser.add_argument("--password", help="Email password or app-specific token")
    parser.add_argument("--smtp_server", help="SMTP server hostname")
    parser.add_argument("--smtp_port", type=int, help="SMTP server port")
    parser.add_argument(
        "--confirm",
        type=parse_bool,
        default=True,
        metavar="BOOL",
        help="whether to run in interactive mode (default: true)",
    )
    # legacy option kept for backwards compatibility
    parser.add_argument("--auto", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument('--input', default='data/inventory_management_results.csv', help='Input CSV file')
    parser.add_argument('--output', default='data/order_placement_results.csv', help='Output CSV file')
    parser.add_argument('--mock', action='store_true', help='Use mock data only')

    if argv and any(h in argv for h in ("-h", "--help")):
        parser.print_help()
        if MISSING_PKGS:
            print(f"\n⚠️ Missing packages: {', '.join(MISSING_PKGS)}")
        raise SystemExit(0)

    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    """Entry point for command line execution."""

    args = parse_args(argv)
    use_mock = args.mock
    if use_mock:
        mock_orders = [dict(row, **{"units_ordered": 100, "order_status": "CONFIRMED"}) for row in get_mock_asins()]
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["asin", "title", "units_ordered", "order_status"])
            writer.writeheader()
            writer.writerows(mock_orders)
        print(f"[MOCK] Saved {len(mock_orders)} order placement rows to {args.output}")
        return
    auto = args.auto or not args.confirm
    ensure_dependencies(auto)
    process_orders(
        auto=auto,
        email_addr=args.email,
        password=args.password,
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
    )
    os.makedirs(os.path.dirname(CONFIRM_LOG), exist_ok=True)
    with open(CONFIRM_LOG, "a", encoding="utf-8") as f:
        f.write(f"run_completed {datetime.utcnow().isoformat()}\n")


if __name__ == "__main__":
    main()
