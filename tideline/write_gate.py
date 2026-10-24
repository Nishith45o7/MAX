"""
Provenance Write-Gate for Tideline.
Guards protected segments against untrusted sources and prevents memory poisoning.
"""
from typing import Tuple, Optional, List
from tideline.schema import FactRecord, PROTECTED_SEGMENTS


class WriteGateError(Exception):
    """Raised when an unauthorized source attempts to write to protected memory."""
    pass


class WriteGate:
    """Evaluates and validates fact write requests before persistence."""

    SOURCE_TRUST_MAP = {
        "user": 1.0,
        "owner": 1.0,
        "operator": 1.0,
        "system": 0.9,
        "verified_tool": 0.8,
        "inferred": 0.6,
        "web": 0.4,
        "peer": 0.3,
        "untrusted": 0.1
    }

    @classmethod
    def evaluate(cls, record: FactRecord, existing_facts: List[FactRecord]) -> Tuple[bool, Optional[str]]:
        """
        Validates write permission based on provenance, segment protection, and deduplication.
        Returns (allowed: bool, reason: Optional[str]).
        """
        # Assign trust score if default
        record.trust_score = cls.SOURCE_TRUST_MAP.get(record.source.lower(), 0.5)

        # 1. Provenance write-gate on protected segments
        if record.segment in PROTECTED_SEGMENTS:
            if record.source.lower() not in {"user", "owner", "operator", "system"}:
                return False, f"Untrusted source '{record.source}' cannot author or alter protected segment '{record.segment}'"
            if record.origin != "owner":
                return False, f"Non-owner origin '{record.origin}' cannot write to protected segment '{record.segment}'"

        # 2. Duplicate detection
        norm_content = " ".join(record.content.lower().strip().split())
        for existing in existing_facts:
            existing_norm = " ".join(existing.content.lower().strip().split())
            if norm_content == existing_norm and record.segment == existing.segment and record.origin == existing.origin:
                # Same fact: reinforce existing
                existing.access_count += 1
                existing.trust_score = max(existing.trust_score, record.trust_score)
                existing.importance = max(existing.importance, record.importance)
                return False, f"Duplicate fact reinforced (id: {existing.id})"

        return True, None
