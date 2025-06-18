"""Manage supplier contact log via CLI."""

import argparse
import csv
import os
from typing import Dict, List

LOG_CSV = os.path.join("data", "supplier_contact_log.csv")


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


def list_contacts(rows: List[Dict[str, str]]):
    if not rows:
        print("No contacts logged.")
        return
    header = (
        f"{'ASIN':12} | {'Title':30} | {'Status':10} | {'Date Sent':10} | {'Resp Date':10}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['ASIN']:12} | {(r['Title'] or '')[:30]:30} | {r['Status']:10} | "
            f"{r['Date Sent']:10} | {r['Response Date']:10}"
        )


def update_contact(asin: str, status: str, response_date: str, notes: str) -> None:
    rows = load_log()
    for r in rows:
        if r["ASIN"] == asin:
            r["Status"] = status
            if response_date:
                r["Response Date"] = response_date
            if notes:
                r["Notes"] = notes
            save_log(rows)
            print(f"Updated {asin}.")
            return
    print(f"ASIN {asin} not found in log.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Track supplier contacts")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List logged contacts")

    up = sub.add_parser("update", help="Update a contact")
    up.add_argument("asin", help="ASIN to update")
    up.add_argument("--status", choices=["pending", "sent", "responded", "rejected"], required=True)
    up.add_argument("--response-date", default="")
    up.add_argument("--notes", default="")

    args = parser.parse_args()
    rows = load_log()

    if args.cmd == "update":
        update_contact(args.asin, args.status, args.response_date, args.notes)
    else:
        list_contacts(rows)


if __name__ == "__main__":
    main()
