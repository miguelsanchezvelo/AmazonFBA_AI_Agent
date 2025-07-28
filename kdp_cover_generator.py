import os
import re
import argparse
import base64
from typing import Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai optional
    OpenAI = None  # type: ignore

PLACEHOLDER_IMAGE = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z/CfHgAHggJ/P9n3WQAAAABJRU5ErkJggg=='
)


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a KDP book cover")
    parser.add_argument("--title", required=True, help="Book title")
    parser.add_argument("--subtitle", help="Optional subtitle")
    parser.add_argument("--author", required=True, help="Author name")
    parser.add_argument("--genre", required=True, help="Book genre")
    parser.add_argument("--style", default="minimalist", help="Cover style")
    parser.add_argument("--size", default="6x9", help="Book size")
    parser.add_argument("--mock", action="store_true", help="Use mock image")
    parser.add_argument("--auto", action="store_true", help="Run without prompts")
    return parser.parse_args()


def generate_image(prompt: str, client: Optional[OpenAI]) -> bytes:
    if not client:
        return PLACEHOLDER_IMAGE
    try:
        resp = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
        url = resp.data[0].url
        if not url:
            return PLACEHOLDER_IMAGE
        import requests
        return requests.get(url, timeout=10).content
    except Exception:
        return PLACEHOLDER_IMAGE


def main() -> None:
    args = parse_args()
    os.makedirs("covers", exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    if not args.mock and api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
        except Exception as exc:  # pragma: no cover - network
            print(f"OpenAI initialization failed: {exc}")
            client = None
    elif not args.mock:
        print("OpenAI API not available, using mock image.")

    prompt = f"{args.style} {args.genre} book cover titled '{args.title}'"
    if args.subtitle:
        prompt += f" subtitle '{args.subtitle}'"
    prompt += f" by {args.author}"

    image_data = generate_image(prompt, client)

    filename = os.path.join("covers", f"{slugify(args.title)}_cover.png")
    with open(filename, "wb") as f:
        f.write(image_data)
    print(f"Cover saved to {filename}")


if __name__ == "__main__":
    main()
