"""
Unit tests for the Channel Inbound Pipeline, Pairing Challenges, and Deduplication.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from brigade_core.config import ConfigManager
from channels.base import ChannelMessage
from channels.inbound_pipeline import InboundPipeline


class TestChannelsSuite(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config_mgr = ConfigManager(self.tmp / "brigade.json")
        self.pipeline = InboundPipeline(self.config_mgr)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_sender_becomes_owner(self):
        msg = ChannelMessage(
            channel="telegram",
            account_id="default",
            sender_id="111222333",
            sender_name="Alice",
            message_id="msg_001",
            text="Hello bot"
        )
        res = self.pipeline.process_inbound(msg)
        self.assertEqual(res.status, "allowed")
        self.assertTrue(res.is_owner)

    def test_second_sender_requires_pairing(self):
        # Alice is owner
        msg_alice = ChannelMessage("telegram", "default", "111", "Alice", "1", "hi")
        self.pipeline.process_inbound(msg_alice)

        # Bob messages without allowlist
        msg_bob = ChannelMessage("telegram", "default", "999", "Bob", "2", "can I enter?")
        res_bob = self.pipeline.process_inbound(msg_bob)
        self.assertEqual(res_bob.status, "pairing_required")
        self.assertIn("pairing code is", res_bob.response_text)

        # Alice approves Bob's pairing code
        code = list(self.pipeline.pending_pairings.keys())[0]
        ok, reason = self.pipeline.approve_pairing(code, "telegram")
        self.assertTrue(ok)

        # Bob messages again: allowed!
        msg_bob2 = ChannelMessage("telegram", "default", "999", "Bob", "3", "thank you")
        res_bob2 = self.pipeline.process_inbound(msg_bob2)
        self.assertEqual(res_bob2.status, "allowed")

    def test_deduplication(self):
        msg = ChannelMessage("telegram", "default", "111", "Alice", "dup_1", "text")
        res1 = self.pipeline.process_inbound(msg)
        self.assertEqual(res1.status, "allowed")

        # Exact same message ID
        res2 = self.pipeline.process_inbound(msg)
        self.assertEqual(res2.status, "duplicate")

    def test_abort_trigger(self):
        msg = ChannelMessage("telegram", "default", "111", "Alice", "abort_1", "/abort")
        res = self.pipeline.process_inbound(msg)
        self.assertEqual(res.status, "aborted")


if __name__ == "__main__":
    unittest.main()
