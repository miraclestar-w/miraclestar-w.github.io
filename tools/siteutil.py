# -*- coding: utf-8 -*-
"""Shared helpers for Miracle static site content tools."""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://miraclestar-w.github.io"
TZ = timezone(timedelta(hours=8))

POST_DIR = ROOT / "post"
MEMOS = ROOT / "memos" / "index.html"
HOME = ROOT / "index.html"
POST_INDEX = POST_DIR / "index.html"
ARCHIVES = ROOT / "archives" / "index.html"
TAGS_DIR = ROOT / "tags"
TAGS_INDEX = TAGS_DIR / "index.html"
TAG_MIN_COUNT = 2  # only publish tags that appear at least N times
TAG_MAX_PUBLISH = 18  # hard cap on tag index/detail pages
HOME_TAG_CLOUD_MAX = 10
SEARCH_JSON = ROOT / "api" / "search.json"
SITEMAP = ROOT / "sitemap.xml"
FEED = ROOT / "feed.xml"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "post.html"
CSS_FILE = ROOT / "styles" / "custom.css"


def now() -> datetime:
    return datetime.now(TZ)


def today_str(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d")


def iso_now(dt: datetime | None = None) -> str:
    d = dt or now()
    return d.strftime("%Y-%m-%dT%H:%M:%S") + "+08:00"


def rfc822(dt: datetime | None = None) -> str:
    d = dt or now()
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    return format_datetime(d)


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def tag_href(tag: str) -> str:
    """Build tag URL path; keep Chinese path segments unescaped for existing dirs."""
    t = (tag or "").strip()
    return f"/tags/{t}/"


def detect_css_version() -> str:
    for path in (HOME, CSS_FILE):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"custom\.css\?v=([0-9a-zA-Z]+)", text)
        if m:
            return m.group(1)
    # fallback: mtime stamp
    if CSS_FILE.exists():
        return now().strftime("%Y%m%d%H%M")
    return "20260713ai"


def slugify(title: str, explicit: str | None = None) -> str:
    if explicit:
        s = explicit.strip().lower()
    else:
        s = title.strip().lower()
        s = re.sub(r"[^a-z0-9\s\-_]+", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s).strip("-")
    s = re.sub(r"[^a-z0-9\-]+", "-", (s or "").lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def needs_explicit_slug(title: str, explicit: str | None) -> bool:
    if explicit and slugify(title, explicit):
        return False
    return not slugify(title, None)


def unique_slug(base: str) -> str:
    if not base:
        base = f"post-{now().strftime('%Y%m%d-%H%M')}"
    candidate = base
    n = 2
    while (POST_DIR / f"{candidate}.html").exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def text_to_html(body: str) -> str:
    body = body.replace("\r\n", "\n").strip()
    if not body:
        return "<p></p>"
    parts: list[str] = []
    chunks = re.split(r"(```[\s\S]*?```)", body)
    for chunk in chunks:
        if chunk.startswith("```") and chunk.endswith("```") and len(chunk) >= 6:
            inner = chunk[3:-3]
            if "\n" in inner:
                _lang, _, code = inner.partition("\n")
                code = code.rstrip("\n")
            else:
                code = inner
            parts.append(f"<pre><code>{esc(code)}</code></pre>")
        else:
            block = _inline_blocks(chunk)
            if block:
                parts.append(block)
    return "\n".join(parts) if parts else "<p></p>"


def _inline_blocks(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    buf: list[str] = []
    list_type: str | None = None
    list_items: list[str] = []

    def flush_para() -> None:
        nonlocal buf
        if not buf:
            return
        para = " ".join(x.strip() for x in buf if x.strip())
        if para:
            out.append(f"<p>{_inline(para)}</p>")
        buf = []

    def flush_list() -> None:
        nonlocal list_type, list_items
        if not list_items or not list_type:
            list_type, list_items = None, []
            return
        tag = "ul" if list_type == "ul" else "ol"
        items = "".join(f"<li>{_inline(i)}</li>\n" for i in list_items)
        out.append(f"<{tag}>\n{items}</{tag}>")
        list_type, list_items = None, []

    for line in lines:
        raw = line.rstrip()
        if not raw.strip():
            flush_list()
            flush_para()
            continue
        if raw.startswith("### "):
            flush_list(); flush_para()
            out.append(f"<h3>{_inline(raw[4:].strip())}</h3>")
            continue
        if raw.startswith("## "):
            flush_list(); flush_para()
            out.append(f"<h2>{_inline(raw[3:].strip())}</h2>")
            continue
        if raw.startswith("# "):
            flush_list(); flush_para()
            out.append(f"<h2>{_inline(raw[2:].strip())}</h2>")
            continue
        m = re.match(r"^[-*]\s+(.+)$", raw)
        if m:
            flush_para()
            if list_type not in (None, "ul"):
                flush_list()
            list_type = "ul"
            list_items.append(m.group(1).strip())
            continue
        m = re.match(r"^\d+\.\s+(.+)$", raw)
        if m:
            flush_para()
            if list_type not in (None, "ol"):
                flush_list()
            list_type = "ol"
            list_items.append(m.group(1).strip())
            continue
        if raw.startswith("> "):
            flush_list(); flush_para()
            out.append(f"<blockquote><p>{_inline(raw[2:].strip())}</p></blockquote>")
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", raw.strip())
        if m:
            flush_list(); flush_para()
            alt, src = m.group(1), m.group(2)
            out.append(
                f'<p><img src="{esc(src)}" alt="{esc(alt)}" class="article-img"></p>'
            )
            continue
        flush_list()
        buf.append(raw)

    flush_list()
    flush_para()
    return "\n".join(out)


def _inline(text: str) -> str:
    codes: list[str] = []

    def save_code(m: re.Match) -> str:
        codes.append(f"<code>{esc(m.group(1))}</code>")
        return f"\x00C{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", save_code, text)
    text = esc(text)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    for i, c in enumerate(codes):
        text = text.replace(f"\x00C{i}\x00", c)
    return text


def memo_html(content: str, date: str, *, allow_html: bool = False) -> str:
    body = content.strip()
    if allow_html and "<" in body:
        html_body = body
    else:
        # always escape; preserve blank-line paragraphs and single newlines as <br>
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if not paras:
            html_body = "<p></p>"
        elif len(paras) == 1:
            lines = [ln.strip() for ln in paras[0].split("\n") if ln.strip()]
            html_body = f"<p>{'<br />\n'.join(_inline(x) for x in lines)}</p>"
        else:
            chunks = []
            for p in paras:
                lines = [ln.strip() for ln in p.split("\n") if ln.strip()]
                chunks.append(f"<p>{'<br />\n'.join(_inline(x) for x in lines)}</p>")
            html_body = "\n".join(chunks)

    return (
        f'    <div class="memo-item" data-created="{esc(date)}">\n'
        f'      <div class="memo-item__marker"></div>\n'
        f'      <div class="memo-item__card">\n'
        f'        <div class="memo-item__content article-content">\n'
        f"          {html_body}\n\n"
        f"        </div>\n"
        f'        <time class="memo-item__date meta-text">{esc(date)}</time>\n'
        f"      </div>\n"
        f"    </div>\n"
    )


def insert_after_marker(text: str, marker: str, insertion: str) -> str:
    i = text.find(marker)
    if i < 0:
        raise ValueError(f"marker not found: {marker!r}")
    j = i + len(marker)
    return text[:j] + "\n" + insertion + text[j:]


def build_post_page(
    *,
    title: str,
    date: str,
    tags: list[str],
    description: str,
    slug: str,
    body_html: str,
) -> str:
    css_v = detect_css_version()
    tags_str = ", ".join(tags)
    published = published_tag_set()
    tag_bits = []
    for t in tags:
        t = (t or "").strip()
        if not t:
            continue
        if t in published:
            tag_bits.append(
                f'            <a href="{esc(tag_href(t))}" class="article-tag">{esc(t)}</a>'
            )
        else:
            tag_bits.append(
                f'            <a href="/tags/" class="article-tag article-tag--soft" title="浏览全部标签">{esc(t)}</a>'
            )
    tags_html = "\n".join(tag_bits)
    url = f"{SITE}/post/{slug}.html"
    tags_meta = "\n".join(
        f'<meta property="article:tag" content="{esc(t)}">' for t in tags
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "datePublished": date,
        "author": {"@type": "Person", "name": "Miracle", "url": SITE},
        "mainEntityOfPage": url,
        "url": url,
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")

    tpl = TEMPLATE.read_text(encoding="utf-8")
    repl = {
        "{{TITLE}}": esc(title),
        "{{TITLE_RAW_COMMENT}}": title.replace("-->", "--\\>"),
        "{{DATE}}": esc(date),
        "{{TAGS}}": esc(tags_str),
        "{{TAGS_HTML}}": tags_html,
        "{{TAGS_RAW_COMMENT}}": tags_str.replace("-->", "--\\>"),
        "{{DESCRIPTION}}": esc(description),
        "{{DESCRIPTION_RAW_COMMENT}}": description.replace("-->", "--\\>"),
        "{{SLUG}}": esc(slug),
        "{{URL}}": url,
        "{{CSS_V}}": css_v,
        "{{TAGS_META}}": tags_meta,
        "{{LD_JSON}}": ld_json,
        "{{BODY}}": body_html,
        "{{SITE}}": SITE,
    }
    page = tpl
    for k, v in repl.items():
        page = page.replace(k, v)
    if "{{" in page:
        leftovers = re.findall(r"\{\{[A-Z_]+\}\}", page)
        raise RuntimeError(f"unreplaced template tokens: {leftovers}")
    return page


def post_list_item(
    title: str, date: str, slug: str, excerpt: str, tags: list[str]
) -> str:
    mmdd = date[5:] if len(date) >= 10 else date
    year = date[:4] if len(date) >= 4 else str(now().year)
    published = published_tag_set()
    kw_parts = []
    for t in tags[:4]:
        t = (t or "").strip()
        if not t:
            continue
        if t in published:
            kw_parts.append(
                f'          <a href="{esc(tag_href(t))}" class="tag">{esc(t)}</a>'
            )
        else:
            kw_parts.append(
                f'          <a href="/tags/" class="tag tag--soft" title="browse tags">{esc(t)}</a>'
            )
    kw = "\n".join(kw_parts)
    return f"""    <article class="post-item">
      <div class="post-item__rail" aria-hidden="true"></div>
      <time class="post-item__date" datetime="{esc(date)}">
        <span class="post-item__day">{esc(mmdd)}</span>
        <span class="post-item__year">{esc(year)}</span>
      </time>
      <div class="post-item__body">
        <h2 class="post-item__title"><a href="/post/{esc(slug)}.html">{esc(title)}</a></h2>
        <p class="post-item__excerpt">{esc(excerpt)}</p></div>
      <aside class="post-item__keywords" aria-label="keywords">
{kw}
      </aside>
    </article>
"""


def featured_card(
    title: str, date: str, slug: str, excerpt: str, tag: str
) -> str:
    return f"""<article class="featured-card">
          <div class="featured-card-header">
            <span class="featured-tag">{esc(tag)}</span>
            <span class="featured-date">{esc(date)}</span>
          </div>
          <h3 class="featured-title">
            <a href="/post/{esc(slug)}.html">{esc(title)}</a>
          </h3>
          <p class="featured-excerpt">{esc(excerpt)}</p>
          <a href="/post/{esc(slug)}.html" class="featured-read">阅读全文 →</a>
        </article>

"""


def prepend_search(title: str, slug: str, content: str) -> str:
    data = json.loads(SEARCH_JSON.read_text(encoding="utf-8"))
    entry = {
        "title": title,
        "url": f"/post/{slug}.html",
        "content": re.sub(r"\\s+", " ", content).strip()[:2000],
    }
    data = [e for e in data if e.get("url") != entry["url"]]
    data.insert(0, entry)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def upsert_sitemap_text(text: str, path_url: str, priority: str = "0.8") -> str:
    text = text.replace("https:/KEEP:/", "https://")
    loc = f"{SITE}{path_url}"
    lastmod = iso_now()
    block = (
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>\n"
    )
    text = re.sub(
        r"  <url>\s*<loc>" + re.escape(loc) + r"</loc>.*?</url>\s*",
        "",
        text,
        flags=re.S,
    )
    m = re.search(r"<urlset[^>]*>\s*", text)
    if not m:
        raise RuntimeError("sitemap urlset not found")
    return text[: m.end()] + block + text[m.end() :]


def prepend_feed_item(
    text: str, *, title: str, slug: str, description: str, date: str
) -> str:
    link = f"{SITE}/post/{slug}.html"
    text = re.sub(
        r"\s*<item>.*?<link>" + re.escape(link) + r"</link>.*?</item>",
        "",
        text,
        flags=re.S,
    )
    try:
        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TZ)
    except ValueError:
        dt = now()
    item = (
        "  <item>\n"
        f"    <title>{esc(title)}</title>\n"
        f"    <link>{link}</link>\n"
        f"    <description>{esc(description)}</description>\n"
        f"    <pubDate>{rfc822(dt)}</pubDate>\n"
        f'    <guid isPermaLink="true">{link}</guid>\n'
        "    <dc:creator>Miracle</dc:creator>\n"
        "  </item>\n"
    )
    text = re.sub(
        r"<lastBuildDate>[^<]*</lastBuildDate>",
        f"<lastBuildDate>{rfc822(now())}</lastBuildDate>",
        text,
        count=1,
    )
    m = re.search(r"<lastBuildDate>[^<]*</lastBuildDate>\s*", text)
    if m:
        return text[: m.end()] + item + text[m.end() :]
    m = re.search(r"<channel>\s*", text)
    if not m:
        raise RuntimeError("feed channel not found")
    return text[: m.end()] + item + text[m.end() :]


def trim_featured_cards(home_html: str, keep: int = 12) -> str:
    """Keep only first N featured-card articles inside featured-grid."""
    m = re.search(
        r'<div[^>]*class="[^"]*featured-grid[^"]*"[^>]*>',
        home_html,
    )
    if not m:
        return home_html
    start = m.end()
    # find matching close for featured-grid by scanning article cards
    cards = list(
        re.finditer(
            r'<article class="featured-card">.*?</article>\s*',
            home_html[start:],
            flags=re.S,
        )
    )
    if len(cards) <= keep:
        return home_html
    # rebuild: open tag + first keep cards + rest after last card
    last = cards[-1]
    grid_end_rel = last.end()
    # find </div> that closes grid after last card
    tail_search = home_html[start + grid_end_rel :]
    close = re.match(r'\s*</div>', tail_search)
    if not close:
        # still rewrite card region only
        new_body = "\n" + "".join(c.group(0) for c in cards[:keep])
        return home_html[:start] + new_body + home_html[start + cards[keep].start() :]
    new_body = "\n" + "".join(c.group(0) for c in cards[:keep]) + "\n"
    end = start + grid_end_rel + close.end()
    return home_html[: m.start()] + m.group(0) + new_body + "</div>" + home_html[end:]




@dataclass
class WriteOp:
    path: Path
    content: str


@dataclass
class Batch:
    ops: list[WriteOp] | None = None

    def __post_init__(self):
        if self.ops is None:
            self.ops = []

    def add(self, path: Path, content: str) -> None:
        self.ops.append(WriteOp(path, content))

    def commit(self) -> list:
        """Write all to .tmp then replace (best-effort atomic batch)."""
        tmps = []
        written = []
        try:
            for op in self.ops:
                op.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = op.path.with_name(op.path.name + ".tmp")
                tmp.write_text(op.content, encoding="utf-8", newline="\n")
                tmps.append((tmp, op.path))
            for tmp, final in tmps:
                tmp.replace(final)
                written.append(final)
            return written
        except Exception:
            for tmp, _ in tmps:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
            raise



def parse_posts_from_index(idx: str | None = None) -> list[dict]:
    """Parse post list items from post/index.html markup."""
    if idx is None:
        idx = POST_INDEX.read_text(encoding="utf-8")
    items: list[dict] = []
    for m in re.finditer(r'<article class="post-item">([\s\S]*?)</article>', idx):
        block = m.group(1)
        dm = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', block)
        tm = re.search(r'post-item__title"><a href="([^"]+)">([^<]+)</a>', block)
        em = re.search(r'post-item__excerpt">([^<]*)', block)
        tags = re.findall(r'class="tag">([^<]+)</a>', block)
        if not (dm and tm):
            continue
        href = tm.group(1)
        slug = href
        if slug.startswith("/post/"):
            slug = slug[len("/post/") :]
        if slug.endswith(".html"):
            slug = slug[: -len(".html")]
        items.append(
            {
                "date": dm.group(1),
                "href": href,
                "title": tm.group(2),
                "excerpt": em.group(1) if em else "",
                "year": dm.group(1)[:4],
                "tags": tags,
                "slug": slug,
            }
        )
    return items


def _chrome_from_post_index(page_title: str, idx: str | None = None) -> tuple[str, str]:
    """Return (head_through_main_open, foot_from_main_close) from post index chrome."""
    if idx is None:
        idx = POST_INDEX.read_text(encoding="utf-8")
    head_m = re.search(r'^(.*?<main class="site-main"[^>]*>)', idx, re.S)
    foot_m = re.search(r'(</main>[\s\S]*)$', idx)
    if not head_m or not foot_m:
        raise RuntimeError("cannot split post index chrome")
    head = head_m.group(1).replace('class="nav-item active"', 'class="nav-item"')
    head = re.sub(
        r"<title>.*?</title>",
        f"<title>{esc(page_title)}</title>",
        head,
        count=1,
        flags=re.S,
    )
    return head, foot_m.group(1)


def rebuild_archives_from_post_index(idx: str | None = None) -> str:
    """Rebuild archives/index.html from current post list (UTF-8 safe)."""
    if idx is None:
        idx = POST_INDEX.read_text(encoding="utf-8")
    items = parse_posts_from_index(idx)
    head, foot = _chrome_from_post_index("归档 | Miracle", idx)

    by_year: dict[str, list[dict]] = {}
    for it in items:
        by_year.setdefault(it["year"], []).append(it)
    years = sorted(by_year.keys(), reverse=True)

    page_title = "归档"
    subtitle = f"共 {len(items)} 篇文章，按时间归档。"
    parts: list[str] = [
        '\n    <div class="container">\n',
        '  <div class="page-header">\n',
        f'    <h1 class="page-title">{page_title}</h1>\n',
        f'    <p class="page-subtitle">{subtitle}</p>\n',
        "  </div>\n\n",
        '  <div class="archive-list" role="list">\n',
    ]
    for y in years:
        parts.append(f'    <div class="timeline-year"><span>{esc(y)}</span></div>\n')
        for it in by_year[y]:
            parts.append('    <article class="archive-item" role="listitem">\n')
            parts.append(
                f'      <time class="archive-item__date" datetime="{esc(it["date"])}">{esc(it["date"])}</time>\n'
            )
            parts.append(
                f'      <h2 class="archive-item__title"><a href="{esc(it["href"])}">{esc(it["title"])}</a></h2>\n'
            )
            if it["excerpt"]:
                parts.append(
                    f'      <p class="archive-item__excerpt">{esc(it["excerpt"])}</p>\n'
                )
            parts.append("    </article>\n")
    parts.append("  </div>\n</div>\n\n  ")
    return head + "".join(parts) + foot


def tag_mark(tag: str) -> str:
    """Short monogram for tag cards (1-2 chars). Consistent, premium, no emoji soup."""
    t = (tag or "").strip()
    if not t:
        return "#"
    # curated short marks for common tags
    marks = {
        "AI": "AI",
        "Agent": "Ag",
        "AI Agent": "AA",
        "Apple": "Ap",
        "Windows": "Win",
        "Microsoft": "MS",
        "GitHub": "GH",
        "Cloudflare": "CF",
        "Docker": "Dk",
        "DevOps": "DO",
        "Prometheus": "Pr",
        "Grafana": "Gr",
        "Kubernetes": "K8",
        "eBPF": "eB",
        "Beats": "Bt",
        "GLM-5.2": "GL",
    }
    # Chinese curated
    marks["安全"] = "安"  # ??
    marks["开源"] = "开"  # ??
    marks["零日漏洞"] = "?"  # ????
    marks["智谱"] = "智"  # ??
    marks["蓝牙"] = "BT"  # ??
    marks["安全漏洞"] = "漏"  # ????
    marks["运维"] = "Ops"
    marks["可观测性"] = "Obs"
    if t in marks:
        return marks[t]
    # ASCII multi-word: initials
    if re.search(r"[A-Za-z]", t) and (" " in t or "-" in t or "_" in t):
        parts = re.split(r"[\s\-_]+", t)
        initials = "".join(p[0] for p in parts if p)[:2]
        return initials.upper() if initials else t[:2].upper()
    # pure ASCII word
    if re.fullmatch(r"[A-Za-z0-9.+]+", t):
        return t[:2].upper() if len(t) <= 3 else (t[:2].upper())
    # CJK: first char
    for ch in t:
        if "一" <= ch <= "鿿":
            return ch
    return t[:1].upper()


def tag_icon(tag: str) -> str:
    """Back-compat alias."""
    return tag_mark(tag)


def _tag_card_html(tag: str, count: int) -> str:
    """Unified editorial tag card: accent bar + name + count only."""
    colors = (
        "#3D8B8C",
        "#1E4F8C",
        "#4A6FA5",
        "#5B6EAE",
        "#2F6F6A",
        "#6B4E9B",
        "#3D6B8C",
        "#5672A8",
    )
    color = colors[sum(ord(c) for c in tag) % len(colors)]
    return (
        f'    <a class="tag-card" href="{esc(tag_href(tag))}" style="--tag-color:{color}">\n'
        f'      <span class="tag-card__name">{esc(tag)}</span>\n'
        f'      <span class="tag-card__count">{count}</span>\n'
        f"    </a>\n"
    )


def select_published_tags(by_tag: dict[str, list]) -> list[tuple[str, list]]:
    """Keep only frequent tags, hard-capped ? avoids 100+ one-off tag pages."""
    ranked = sorted(by_tag.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))
    filtered = [(t, pl) for t, pl in ranked if len(pl) >= TAG_MIN_COUNT]
    if not filtered:
        # fallback: top N even if sparse
        filtered = ranked[: min(TAG_MAX_PUBLISH, len(ranked))]
    return filtered[:TAG_MAX_PUBLISH]


def published_tag_set(idx: str | None = None) -> set[str]:
    posts = parse_posts_from_index(idx)
    by_tag: dict[str, list] = {}
    for p in posts:
        for t in p["tags"]:
            t = (t or "").strip()
            if t:
                by_tag.setdefault(t, []).append(p)
    return {t for t, _ in select_published_tags(by_tag)}


def rebuild_tags_from_post_index(
    idx: str | None = None, *, prune_orphans: bool = True
) -> dict[Path, str]:
    """Build restrained tags index + per-tag list pages. Returns path->content."""
    if idx is None:
        idx = POST_INDEX.read_text(encoding="utf-8")
    posts = parse_posts_from_index(idx)

    by_tag: dict[str, list[dict]] = {}
    for p in posts:
        for t in p["tags"]:
            t = (t or "").strip()
            if not t:
                continue
            by_tag.setdefault(t, []).append(p)

    ranked = select_published_tags(by_tag)
    published = {t for t, _ in ranked}

    files: dict[Path, str] = {}

    # --- tags/index.html ---
    head, foot = _chrome_from_post_index("标签 | Miracle", idx)
    parts = [
        '\n    <div class="container">\n',
        '  <div class="tags-page">\n',
        '  <div class="page-header">\n',
        '    <h1 class="page-title">标签</h1>\n',
        f'    <p class="page-subtitle">精选 {len(ranked)} 个标签 · {len(posts)} 篇文章'
        f' · 仅展示出现≥{TAG_MIN_COUNT}次的主题</p>\n',
        "  </div>\n\n",
        '  <div class="tags-grid" role="list">\n',
    ]
    for tag, plist in ranked:
        parts.append(_tag_card_html(tag, len(plist)))
    parts.append("  </div>\n  </div>\n</div>\n\n  ")
    files[TAGS_INDEX] = head + "".join(parts) + foot

    # --- tags/<tag>/index.html ---
    for tag, plist in ranked:
        page_title = f"{tag} | 标签 | Miracle"
        thead, tfoot = _chrome_from_post_index(page_title, idx)
        # only show published tags in keyword chips
        body: list[str] = [
            '\n    <div class="container">\n',
            '  <div class="page-header">\n',
            f'    <h1 class="page-title">#{esc(tag)}</h1>\n',
            f'    <p class="page-subtitle">共 {len(plist)} 篇文章 · '
            f'<a href="/tags/" class="page-back">全部标签</a></p>\n',
            "  </div>\n\n",
            '  <div class="post-list tag-post-list" role="list">\n',
        ]
        seen: set[str] = set()
        for p in plist:
            key = p["href"]
            if key in seen:
                continue
            seen.add(key)
            # filter keyword links to published tags only
            kw = [t for t in p["tags"] if t in published] or [tag]
            body.append(
                post_list_item(
                    p["title"],
                    p["date"],
                    p["slug"],
                    p["excerpt"],
                    kw,
                )
            )
        body.append("  </div>\n</div>\n\n  ")
        tag_path = TAGS_DIR / tag / "index.html"
        files[tag_path] = thead + "".join(body) + tfoot

    if prune_orphans and TAGS_DIR.exists():
        keep_dirs = {TAGS_DIR.resolve()}
        for p in files:
            if p.name == "index.html" and p.parent != TAGS_DIR:
                keep_dirs.add(p.parent.resolve())
        for child in list(TAGS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if child.resolve() not in keep_dirs:
                for sub in child.rglob("*"):
                    if sub.is_file():
                        try:
                            sub.unlink()
                        except OSError:
                            pass
                try:
                    for sub in sorted(child.rglob("*"), reverse=True):
                        if sub.is_dir():
                            try:
                                sub.rmdir()
                            except OSError:
                                pass
                    child.rmdir()
                except OSError:
                    pass

    return files


def rebuild_home_tag_cloud(home_html: str | None = None, idx: str | None = None) -> str:
    """Replace homepage tags-cloud with top published tags."""
    if home_html is None:
        home_html = HOME.read_text(encoding="utf-8")
    if idx is None:
        idx = POST_INDEX.read_text(encoding="utf-8")
    posts = parse_posts_from_index(idx)
    by_tag: dict[str, list] = {}
    for p in posts:
        for t in p["tags"]:
            t = (t or "").strip()
            if t:
                by_tag.setdefault(t, []).append(p)
    ranked = select_published_tags(by_tag)[:HOME_TAG_CLOUD_MAX]
    items = []
    for tag, _plist in ranked:
        items.append(
            f'        <a class="tag-cloud-item" href="{esc(tag_href(tag))}">{esc(tag)}</a>'
        )
    block = '<div class="tags-cloud">\n' + "\n".join(items) + "\n      </div>"
    new_html, n = re.subn(
        r'<div class="tags-cloud">[\s\S]*?</div>',
        block,
        home_html,
        count=1,
    )
    if n != 1:
        raise RuntimeError("tags-cloud block not found on homepage")
    return new_html


def apply_new_post(
    *,
    title: str,
    date: str,
    tags: list[str],
    excerpt: str,
    slug: str,
    body_html: str,
    plain: str,
    update_home: bool = True,
) -> list[Path]:
    page = build_post_page(
        title=title,
        date=date,
        tags=tags,
        description=excerpt,
        slug=slug,
        body_html=body_html,
    )
    list_item = post_list_item(title, date, slug, excerpt, tags)
    card = featured_card(title, date, slug, excerpt, tags[0] if tags else "note")

    idx_html = POST_INDEX.read_text(encoding="utf-8")
    year = (date or "")[:4]
    year_block = f'<div class="timeline-year"><span>{esc(year)}</span></div>\n' if year else ""
    # Prefer insert under matching year; create year header if missing.
    if year and f'<div class="timeline-year"><span>{year}</span></div>' in idx_html:
        marker = f'<div class="timeline-year"><span>{year}</span></div>'
        pos = idx_html.find(marker)
        end = pos + len(marker)
        idx_html = idx_html[:end] + "\n" + list_item + idx_html[end:]
    else:
        needle = '<div class="post-list" role="list">'
        if needle not in idx_html:
            raise RuntimeError("post list marker not found")
        insert = (year_block if year else "") + list_item
        # If other years exist, still prepend at top of list
        idx_html = idx_html.replace(needle, needle + "\n" + insert, 1)

    home = HOME.read_text(encoding="utf-8")
    if update_home:
        marker = 'class="featured-grid"'
        pos = home.find(marker)
        if pos < 0:
            raise RuntimeError("featured-grid not found on homepage")
        gt = home.find(">", pos)
        home = home[: gt + 1] + "\n" + card + home[gt + 1 :]
        home = trim_featured_cards(home, keep=12)
    home = rebuild_home_tag_cloud(home, idx_html)

    search = prepend_search(title, slug, plain)
    sitemap = upsert_sitemap_text(
        SITEMAP.read_text(encoding="utf-8"), f"/post/{slug}.html"
    )
    feed = prepend_feed_item(
        FEED.read_text(encoding="utf-8"),
        title=title,
        slug=slug,
        description=excerpt,
        date=date,
    )

    batch = Batch()
    batch.add(POST_DIR / f"{slug}.html", page)
    batch.add(POST_INDEX, idx_html)
    batch.add(ARCHIVES, rebuild_archives_from_post_index(idx_html))
    for tpath, tcontent in rebuild_tags_from_post_index(
        idx_html, prune_orphans=False
    ).items():
        batch.add(tpath, tcontent)
    if update_home:
        batch.add(HOME, home)
    batch.add(SEARCH_JSON, search)
    batch.add(SITEMAP, sitemap)
    batch.add(FEED, feed)
    written = batch.commit()
    # prune orphans after successful write (uses disk post index which matches idx_html)
    rebuild_tags_from_post_index(idx_html, prune_orphans=True)
    return written


def apply_new_memo(content: str, date: str, *, allow_html: bool = False) -> list[Path]:
    html_doc = MEMOS.read_text(encoding="utf-8")
    marker = '<div class="memo-timeline">'
    if marker not in html_doc:
        raise RuntimeError("memo-timeline not found")
    block = memo_html(content, date, allow_html=allow_html)
    new_html = insert_after_marker(html_doc, marker, "\n" + block)
    batch = Batch()
    batch.add(MEMOS, new_html)
    return batch.commit()
