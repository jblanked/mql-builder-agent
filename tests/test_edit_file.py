"""
Test the MQL Builder Agent's --path (edit file) feature.

Tests:
1. read_context resolves names with .md extension
2. Editing an existing .mq5 file via --path works end-to-end
3. The output is valid JSON with expected fields
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.read_context import read_context

SAMPLE_EA = """#property copyright "Copyright 2025"
#property link      "https://example.com"
#property version   "1.00"
#property strict

int OnInit()
{
    Print("Hello World");
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
}

void OnTick()
{
}
"""


class TestReadContext(unittest.TestCase):
    """Tests for the read_context tool (the .md resolution fix)."""

    def test_read_single_file_by_bare_name(self):
        """Should find 'expert-advisor' -> 'expert-advisor.md'."""
        result = read_context("expert-advisor")
        self.assertNotIn("Missing context file", result)
        self.assertIn("## expert-advisor", result)
        self.assertTrue(len(result) > 50)

    def test_read_single_file_by_full_name(self):
        """Should also work with 'expert-advisor.md'."""
        result = read_context("expert-advisor.md")
        self.assertNotIn("Missing context file", result)
        self.assertIn("## expert-advisor.md", result)

    def test_read_multiple_files(self):
        """Comma-separated resources should all be found."""
        result = read_context("expert-advisor, style")
        self.assertNotIn("Missing context file", result)
        self.assertIn("## expert-advisor", result)
        self.assertIn("## style", result)

    def test_read_missing_file(self):
        """A non-existent file should report missing."""
        result = read_context("nonexistent-file-xyz")
        self.assertIn("Missing context file", result)

    def test_read_empty_string(self):
        """Empty resources string should return empty."""
        result = read_context("")
        self.assertEqual(result, "")

    def test_all_context_files_resolve(self):
        """Every CONTEXT_RESOURCE_URIs name should resolve."""
        names = [
            "voice", "trade", "risk-management", "object",
            "indicator", "expert-advisor", "script", "chart",
            "terminal", "strategies", "style",
        ]
        for name in names:
            with self.subTest(file=name):
                result = read_context(name)
                self.assertNotIn(
                    "Missing context file", result,
                    f"Context file '{name}' could not be resolved"
                )


class TestMqlFileRead(unittest.TestCase):
    """Tests for _read_mql_file utility."""

    def test_read_mql_file_utf8(self):
        """Should read a UTF-8 .mq5 file."""
        from main import _read_mql_file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".mq5", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_EA)
            tmp = f.name
        try:
            content, ext = _read_mql_file(tmp)
            self.assertEqual(ext, ".mq5")
            self.assertIn("Hello World", content)
            self.assertIn("OnDeinit", content)
        finally:
            os.unlink(tmp)

    def test_read_mql_file_not_found(self):
        """Non-existent file should raise FileNotFoundError."""
        from main import _read_mql_file
        with self.assertRaises(FileNotFoundError):
            _read_mql_file("/nonexistent/path/file.mq5")


class TestEndToEndEdit(unittest.TestCase):
    """End-to-end test: create a temp .mq5, edit via agent, verify result.

    This test actually calls the LLM and may cost credits.
    Skip unless TEST_E2E=1 environment variable is set.
    """

    def setUp(self):
        if not os.environ.get("TEST_E2E"):
            self.skipTest("Set TEST_E2E=1 to run end-to-end tests")

        self.tmpdir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.tmpdir, "TestEA.mq5")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_EA)

    def tearDown(self):
        if hasattr(self, "tmpdir") and os.path.isdir(self.tmpdir):
            import shutil
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_edit_file_via_topic(self):
        """Edit the file to add a goodbye message in OnDeinit."""
        from main import run_agent

        result = run_agent(
            topic="add a Print('Goodbye') to the OnDeinit handler",
            file_path=self.test_file,
        )
        self.assertIsInstance(result, str)

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            self.fail(f"Result is not valid JSON: {result[:200]}")

        self.assertIn("status", parsed)
        self.assertIn("file_path", parsed)
        # Should show as compiled_successfully (even if MetaEditor not found,
        # it might say compiled_with_warnings — but errors should be empty)
        self.assertNotEqual(parsed.get("status"), "compilation_failed",
                            f"Compilation failed with errors: {parsed.get('errors')}")

        # Verify the file on disk was updated
        with open(self.test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        self.assertIn("Goodbye", updated,
                      "Edited file should contain 'Goodbye'")


class TestJsonMode(unittest.TestCase):
    """Tests for the --json / run_agent_payload interface."""

    def test_payload_with_message(self):
        """run_agent_payload should handle 'message' key."""
        from main import run_agent_payload

        # This won't actually call the LLM since topic is empty ...
        # just tests the dispatch wrapper
        result = run_agent_payload({"message": "", "path": ""})
        self.assertIn("status", result)

    def test_payload_with_topic(self):
        """run_agent_payload should handle 'topic' key."""
        from main import run_agent_payload

        result = run_agent_payload({"topic": "", "path": ""})
        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
