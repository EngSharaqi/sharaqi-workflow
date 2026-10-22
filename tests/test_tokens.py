"""Tests for scripts/tokens.py against a small synthetic transcript. Standard library only.

usage: python3 -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "tokens.py")
SID = "11111111-2222-3333-4444-555555555555"


def assistant(ts, req, model, **usage):
    return {"type": "assistant", "timestamp": ts, "requestId": req,
            "message": {"id": "msg_" + req, "model": model, "usage": usage}}


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write((r if isinstance(r, str) else json.dumps(r)) + "\n")


class TokensTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        proj = os.path.join(self.tmp.name, "projects", "-repo")
        os.makedirs(os.path.join(proj, SID, "subagents"))
        write_jsonl(os.path.join(proj, SID + ".jsonl"), [
            # Before --since: ignored.
            assistant("2026-01-01T09:00:00Z", "r0", "claude-opus-5-5",
                      input_tokens=999999, output_tokens=999999),
            "not json",
            {"type": "user", "timestamp": "2026-01-01T10:00:01Z"},
            # One response written as two lines: the last one carries the full output.
            assistant("2026-01-01T10:00:02Z", "r1", "claude-opus-5-5",
                      input_tokens=10, cache_creation_input_tokens=1000,
                      cache_read_input_tokens=2000, output_tokens=1),
            assistant("2026-01-01T10:00:03Z", "r1", "claude-opus-5-5",
                      input_tokens=10, cache_creation_input_tokens=1000,
                      cache_read_input_tokens=2000, output_tokens=500),
            assistant("2026-01-01T10:00:04Z", "r2", "some-other-model",
                      input_tokens=7, output_tokens=7),
        ])
        sub = os.path.join(proj, SID, "subagents", "agent-a")
        write_jsonl(sub + ".jsonl", [
            # Haiku over 100k prompt tokens: long-context rates.
            assistant("2026-01-01T10:01:00Z", "s1", "claude-haiku-5-5",
                      input_tokens=5, cache_read_input_tokens=200000, output_tokens=100),
        ])
        with open(sub + ".meta.json", "w", encoding="utf-8") as fh:
            json.dump({"agentType": "sharaqi:reviewer"}, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra, session=SID):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.tmp.name)
        return subprocess.run(
            [sys.executable, "-I", SCRIPT, "--session", session,
             "--since", "2026-01-01T10:00:00Z", *extra],
            capture_output=True, text=True, encoding="utf-8", env=env)

    def test_totals(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        # opus: 10 + 1000 + 2000 + 500; haiku: 5 + 200000 + 100
        self.assertIn("TOTAL_TOKENS: 203,615 (output 600)", r.stdout)
        self.assertIn("REQUESTS: 2 (subagent 1)", r.stdout)
        # (10*4 + 1000*5 + 2000*0.2 + 500*20 + 5*0.5 + 200000*0.05 + 100*2.5) / 1e6
        self.assertIn("LIST_PRICE_USD: 0.0257", r.stdout)
        self.assertIn("UNPRICED_REQUESTS: 1", r.stdout)
        self.assertIn("| sharaqi:reviewer | haiku | 1 |", r.stdout)
        self.assertIn("PRICES_CHECKED:", r.stdout)
        # Sorted by cost: opus $0.0154, then haiku $0.0103.
        self.assertIn("By model (tokens · requests · $): opus ", r.stdout)
        self.assertIn(" · 1 · `$0.02` | haiku ", r.stdout)

    def test_arabic_summary(self):
        r = self.run_script("--lang", "ar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("التوكنز:", r.stdout)

    def test_missing_transcript(self):
        r = self.run_script(session="no-such-session")
        self.assertEqual(r.returncode, 1)
        self.assertIn("TOKENS: unavailable", r.stdout)


if __name__ == "__main__":
    unittest.main()
