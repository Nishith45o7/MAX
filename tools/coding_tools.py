"""
Coding tools for file reading, writing, editing, directory inspection, and command execution.
Guarded by PathGuard and ExecApprovalManager.
"""
import os
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional
from security.path_guard import PathGuard, PathGuardError
from security.exec_approvals import ExecApprovalManager


class CodingTools:
    """Standard coding toolset matching Brigade's pi SDK tools."""

    def __init__(self, path_guard: Optional[PathGuard] = None, exec_approvals: Optional[ExecApprovalManager] = None):
        self.path_guard = path_guard or PathGuard()
        self.exec_approvals = exec_approvals or ExecApprovalManager()

    def read(self, path: str, offset: int = 0, limit: int = 200) -> str:
        """Reads lines from a file."""
        target = self.path_guard.validate_path(Path(path), for_write=False)
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: '{path}' is a directory, not a file."

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            sliced = lines[offset:offset+limit]
            numbered = [f"{offset + i + 1}: {line}" for i, line in enumerate(sliced)]
            return "".join(numbered) or "(Empty file or slice)"
        except Exception as e:
            return f"Error reading file: {e}"

    def write(self, path: str, content: str) -> str:
        """Writes content to a file."""
        target = self.path_guard.validate_path(Path(path), for_write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    def edit(self, path: str, old_text: str, new_text: str) -> str:
        """Replaces exact target text with new text in a file."""
        target = self.path_guard.validate_path(Path(path), for_write=True)
        if not target.exists():
            return f"Error: File '{path}' does not exist."

        try:
            current = target.read_text(encoding="utf-8")
            if old_text not in current:
                return f"Error: Target text not found in {path}"
            updated = current.replace(old_text, new_text, 1)
            target.write_text(updated, encoding="utf-8")
            return f"Successfully updated {path}"
        except Exception as e:
            return f"Error editing file: {e}"

    def bash(self, command: str) -> str:
        """Executes a command under the approval bridge."""
        allowed, reason = self.exec_approvals.check_command(command)
        if not allowed:
            return f"Execution Denied: {reason}"

        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace"
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            if res.returncode != 0:
                return f"Exit code {res.returncode}\n{out}\n{err}"
            return out or err or "(Command completed with no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 60 seconds."
        except Exception as e:
            return f"Error running command: {e}"

    def ls(self, directory: str = ".") -> str:
        """Lists directory entries."""
        target = self.path_guard.validate_path(Path(directory), for_write=False)
        if not target.exists():
            return f"Error: Directory '{directory}' does not exist."
        try:
            entries = []
            for item in sorted(target.iterdir()):
                prefix = "📁 " if item.is_dir() else "📄 "
                entries.append(f"{prefix}{item.name}")
            return "\n".join(entries) or "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    def find(self, directory: str = ".", pattern: str = "*") -> str:
        """Finds files matching pattern."""
        target = self.path_guard.validate_path(Path(directory), for_write=False)
        matches = []
        try:
            for root, dirs, files in os.walk(target):
                for f in files:
                    if fnmatch.fnmatch(f, pattern):
                        matches.append(str(Path(root) / f))
                        if len(matches) >= 50:
                            break
            return "\n".join(matches) or "No matching files found."
        except Exception as e:
            return f"Error finding files: {e}"
