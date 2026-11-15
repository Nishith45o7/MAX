"""
actions/bookmark_manager.py
Save, search, tag, and organize bookmarks — inspired by karkeep.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("bookmark_manager")
USER_AGENT = "MAX-MARK-I/1.0"
TIMEOUT = 4.0


def _db_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "memory" / "bookmarks.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _init_db():
    conn = sqlite3.connect(str(_db_path()))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            favicon_url TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _fetch_title(url: str) -> str:
    """Fetch page title from URL."""
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT},
                            allow_redirects=True)
        if resp.status_code == 200:
            from html.parser import HTMLParser
            class TitleParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_title = False
                    self.title = ""
                def handle_starttag(self, tag, attrs):
                    if tag.lower() == "title":
                        self.in_title = True
                def handle_data(self, data):
                    if self.in_title:
                        self.title += data
                def handle_endtag(self, tag):
                    if tag.lower() == "title":
                        self.in_title = False
            parser = TitleParser()
            parser.feed(resp.text[:10000])
            return parser.title.strip()[:200] or url
    except Exception:
        pass
    return ""


def bookmark_manager(parameters: dict, player=None) -> str:
    """Bookmark management engine."""
    action = (parameters.get("action") or "list").strip().lower()
    aliases = {"add": "save", "store": "save", "new": "save", "find": "search", "remove": "delete"}
    action = aliases.get(action, action)
    conn = _init_db()

    try:
        if action == "save":
            url = (parameters.get("url") or "").strip()
            if not url:
                return "URL is required to save a bookmark."
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            title = parameters.get("title", "").strip()
            if not title:
                title = _fetch_title(url) or url
            desc = parameters.get("description", "").strip()
            tags = parameters.get("tags", "").strip()
            favicon = f"https://www.google.com/s2/favicons?domain={url.split('/')[2]}&sz=32"
            try:
                conn.execute(
                    "INSERT INTO bookmarks (url, title, description, tags, favicon_url) VALUES (?, ?, ?, ?, ?)",
                    (url, title, desc, tags, favicon)
                )
                conn.commit()
                return f"🔖 Saved bookmark: {title}\n  URL: {url}\n  Tags: {tags or 'none'}"
            except sqlite3.IntegrityError:
                conn.execute(
                    "UPDATE bookmarks SET title=?, description=?, tags=? WHERE url=?",
                    (title, desc, tags, url)
                )
                conn.commit()
                return f"🔖 Updated existing bookmark: {title}"

        elif action == "list":
            limit = int(parameters.get("limit", 20))
            tag_filter = parameters.get("tag", "").strip().lower()
            if tag_filter:
                rows = conn.execute(
                    "SELECT id, url, title, tags, created_at FROM bookmarks WHERE LOWER(tags) LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{tag_filter}%", limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, url, title, tags, created_at FROM bookmarks ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            if not rows:
                return "No bookmarks saved yet. Use action 'save' with a URL."
            lines = [f"🔖 Bookmarks ({len(rows)}):\n"]
            for row in rows:
                tags_str = f" [{row[3]}]" if row[3] else ""
                lines.append(f"  #{row[0]} {row[2]}{tags_str}\n     {row[1]}")
            return "\n".join(lines)

        elif action == "search":
            query = (parameters.get("query") or "").strip().lower()
            if not query:
                return "Search query is required."
            rows = conn.execute(
                "SELECT id, url, title, tags, description FROM bookmarks "
                "WHERE LOWER(title) LIKE ? OR LOWER(url) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ? "
                "ORDER BY created_at DESC LIMIT 20",
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
            ).fetchall()
            if not rows:
                return f"No bookmarks matching '{query}'."
            lines = [f"🔍 {len(rows)} bookmarks matching '{query}':\n"]
            for row in rows:
                tags_str = f" [{row[3]}]" if row[3] else ""
                lines.append(f"  #{row[0]} {row[2]}{tags_str}\n     {row[1]}")
            return "\n".join(lines)

        elif action == "delete":
            bid = parameters.get("id") or parameters.get("bookmark_id", "")
            url = parameters.get("url", "")
            if bid:
                conn.execute("DELETE FROM bookmarks WHERE id=?", (int(bid),))
            elif url:
                conn.execute("DELETE FROM bookmarks WHERE url=?", (url,))
            else:
                return "Provide 'id' or 'url' to delete."
            conn.commit()
            return f"🗑️ Bookmark deleted."

        elif action == "tag":
            bid = parameters.get("id") or parameters.get("bookmark_id", "")
            tags = parameters.get("tags", "").strip()
            if not bid:
                return "Bookmark 'id' is required."
            row = conn.execute("SELECT tags FROM bookmarks WHERE id=?", (int(bid),)).fetchone()
            if not row:
                return f"Bookmark #{bid} not found."
            existing = set(t.strip() for t in (row[0] or "").split(",") if t.strip())
            new = set(t.strip() for t in tags.split(",") if t.strip())
            merged = ",".join(sorted(existing | new))
            conn.execute("UPDATE bookmarks SET tags=? WHERE id=?", (merged, int(bid)))
            conn.commit()
            return f"🏷️ Tags updated for bookmark #{bid}: {merged}"

        elif action == "export":
            fmt = (parameters.get("format") or "json").lower()
            rows = conn.execute("SELECT id, url, title, description, tags, created_at FROM bookmarks ORDER BY created_at DESC").fetchall()
            if not rows:
                return "No bookmarks to export."
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "OneDrive" / "Desktop"
            if fmt == "html":
                html_lines = ["<!DOCTYPE NETSCAPE-Bookmark-file-1>", "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">",
                              "<TITLE>MAX Bookmarks</TITLE>", "<H1>MAX Bookmarks Export</H1>", "<DL><p>"]
                for r in rows:
                    html_lines.append(f'  <DT><A HREF="{r[1]}">{r[2]}</A>')
                    if r[3]:
                        html_lines.append(f"  <DD>{r[3]}")
                html_lines.append("</DL><p>")
                out = desktop / "max_bookmarks.html"
                out.write_text("\n".join(html_lines), encoding="utf-8")
                return f"✅ Exported {len(rows)} bookmarks as HTML → {out}"
            else:
                data = [{"id": r[0], "url": r[1], "title": r[2], "description": r[3], "tags": r[4], "created_at": r[5]} for r in rows]
                out = desktop / "max_bookmarks.json"
                out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                return f"✅ Exported {len(rows)} bookmarks as JSON → {out}"

        elif action in ("import", "import_bookmarks"):
            src = parameters.get("path", "")
            if not src or not Path(src).exists():
                return f"File not found: {src}. Provide path to a JSON or HTML bookmarks file."
            content = Path(src).read_text(encoding="utf-8", errors="ignore")
            count = 0
            if src.endswith(".json"):
                data = json.loads(content)
                for item in data:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO bookmarks (url, title, description, tags) VALUES (?, ?, ?, ?)",
                            (item["url"], item.get("title", ""), item.get("description", ""), item.get("tags", ""))
                        )
                        count += 1
                    except Exception:
                        pass
            else:
                import re
                for m in re.finditer(r'HREF="([^"]+)"[^>]*>([^<]*)', content):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO bookmarks (url, title) VALUES (?, ?)",
                            (m.group(1), m.group(2))
                        )
                        count += 1
                    except Exception:
                        pass
            conn.commit()
            return f"✅ Imported {count} bookmarks from {Path(src).name}"

        else:
            return f"Unknown action '{action}'. Available: save, list, search, delete, tag, export, import_bookmarks"

    finally:
        conn.close()


if __name__ == "__main__":
    print(bookmark_manager({"action": "save", "url": "https://github.com", "tags": "code,dev"}))
    print(bookmark_manager({"action": "list"}))

