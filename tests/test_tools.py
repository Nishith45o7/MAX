"""
Unit tests for the Unified Tool Suite and Ownership Gating.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from tools.registry import ToolRegistry
from tools.coding_tools import CodingTools
from tools.doc_tools import DocumentTools
from security.path_guard import PathGuard


class TestToolsSuite(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path_guard = PathGuard([self.tmp])
        self.coding = CodingTools(path_guard=self.path_guard)
        self.docs = DocumentTools(path_guard=self.path_guard)
        self.registry = ToolRegistry(coding_tools=self.coding, doc_tools=self.docs)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_coding_tools_write_and_read(self):
        test_file = self.tmp / "sample.txt"
        res_write = self.registry.execute("write", {"path": str(test_file), "content": "Hello World\nLine 2"}, is_owner=True)
        self.assertIn("Successfully wrote", res_write)

        res_read = self.registry.execute("read", {"path": str(test_file)}, is_owner=True)
        self.assertIn("Hello World", res_read)

    def test_ownership_gating(self):
        # Peer cannot call owner_only write
        test_file = self.tmp / "peer_hack.txt"
        res_denied = self.registry.execute("write", {"path": str(test_file), "content": "attack"}, is_owner=False)
        self.assertIn("Permission Denied", res_denied)

    def test_doc_creation(self):
        txt_doc = self.tmp / "report.txt"
        res = self.registry.execute("make_document", {
            "doc_type": "txt",
            "path": str(txt_doc),
            "title": "Quarterly Report",
            "content": "All systems operational."
        }, is_owner=True)
        self.assertIn("Successfully created", res)
        self.assertTrue(txt_doc.exists())


if __name__ == "__main__":
    unittest.main()
