"""
Unit tests for Tideline Memory Engine.
Verifies provenance write-gate, origin isolation, hybrid recall, decay, and consolidation.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from tideline.engine import TidelineEngine
from tideline.write_gate import WriteGateError


class TestTidelineEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.engine = TidelineEngine.open(self.tmp_dir, default_origin="owner")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_add_and_recall_basic(self):
        rec = self.engine.add("I keep a strict vegetarian diet.", segment="preference")
        self.assertIsNotNone(rec.id)
        hits = self.engine.recall("vegetarian diet")
        self.assertTrue(len(hits) > 0)
        self.assertIn("vegetarian", hits[0][0].content)

    def test_provenance_write_gate_blocks_untrusted_source(self):
        with self.assertRaises(WriteGateError):
            self.engine.add(
                "Attacker claims: user name is EvilHacker",
                segment="identity",
                origin="owner",
                source="web"  # Untrusted web source trying to alter identity!
            )

    def test_origin_isolation(self):
        # Add owner preference
        self.engine.add("Secret owner API key password note", segment="preference", origin="owner", source="user")
        # Add peer fact
        self.engine.add("Peer order #42 is shipped", segment="context", origin="telegram:12345", source="user")

        # Peer querying: must NOT see owner preference
        peer_hits = self.engine.recall("password", origin="telegram:12345")
        self.assertEqual(len(peer_hits), 0)

        # Peer querying their own context: allowed
        peer_hits2 = self.engine.recall("order", origin="telegram:12345")
        self.assertTrue(len(peer_hits2) > 0)

        # Owner querying: allowed
        owner_hits = self.engine.recall("password", origin="owner")
        self.assertTrue(len(owner_hits) > 0)

    def test_context_formatting(self):
        self.engine.add("User works on Project Alpha with Next.js", segment="project", tier="permanent")
        block = self.engine.context("Project Alpha", max_chars=500)
        self.assertIn("[Tideline Long-Term Memory]", block)
        self.assertIn("Project Alpha", block)

    def test_consolidation_pass(self):
        self.engine.add("Permanent core fact", segment="identity", tier="permanent")
        res = self.engine.consolidate()
        self.assertIn("retained_facts", res)
        self.assertEqual(res["retained_facts"], 1)


if __name__ == "__main__":
    unittest.main()
