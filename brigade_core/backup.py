"""
Forensic backup, verification, and restore tools for Brigade.
Produces and restores standard .tar.gz snapshots of ~/.brigade state.
"""
import os
import tarfile
import time
from pathlib import Path
from typing import Dict, Any, Optional
from brigade_core import get_state_dir


class BackupManager:
    """Manages creation, verification, and restoration of state backups."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()

    def create_backup(self, output_path: Optional[Path] = None) -> Path:
        """Packages the state directory into a timestamped tar.gz archive."""
        if not output_path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = self.state_dir / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            output_path = backup_dir / f"brigade_backup_{ts}.tar.gz"

        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(self.state_dir):
                # Exclude existing backups to avoid recursion
                if "backups" in Path(root).parts:
                    continue
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(self.state_dir)
                    tar.add(str(full_p), arcname=str(rel_p))

        return output_path

    def verify_backup(self, archive_path: Path) -> Dict[str, Any]:
        """Validates archive integrity and lists entries."""
        if not archive_path.exists():
            return {"valid": False, "error": f"File does not exist: {archive_path}"}

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                names = [m.name for m in members]
                has_config = any("brigade.json" in n for n in names)
                return {
                    "valid": True,
                    "total_files": len(members),
                    "has_config": has_config,
                    "entries": names[:20]
                }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def restore_backup(self, archive_path: Path, target_dir: Optional[Path] = None) -> bool:
        """Restores state from archive into the target state directory."""
        target = target_dir or self.state_dir
        target.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "r:gz") as tar:
            # Safe extraction avoiding path traversal
            for member in tar.getmembers():
                dest = (target / member.name).resolve()
                if not str(dest).startswith(str(target.resolve())):
                    raise SecurityError(f"Path traversal detected in archive: {member.name}")
            tar.extractall(path=str(target))
        return True
