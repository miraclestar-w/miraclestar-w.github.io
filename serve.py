#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local static server with clean-URL fallbacks for Miracle site."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.parse
import sys

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        # try direct / directory index / .html
        candidates = []
        rel = path.lstrip("/")
        if not rel:
            candidates.append(ROOT / "index.html")
        else:
            p = ROOT / rel
            candidates.extend([
                p,
                p / "index.html",
                Path(str(p) + ".html"),
                ROOT / (rel.rstrip("/") + ".html"),
            ])
            # /post/foo -> post/foo.html
            if not rel.endswith("/") and not Path(rel).suffix:
                candidates.append(ROOT / f"{rel}.html")
                candidates.append(ROOT / rel / "index.html")

        for c in candidates:
            try:
                c = c.resolve()
                if str(c).startswith(str(ROOT)) and c.is_file():
                    self.path = "/" + c.relative_to(ROOT).as_posix()
                    return SimpleHTTPRequestHandler.do_GET(self)
            except Exception:
                pass
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Miracle preview: http://127.0.0.1:{port}/")
    server.serve_forever()
