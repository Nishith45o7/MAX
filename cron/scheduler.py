"""
Cron Scheduler and Job Definitions.
Persists job configurations and manages scheduling state.
"""
import json
import uuid
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal
from brigade_core import get_state_dir
from cron.parser import parse_interval_seconds, matches_cron


@dataclass
class CronJob:
    id: str = field(default_factory=lambda: f"job_{uuid.uuid4().hex[:6]}")
    schedule_type: Literal["cron", "every", "at"] = "cron"
    expression: str = "* * * * *"
    tz: str = "UTC"
    payload_type: Literal["message", "turn", "command"] = "message"
    message: str = ""
    agent_id: str = "main"
    target_channel: Optional[str] = None
    enabled: bool = True
    last_run: Optional[float] = None
    created_at: float = field(default_factory=time.time)


class CronScheduler:
    """Manages creation, removal, and querying of persistent cron jobs."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()
        self.cron_dir = self.state_dir / "cron"
        self.cron_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.cron_dir / "jobs.json"
        self._load()

    def _load(self) -> None:
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.jobs = {j["id"]: CronJob(**j) for j in data}
                    return
            except Exception:
                pass
        self.jobs = {}

    def _save(self) -> None:
        data = [asdict(j) for j in self.jobs.values()]
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_jobs(self) -> List[CronJob]:
        return list(self.jobs.values())

    def get_job(self, job_id: str) -> Optional[CronJob]:
        return self.jobs.get(job_id)

    def add_job(
        self,
        schedule_type: Literal["cron", "every", "at"],
        expression: str,
        message: str,
        tz: str = "UTC",
        payload_type: Literal["message", "turn", "command"] = "message",
        agent_id: str = "main",
        target_channel: Optional[str] = None
    ) -> CronJob:
        job = CronJob(
            schedule_type=schedule_type,
            expression=expression,
            message=message,
            tz=tz,
            payload_type=payload_type,
            agent_id=agent_id,
            target_channel=target_channel,
            enabled=True
        )
        self.jobs[job.id] = job
        self._save()
        return job

    def remove_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save()
            return True
        return False

    def toggle_job(self, job_id: str, enabled: bool) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id].enabled = enabled
            self._save()
            return True
        return False
