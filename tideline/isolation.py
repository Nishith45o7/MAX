"""
Origin-based isolation rules for Tideline.
Ensures peer channels and untrusted origins cannot access owner memories.
"""
from typing import List
from tideline.schema import FactRecord, PROTECTED_SEGMENTS


class OriginIsolation:
    """Enforces strict isolation boundaries on memory queries."""

    @staticmethod
    def filter_by_origin(facts: List[FactRecord], caller_origin: str) -> List[FactRecord]:
        """
        Filters memory facts based on caller origin.
        Fails closed on unknown or invalid callers.
        """
        if not caller_origin or not isinstance(caller_origin, str):
            return []

        caller = caller_origin.strip()
        allowed: List[FactRecord] = []

        for f in facts:
            # If caller is system owner, they see owner facts and public knowledge
            if caller == "owner":
                allowed.append(f)
            else:
                # Non-owner peer (e.g. "telegram:12345")
                # Never allow protected segments of the owner
                if f.origin == "owner" and f.segment in PROTECTED_SEGMENTS:
                    continue
                # Peer can see their own facts
                if f.origin == caller:
                    allowed.append(f)
                # Or general/shared knowledge not marked private
                elif f.origin == "public" or (f.origin == "owner" and f.segment == "knowledge" and f.importance >= 0.8):
                    allowed.append(f)

        return allowed
