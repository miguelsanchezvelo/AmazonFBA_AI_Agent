import csv
import os
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

INPUT_CSV = os.path.join("data", "supplier_selection_results.csv")
OUTPUT_TXT = os.path.join("data", "supplier_emails.txt")


def parse_int(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    m = re.search(r"\d+", str(val))
    return int(m.group()) if m else None


def load_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def search_url(title: str) -> str:
    query = (
        f'"{title}" supplier OR wholesaler '
        'site:alibaba.com OR site:globalsources.com OR site:made-in-china.com'
    )
    return f"https://www.google.com/search?q={quote_plus(query)}"


def email_template(title: str) -> str:
    return (
        "Dear Sir or Madam,\n\n"
        f"I am interested in sourcing the product \"{title}\". "
        "Could you please provide the minimum order quantity (MOQ), price per unit "
        "and estimated lead time? "
        "I would also appreciate your catalogue of similar products.\n\n"
        "Best regards,\n"
        "Carlos Ruiz\n"
        "sourcing@example.com\n"
        "Spain\n"
    )


def main() -> None:
    rows = load_rows(INPUT_CSV)
    if not rows:
        print(f"Input file '{INPUT_CSV}' not found. Exiting.")
        return

    templates: List[str] = []
    for r in rows:
        units = parse_int(r.get("units_to_order")) or 0
        if units <= 0:
            continue
        asin = r.get("asin", "")
        title = r.get("title", "")
        url = search_url(title)
        print(url)
        email = email_template(title)
        templates.append(f"ASIN: {asin}\nTitle: {title}\n\n{email}\n")

    if not templates:
        print("No products with units to order found.")
        return

    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        for tmpl in templates:
            f.write(tmpl)
            f.write("-" * 40 + "\n")
    print(f"Saved {len(templates)} email templates to {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
