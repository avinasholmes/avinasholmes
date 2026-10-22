#!/usr/bin/env python3
"""Place each recovered legacy cover back into its local article page."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "assets" / "archive-posts.js"


def main() -> None:
    match = re.search(r"=\s*(\[.*\]);", DATA.read_text(encoding="utf-8"), re.S)
    posts = json.loads(match.group(1))
    changed = 0
    for post in posts:
        image = post.get("image")
        if not image:
            continue
        article = PROJECT / post["url"]
        source = article.read_text(encoding="utf-8")
        if "class=\"article-cover\"" in source:
            continue
        figure = f'<figure class="article-cover"><img src="../{html.escape(image)}" alt="Cover image for {html.escape(post["title"])}"></figure>'
        updated, count = re.subn(r'(<p class="article-deck">.*?</p>)', r'\1' + figure, source, count=1, flags=re.S)
        if count:
            article.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Restored covers inside {changed} article pages")


if __name__ == "__main__":
    main()
