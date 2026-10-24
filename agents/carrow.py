"""
Carrow: Cross-Model Continuity and Reasoning Block Sanitizer.
Ensures seamless model switching mid-conversation without dropping transcript context.
"""
import re
from typing import List, Dict, Any

THINKING_LEVELS = ["off", "minimal", "low", "medium", "high"]

PROVIDER_TAG_PATTERNS = [
    re.compile(r"<think>[\s\S]*?<\/think>", re.IGNORECASE),
    re.compile(r"<thought>[\s\S]*?<\/thought>", re.IGNORECASE),
    re.compile(r"\[reasoning\][\s\S]*?\[\/reasoning\]", re.IGNORECASE)
]


class Carrow:
    """Carries conversation context safely across model and provider switches."""

    @classmethod
    def sanitize_messages_for_target(
        cls,
        messages: List[Dict[str, Any]],
        target_supports_reasoning: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sanitizes transcripts for target model compatibility.
        Strips internal reasoning tags if target model rejects them.
        """
        clean_messages = []
        for msg in messages:
            m_copy = dict(msg)
            content = m_copy.get("content", "")

            if isinstance(content, str):
                if not target_supports_reasoning:
                    for pat in PROVIDER_TAG_PATTERNS:
                        content = pat.sub("", content).strip()
                m_copy["content"] = content

            clean_messages.append(m_copy)
        return clean_messages

    @classmethod
    def reanchor_thinking(cls, current_level: str, target_model: str) -> str:
        """Adjusts thinking level based on target model capabilities."""
        level = current_level.lower()
        if "o1" in target_model.lower() or "o3" in target_model.lower() or "r1" in target_model.lower():
            return level if level != "off" else "medium"
        elif "flash" in target_model.lower() or "mini" in target_model.lower() or "turbo" in target_model.lower():
            return "off"
        return level if level in THINKING_LEVELS else "medium"
