# Miracle local content tools

No server needed. Edit static files locally -> preview -> git push.

## Preview

```powershell
cd D:\Desktop\mk\miraclestar-w.github.io
python serve.py 5500
```

Open: http://127.0.0.1:5500/

## Add memo (闪念)

```powershell
python tools/new_memo.py "today tried agent-browser"
python tools/new_memo.py -f note.txt
python tools/new_memo.py --date 2026-07-13 "content"
python tools/new_memo.py --html "<p>raw html</p>"
```

Preview: http://127.0.0.1:5500/memos/

## Add post

```powershell
# English title can auto-slug; Chinese/non-ASCII title REQUIRES --slug
python tools/new_post.py --title "My title" --slug my-title --tags AI,Agent --excerpt "summary" --body "hello"

# body from file (recommended)
python tools/new_post.py --title "中文标题" --slug english-slug --tags AI -f body.md

# dry-run (no write)
python tools/new_post.py --title "Demo" --slug demo --body "hi" --dry-run
```

Auto updates:
1. `post/<slug>.html` (from `tools/templates/post.html`)
2. blog list `/post/`
3. home featured card
4. `api/search.json`
5. `sitemap.xml`
6. `feed.xml`

Light Markdown: headings, lists, bold, code, fences, links.

## Publish

```powershell
python tools/publish.py "add memo"
python tools/publish.py "add post: title" --push
```

`publish.py` prints staged files before commit.

## Self-test

```powershell
python tools/selftest.py
```

## Notes

- No online editor (static GitHub Pages — no server)
- Tag pages under `/tags/...` are not auto-created
- Chinese titles must pass English `--slug`
- UI: Mondrian system in `styles/custom.css` only (cache query `?v=` after CSS changes)
- Content width 1240px; article reading column ~860–880px