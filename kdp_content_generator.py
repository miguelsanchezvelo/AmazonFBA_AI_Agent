import os
import re
import argparse
from typing import Optional, List

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai optional
    OpenAI = None  # type: ignore


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate KDP book content")
    parser.add_argument("--book_type", choices=["low-content", "text-content"], required=True)
    parser.add_argument("--title", required=True, help="Book title")
    parser.add_argument("--genre", required=True, help="Book genre")
    parser.add_argument("--chapters", type=int, default=5, help="Number of chapters/pages")
    parser.add_argument("--tone", help="Writing tone")
    parser.add_argument("--audience", help="Target audience")
    parser.add_argument("--mock", action="store_true", help="Use mock content")
    parser.add_argument("--auto", action="store_true", help="Run without prompts")
    return parser.parse_args()


def generate_text_content(client: Optional[OpenAI], args: argparse.Namespace) -> str:
    chapters: List[str] = []
    for i in range(1, args.chapters + 1):
        if not client:
            chapters.append(f"Chapter {i}\nLorem ipsum dolor sit amet...")
            continue
        prompt = (
            f"Write chapter {i} of a {args.genre} book titled '{args.title}'."
        )
        if args.tone:
            prompt += f" Tone: {args.tone}."
        if args.audience:
            prompt += f" Audience: {args.audience}."
        try:
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            chapters.append(resp.choices[0].message.content.strip())
        except Exception:
            chapters.append(f"Chapter {i}\n(Content unavailable)")
    return "\n\n".join(chapters)


def generate_low_content(args: argparse.Namespace) -> str:
    pages = [f"Page {i}" for i in range(1, args.chapters + 1)]
    return "\n".join(pages)


def main() -> None:
    args = parse_args()
    os.makedirs("manuscripts", exist_ok=True)

    if args.book_type == "text-content" and args.chapters <= 1:
        print("text-content books require at least 2 chapters")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    if not args.mock and api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
        except Exception as exc:  # pragma: no cover - network
            print(f"OpenAI initialization failed: {exc}")
            client = None
    elif not args.mock:
        print("OpenAI API not available, using mock content.")

    if args.book_type == "low-content":
        content = generate_low_content(args)
    else:
        content = generate_text_content(client, args)

    filename = os.path.join("manuscripts", f"{slugify(args.title)}_manuscript.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Manuscript saved to {filename}")


if __name__ == "__main__":
    main()
