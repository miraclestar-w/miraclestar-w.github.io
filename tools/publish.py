#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Commit and optionally push site changes."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="git commit / push")
    ap.add_argument("message")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        code = run(["git", "add", "-A"])
    else:
        paths = [
            "index.html", "memos", "post", "api", "styles", "tags", "archives",
            "sitemap.xml", "feed.xml", "404.html", "scripts", "images",
            "post-images", "media", "tools", "serve.py",
        ]
        code = run(["git", "add", "--"] + paths)
    if code != 0:
        return code

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    names = [n for n in (staged.stdout or "").splitlines() if n.strip()]
    if not names:
        print("no staged changes")
        return 0
    print("staged (%d):" % len(names))
    for n in names[:40]:
        print(" ", n)
    if len(names) > 40:
        print("  ... +%d more" % (len(names) - 40))

    code = run(["git", "commit", "-m", args.message])
    if code != 0:
        return code

    if args.push:
        code = run(["git", "push", "origin", "HEAD"])
        if code != 0:
            return code
        print("pushed (GitHub Pages will update shortly)")
    else:
        print("committed. push: git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
