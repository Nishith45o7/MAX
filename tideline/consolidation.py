"""
Consolidation and Nightly Dream Engine for Tideline.
Runs garbage collection on decayed facts, merges duplicate insights,
and updates relation links.
"""
import time
from typing import Dict, Any, List
from tideline.store import FactStore
from tideline.retrieval import HybridRetriever


class ConsolidationEngine:
    """Performs memory maintenance and nightly consolidation passes."""

    def __init__(self, store: FactStore):
        self.store = store

    def run_pass(self, min_effective_score: float = 0.05) -> Dict[str, Any]:
        """
        Executes a consolidation pass:
        - Prunes dead facts that have decayed below min_effective_score (unless permanent)
        - Cleans up dangling links
        """
        now = time.time()
        facts = self.store.get_all()
        retained = []
        evicted = 0

        for f in facts:
            if f.tier == "permanent":
                retained.append(f)
                continue

            decay = HybridRetriever.compute_decay(f, now)
            effective = decay * f.trust_score * f.importance
            if effective < min_effective_score:
                evicted += 1
                self.store.remove(f.id)
            else:
                retained.append(f)

        # Clean dangling links
        valid_ids = {f.id for f in retained}
        modified = False
        for f in retained:
            original_len = len(f.links)
            f.links = [l for l in f.links if l.get("target_id") in valid_ids]
            if len(f.links) != original_len:
                self.store.put(f)
                modified = True

        return {
            "timestamp": now,
            "retained_facts": len(retained),
            "evicted_facts": evicted,
            "links_cleaned": modified
        }
