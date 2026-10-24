"""
Prompt Injection and Malicious External Content Guard.
Sanitizes and flags prompt injection payloads in web searches, documents, and channel messages.
"""
import re
from typing import Tuple, List, Dict, Any

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"(disregard|forget)\s+(all\s+)?(previous|prior|above)\s+(instructions|directives)", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(unfiltered|dan|jailbreak)", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]", re.IGNORECASE),
    re.compile(r"new\s+role:\s*system", re.IGNORECASE),
    re.compile(r"do\s+not\s+tell\s+the\s+user", re.IGNORECASE),
    re.compile(r"send\s+(your|the)\s+(api\s*key|password|credentials)\s+to", re.IGNORECASE),
]


class InjectionGuard:
    """Scans external or untrusted text for indirect prompt injection attempts."""

    @classmethod
    def scan(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Scans text for injection signatures.
        Returns (has_threat: bool, matched_patterns: List[str]).
        """
        matches = []
        for pat in INJECTION_PATTERNS:
            if pat.search(text):
                matches.append(pat.pattern)
        return len(matches) > 0, matches

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Neutralizes detected prompt injection markers with safe redaction notices."""
        sanitized = text
        for pat in INJECTION_PATTERNS:
            sanitized = pat.sub("[REDACTED_SUSPECTED_INJECTION]", sanitized)
        return sanitized
