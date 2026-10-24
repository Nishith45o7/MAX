"""
Result Review Gate and Verification for Team Tasks.
"""
from typing import Tuple, Optional


class ReviewGate:
    """Validates worker results before accepting task resolution."""

    @classmethod
    def verify_result(cls, result: Optional[str]) -> Tuple[bool, Optional[str]]:
        if result is None:
            return False, "Result is None"

        text = result.strip()
        if len(text) < 5:
            return False, f"Result content too short ({len(text)} characters)"

        if text.lower().startswith("error:") or text.lower().startswith("failed:"):
            return False, f"Result reports unhandled execution failure: {text[:60]}"

        return True, None
