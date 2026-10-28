"""Tests for the three-arm benchmark kit in benchmarks/v1.0: route normalization in score.py,
run.sh's records for failed runs, score.py on a partial RUNS, and prepare.sh's copies.
Standard library only. No test calls the API: `claude` is a stub on PATH.

usage: python3 -m unittest discover -s tests
"""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "benchmarks", "v1.0")
RUNRECORD = os.path.join(ROOT, "scripts", "runrecord.py")

spec = importlib.util.spec_from_file_location("score", os.path.join(BENCH, "score.py"))
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)

CASE4_V09 = ("ROUTE track=coding tier=critical mode=CRITICAL plan=card approval=yes "
             "executor=inline review=reviewer-high·opus·high checks=standard+negative")
CASE10_V10 = ("ROUTE track=mixed tier=tiny mode=FAST plan=none approval=no executor=inline "
              "review=none writing=direct")

# A stand-in `claude`: FAKE_MODE picks what it prints and how it exits.
FAKE_CLAUDE = r"""#!/bin/bash
[ "${1:-}" = --version ] && { echo "0.0.0 (fake)"; exit 0; }
[ -n "${FAKE_CALLED:-}" ] && : > "$FAKE_CALLED"
init='{"type":"system","subtype":"init","agents":["sharaqi:implementer","sharaqi:planner","sharaqi:reviewer"]}'
res='{"type":"result","subtype":"success","is_error":false,"session_id":"fake-sid","total_cost_usd":0.25,"duration_ms":1000,"num_turns":2}'
case "$FAKE_MODE" in
  ok) echo "$init"; echo "$res" ;;
  empty) ;;
  malformed) echo "$init"; printf '{"type":"result","subt' ;;
  nonzero) echo "$init"; echo boom >&2; exit 1 ;;
  nonzero-with-result) echo "$init"; echo "$res"; exit 3 ;;
  sleep) echo "$init"; exec sleep 10 ;;
  bad-record) echo '{"type":"result","subtype":"success","session_id":"fake-sid","total_cost_usd":0.1,"modelUsage":{"m":5}}' ;;
esac
"""


def write_exe(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


class Normalize(unittest.TestCase):
    def test_trailing_backticks(self):
        self.assertEqual(score.misses("v0.9", "4", CASE4_V09 + " gate=hook`"), [])
        self.assertEqual(score.misses("v1.0", "10", CASE10_V10 + "``"), [])

    def test_trailing_asterisks(self):
        self.assertEqual(score.misses("v1.0", "10", CASE10_V10 + "**"), [])
        self.assertEqual(score.clean_route(CASE10_V10 + "*` "), (CASE10_V10, True))

    def test_whitespace(self):
        self.assertEqual(score.misses("v1.0", "10", CASE10_V10 + "  \n"), [])
        self.assertEqual(score.clean_route(CASE10_V10), (CASE10_V10, False))

    def test_wrong_route_stays_wrong(self):
        wrong = CASE10_V10.replace("writing=direct", "writing=draft") + "`"
        self.assertEqual(score.misses("v1.0", "10", wrong), ["writing=direct (got draft)"])
        # only trailing delimiters go: a value that is wrong inside the line stays wrong
        self.assertEqual(score.misses("v1.0", "10", CASE10_V10.replace("tier=tiny", "tier=`tiny`")),
                         ["tier=tiny (got `tiny`)"])

    def test_missing_route(self):
        for line in (None, "", "`**"):
            self.assertEqual(len(score.misses("v1.0", "10", line)), len(score.EXP["v1.0"]["10"]),
                             repr(line))

    def test_format_reported_apart_from_correctness(self):
        rec = {"arm": "v1.0", "case_id": "10", "status": "completed",
               "route_printed": [CASE10_V10 + "`"], "events": {"route": {"route": CASE10_V10}}}
        self.assertEqual(score.route_verdict(rec), ("PASS", "trailing Markdown dropped"))
        rec["route_printed"] = [CASE10_V10.replace("tier=tiny", "tier=planned") + "`"]
        self.assertIn("printed route differs", score.route_verdict(rec)[0])
        rec = {"arm": "v1.0", "case_id": "10", "status": "no-result", "route_printed": None,
               "events": None}
        self.assertEqual(score.route_verdict(rec), ("FAIL: no route (run no-result)", "no route"))


class Bench(unittest.TestCase):
    """A RUNS whose v1.0 plugin is this repo, with `claude` stubbed on PATH."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.runs = os.path.join(t, "runs")
        for d in ("out", "records", "work", "plugins"):
            os.makedirs(os.path.join(self.runs, d))
        os.symlink(ROOT, os.path.join(self.runs, "plugins", "v1.0"))
        with open(os.path.join(self.runs, "plugins", "v1.0.id"), "w") as fh:
            fh.write("worktree-tree:test\n")
        with open(os.path.join(self.runs, "claude-version.txt"), "w") as fh:
            fh.write("0.0.0 (fake)\n")
        self.bin = os.path.join(t, "bin")
        os.makedirs(self.bin)
        write_exe(os.path.join(self.bin, "claude"), FAKE_CLAUDE)
        self.called = os.path.join(t, "called")
        self.env = dict(os.environ, RUNS=self.runs, PATH=self.bin + os.pathsep + os.environ["PATH"],
                        CLAUDE_CONFIG_DIR=os.path.join(t, "cfg"), FAKE_CALLED=self.called,
                        BENCH_TIMEOUT_S="2")
        self.env.pop("PREFLIGHT", None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_sh(self, mode, arm="v1.0", case="1"):
        env = dict(self.env, FAKE_MODE=mode)
        return subprocess.run(["bash", os.path.join(BENCH, "run.sh"), arm, case, "1"], env=env,
                              capture_output=True, text=True, timeout=60)

    def rec(self, name="v1.0-1-1"):
        with open(os.path.join(self.runs, "records", name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)

    def assert_no_temp(self):
        self.assertEqual([f for f in os.listdir(os.path.join(self.runs, "records"))
                          if f.endswith(".tmp")], [])


class RunSh(Bench):
    def test_success(self):
        p = self.run_sh("ok")
        self.assertEqual(p.returncode, 0, p.stderr)
        r = self.rec()
        self.assertEqual((r["status"], r["cost"]["actual_usd"], r["exit_code"]), ("completed", 0.25, 0))
        self.assertEqual(json.loads(p.stdout)["status"], "completed")
        self.assert_no_temp()

    def check_failure(self, mode, reason, rc=None):
        p = self.run_sh(mode)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        r = self.rec()
        self.assertEqual((r["status"], r["failure"]["reason"]), ("no-result", reason))
        self.assertIsNone(r["cost"]["actual_usd"])
        self.assertIn("actual_usd", r["unknown"])
        if rc is not None:
            self.assertEqual(r["exit_code"], rc)
        self.assertEqual(subprocess.call([sys.executable, "-I", RUNRECORD, "validate",
                                          os.path.join(self.runs, "records", "v1.0-1-1.json")]), 0)
        self.assert_no_temp()
        return r

    def test_empty_output(self):
        self.check_failure("empty", "empty-output", 0)

    def test_malformed_output(self):
        self.check_failure("malformed", "no-result-event", 0)

    def test_nonzero_exit(self):
        r = self.check_failure("nonzero", "no-result-event", 1)
        self.assertIn("boom", r["failure"]["error_log_tail"])

    def test_timeout(self):
        self.check_failure("sleep", "timeout", 142)

    def test_record_generation_failure(self):
        self.check_failure("bad-record", "record-failed", 0)

    def test_nonzero_exit_with_result_is_not_success(self):
        p = self.run_sh("nonzero-with-result")
        self.assertEqual(p.returncode, 1)
        r = self.rec()
        self.assertEqual((r["status"], r["exit_code"], r["cost"]["actual_usd"]), ("error", 3, 0.25))

    def test_existing_record_is_never_overwritten(self):
        path = os.path.join(self.runs, "records", "v1.0-1-1.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"historical": true}')
        p = self.run_sh("empty")
        self.assertEqual(p.returncode, 1)
        self.assertIn("exists", p.stderr)
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), '{"historical": true}')
        self.assertFalse(os.path.exists(self.called), "claude must not run")


class PartialRuns(Bench):
    def score(self):
        return subprocess.run([sys.executable, "-I", os.path.join(BENCH, "score.py"), self.runs],
                              capture_output=True, text=True, timeout=60)

    def test_partial_directory(self):
        self.assertEqual(self.run_sh("ok", "v1.0", "1").returncode, 0)
        self.assertEqual(self.run_sh("empty", "plain", "1").returncode, 1)
        recs = os.path.join(self.runs, "records")
        open(os.path.join(recs, "v0.9-2-1.json"), "w").close()  # an empty file
        with open(os.path.join(recs, "v0.9-3-1.json"), "w") as fh:
            fh.write("{not json")
        p = self.score()
        self.assertEqual(p.returncode, 1, "a partial RUNS is never a clean result")
        self.assertNotIn("Traceback", p.stderr)
        out = p.stdout
        self.assertIn("| v0.9-2-1 | unreadable record", out)
        self.assertIn("| v0.9-3-1 | unreadable record", out)
        self.assertIn("| plain-1-1 | no-result (empty-output, rc=0) | unknown |", out)
        self.assertIn("v0.9-1-1", out.split("Missing runs")[1].splitlines()[0])
        self.assertIn("v1.0-10-1", out)
        self.assertIn("| plain | 1 | 0 | unknown | unknown |", out)
        self.assertIn("| v1.0 | 1 | 1 | 0.2500 | 0.2500 |", out)

    def test_empty_directory(self):
        p = self.score()
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("No usable records", p.stdout)
        self.assertEqual(p.returncode, 0, "nothing ran, nothing missing")


class Prepare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = os.path.join(self.tmp.name, "bin")
        os.makedirs(self.bin)
        write_exe(os.path.join(self.bin, "claude"), FAKE_CLAUDE)
        self.runs = os.path.join(self.tmp.name, "runs")
        self.env = dict(os.environ, RUNS=self.runs,
                        PATH=self.bin + os.pathsep + os.environ["PATH"])

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self):
        return subprocess.run(["bash", os.path.join(BENCH, "prepare.sh")], env=self.env,
                              capture_output=True, text=True, timeout=120)

    def git(self, *a):
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True,
                              check=True).stdout

    def test_copies_match_their_trees(self):
        p = self.prepare()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("Cannot stat", p.stderr)
        self.assertEqual(p.stderr, "")
        plugins = os.path.join(self.runs, "plugins")
        with open(os.path.join(plugins, "v0.9.id")) as fh:
            self.assertEqual(fh.read().strip(), self.git("rev-parse", "a05e49d").strip())
        with open(os.path.join(plugins, "v1.0.id")) as fh:
            tree = fh.read().strip().split(":", 1)[1]
        want = sorted(self.git("ls-tree", "-r", "--name-only", tree).split("\n")[:-1])
        have = sorted(os.path.relpath(os.path.join(d, f), os.path.join(plugins, "v1.0"))
                      for d, _, fs in os.walk(os.path.join(plugins, "v1.0")) for f in fs)
        self.assertEqual(have, want)
        for gone in self.git("ls-files", "--deleted").split("\n")[:-1]:
            self.assertNotIn(gone, have)

    def test_extract_failure_propagates(self):
        write_exe(os.path.join(self.bin, "tar"), "#!/bin/sh\necho 'tar: broken' >&2\nexit 1\n")
        p = self.prepare()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("extracting", p.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.runs, "plugins", "v0.9.id")))

    def test_refuses_existing_runs(self):
        os.makedirs(self.runs)
        p = self.prepare()
        self.assertEqual(p.returncode, 1)
        self.assertIn("exists", p.stderr)


if __name__ == "__main__":
    unittest.main()
