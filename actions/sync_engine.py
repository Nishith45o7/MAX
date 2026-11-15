"""
actions/sync_engine.py
File sync monitoring, folder comparison, backup/restore — inspired by syncthing.
"""

import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sync_engine")


def _state_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "memory" / "sync_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_state() -> dict:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"watched_folders": {}, "backups": [], "last_scan": None}


def _save_state(state: dict):
    state["last_scan"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _state_path().write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _hash_file(filepath: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def _scan_folder(folder: Path) -> dict:
    files = {}
    try:
        for fp in folder.rglob("*"):
            if fp.is_file():
                rel = str(fp.relative_to(folder))
                files[rel] = {
                    "hash": _hash_file(fp),
                    "size": fp.stat().st_size,
                    "modified": fp.stat().st_mtime,
                }
    except Exception as e:
        logger.error(f"Scan error: {e}")
    return files


def sync_engine(parameters: dict, player=None) -> str:
    """File sync engine."""
    action = (parameters.get("action") or "sync_status").strip().lower()
    aliases = {
        "status": "sync_status", "watch": "add_watch", "unwatch": "remove_watch",
        "sync": "sync_folder", "compare": "compare_folders", "backup": "backup_folder",
        "restore": "restore_backup", "list": "list_synced"
    }
    action = aliases.get(action, action)

    if action == "sync_status":
        state = _load_state()
        watched = state.get("watched_folders", {})
        if not watched:
            return "📁 No folders being watched. Use 'add_watch' to start monitoring a folder."
        lines = ["📁 Sync Engine Status:\n"]
        for folder, info in watched.items():
            file_count = len(info.get("files", {}))
            lines.append(f"  • {folder} — {file_count} files tracked")
        lines.append(f"\nLast scan: {state.get('last_scan', 'never')}")
        return "\n".join(lines)

    elif action == "add_watch":
        folder = (parameters.get("path") or parameters.get("folder", "")).strip()
        if not folder:
            return "Folder path is required."
        fp = Path(folder)
        if not fp.exists():
            return f"Folder not found: {folder}"
        state = _load_state()
        files = _scan_folder(fp)
        state["watched_folders"][str(fp)] = {"files": files, "added_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        _save_state(state)
        return f"👁️ Now watching '{fp}' — {len(files)} files indexed."

    elif action == "remove_watch":
        folder = (parameters.get("path") or parameters.get("folder", "")).strip()
        state = _load_state()
        removed = False
        for key in list(state["watched_folders"]):
            if folder.lower() in key.lower():
                del state["watched_folders"][key]
                removed = True
                break
        if removed:
            _save_state(state)
            return f"✅ Stopped watching '{folder}'."
        return f"Folder '{folder}' is not being watched."

    elif action == "sync_folder":
        folder = (parameters.get("path") or parameters.get("folder", "")).strip()
        if not folder:
            return "Folder path is required."
        fp = Path(folder)
        if not fp.exists():
            return f"Folder not found: {folder}"
        state = _load_state()
        old_files = state.get("watched_folders", {}).get(str(fp), {}).get("files", {})
        new_files = _scan_folder(fp)
        added = [f for f in new_files if f not in old_files]
        deleted = [f for f in old_files if f not in new_files]
        modified = [f for f in new_files if f in old_files and new_files[f]["hash"] != old_files[f]["hash"]]
        state["watched_folders"][str(fp)] = {"files": new_files, "added_at": state.get("watched_folders", {}).get(str(fp), {}).get("added_at", "")}
        _save_state(state)
        lines = [f"🔄 Sync Report for '{fp.name}':\n"]
        lines.append(f"  • Total files: {len(new_files)}")
        lines.append(f"  • Added: {len(added)}")
        lines.append(f"  • Modified: {len(modified)}")
        lines.append(f"  • Deleted: {len(deleted)}")
        if added:
            lines.append("\n  New files:")
            for f in added[:10]:
                lines.append(f"    + {f}")
        if modified:
            lines.append("\n  Modified files:")
            for f in modified[:10]:
                lines.append(f"    ~ {f}")
        if deleted:
            lines.append("\n  Deleted files:")
            for f in deleted[:10]:
                lines.append(f"    - {f}")
        return "\n".join(lines)

    elif action == "compare_folders":
        src = (parameters.get("source") or parameters.get("path", "")).strip()
        dst = (parameters.get("target") or parameters.get("destination", "")).strip()
        if not src or not dst:
            return "Both 'source' and 'target' folder paths are required."
        src_p, dst_p = Path(src), Path(dst)
        if not src_p.exists() or not dst_p.exists():
            return f"One or both folders don't exist."
        src_files = _scan_folder(src_p)
        dst_files = _scan_folder(dst_p)
        only_src = [f for f in src_files if f not in dst_files]
        only_dst = [f for f in dst_files if f not in src_files]
        differ = [f for f in src_files if f in dst_files and src_files[f]["hash"] != dst_files[f]["hash"]]
        same = [f for f in src_files if f in dst_files and src_files[f]["hash"] == dst_files[f]["hash"]]
        return (
            f"📊 Folder Comparison:\n"
            f"  Source: {src_p} ({len(src_files)} files)\n"
            f"  Target: {dst_p} ({len(dst_files)} files)\n\n"
            f"  ✅ Identical: {len(same)}\n"
            f"  ⚡ Different: {len(differ)}\n"
            f"  📄 Only in source: {len(only_src)}\n"
            f"  📄 Only in target: {len(only_dst)}"
        )

    elif action == "backup_folder":
        folder = (parameters.get("path") or parameters.get("folder", "")).strip()
        dest = parameters.get("destination", "")
        if not folder:
            return "Folder path is required."
        fp = Path(folder)
        if not fp.exists():
            return f"Folder not found: {folder}"
        ts = time.strftime("%Y%m%d_%H%M%S")
        if dest:
            backup_path = Path(dest) / f"{fp.name}_backup_{ts}"
        else:
            backup_path = fp.parent / f"{fp.name}_backup_{ts}"
        try:
            shutil.copytree(str(fp), str(backup_path))
            file_count = sum(1 for _ in backup_path.rglob("*") if _.is_file())
            state = _load_state()
            state["backups"].append({"source": str(fp), "backup": str(backup_path), "timestamp": ts, "files": file_count})
            _save_state(state)
            return f"✅ Backup created: {backup_path} ({file_count} files)"
        except Exception as e:
            return f"Backup failed: {e}"

    elif action == "restore_backup":
        backup = (parameters.get("backup_path") or parameters.get("path", "")).strip()
        target = (parameters.get("target") or parameters.get("destination", "")).strip()
        if not backup:
            state = _load_state()
            backups = state.get("backups", [])
            if not backups:
                return "No backups found."
            lines = ["📦 Available Backups:\n"]
            for b in backups[-10:]:
                lines.append(f"  • {b['backup']} ({b.get('files', '?')} files) — {b['timestamp']}")
            return "\n".join(lines)
        bp = Path(backup)
        if not bp.exists():
            return f"Backup not found: {backup}"
        if not target:
            return "Target/destination path is required for restore."
        try:
            shutil.copytree(str(bp), target, dirs_exist_ok=True)
            return f"✅ Restored backup from {bp} → {target}"
        except Exception as e:
            return f"Restore failed: {e}"

    elif action == "list_synced":
        state = _load_state()
        watched = state.get("watched_folders", {})
        backups = state.get("backups", [])
        lines = [f"📁 Sync Engine Overview:\n  Watched folders: {len(watched)}"]
        for f in watched:
            lines.append(f"    • {f}")
        lines.append(f"  Backups: {len(backups)}")
        for b in backups[-5:]:
            lines.append(f"    • {b['backup']} — {b['timestamp']}")
        return "\n".join(lines)

    else:
        return (
            f"Unknown action '{action}'. Available: sync_status, sync_folder, add_watch, "
            "remove_watch, compare_folders, backup_folder, restore_backup, list_synced"
        )


if __name__ == "__main__":
    print(sync_engine({"action": "sync_status"}))

