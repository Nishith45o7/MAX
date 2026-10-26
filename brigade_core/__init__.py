"""
Brigade Core Framework for MAX.
Provides configuration, storage, encryption, backup, secrets audit, and gateway protocol.
"""
from pathlib import Path
import os
import sys

def get_state_dir() -> Path:
    """Returns the resolved Brigade state directory, respecting BRIGADE_STATE_DIR."""
    override = os.environ.get("BRIGADE_STATE_DIR")
    if override:
        p = Path(override).expanduser().resolve()
    else:
        p = (Path.home() / ".brigade").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
