"""
Worker Leasing, Fencing Tokens, and Attempt Isolation for Team Mode.
"""
import time
import uuid
from typing import Dict, Any, Optional


class WorkerLease:
    def __init__(self, task_id: str, worker_id: str, timeout_seconds: float = 60.0):
        self.task_id = task_id
        self.worker_id = worker_id
        self.fencing_token = uuid.uuid4().hex
        self.expires_at = time.time() + timeout_seconds

    def is_valid(self, token: str) -> bool:
        return self.fencing_token == token and time.time() < self.expires_at


class WorkerLeaseManager:
    """Manages worker leases and prevents stale worker state overwrite."""

    def __init__(self):
        self.leases: Dict[str, WorkerLease] = {}

    def acquire_lease(self, task_id: str, worker_id: str, timeout: float = 60.0) -> WorkerLease:
        lease = WorkerLease(task_id, worker_id, timeout)
        self.leases[task_id] = lease
        return lease

    def validate_fencing_token(self, task_id: str, token: str) -> bool:
        lease = self.leases.get(task_id)
        if not lease:
            return False
        return lease.is_valid(token)

    def release_lease(self, task_id: str, token: str) -> bool:
        if self.validate_fencing_token(task_id, token):
            del self.leases[task_id]
            return True
        return False
