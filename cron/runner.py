"""
Cron Background Runner executing due jobs and appending to forensic run logs.
"""
import time
import threading
from datetime import datetime
from typing import Optional, Callable
from cron.scheduler import CronScheduler, CronJob
from cron.parser import parse_interval_seconds, matches_cron
from brigade_core.storage import StorageManager


class CronRunner:
    """Monitors scheduled jobs in a background thread and triggers execution."""

    def __init__(
        self,
        scheduler: Optional[CronScheduler] = None,
        storage_mgr: Optional[StorageManager] = None,
        job_executor: Optional[Callable[[CronJob], str]] = None
    ):
        self.scheduler = scheduler or CronScheduler()
        self.storage_mgr = storage_mgr or StorageManager()
        self.job_executor = job_executor
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            now_dt = datetime.now()
            jobs = self.scheduler.list_jobs()

            for job in jobs:
                if not job.enabled:
                    continue
                if self._is_job_due(job, now, now_dt):
                    self._execute_job(job)

            # Check every 10 seconds
            self._stop_event.wait(10.0)

    def _is_job_due(self, job: CronJob, now: float, now_dt: datetime) -> bool:
        if job.schedule_type == "every":
            sec = parse_interval_seconds(job.expression)
            if sec and (job.last_run is None or (now - job.last_run) >= sec):
                return True
        elif job.schedule_type == "cron":
            if matches_cron(now_dt, job.expression):
                # Ensure we don't fire multiple times within the same minute
                if job.last_run is None or (now - job.last_run) >= 60.0:
                    return True
        elif job.schedule_type == "at":
            try:
                target_ts = float(job.expression)
                if now >= target_ts and job.last_run is None:
                    return True
            except Exception:
                pass
        return False

    def _execute_job(self, job: CronJob) -> None:
        job.last_run = time.time()
        start_t = time.time()
        status = "success"
        output = ""

        try:
            if self.job_executor:
                output = self.job_executor(job)
            else:
                output = f"Executed payload: {job.message}"
        except Exception as e:
            status = "failed"
            output = str(e)
        finally:
            duration = (time.time() - start_t) * 1000.0
            self.storage_mgr.append_cron_run(job.id, status, output, duration)

            # Auto-disable one-shot 'at' jobs
            if job.schedule_type == "at":
                self.scheduler.toggle_job(job.id, False)
            else:
                self.scheduler._save()
