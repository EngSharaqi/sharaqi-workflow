"""Tests for scripts/runrecord.py: one record per benchmark run, and the per-arm summary.
Standard library only.

The aggregation check uses the recorded session in tests/fixtures/bench-2026-10-22 (a main
thread and two subagents) whose Claude Code total was $1.4918871: the transcript estimate
must land on it (each request counted once), and the record's actual cost must be that
total alone, never the total plus the subagents again.

usage: python3 -m unittest discover -s tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "runrecord.py")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "bench-2026-10-22")
SID = "00000000-0000-4000-8000-000000000001"
CLI_USD = 1.4918871


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Record(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = os.path.join(self.tmp.name, "cfg")
        shutil.copytree(FIXTURE, self.cfg)
        self.result = os.path.join(self.tmp.name, "r.json")
        self.write_result()

    def tearDown(self):
        self.tmp.cleanup()

    def write_result(self, **over):
        res = {"type": "result", "subtype": "success", "is_error": False, "session_id": SID,
               "total_cost_usd": CLI_USD, "duration_ms": 245000, "duration_api_ms": 200000,
               "num_turns": 19,
               "modelUsage": {"claude-opus-5": {"inputTokens": 1, "outputTokens": 2,
                                                "cacheReadInputTokens": 3,
                                                "cacheCreationInputTokens": 4,
                                                "costUSD": 1.2}}}
        res.update(over)
        with open(self.result, "w", encoding="utf-8") as fh:
            json.dump({k: v for k, v in res.items() if v is not None}, fh)

    def record(self, *extra, arm="v1.0"):
        rc, out, err = run("record", "--result", self.result, "--run-id", "r1", "--arm", arm,
                           "--version", "test", "--case", "2", "--config-dir", self.cfg, *extra)
        self.assertEqual(rc, 0, err)
        return json.loads(out)

    def test_no_double_counting(self):
        r = self.record("--wall-s", "250.5", "--started", "2026-10-22T10:00:00Z",
                        "--finished", "2026-10-22T10:04:10Z")
        c = r["cost"]
        self.assertEqual(c["actual_usd"], CLI_USD)
        self.assertIn("includes subagents", c["actual_source"])
        self.assertAlmostEqual(c["transcript_estimate_usd"], CLI_USD, places=4)
        self.assertLess(abs(c["reconciliation_delta_usd"]), 0.0001)
        self.assertEqual(r["delegation"]["subagent_threads"], 2)
        self.assertEqual(r["delegation"]["subagent_types"],
                         ["sharaqi:implementer", "sharaqi:reviewer"])
        self.assertEqual(r["wall_s"], 250.5)
        self.assertEqual(r["status"], "completed")
        self.assertNotIn("wall_s", r["unknown"])

    def test_models_by_role(self):
        m = self.record()["models"]
        self.assertTrue(m["orchestration"])
        self.assertTrue(m["execution"], "implementer subagent")
        self.assertTrue(m["review"], "reviewer subagent")

    def test_per_model_usage_comes_from_claude_code(self):
        bm = self.record()["cost"]["by_model"]["claude-opus-5"]
        self.assertEqual((bm["input"], bm["output"], bm["cache_read"], bm["cache_write"],
                          bm["cost_usd"]), (1, 2, 3, 4, 1.2))

    def test_unknown_is_null_never_guessed(self):
        self.write_result(total_cost_usd=None, modelUsage=None)
        r = self.record()
        self.assertIsNone(r["cost"]["actual_usd"])
        self.assertIsNone(r["cost"]["reconciliation_delta_usd"])
        for k in ("actual_usd", "tokens_by_model", "wall_s", "tests", "repairs"):
            self.assertIn(k, r["unknown"], k)
        self.assertIsNotNone(r["cost"]["transcript_estimate_usd"], "the estimate is separate")

    def test_missing_transcript(self):
        self.write_result(session_id="11111111-0000-4000-8000-000000000009")
        r = self.record()
        self.assertIn("transcript", r["unknown"])
        self.assertIsNone(r["delegation"])
        self.assertEqual(r["cost"]["actual_usd"], CLI_USD)

    def test_events(self):
        d = os.path.join(self.cfg, "sharaqi-state")
        os.makedirs(d)
        rows = [
            {"event": "route", "route": "ROUTE track=coding tier=planned", "confidence": "high"},
            {"event": "agent", "model": "sonnet", "effort": "low", "decision": "allow"},
            {"event": "agent", "model": "opus", "effort": "high", "escalate": "critical",
             "subagent_type": "sharaqi:reviewer", "decision": "allow"},
            {"event": "agent", "model": "opus", "decision": "block"},
            {"event": "gate", "decision": "allow", "class": "ok"},
            {"event": "gate", "decision": "block", "class": "unverified-window"},
        ]
        with open(os.path.join(d, SID + ".events.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        e = self.record()["events"]
        self.assertEqual(e["route"]["route"], "ROUTE track=coding tier=planned")
        self.assertEqual((e["agent_calls_logged"], e["agent_calls_blocked"]), (3, 1))
        self.assertEqual([x["escalate"] for x in e["escalations"]], ["critical", None])
        self.assertEqual(e["gate"], {"allow:ok": 1, "block:unverified-window": 1})

    def test_plain_arm_has_no_events_and_says_nothing_missing(self):
        r = self.record(arm="plain")
        self.assertIsNone(r["events"])
        self.assertNotIn("events", r["unknown"])
        self.assertIn("events", self.record(arm="v1.0")["unknown"])

    def test_stream_json_and_errors(self):
        with open(self.result, "w", encoding="utf-8") as fh:
            fh.write('{"type":"system","subtype":"init"}\nnoise\n')
            fh.write(json.dumps({"type": "result", "subtype": "error_max_budget_usd",
                                 "is_error": True, "session_id": SID,
                                 "total_cost_usd": 0.5}) + "\n")
        r = self.record()
        self.assertEqual((r["status"], r["cost"]["actual_usd"]), ("error", 0.5))
        with open(self.result, "w", encoding="utf-8") as fh:
            fh.write("nothing here\n")
        rc, _, err = run("record", "--result", self.result, "--run-id", "x", "--arm", "v1.0",
                         "--version", "t", "--config-dir", self.cfg)
        self.assertEqual(rc, 1)
        self.assertIn("no result event", err)

    def test_summary_per_arm(self):
        paths = []
        for arm, usd, wall in (("plain", 0.2, 10.0), ("plain", 0.3, 12.0), ("v1.0", 0.1, None)):
            p = os.path.join(self.tmp.name, "%s-%d.json" % (arm, len(paths)))
            rec = {"arm": arm, "status": "completed", "cost": {"actual_usd": usd},
                   "wall_s": wall, "cli_duration_ms": 1000, "num_turns": 2,
                   "delegation": {"agent_calls": 1}, "events": None}
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(rec, fh)
            paths.append(p)
        rc, out, _ = run("summarize", *paths)
        self.assertEqual(rc, 0)
        self.assertIn("| plain | 2 | 2 | 0.5000 | 0.2500 | 22.0 · 11.0 |", out)
        self.assertIn("| v1.0 | 1 | 1 | 0.1000 | 0.1000 | n/a · n/a |", out)

    def failure(self, *extra):
        rc, out, err = run("failure", "--result", self.result, "--run-id", "v1.0-2-1",
                           "--arm", "v1.0", "--version", "t", "--case", "2", *extra)
        self.assertEqual(rc, 0, err)
        return json.loads(out)

    def assert_no_result(self, r, reason):
        self.assertEqual(r["status"], "no-result")
        self.assertEqual(r["failure"]["reason"], reason)
        self.assertIsNone(r["cost"]["actual_usd"])
        self.assertIn("actual_usd", r["unknown"])
        rc, _, err = run("validate", self.write_record(r))
        self.assertEqual(rc, 0, err)

    def write_record(self, r):
        p = os.path.join(self.tmp.name, "rec.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(r, fh)
        return p

    def test_failure_empty_output(self):
        open(self.result, "w").close()
        self.assert_no_result(self.failure("--exit-code", "0"), "empty-output")

    def test_failure_malformed_output(self):
        with open(self.result, "w", encoding="utf-8") as fh:
            fh.write('{"type":"system","subtype":"init"}\n{"type": "res')
        self.assert_no_result(self.failure("--exit-code", "1"), "no-result-event")

    def test_failure_timeout_and_error_log(self):
        log = os.path.join(self.tmp.name, "err")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("x" * 5000 + "killed\n")
        r = self.failure("--exit-code", "142", "--error-log", log, "--wall-s", "300.2")
        self.assert_no_result(r, "timeout")
        self.assertEqual((r["exit_code"], r["wall_s"]), (142, 300.2))
        self.assertTrue(r["failure"]["error_log_tail"].endswith("killed\n"))
        self.assertLessEqual(len(r["failure"]["error_log_tail"]), 2000)

    def test_failure_record_failed(self):
        self.assert_no_result(self.failure("--exit-code", "0"), "record-failed")

    def test_failure_missing_output_file(self):
        os.remove(self.result)
        self.assert_no_result(self.failure("--exit-code", "1"), "empty-output")

    def test_nonzero_exit_with_success_event_is_not_completed(self):
        r = self.record("--exit-code", "3")
        self.assertEqual((r["status"], r["exit_code"]), ("error", 3))
        self.assertEqual(self.record("--exit-code", "0")["status"], "completed")

    def test_validate_rejects_incomplete_records(self):
        good = self.record()
        for broken in ({}, [], {k: v for k, v in good.items() if k != "status"},
                       dict(good, cost={}), dict(good, cost={"actual_usd": "0.2"}),
                       dict(good, cost={"actual_usd": None}, unknown=[])):
            rc, _, err = run("validate", self.write_record(broken))
            self.assertEqual(rc, 1, broken)
        for text in ("", "{not json"):
            p = os.path.join(self.tmp.name, "bad.json")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.assertEqual(run("validate", p)[0], 1, repr(text))
        self.assertEqual(run("validate", self.write_record(good))[0], 0)

    def test_summary_no_cost_observations_is_unknown_not_zero(self):
        paths = []
        for i in range(2):
            p = os.path.join(self.tmp.name, "f%d.json" % i)
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"arm": "v1.0", "run_id": "r%d" % i, "case_id": "1",
                           "status": "no-result", "cost": {"actual_usd": None},
                           "unknown": ["actual_usd"]}, fh)
            paths.append(p)
        rc, out, _ = run("summarize", *paths)
        self.assertEqual(rc, 0)
        self.assertIn("| v1.0 | 2 | 0 | unknown | unknown |", out)
        self.assertNotIn("0.0000", out)
        self.assertTrue(out.rstrip().endswith("| 2 |"), "unknown-cost count")

    def test_summary_skips_unreadable_records(self):
        p = os.path.join(self.tmp.name, "empty.json")
        open(p, "w").close()
        rc, out, err = run("summarize", p)
        self.assertEqual(rc, 0)
        self.assertIn("skipped", err)


if __name__ == "__main__":
    unittest.main()
