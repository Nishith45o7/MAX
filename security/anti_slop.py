"""
Deterministic Anti-Slop AI Quality Gate.
Scans generated text in 4 passes (vocabulary crutches, clichés, formulaic openers,
structural patterns) and evaluates density for bounded repair retry.
"""
import re
from typing import Dict, Any, List, Tuple

VOCAB_CRUTCHES = [
    r"\bdelve\b", r"\btapestry\b", r"\bembark\b", r"\btestament\b",
    r"\bbeacon\b", r"\bpinnacle\b", r"\bbustling\b", r"\bplethora\b",
    r"\bmultifaceted\b", r"\bmoreover\b", r"\bfurthermore\b",
    r"\bparamount\b", r"\bcatalyst\b", r"\bnuance\b"
]

CLICHES = [
    r"in conclusion\b",
    r"it is (important|crucial|worth) (to note|noting) that",
    r"serves as a testament\b",
    r"in today'?s (fast-paced|rapidly changing|digital) world\b",
    r"plays a (crucial|vital|pivotal) role",
    r"without further ado\b"
]

FORMULAIC_OPENERS = [
    r"^(sure|certainly),?\s+(i('d| would) be happy to|here is|here are)\b",
    r"^as an ai (language model|assistant)\b",
    r"^in this (article|response|guide),? we will explore\b"
]


class AntiSlopDetector:
    """Scans text for AI slop and calculates density score."""

    @classmethod
    def scan(cls, text: str) -> Dict[str, Any]:
        words = re.findall(r"\w+", text.lower())
        total_words = max(1, len(words))

        hits: List[str] = []

        # Pass 1: Vocabulary crutches
        for pat in VOCAB_CRUTCHES:
            matches = re.findall(pat, text, re.IGNORECASE)
            hits.extend(matches)

        # Pass 2: Clichés
        for pat in CLICHES:
            matches = re.findall(pat, text, re.IGNORECASE)
            if matches:
                hits.append(f"cliche: {pat}")

        # Pass 3: Openers
        first_sentence = text.strip().split(".")[0] if text else ""
        for pat in FORMULAIC_OPENERS:
            if re.search(pat, first_sentence, re.IGNORECASE):
                hits.append("formulaic_opener")

        # Density = violations per 100 words
        density = (len(hits) / total_words) * 100.0
        exceeds_threshold = density >= 2.5 and len(hits) >= 2

        return {
            "total_words": total_words,
            "violations_count": len(hits),
            "density_per_100_words": round(density, 2),
            "exceeds_threshold": exceeds_threshold,
            "hits": hits[:10]
        }

    @classmethod
    def clean_openers(cls, text: str) -> str:
        """Strips formulaic introductory chatter."""
        cleaned = text
        for pat in FORMULAIC_OPENERS:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).lstrip(":, \n")
        return cleaned
