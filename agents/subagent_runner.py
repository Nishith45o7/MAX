"""
Subagent Runner with Abort Cascade and Completion Wake-On-Settle.
Supports single-child delegation (spawn_agent) and parallel fan-out (spawn_agents).
"""
import time
import uuid
import threading
from typing import List, Dict, Any, Optional, Callable
from agents.a2a_policy import A2APolicy


class SubagentTask:
    """Represents an active or settled subagent run."""
    def __init__(self, task_id: str, parent_id: str, agent_id: str, prompt: str, depth: int = 1):
        self.task_id = task_id
        self.parent_id = parent_id
        self.agent_id = agent_id
        self.prompt = prompt
        self.depth = depth
        self.status = "running"  # "running", "completed", "failed", "aborted"
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self._cancel_flag = threading.Event()

    def abort(self) -> None:
        self._cancel_flag.set()
        self.status = "aborted"
        self.completed_at = time.time()


class SubagentRunner:
    """Manages spawning, execution limits, parallel fan-out, and cancellation cascades."""

    MAX_DEPTH = 3
    MAX_CONCURRENT_PER_PARENT = 5

    def __init__(self, a2a_policy: Optional[A2APolicy] = None):
        self.a2a_policy = a2a_policy or A2APolicy()
        self.active_tasks: Dict[str, SubagentTask] = {}
        self._lock = threading.RLock()

    def spawn_agent(
        self,
        parent_id: str,
        target_agent: str,
        prompt: str,
        depth: int = 1,
        agent_executor: Optional[Callable[[str, str], str]] = None
    ) -> Dict[str, Any]:
        """
        Executes a single child agent task.
        """
        # 1. Depth check
        if depth > self.MAX_DEPTH:
            raise ValueError(f"Subagent depth limit ({self.MAX_DEPTH}) exceeded (attempted depth: {depth}).")

        # 2. A2A Policy permission check
        allowed, reason = self.a2a_policy.can_message(parent_id, target_agent)
        if not allowed:
            raise PermissionError(f"A2A Policy denied delegation from '{parent_id}' to '{target_agent}': {reason}")

        # 3. Concurrency check
        with self._lock:
            parent_running = [t for t in self.active_tasks.values() if t.parent_id == parent_id and t.status == "running"]
            if len(parent_running) >= self.MAX_CONCURRENT_PER_PARENT:
                raise RuntimeError(f"Parent '{parent_id}' reached max concurrent child limit ({self.MAX_CONCURRENT_PER_PARENT}).")

            task_id = f"subtask_{uuid.uuid4().hex[:8]}"
            task = SubagentTask(task_id, parent_id, target_agent, prompt, depth)
            self.active_tasks[task_id] = task

        # Execute task
        try:
            if agent_executor:
                output = agent_executor(target_agent, prompt)
            else:
                output = f"[Simulated Output from {target_agent} for: {prompt[:40]}]"
            task.result = output
            task.status = "completed"
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
        finally:
            task.completed_at = time.time()

        return {
            "taskId": task.task_id,
            "agent": task.agent_id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "durationMs": round((task.completed_at - task.created_at) * 1000, 2)
        }

    def spawn_agents(
        self,
        parent_id: str,
        tasks: List[Dict[str, str]],
        depth: int = 1,
        agent_executor: Optional[Callable[[str, str], str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes parallel fan-out across multiple child agents.
        """
        results: List[Dict[str, Any]] = [None] * len(tasks)
        threads = []

        def worker(index: int, t_info: Dict[str, str]):
            target = t_info.get("agent", "main")
            prompt = t_info.get("prompt", "")
            try:
                res = self.spawn_agent(parent_id, target, prompt, depth=depth, agent_executor=agent_executor)
                results[index] = res
            except Exception as e:
                results[index] = {
                    "agent": target,
                    "status": "failed",
                    "error": str(e)
                }

        for i, t in enumerate(tasks):
            th = threading.Thread(target=worker, args=(i, t), daemon=True)
            threads.append(th)
            th.start()

        for th in threads:
            th.join(timeout=60)

        return results

    def abort_cascade(self, parent_id: str) -> int:
        """Aborts all active child subagent tasks spawned by parent_id."""
        aborted = 0
        with self._lock:
            for task in self.active_tasks.values():
                if task.parent_id == parent_id and task.status == "running":
                    task.abort()
                    aborted += 1
        return aborted
