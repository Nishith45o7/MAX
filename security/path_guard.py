"""
Path Write Guard for file operations.
Prevents path traversal, blocks modifications to system or credential files,
and confines agent operations to permitted workspaces.
"""
import os
from pathlib import Path
from typing import List, Optional


class PathGuardError(PermissionError):
    """Raised when an operation violates path safety constraints."""
    pass


class PathGuard:
    """Enforces boundaries and path restrictions for file read/write/edit tools."""

    BLOCKED_PATTERNS = [
        "encryption.key",
        "api_keys.json",
        "id_rsa",
        "id_ed25519",
        ".ssh",
        "credentials"
    ]

    def __init__(self, allowed_roots: Optional[List[Path]] = None):
        self.allowed_roots = [p.resolve() for p in (allowed_roots or [])]

    def add_allowed_root(self, root: Path) -> None:
        self.allowed_roots.append(root.resolve())

    def validate_path(self, target_path: Path, for_write: bool = False) -> Path:
        """
        Validates target path against traversal and blocked targets.
        Returns resolved absolute Path or raises PathGuardError.
        """
        resolved = Path(target_path).expanduser().resolve()

        # 1. Blocked credential and key targets
        for bp in self.BLOCKED_PATTERNS:
            if bp in resolved.name.lower() or bp in str(resolved).lower():
                raise PathGuardError(f"Access denied: Path matches protected pattern '{bp}': {resolved}")

        # 2. Workspace boundary check if allowed_roots is specified
        if self.allowed_roots:
            is_inside = any(
                str(resolved).startswith(str(root)) or resolved == root
                for root in self.allowed_roots
            )
            if not is_inside:
                raise PathGuardError(f"Access denied: Path outside permitted workspaces: {resolved}")

        # 3. Prevent modifying system roots
        if for_write:
            system_dirs = ["c:\\windows", "c:\\program files", "/etc", "/bin", "/sbin", "/usr"]
            for s in system_dirs:
                if str(resolved).lower().startswith(s):
                    raise PathGuardError(f"Write access denied to critical system directory: {resolved}")

        return resolved
