"""
Unit tests for Multi-Agent Registry, Org Chart, A2A Policy, Subagent Runner, and Carrow.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from brigade_core.config import ConfigManager
from brigade_core.storage import StorageManager
from agents.registry import AgentRegistry
from agents.org_chart import OrgChart
from agents.a2a_policy import A2APolicy
from agents.subagent_runner import SubagentRunner
from agents.carrow import Carrow


class TestAgentsSuite(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config_mgr = ConfigManager(self.tmp / "brigade.json")
        self.storage_mgr = StorageManager(self.tmp)
        self.registry = AgentRegistry(self.config_mgr, self.storage_mgr)
        self.org_chart = OrgChart(self.config_mgr)
        self.a2a = A2APolicy(self.org_chart)
        self.runner = SubagentRunner(self.a2a)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_agent_registry_lifecycle(self):
        # Initial list should have 'main'
        agents = self.registry.list_agents()
        self.assertTrue(any(a["id"] == "main" for a in agents))

        # Add agent
        coder = self.registry.add_agent("coder", "Code Specialist", "Writes Python code")
        self.assertEqual(coder["id"], "coder")
        self.assertTrue((self.tmp / "agents" / "coder" / "workspace" / "SOUL.md").exists())

        # Cannot delete main
        with self.assertRaises(ValueError):
            self.registry.delete_agent("main", force=True)

        # Delete coder
        deleted = self.registry.delete_agent("coder", force=True)
        self.assertTrue(deleted)

    def test_org_chart_and_a2a_policy(self):
        # Tree renders
        tree = self.org_chart.render_tree()
        self.assertIn("Executive & Coordination", tree)

        # Main can message self and anyone
        allowed, _ = self.a2a.can_message("main", "main")
        self.assertTrue(allowed)

    def test_subagent_runner_and_cascade(self):
        res = self.runner.spawn_agent(
            parent_id="main",
            target_agent="main",
            prompt="Compute 2+2",
            agent_executor=lambda a, p: "4"
        )
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["result"], "4")

    def test_carrow_reasoning_sanitization(self):
        msgs = [{"role": "assistant", "content": "<think>private thoughts</think>Final answer."}]
        cleaned = Carrow.sanitize_messages_for_target(msgs, target_supports_reasoning=False)
        self.assertEqual(cleaned[0]["content"], "Final answer.")


if __name__ == "__main__":
    unittest.main()
