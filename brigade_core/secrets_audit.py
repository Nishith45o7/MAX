"""
Forensic secret auditor for Brigade.
Scans files in ~/.brigade for suspected leaked API keys, tokens, or credentials.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from brigade_core import get_state_dir

PATTERNS = [
    ("OpenAI Key", re.compile(r"sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}")),
    ("OpenRouter Key", re.compile(r"sk-or-v1-[a-zA-Z0-9]{64}")),
    ("Anthropic Key", re.compile(r"sk-ant-[a-zA-Z0-9]{32,}")),
    ("Telegram Bot Token", re.compile(r"\b\d{9,10}:[a-zA-Z0-9_-]{35}\b")),
    ("GitHub Token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}\b")),
    ("Composio API Key", re.compile(r"\bak_[a-zA-Z0-9]{24,}\b")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("Discord Token", re.compile(r"[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}")),
]


class SecretsAuditor:
    """Audits files in the state directory for exposed secret tokens."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()

    def audit(self) -> List[Dict[str, Any]]:
        """Scans state files and returns findings with masked values."""
        findings = []
        if not self.state_dir.exists():
            return findings

        for p in self.state_dir.rglob("*"):
            if not p.is_file():
                continue
            # Skip binary and backup archives
            if p.suffix in [".gz", ".tar", ".db", ".png", ".jpg", ".bin"]:
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for name, regex in PATTERNS:
                    for match in regex.finditer(content):
                        raw_val = match.group(0)
                        masked = raw_val[:4] + "..." + raw_val[-4:] if len(raw_val) > 8 else "***"
                        findings.append({
                            "type": name,
                            "file": str(p.relative_to(self.state_dir)),
                            "masked": masked,
                            "start": match.start()
                        })
            except Exception:
                pass
        return findings
