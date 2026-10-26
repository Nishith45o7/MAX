"""
Task Dependency DAG Engine with All, Any, and Quorum Joins.
"""
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal

JoinPolicy = Literal["all", "any", "quorum"]


@dataclass
class TeamTask:
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:6]}")
    title: str = ""
    assignee: str = "main"
    depends_on: List[str] = field(default_factory=list)
    join_policy: JoinPolicy = "all"
    min_completed: int = 1
    status: Literal["pending", "ready", "leased", "completed", "failed"] = "pending"
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class TaskGraph:
    """Manages task dependency execution graphs and join policies."""

    def __init__(self):
        self.tasks: Dict[str, TeamTask] = {}

    def add_task(
        self,
        title: str,
        assignee: str = "main",
        depends_on: Optional[List[str]] = None,
        join_policy: JoinPolicy = "all",
        min_completed: int = 1
    ) -> TeamTask:
        task = TeamTask(
            title=title,
            assignee=assignee,
            depends_on=depends_on or [],
            join_policy=join_policy,
            min_completed=min_completed,
            status="pending" if depends_on else "ready"
        )
        self.tasks[task.id] = task
        return task

    def evaluate_readiness(self) -> List[TeamTask]:
        """Evaluates pending tasks against upstream dependencies and marks eligible ones ready."""
        ready_tasks = []
        for task in self.tasks.values():
            if task.status != "pending":
                if task.status == "ready":
                    ready_tasks.append(task)
                continue

            upstream = [self.tasks.get(tid) for tid in task.depends_on if tid in self.tasks]
            completed_count = sum(1 for u in upstream if u and u.status == "completed")

            is_ready = False
            if task.join_policy == "all":
                is_ready = (completed_count == len(task.depends_on))
            elif task.join_policy == "any":
                is_ready = (completed_count >= 1)
            elif task.join_policy == "quorum":
                is_ready = (completed_count >= task.min_completed)

            if is_ready:
                task.status = "ready"
                ready_tasks.append(task)

        return ready_tasks

    def complete_task(self, task_id: str, result: str) -> bool:
        if task_id in self.tasks:
            t = self.tasks[task_id]
            t.status = "completed"
            t.result = result
            t.completed_at = time.time()
            self.evaluate_readiness()
            return True
        return False
