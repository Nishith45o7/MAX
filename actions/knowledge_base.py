"""
actions/knowledge_base.py
Structured notes, knowledge graph, skill library, and code snippets.
Inspired by anytype-ts, claude-mem, andrej-karpathy/skills, everything-claude-code.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("knowledge_base")


def _db_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "memory" / "knowledge.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _init_db():
    conn = sqlite3.connect(str(_db_path()))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS note_links (
            source_id INTEGER,
            target_id INTEGER,
            relationship TEXT DEFAULT 'relates_to',
            PRIMARY KEY (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES notes(id),
            FOREIGN KEY (target_id) REFERENCES notes(id)
        );
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            instructions TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS code_snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            language TEXT DEFAULT 'python',
            code TEXT DEFAULT '',
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            title, content, tags, category, content='notes', content_rowid='id'
        );
    """)
    conn.commit()
    return conn


def _rebuild_fts(conn):
    """Rebuild FTS index from notes table."""
    try:
        conn.execute("DELETE FROM notes_fts")
        conn.execute("INSERT INTO notes_fts(rowid, title, content, tags, category) SELECT id, title, content, tags, category FROM notes")
        conn.commit()
    except Exception:
        pass


def knowledge_base(parameters: dict, player=None) -> str:
    """Knowledge base, notes, skills, and code snippets."""
    action = (parameters.get("action") or "list_notes").strip().lower()
    aliases = {
        "list": "list_notes", "add": "add_note", "search": "search_notes",
        "get": "get_note", "delete": "delete_note", "link": "link_notes",
        "export": "export_knowledge", "skills": "list_skills", "snippets": "search_snippets"
    }
    action = aliases.get(action, action)
    conn = _init_db()

    try:
        # ── Notes ──
        if action == "add_note":
            title = (parameters.get("title") or "").strip()
            content = (parameters.get("content") or "").strip()
            tags = (parameters.get("tags") or "").strip()
            category = (parameters.get("category") or "general").strip()
            if not title:
                return "Note title is required."
            conn.execute(
                "INSERT INTO notes (title, content, tags, category) VALUES (?, ?, ?, ?)",
                (title, content, tags, category)
            )
            conn.commit()
            _rebuild_fts(conn)
            nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return f"📝 Note #{nid} created: '{title}' [{category}]"

        elif action == "search_notes":
            query = (parameters.get("query") or "").strip()
            if not query:
                return "Search query is required."
            try:
                rows = conn.execute(
                    "SELECT n.id, n.title, n.tags, n.category, n.created_at "
                    "FROM notes_fts f JOIN notes n ON f.rowid = n.id "
                    "WHERE notes_fts MATCH ? ORDER BY rank LIMIT 15",
                    (query,)
                ).fetchall()
            except Exception:
                rows = conn.execute(
                    "SELECT id, title, tags, category, created_at FROM notes "
                    "WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? OR LOWER(tags) LIKE ? "
                    "ORDER BY created_at DESC LIMIT 15",
                    (f"%{query.lower()}%",) * 3
                ).fetchall()
            if not rows:
                return f"No notes matching '{query}'."
            lines = [f"🔍 {len(rows)} notes matching '{query}':\n"]
            for r in rows:
                lines.append(f"  #{r[0]} {r[1]} [{r[3]}] {r[2]} — {r[4]}")
            return "\n".join(lines)

        elif action == "list_notes":
            category = (parameters.get("category") or "").strip().lower()
            limit = int(parameters.get("limit", 20))
            if category:
                rows = conn.execute(
                    "SELECT id, title, tags, category, created_at FROM notes WHERE LOWER(category)=? ORDER BY created_at DESC LIMIT ?",
                    (category, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, tags, category, created_at FROM notes ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            if not rows:
                return "No notes yet. Use action 'add_note' to create one."
            lines = [f"📝 Notes ({len(rows)}):\n"]
            for r in rows:
                tags_str = f" [{r[2]}]" if r[2] else ""
                lines.append(f"  #{r[0]} {r[1]} ({r[3]}){tags_str} — {r[4]}")
            return "\n".join(lines)

        elif action == "get_note":
            nid = parameters.get("id") or parameters.get("note_id", "")
            if not nid:
                return "Note ID is required."
            row = conn.execute("SELECT * FROM notes WHERE id=?", (int(nid),)).fetchone()
            if not row:
                return f"Note #{nid} not found."
            return (
                f"📝 Note #{row[0]}: {row[1]}\n"
                f"Category: {row[4]} | Tags: {row[3] or 'none'}\n"
                f"Created: {row[5]} | Updated: {row[6]}\n\n"
                f"{row[2]}"
            )

        elif action == "delete_note":
            nid = parameters.get("id") or parameters.get("note_id", "")
            if not nid:
                return "Note ID is required."
            conn.execute("DELETE FROM notes WHERE id=?", (int(nid),))
            conn.execute("DELETE FROM note_links WHERE source_id=? OR target_id=?", (int(nid), int(nid)))
            conn.commit()
            _rebuild_fts(conn)
            return f"🗑️ Note #{nid} deleted."

        elif action == "link_notes":
            src = parameters.get("source_id") or parameters.get("from", "")
            tgt = parameters.get("target_id") or parameters.get("to", "")
            rel = (parameters.get("relationship") or "relates_to").strip()
            if not src or not tgt:
                return "source_id and target_id are required."
            conn.execute(
                "INSERT OR REPLACE INTO note_links (source_id, target_id, relationship) VALUES (?, ?, ?)",
                (int(src), int(tgt), rel)
            )
            conn.commit()
            return f"🔗 Linked note #{src} → #{tgt} ({rel})"

        # ── Skills ──
        elif action == "add_skill":
            name = (parameters.get("name") or "").strip()
            desc = (parameters.get("description") or "").strip()
            instructions = (parameters.get("instructions") or "").strip()
            category = (parameters.get("category") or "general").strip()
            if not name:
                return "Skill name is required."
            try:
                conn.execute(
                    "INSERT INTO skills (name, description, instructions, category) VALUES (?, ?, ?, ?)",
                    (name, desc, instructions, category)
                )
                conn.commit()
                return f"🧩 Skill '{name}' added [{category}]."
            except sqlite3.IntegrityError:
                conn.execute(
                    "UPDATE skills SET description=?, instructions=?, category=? WHERE name=?",
                    (desc, instructions, category, name)
                )
                conn.commit()
                return f"🧩 Skill '{name}' updated."

        elif action == "list_skills":
            rows = conn.execute("SELECT id, name, category, description FROM skills ORDER BY name").fetchall()
            if not rows:
                return "No skills saved. Use 'add_skill' to create one."
            lines = [f"🧩 Skills ({len(rows)}):\n"]
            for r in rows:
                lines.append(f"  #{r[0]} {r[1]} [{r[2]}] — {r[3][:60]}")
            return "\n".join(lines)

        elif action == "get_skill":
            name = (parameters.get("name") or "").strip()
            sid = parameters.get("id")
            if sid:
                row = conn.execute("SELECT * FROM skills WHERE id=?", (int(sid),)).fetchone()
            elif name:
                row = conn.execute("SELECT * FROM skills WHERE LOWER(name)=?", (name.lower(),)).fetchone()
            else:
                return "Provide skill name or id."
            if not row:
                return f"Skill not found."
            return f"🧩 Skill: {row[1]}\nCategory: {row[4]}\nDescription: {row[2]}\n\nInstructions:\n{row[3]}"

        # ── Code Snippets ──
        elif action == "add_snippet":
            title = (parameters.get("title") or "").strip()
            code = (parameters.get("code") or "").strip()
            lang = (parameters.get("language") or "python").strip()
            desc = (parameters.get("description") or "").strip()
            tags = (parameters.get("tags") or "").strip()
            if not title or not code:
                return "Title and code are required."
            conn.execute(
                "INSERT INTO code_snippets (title, language, code, description, tags) VALUES (?, ?, ?, ?, ?)",
                (title, lang, code, desc, tags)
            )
            conn.commit()
            return f"💻 Snippet '{title}' saved [{lang}]."

        elif action == "search_snippets":
            query = (parameters.get("query") or "").strip().lower()
            if not query:
                return "Search query is required."
            rows = conn.execute(
                "SELECT id, title, language, tags FROM code_snippets "
                "WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(code) LIKE ? "
                "ORDER BY created_at DESC LIMIT 15",
                (f"%{query}%",) * 4
            ).fetchall()
            if not rows:
                return f"No snippets matching '{query}'."
            lines = [f"💻 {len(rows)} snippets matching '{query}':\n"]
            for r in rows:
                lines.append(f"  #{r[0]} {r[1]} [{r[2]}] {r[3]}")
            return "\n".join(lines)

        # ── Export ──
        elif action == "export_knowledge":
            notes = conn.execute("SELECT * FROM notes").fetchall()
            skills = conn.execute("SELECT * FROM skills").fetchall()
            snippets = conn.execute("SELECT * FROM code_snippets").fetchall()
            links = conn.execute("SELECT * FROM note_links").fetchall()
            export = {
                "notes": [{"id": r[0], "title": r[1], "content": r[2], "tags": r[3], "category": r[4]} for r in notes],
                "skills": [{"id": r[0], "name": r[1], "description": r[2], "instructions": r[3], "category": r[4]} for r in skills],
                "snippets": [{"id": r[0], "title": r[1], "language": r[2], "code": r[3]} for r in snippets],
                "links": [{"from": r[0], "to": r[1], "rel": r[2]} for r in links],
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "OneDrive" / "Desktop"
            out = desktop / "max_knowledge_export.json"
            out.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
            return f"✅ Exported knowledge base → {out}\n  {len(notes)} notes, {len(skills)} skills, {len(snippets)} snippets"

        else:
            return (
                f"Unknown action '{action}'. Available: "
                "add_note, search_notes, list_notes, get_note, delete_note, link_notes, "
                "add_skill, list_skills, get_skill, add_snippet, search_snippets, export_knowledge"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    print(knowledge_base({"action": "add_note", "title": "Test Note", "content": "Hello world", "tags": "test", "category": "idea"}))
    print(knowledge_base({"action": "list_notes"}))

