"""
Tideline Coordinator Engine.
Public interface uniting Store, Write-Gate, Origin Isolation, and Hybrid Retrieval.
"""
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tideline.schema import FactRecord, FactSegment, FactTier
from tideline.store import FactStore
from tideline.write_gate import WriteGate, WriteGateError
from tideline.isolation import OriginIsolation
from tideline.retrieval import HybridRetriever
from tideline.consolidation import ConsolidationEngine


class TidelineEngine:
    """Core Tideline memory facade."""

    def __init__(self, store: FactStore, default_origin: str = "owner"):
        self.store = store
        self.default_origin = default_origin
        self.consolidator = ConsolidationEngine(store)

    @classmethod
    def open(cls, workspace_dir: Path, default_origin: str = "owner") -> "TidelineEngine":
        store = FactStore(workspace_dir)
        return cls(store, default_origin=default_origin)

    def add(
        self,
        content: str,
        segment: FactSegment = "knowledge",
        tier: FactTier = "long",
        importance: float = 0.5,
        origin: Optional[str] = None,
        source: str = "user"
    ) -> FactRecord:
        """Adds a fact subject to write-gate and deduplication validation."""
        origin = origin or self.default_origin
        rec = FactRecord(
            content=content.strip(),
            segment=segment,
            tier=tier,
            importance=importance,
            origin=origin,
            source=source
        )

        all_facts = self.store.get_all()
        allowed, reason = WriteGate.evaluate(rec, all_facts)
        if not allowed:
            raise WriteGateError(f"Write rejected by provenance gate: {reason}")

        self.store.put(rec)
        return rec

    def recall(
        self,
        query: str,
        top_k: int = 5,
        origin: Optional[str] = None
    ) -> List[Tuple[FactRecord, float]]:
        """Recalls facts matching query, strictly bounded by origin isolation."""
        caller_origin = origin or self.default_origin
        all_facts = self.store.get_all()
        isolated = OriginIsolation.filter_by_origin(all_facts, caller_origin)
        ranked = HybridRetriever.rank(query, isolated, top_k=top_k)

        # Update last accessed and access count
        for fact, score in ranked:
            fact.last_accessed_at = time.time()
            fact.access_count += 1
            self.store.put(fact)

        return ranked

    def context(
        self,
        query: str,
        max_chars: int = 800,
        origin: Optional[str] = None
    ) -> str:
        """Returns a budgeted string context ready for prompt injection."""
        ranked = self.recall(query, top_k=8, origin=origin)
        return HybridRetriever.format_context_block(ranked, max_chars=max_chars)

    def remove(self, fact_id: str) -> bool:
        return self.store.remove(fact_id)

    def list_facts(self, origin: Optional[str] = None) -> List[FactRecord]:
        caller_origin = origin or self.default_origin
        all_facts = self.store.get_all()
        return OriginIsolation.filter_by_origin(all_facts, caller_origin)

    def consolidate(self) -> Dict[str, Any]:
        return self.consolidator.run_pass()
