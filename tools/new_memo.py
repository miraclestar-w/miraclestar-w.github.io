#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add a memo to memos/index.html."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from siteutil import apply_new_memo, today_str


def read_content(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()
    if args.text:
        return " ".join(args.text).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print("Input memo (empty line to finish):")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Add memo (flash note)")
    ap.add_argument("text", nargs="*", help="memo body")
    ap.add_argument("-f", "--file", help="read body from file")
    ap.add_argument("--date", help="YYYY-MM-DD (default today)")
    ap.add_argument("--html", action="store_true", help="allow raw HTML (unsafe)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    content = read_content(args)
    if not content:
        print("error: empty content", file=sys.stderr)
        return 1

    date = args.date or today_str()
    if args.dry_run:
        from siteutil import memo_html
        print(memo_html(content, date, allow_html=args.html))
        return 0

    paths = apply_new_memo(content, date, allow_html=args.html)
    print("memo added:", date)
    for p in paths:
        print(" ", p)
    print("preview: http://127.0.0.1:5500/memos/")
    print('publish: python tools/publish.py "add memo" --push')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
