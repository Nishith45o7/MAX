"""
Unit tests for Team Mode Collaboration: Rooms, Task DAGs, Leases, and Review Gates.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from collaboration.room import TeamRoomManager
from collaboration.task_graph import TaskGraph
from collaboration.leasing import WorkerLeaseManager
from collaboration.review_gate import ReviewGate


class TestCollaborationSuite(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.room_mgr = TeamRoomManager(self.tmp)
        self.graph = TaskGraph()
        self.lease_mgr = WorkerLeaseManager()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_room_lifecycle_and_mentions(self):
        room = self.room_mgr.create_room("Sprint Room", topic="Project Alpha")
        self.assertIsNotNone(room.id)

        msg = self.room_mgr.post_message(room.id, sender="main", content="Hey @coder and @tester please review!")
        self.assertEqual(len(msg.mentions), 2)
        self.assertIn("coder", msg.mentions)
        self.assertIn("tester", msg.mentions)

        retrieved = self.room_mgr.get_messages(room.id)
        self.assertEqual(len(retrieved), 1)

    def test_task_dag_joins(self):
        t1 = self.graph.add_task("Gather data", assignee="coder")
        t2 = self.graph.add_task("Process data", assignee="coder")
        t3 = self.graph.add_task("Final report", assignee="main", depends_on=[t1.id, t2.id], join_policy="all")

        ready = self.graph.evaluate_readiness()
        self.assertEqual(len(ready), 2) # t1 and t2 ready, t3 pending

        self.graph.complete_task(t1.id, "Data gathered")
        self.assertEqual(t3.status, "pending")

        self.graph.complete_task(t2.id, "Data processed")
        ready_now = self.graph.evaluate_readiness()
        self.assertTrue(any(t.id == t3.id for t in ready_now))
        self.assertEqual(t3.status, "ready")

    def test_worker_leasing_and_fencing(self):
        lease = self.lease_mgr.acquire_lease("task_1", "worker_coder", timeout=10.0)
        self.assertTrue(self.lease_mgr.validate_fencing_token("task_1", lease.fencing_token))
        self.assertFalse(self.lease_mgr.validate_fencing_token("task_1", "fake_token"))

    def test_review_gate(self):
        passed, _ = ReviewGate.verify_result("Valid analysis output completed.")
        self.assertTrue(passed)
        failed, _ = ReviewGate.verify_result("error: failed to connect")
        self.assertFalse(failed)


if __name__ == "__main__":
    unittest.main()
