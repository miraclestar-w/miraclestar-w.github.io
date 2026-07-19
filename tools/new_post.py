#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a blog post and update indexes (atomic batch)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from siteutil import (
    apply_new_post,
    needs_explicit_slug,
    slugify,
    text_to_html,
    today_str,
    unique_slug,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Create post + update list/home/search/sitemap/feed")
    ap.add_argument("--title", required=True)
    ap.add_argument("--slug", help="english-kebab slug (required for CJK titles)")
    ap.add_argument("--tags", default="note")
    ap.add_argument("--date")
    ap.add_argument("--excerpt")
    ap.add_argument("--body")
    ap.add_argument("-f", "--body-file")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-home", action="store_true")
    args = ap.parse_args()

    if needs_explicit_slug(args.title, args.slug):
        print(
            "error: Chinese/non-ASCII title needs --slug english-name",
            file=sys.stderr,
        )
        return 2

    if args.body_file:
        body_raw = Path(args.body_file).read_text(encoding="utf-8")
    elif args.body is not None:
        body_raw = args.body
    elif not sys.stdin.isatty():
        body_raw = sys.stdin.read()
    else:
        body_raw = ""

    body_raw = (body_raw or "").strip()
    if not body_raw:
        body_raw = (
            f"## {args.title}\n\n"
            "Write here.\n\n"
            "### Summary\n\n"
            "- point 1\n"
            "- point 2\n"
        )

    date = args.date or today_str()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] or ["note"]
    slug = unique_slug(slugify(args.title, args.slug))
    body_html = text_to_html(body_raw)

    plain = body_raw
    for ch in ["#", "*", "`", ">", "-", "[", "]"]:
        plain = plain.replace(ch, " ")
    plain = " ".join(plain.split())
    excerpt = (args.excerpt or plain[:100]).strip()

    if args.dry_run:
        print("slug:", slug)
        print("files: post, post/index, home, search, sitemap, feed")
        print(body_html[:500])
        return 0

    paths = apply_new_post(
        title=args.title,
        date=date,
        tags=tags,
        excerpt=excerpt,
        slug=slug,
        body_html=body_html,
        plain=plain,
        update_home=not args.no_home,
    )
    print("created:", slug)
    for p in paths:
        print(" ", p)
    print("preview: http://127.0.0.1:5500/post/%s.html" % slug)
    print('publish: python tools/publish.py "add post: %s" --push' % args.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
