"""
Storage and state management for Brigade.
Handles agent workspaces, session transcripts (JSONL), channel profiles,
cron run logs, and workspace persona bootstrapping.
"""
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from brigade_core import get_state_dir

DEFAULT_SOUL = """# Soul of MAX / Brigade Agent
You are an intelligent, autonomous, and decisive AI agent.
- Prioritize real tool execution over conversational narration.
- Never simulate actions or pretend results were achieved when tools can run.
- Maintain persistent memory and context across sessions.
- Respect safety boundaries, file path confinements, and explicit approval requirements.
"""

DEFAULT_IDENTITY = """# Agent Identity
Name: MAX
Role: Central Coordinator & Autonomous Operator
Tone: Direct, concise, highly capable, professional
"""

DEFAULT_USER = """# User Profile
Identity: System Owner
Access Level: Owner (Superuser / Full Authority)
Preferences: Low-friction automation, clear verification, zero bloat
"""

DEFAULT_TOOLS = """# Tool Conventions
Use coding tools for file inspection and edits.
Use Tideline memory tools to store durable knowledge and recall facts.
Use channel tools to communicate with external peers.
"""


class StorageManager:
    """Manages files, workspaces, transcripts, and persistent directories."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()
        self._init_layout()

    def _init_layout(self) -> None:
        """Initializes standard Brigade directory structure."""
        dirs = [
            self.state_dir / "workspace",
            self.state_dir / "agents",
            self.state_dir / "channels",
            self.state_dir / "cron" / "runs",
            self.state_dir / "logs",
            self.state_dir / "sessions"
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Bootstrap main workspace personas
        self.ensure_workspace("main")

    def get_agent_dir(self, agent_id: str) -> Path:
        """Returns the base directory for an agent."""
        if agent_id == "main":
            return self.state_dir
        p = self.state_dir / "agents" / agent_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_workspace_dir(self, agent_id: str) -> Path:
        """Returns the workspace directory for an agent."""
        if agent_id == "main":
            p = self.state_dir / "workspace"
        else:
            p = self.get_agent_dir(agent_id) / "workspace"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ensure_workspace(self, agent_id: str) -> Path:
        """Bootstraps persona files in the agent workspace."""
        ws = self.get_workspace_dir(agent_id)
        (ws / "memory").mkdir(parents=True, exist_ok=True)
        (ws / "skills").mkdir(parents=True, exist_ok=True)

        files = {
            "SOUL.md": DEFAULT_SOUL,
            "IDENTITY.md": DEFAULT_IDENTITY,
            "USER.md": DEFAULT_USER,
            "TOOLS.md": DEFAULT_TOOLS,
            "BOOTSTRAP.md": "# Bootstrap Routine\nVerify environment, skills, and memory on boot.\n",
            "HEARTBEAT.md": "# Heartbeat Checks\nRoutine health checks.\n"
        }
        for name, content in files.items():
            fpath = ws / name
            if not fpath.exists():
                fpath.write_text(content, encoding="utf-8")

        return ws

    def get_session_file(self, agent_id: str, session_id: str) -> Path:
        """Returns the JSONL transcript file for a given session."""
        agent_dir = self.get_agent_dir(agent_id)
        sessions_dir = agent_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir / f"{session_id}.jsonl"

    def append_session_turn(self, agent_id: str, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Appends a turn to the session transcript in JSONL format."""
        file_path = self.get_session_file(agent_id, session_id)
        record = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_session_turns(self, agent_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Loads recent conversation turns from JSONL."""
        file_path = self.get_session_file(agent_id, session_id)
        if not file_path.exists():
            return []
        turns = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        turns.append(json.loads(line))
                    except Exception:
                        pass
        return turns[-limit:]

    def list_sessions(self, agent_id: str) -> List[str]:
        """Lists all session IDs for an agent."""
        agent_dir = self.get_agent_dir(agent_id)
        sessions_dir = agent_dir / "sessions"
        if not sessions_dir.exists():
            return []
        return [f.stem for f in sessions_dir.glob("*.jsonl")]

    def get_cron_run_file(self, job_id: str) -> Path:
        """Returns JSONL run log for a scheduled cron job."""
        return self.state_dir / "cron" / "runs" / f"{job_id}.jsonl"

    def append_cron_run(self, job_id: str, status: str, output: str, duration_ms: float) -> None:
        """Logs a cron execution record."""
        fpath = self.get_cron_run_file(job_id)
        record = {
            "timestamp": time.time(),
            "status": status,
            "durationMs": duration_ms,
            "output": output
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
