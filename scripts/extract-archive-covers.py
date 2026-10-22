#!/usr/bin/env python3
"""Restore original embedded story images from saved legacy HTML pages."""

from __future__ import annotations

import base64
import io
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from PIL import Image, ImageOps


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
DATA = PROJECT / "assets" / "archive-posts.js"
OUTPUT = PROJECT / "assets" / "archive-covers"


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in value if character.isalnum())


def embedded_images(path: Path):
    html = path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(r"src=[\"']?(data:image/([^;,]+);base64,([^\"' >]+))", re.I)
    for match in pattern.finditer(html):
        try:
            raw = base64.b64decode(match.group(3))
            image = Image.open(io.BytesIO(raw))
            image.load()
            yield ImageOps.exif_transpose(image).convert("RGB")
        except Exception:
            continue


def main() -> None:
    if SOURCE is None:
        raise SystemExit("Usage: python scripts/extract-archive-covers.py ARCHIVE_FOLDER")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    match = re.search(r"=\s*(\[.*\]);", DATA.read_text(encoding="utf-8"), re.S)
    posts = json.loads(match.group(1))
    pages = [path for path in SOURCE.rglob("*.html") if "homepage" not in str(path).lower() and "main page" not in path.name.lower()]
    available = list(pages)
    restored = 0
    for post in posts:
        title_key = normalized(post["title"])
        ranked = sorted(available, key=lambda page: SequenceMatcher(None, title_key, normalized(page.stem)).ratio(), reverse=True)
        if not ranked:
            continue
        page = ranked[0]
        score = SequenceMatcher(None, title_key, normalized(page.stem)).ratio()
        if score < 0.45:
            continue
        candidates = [image for image in embedded_images(page) if image.width >= 300 and image.height >= 250 and image.width * image.height >= 120_000]
        if not candidates:
            continue
        cover = candidates[0]
        cover.thumbnail((1100, 760), Image.Resampling.LANCZOS)
        filename = Path(post["url"]).stem + ".webp"
        cover.save(OUTPUT / filename, "WEBP", quality=82, method=6)
        post["image"] = f"assets/archive-covers/{filename}"
        restored += 1
        available.remove(page)
    DATA.write_text("window.ARCHIVE_POSTS = " + json.dumps(posts, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(f"Restored original cover images for {restored} of {len(posts)} archived pieces")


if __name__ == "__main__":
    main()
