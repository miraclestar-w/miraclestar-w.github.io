#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline self-test for content tools (no network, no permanent writes)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siteutil as S


def main() -> int:
    fails = []

    def check(name, cond, detail=""):
        if cond:
            print("OK ", name)
        else:
            print("FAIL", name, detail)
            fails.append(name)

    check("slugify ascii", S.slugify("Hello World") == "hello-world")
    check("needs slug CJK", S.needs_explicit_slug("中文标题", None) is True)
    check("needs slug ok", S.needs_explicit_slug("中文", "cn-title") is False)
    html = S.text_to_html("## T\n\n**b** and `c`\n\n- a\n- b")
    check("md h2", "<h2>" in html)
    check("md strong", "<strong>b</strong>" in html)
    check("md code", "<code>c</code>" in html)
    check("md ul", "<ul>" in html)
    memo = S.memo_html("<script>x</script>", "2026-07-13")
    check("memo escapes html", "<script>" not in memo and "&lt;script&gt;" in memo)
    page = S.build_post_page(
        title='</script><script>alert(1)</script>',
        date="2026-07-13",
        tags=["AI"],
        description="d",
        slug="t",
        body_html="<p>x</p>",
    )
    check("ld escape", "\u003c" in page or "\\u003c" in page or "\u003c/script>" in page)
    ld_line = [ln for ln in page.splitlines() if "ld+json" in ln][0]
    check("ld no raw close", "</script><script>" not in ld_line)

    sm = S.upsert_sitemap_text(
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>\n',
        "/post/a.html",
    )
    check("sitemap insert", "/post/a.html" in sm and sm.count("/post/a.html") == 1)
    sm2 = S.upsert_sitemap_text(sm, "/post/a.html")
    check("sitemap upsert once", sm2.count("/post/a.html") == 1)

    feed = (
        '<?xml version="1.0"?><rss><channel>'
        "<title>t</title><lastBuildDate>x</lastBuildDate>"
        "</channel></rss>"
    )
    feed2 = S.prepend_feed_item(
        feed, title="Hello", slug="h", description="d", date="2026-07-13"
    )
    check("feed item", "<item>" in feed2 and "/post/h.html" in feed2)

    cards = "".join(
        f'<article class="featured-card"><h3>c{i}</h3></article>\n' for i in range(5)
    )
    grid = f'<div class="featured-grid">{cards}</div><p>after</p>'
    trimmed = S.trim_featured_cards(grid, keep=2)
    check(
        "trim featured",
        trimmed.count('<article class="featured-card">') == 2
        and "after" in trimmed
        and "c0" in trimmed
        and "c1" in trimmed
        and "c4" not in trimmed,
    )


    posts = S.parse_posts_from_index()
    check("parse posts", len(posts) >= 1 and "title" in posts[0] and "tags" in posts[0])
    files = S.rebuild_tags_from_post_index(prune_orphans=False)
    check("rebuild tags files", S.TAGS_INDEX in files and len(files) >= 2)
    ai_pages = [path for path in files if path.parent.name == "AI" and path.name == "index.html"]
    check("rebuild has AI", len(ai_pages) == 1 and files[ai_pages[0]].count("post-item") >= 1)

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        f1, f2 = base / "a.txt", base / "b.txt"
        b = S.Batch()
        b.add(f1, "one")
        b.add(f2, "two")
        written = b.commit()
        check("batch write", f1.read_text(encoding="utf-8") == "one" and f2.read_text(encoding="utf-8") == "two")
        check("batch paths", len(written) == 2)

    if fails:
        print("FAILED", len(fails), fails)
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())