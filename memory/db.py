import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
DB_PATH = BASE_DIR / "memory" / "max_memory.db"
JSON_MEMORY_PATH = BASE_DIR / "memory" / "long_term.json"

def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Initializes SQLite tables for conversations and user preferences with WAL mode."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT ''
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.commit()

    # Automatically migrate existing long_term.json entries if table is empty
    _migrate_from_json_if_needed()

def _migrate_from_json_if_needed():
    try:
        with _get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) AS cnt FROM user_preferences;")
            row = cursor.fetchone()
            if row and row["cnt"] > 0:
                return

        if JSON_MEMORY_PATH.exists():
            with open(JSON_MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            migrated_count = 0
            with _get_connection() as conn:
                for category, items in data.items():
                    if isinstance(items, dict):
                        for k, v in items.items():
                            val_str = v.get("value") if isinstance(v, dict) else str(v)
                            key_name = f"{category}:{k}" if category != "preferences" else k
                            if val_str:
                                conn.execute("""
                                    INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                                    VALUES (?, ?, ?)
                                """, (key_name, str(val_str), now_str))
                                migrated_count += 1
                conn.commit()
            if migrated_count > 0:
                print(f"[Memory DB] Successfully migrated {migrated_count} preference items from long_term.json")
    except Exception as e:
        print(f"[Memory DB] Warning: Migration from JSON skipped: {e}")

def save_conversation_turn(role: str, content: str, metadata: str = ""):
    """Saves a message turn (user, assistant, tool, system) to the conversations table."""
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _get_connection() as conn:
            conn.execute("""
                INSERT INTO conversations (timestamp, role, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (now_str, role, content, metadata))
            conn.commit()
    except Exception as e:
        print(f"[Memory DB] Failed to save conversation turn: {e}")

def get_recent_conversations(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most recent conversation messages in chronological order."""
    try:
        with _get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, timestamp, role, content, metadata
                FROM conversations
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = [dict(r) for r in reversed(rows)]
            return results
    except Exception as e:
        print(f"[Memory DB] Failed to fetch recent conversations: {e}")
        return []

def set_preference(key: str, value: str):
    """Sets or updates a key-value pair in user_preferences."""
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now_str))
            conn.commit()
    except Exception as e:
        print(f"[Memory DB] Failed to set preference '{key}': {e}")

def get_preference(key: str) -> Optional[str]:
    """Retrieves a single preference by key."""
    try:
        with _get_connection() as conn:
            cursor = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
    except Exception as e:
        print(f"[Memory DB] Failed to get preference '{key}': {e}")
    return None

def get_all_preferences() -> Dict[str, str]:
    """Returns all user preferences as a dictionary."""
    try:
        with _get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM user_preferences ORDER BY key ASC")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    except Exception as e:
        print(f"[Memory DB] Failed to get all preferences: {e}")
        return {}

def get_context_for_prompt(query: str = "", max_items: int = 5) -> str:
    """
    Retrieves formatted memory context relevant to the query to inject into the system prompt.
    """
    try:
        prefs = get_all_preferences()
        if not prefs:
            return ""

        context_lines = []
        q_tokens = set(query.lower().split()) if query else set()

        # Prioritize matching keys/values
        ranked_items = []
        for k, v in prefs.items():
            score = 0
            for token in q_tokens:
                if len(token) > 2:
                    if token in k.lower():
                        score += 2
                    if token in v.lower():
                        score += 1
            ranked_items.append((score, k, v))

        ranked_items.sort(key=lambda x: x[0], reverse=True)
        selected = ranked_items[:max_items]

        for _, k, v in selected:
            clean_k = k.split(":")[-1].replace("_", " ").title()
            context_lines.append(f"- {clean_k}: {v}")

        if context_lines:
            return "\n[Persistent User Context & Memory]:\n" + "\n".join(context_lines)
    except Exception as e:
        print(f"[Memory DB] Error building prompt context: {e}")
    return ""

# Auto-initialize DB schema on module import
init_db()
