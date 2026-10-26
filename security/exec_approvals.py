"""
Command Execution Approval Bridge for bash/shell commands.
Enforces allowlists, regex pattern filters, and interactive human approvals.
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from brigade_core import get_state_dir


class ExecApprovalManager:
    """Manages command approval rules, allowlists, and execution policy."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()
        self.file_path = self.state_dir / "exec-approvals.json"
        self._load()

    def _load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    return
            except Exception:
                pass
        self.data = {
            "mode": "ask",  # "ask", "allow", "deny"
            "allowedCommands": [],
            "allowedPatterns": [
                r"^python\s+",
                r"^dir\b",
                r"^ls\b",
                r"^git\s+status\b",
                r"^git\s+diff\b"
            ],
            "deniedPatterns": [
                r"\brm\s+-rf\s+/",
                r"\bformat\b",
                r"\bshutdown\b",
                r"\bdel\s+/f\s+/s\s+/q\s+c:\\"
            ]
        }
        self._save()

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def allow_command(self, cmd: str) -> None:
        cmd = cmd.strip()
        if cmd not in self.data["allowedCommands"]:
            self.data["allowedCommands"].append(cmd)
            self._save()

    def allow_pattern(self, pattern: str) -> None:
        pattern = pattern.strip()
        if pattern not in self.data["allowedPatterns"]:
            self.data["allowedPatterns"].append(pattern)
            self._save()

    def remove_command(self, cmd: str) -> bool:
        if cmd in self.data["allowedCommands"]:
            self.data["allowedCommands"].remove(cmd)
            self._save()
            return True
        return False

    def list_rules(self) -> Dict[str, Any]:
        return self.data.copy()

    def check_command(self, cmd: str, approval_callback: Optional[Callable[[str], bool]] = None) -> Tuple[bool, str]:
        """
        Validates if a command is allowed to execute.
        Returns (allowed: bool, reason: str).
        """
        cmd_clean = cmd.strip()

        # 1. Deny patterns
        for dp in self.data.get("deniedPatterns", []):
            if re.search(dp, cmd_clean, re.IGNORECASE):
                return False, f"Command matches dangerous pattern: '{dp}'"

        # 2. Exact allowlist
        if cmd_clean in self.data.get("allowedCommands", []):
            return True, "Allowed by exact command match"

        # 3. Regex allowlist
        for ap in self.data.get("allowedPatterns", []):
            if re.search(ap, cmd_clean, re.IGNORECASE):
                return True, f"Allowed by pattern: '{ap}'"

        # 4. Mode-based decision
        mode = self.data.get("mode", "ask")
        if mode == "allow":
            return False, "Not in allowlist (mode: allow-only)"
        elif mode == "deny":
            return False, "All unapproved execution disabled (mode: deny)"
        elif mode == "ask":
            if approval_callback:
                approved = approval_callback(cmd_clean)
                if approved:
                    return True, "Approved interactively by operator"
                return False, "Rejected by operator"
            return False, "Approval required but no interactive approval callback provided"

        return False, "Execution denied by default policy"
