"""
FactStore handles persistence of facts in JSONL format with thread safety.
"""
import os
import json
import shutil
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from tideline.schema import FactRecord


class FactStore:
    """Persistent storage for Tideline memory facts."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.memory_dir = self.workspace_dir / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.facts_file = self.memory_dir / "facts.jsonl"
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, FactRecord]] = None

    def _load_cache(self) -> Dict[str, FactRecord]:
        with self._lock:
            if self._cache is not None:
                return self._cache

            records: Dict[str, FactRecord] = {}
            if self.facts_file.exists():
                with open(self.facts_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                rec = FactRecord.from_dict(data)
                                records[rec.id] = rec
                            except Exception:
                                pass
            self._cache = records
            return self._cache

    def flush(self) -> None:
        """Persists memory state atomically to facts.jsonl."""
        with self._lock:
            if self._cache is None:
                return
            tmp_path = self.facts_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                for rec in self._cache.values():
                    f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
            shutil.move(str(tmp_path), str(self.facts_file))

    def get_all(self) -> List[FactRecord]:
        with self._lock:
            cache = self._load_cache()
            return list(cache.values())

    def get(self, fact_id: str) -> Optional[FactRecord]:
        with self._lock:
            cache = self._load_cache()
            return cache.get(fact_id)

    def put(self, record: FactRecord) -> None:
        with self._lock:
            cache = self._load_cache()
            cache[record.id] = record
            self.flush()

    def remove(self, fact_id: str) -> bool:
        with self._lock:
            cache = self._load_cache()
            if fact_id in cache:
                del cache[fact_id]
                self.flush()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache = {}
            self.flush()
