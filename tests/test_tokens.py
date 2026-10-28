"""Tests for scripts/tokens.py: a small synthetic transcript, and the usage lines of a real
benchmark session (content stripped) checked against the cost Claude Code reported for it.
Standard library only.

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
BENCH_DIR = os.path.join(ROOT, "tests", "fixtures", "bench-2026-10-22")
BENCH_SID = "00000000-0000-4000-8000-000000000001"  # ids replaced with placeholders
# total_cost_usd from `claude -p --output-format json` for that session (CLI 2.1.274).
BENCH_CLI_USD = 1.4918871


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
            # An Opus version the table doesn't know: unpriced, not priced as another Opus.
            assistant("2026-01-01T10:00:05Z", "r3", "claude-opus-5-7",
                      input_tokens=7, output_tokens=7),
            # Date-suffixed id matches its base id.
            assistant("2026-01-01T10:00:06Z", "r4", "claude-haiku-4-5-20251001",
                      input_tokens=1000, output_tokens=100),
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

    def run_script(self, *extra, session=SID, config=None, since="2026-01-01T10:00:00Z"):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config or self.tmp.name)
        return subprocess.run(
            [sys.executable, "-I", SCRIPT, "--session", session, "--since", since, *extra],
            capture_output=True, text=True, encoding="utf-8", env=env)

    def test_totals(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        # opus-5-5: 10 + 1000 + 2000 + 500; haiku-5-5: 5 + 200000 + 100; haiku-4-5: 1000 + 100
        self.assertIn("TOTAL_TOKENS: 204,715 (output 700)", r.stdout)
        self.assertIn("REQUESTS: 3 (subagent 1)", r.stdout)
        # opus-5-5 (10*4 + 1000*5 + 2000*0.2 + 500*20) = 15440
        # haiku-5-5 long context (5*0.5 + 200000*0.05 + 100*2.5) = 10252.5
        # haiku-4-5 (1000*1 + 100*5) = 1500                        -> 27192.5 / 1e6
        self.assertIn("LIST_PRICE_USD: 0.0272", r.stdout)
        self.assertIn("UNPRICED_REQUESTS: 2", r.stdout)
        self.assertIn("| sharaqi:reviewer | claude-haiku-5-5 | 1 |", r.stdout)
        self.assertIn("| main | claude-haiku-4-5 | 1 |", r.stdout)
        self.assertIn("PRICES_CHECKED:", r.stdout)
        # Sorted by cost: opus $0.0154, then haiku-5-5 $0.0103, then haiku-4-5 $0.0015.
        self.assertIn("By model (tokens · requests · $): claude-opus-5-5 ", r.stdout)
        self.assertIn(" · 1 · `$0.02` estimate (price unverified for claude-opus-5-5) | claude-haiku-5-5 ", r.stdout)

    def test_unverified_prices_are_marked(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        row = lambda model: next(l for l in lines if l.startswith("| ") and "| %s |" % model in l)
        # claude-opus-5-5 and claude-haiku-5-5 come from docs only; claude-haiku-4-5 is verified.
        self.assertIn("estimate (price unverified for claude-opus-5-5)", row("claude-opus-5-5"))
        self.assertIn("estimate (price unverified for claude-haiku-5-5)", row("claude-haiku-5-5"))
        self.assertNotIn("estimate", row("claude-haiku-4-5"))
        summary = next(l for l in lines if l.startswith("Tokens:"))
        self.assertIn("estimate (price unverified for claude-opus-5-5)", summary)
        self.assertIn("estimate (price unverified for claude-haiku-5-5)", summary)
        total = next(l for l in lines if l.startswith("LIST_PRICE_USD:"))
        self.assertIn("estimate (price unverified for claude-opus-5-5)", total)
        by_model = next(l for l in lines if l.startswith("By model"))
        self.assertIn("estimate (price unverified for claude-opus-5-5) | ", by_model)
        self.assertTrue(by_model.endswith("claude-haiku-4-5 `1K` · 1 · `$0.00`"), by_model)
        # Unrecognised models are still counted, not priced.
        self.assertIn("UNPRICED_REQUESTS: 2", r.stdout)

    def test_stale_table_warns(self):
        r = self.run_script()
        self.assertRegex(r.stdout, r"PRICES_CHECKED: \d{4}-\d{2}-\d{2} \(\d+ days ago(; STALE)?\)")
        with open(os.path.join(ROOT, "scripts", "prices.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["stale_after_days"], 90)

    def test_benchmark_session_matches_claude_code(self):
        r = self.run_script(session=BENCH_SID, config=BENCH_DIR, since="2026-10-22T00:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        usd = float(r.stdout.split("LIST_PRICE_USD: ")[1].split()[0])
        self.assertLess(abs(usd - BENCH_CLI_USD) / BENCH_CLI_USD, 0.03, r.stdout)
        self.assertNotIn("UNPRICED_REQUESTS", r.stdout)
        # Both models in that session have verified rows.
        self.assertNotIn("estimate (price unverified", r.stdout)
        self.assertIn("| sharaqi:reviewer | claude-opus-5 |", r.stdout)
        self.assertIn("| sharaqi:implementer | claude-sonnet-5 |", r.stdout)

    def test_price_table_is_complete(self):
        with open(os.path.join(ROOT, "scripts", "prices.json"), encoding="utf-8") as fh:
            p = json.load(fh)
        keys = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")
        for model, rates in p["models"].items():
            for k in keys:
                self.assertIsInstance(rates[k], (int, float), model + " " + k)
            self.assertTrue(rates.get("source"), model)
            self.assertIsInstance(rates.get("verified"), bool, model)
            if not rates["verified"]:
                self.assertIn("Not checked against Claude Code", rates["source"], model)
        self.assertIn("fable", p["ceiling"]["blocked_models"])

    def test_arabic_summary(self):
        r = self.run_script("--lang", "ar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("التوكنز:", r.stdout)

    def test_missing_transcript(self):
        r = self.run_script(session="no-such-session")
        self.assertEqual(r.returncode, 1)
        self.assertIn("TOKENS: unavailable", r.stdout)


def tool_use(ts, req, msg_id, name, msg_model="claude-opus-5", effort="medium", usage=None, **inp):
    row = {"type": "assistant", "timestamp": ts, "requestId": req, "cwd": "/w/repo",
           "message": {"id": msg_id, "model": msg_model,
                       "content": [{"type": "tool_use", "name": name, "input": inp}]}}
    if effort:
        row["effort"] = effort
    if usage:
        row["message"]["usage"] = usage
    return row


class PhasesTest(unittest.TestCase):
    """--phases on a synthetic delegated session: cost per phase, recorded effort, parallel
    spawns, and both kinds of double read."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        proj = os.path.join(self.tmp.name, "projects", "-w-repo")
        os.makedirs(os.path.join(proj, SID, "subagents"))
        u = lambda out: {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": out}
        write_jsonl(os.path.join(proj, SID + ".jsonl"), [
            # The orchestrator reads a.js twice (same range) and b.js once ...
            tool_use("2026-01-01T10:00:01Z", "m1", "msg1", "Read", file_path="/w/repo/src/a.js"),
            tool_use("2026-01-01T10:00:01Z", "m1", "msg1", "Read", usage=u(100), file_path="/w/repo/src/b.js"),
            tool_use("2026-01-01T10:00:02Z", "m2", "msg2", "Read", usage=u(50), file_path="/w/repo/src/a.js"),
            # ... then spawns two agents in one message, and one more later.
            tool_use("2026-01-01T10:00:03Z", "m3", "msg3", "Agent", subagent_type="sharaqi:implementer-low", model="haiku"),
            tool_use("2026-01-01T10:00:03Z", "m3", "msg3", "Agent", usage=u(400), subagent_type="sharaqi:implementer-high", model="sonnet"),
            # The orchestrator's own fix to b.js is a delta, not a write conflict.
            tool_use("2026-01-01T10:00:09Z", "m4", "msg4", "Edit", file_path="/w/repo/src/b.js"),
            tool_use("2026-01-01T10:00:09Z", "m4", "msg4", "Agent", usage=u(200), subagent_type="sharaqi:reviewer", model="sonnet"),
        ])
        # Both implementers edit a.js: the one write conflict.
        subs = [
            ("agent-z", "sharaqi:implementer-low", "claude-haiku-4-5", None, "10:00:04", "/w/repo/src/a.js",
             ["/w/repo/src/a.js"]),
            ("agent-y", "sharaqi:implementer-high", "claude-sonnet-5", "high", "10:00:05", "/w/repo/src/c.js",
             ["/w/repo/src/c.js", "/w/repo/src/a.js"]),
            ("agent-x", "sharaqi:reviewer", "claude-sonnet-5", "medium", "10:00:10", "/w/repo/src/c.js", []),
        ]
        for name, kind, model, effort, t, path, edits in subs:
            base = os.path.join(proj, SID, "subagents", name)
            write_jsonl(base + ".jsonl", [
                tool_use("2026-01-01T%sZ" % t, name + "1", name + "m1", "Edit", msg_model=model,
                         effort=effort, file_path=p) for p in edits] + [
                tool_use("2026-01-01T%sZ" % t, name + "1", name + "m1", "Read", msg_model=model,
                         effort=effort, usage=u(30), file_path=path),
            ])
            with open(base + ".meta.json", "w", encoding="utf-8") as fh:
                json.dump({"agentType": kind}, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def run_phases(self, *extra):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.tmp.name)
        return subprocess.run(
            [sys.executable, "-I", SCRIPT, "--session", SID, "--since", "2026-01-01T10:00:00Z", *extra],
            capture_output=True, text=True, encoding="utf-8", env=env)

    def test_phases(self):
        r = self.run_phases("--phases")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        # Phases in start order (not file-name order), with the effort each one recorded.
        lines = [l for l in out.splitlines() if l.startswith("| ") and "#" in l or l.startswith("| orchestrator")]
        self.assertEqual([l.split(" | ")[0] for l in lines],
                         ["| orchestrator", "| implementer #1", "| implementer #2", "| reviewer #1"])
        self.assertIn("| orchestrator | main | claude-opus-5 | medium | 4 | 750 |", out)
        self.assertIn("| implementer #1 | sharaqi:implementer-low | claude-haiku-4-5 | none | 1 | 30 |", out)
        self.assertIn("| implementer #2 | sharaqi:implementer-high | claude-sonnet-5 | high | 1 | 30 |", out)
        self.assertIn("| reviewer #1 | sharaqi:reviewer | claude-sonnet-5 | medium | 1 | 30 |", out)
        self.assertIn("ORCHESTRATOR: 4 requests · output 750 · ", out)
        self.assertIn("SPAWNS: 3 agent calls · 2 in parallel (largest batch in one message: 2)", out)
        # a.js: read by the orchestrator, then by the haiku implementer (handoff), and twice by the
        # orchestrator (re-read). c.js is read by two subagents but never by the orchestrator.
        self.assertIn("DOUBLE_READS: handoff 1 (src/a.js) · re-read in one thread 1 (src/a.js (orchestrator ×2))", out)
        self.assertIn("WRITE_CONFLICTS: 1 (src/a.js)\n", out)

    def test_phases_off_by_default(self):
        r = self.run_phases()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("PHASES:", r.stdout)
        self.assertNotIn("COST_SPLIT", r.stdout)

    def test_phase_rows_stay_parseable(self):
        # benchmarks/v0.8/summarize.py takes every "| " row after PHASES: as a phase row.
        out = self.run_phases("--phases").stdout
        rows = [l for l in out.split("PHASES:")[1].splitlines()
                if l.startswith("| ") and not l.startswith("| Phase")]
        self.assertEqual(len(rows), 4, out)


def result(ts, tool_use_id, content):
    return {"type": "user", "timestamp": ts,
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}]}}


def call(ts, req, msg_model, name, uid, usage, **inp):
    return {"type": "assistant", "timestamp": ts, "requestId": req, "cwd": "/w/repo",
            "message": {"id": "msg_" + req, "model": msg_model, "usage": usage,
                        "content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}


class CompositionTest(unittest.TestCase):
    """The --phases composition lines: cost by token category, cache TTL, tool results,
    subagent prompts and cache rebuilds, on a synthetic session with known numbers."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = os.path.join(self.tmp.name, "projects", "-w-repo")
        os.makedirs(self.proj)

    def tearDown(self):
        self.tmp.cleanup()

    def run_rows(self, rows, sid=SID):
        write_jsonl(os.path.join(self.proj, sid + ".jsonl"), rows)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.tmp.name)
        r = subprocess.run(
            [sys.executable, "-I", SCRIPT, "--session", sid, "--since", "2026-01-01T10:00:00Z",
             "--phases"], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def session(self):
        h1 = lambda w, rd, out: {"input_tokens": 0, "cache_creation_input_tokens": w,
                                 "cache_read_input_tokens": rd, "output_tokens": out,
                                 "cache_creation": {"ephemeral_1h_input_tokens": w,
                                                    "ephemeral_5m_input_tokens": 0}}
        return [
            # 1: first request, 1h write (claude-opus-5: 1h write $10/M, read $0.5/M, out $25/M).
            call("2026-01-01T10:00:01Z", "r1", "claude-opus-5", "Bash", "t1", h1(10000, 0, 100),
                 command="curl -H 'Authorization: Bearer sk-SECRET' https://x"),
            result("2026-01-01T10:00:02Z", "t1", "x" * 1200),
            # 2: normal growth, reads the whole previous prompt.
            call("2026-01-01T10:00:03Z", "r2", "claude-opus-5", "Read", "t2", h1(500, 10000, 100),
                 file_path="/w/repo/src/a.js"),
            result("2026-01-01T10:00:04Z", "t2", [{"type": "text", "text": "y" * 300},
                                                  {"type": "image", "source": {}}]),
            # 3: spawns a reviewer with a 2,000-char prompt; writes with no TTL breakdown.
            call("2026-01-01T10:00:05Z", "r3", "claude-opus-5", "Agent", "t3",
                 {"input_tokens": 0, "cache_creation_input_tokens": 400,
                  "cache_read_input_tokens": 10500, "output_tokens": 600},
                 subagent_type="sharaqi:reviewer", model="opus", prompt="d" * 2000),
            result("2026-01-01T10:00:06Z", "t3", "PASS"),
            # 4: a compaction, then a request that rewrites the prefix.
            {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-01-01T10:01:00Z",
             "compactMetadata": {"trigger": "manual", "preTokens": 10900, "postTokens": 3000}},
            call("2026-01-01T10:01:30Z", "r4", "claude-opus-5", "SendMessage", "t4",
                 h1(3000, 0, 50), to="agent-1", message="m" * 150),
            # 5: same model, no compaction, cache not read: unexplained (e.g. TTL expiry).
            call("2026-01-01T11:30:00Z", "r5", "claude-opus-5", "Grep", "t5", h1(3000, 0, 50),
                 pattern="x"),
            # 6: model change.
            call("2026-01-01T11:30:10Z", "r6", "claude-sonnet-5", "Grep", "t6", h1(3000, 0, 50),
                 pattern="y"),
        ]

    def test_cost_split_and_ttl(self):
        out = self.run_rows(self.session())
        # Tokens per category as recorded; r3's write has no TTL breakdown, so it is shown
        # apart, not as 5m and not as zero.
        self.assertIn("  orchestrator: input 0 (0%) · write 5m 0 (0%) · write 1h 19,500 ", out)
        self.assertIn("write TTL? 400 ", out)
        self.assertIn("read 20,500 ", out)
        self.assertIn("CACHE_TTL: tokens written 1h 19,500 · 5m 0 · TTL not recorded 400 "
                      "(1 requests, priced as 5m)", out)
        # Shares are of the phase's computed list price and add up to the total.
        line = next(l for l in out.splitlines() if l.startswith("  orchestrator:"))
        shares = [int(p.split("(")[1].split("%")[0]) for p in line.split(" · ")]
        self.assertTrue(98 <= sum(shares) <= 102, line)
        usd = float(out.split("LIST_PRICE_USD: ")[1].split()[0])
        # opus-5: 16,500 1h writes, 400 unrecorded (5m rate), 20,500 reads, 900 output;
        # sonnet-5: 3,000 1h writes, 50 output.
        want = (16500 * 10 + 400 * 6.25 + 20500 * 0.5 + 900 * 25 + 3000 * 4 + 50 * 10) / 1e6
        self.assertAlmostEqual(usd, want, places=3)

    def test_tool_outputs_and_prompts(self):
        out = self.run_rows(self.session())
        self.assertIn("TOOL_OUTPUTS (orchestrator, characters not tokens): 3 results · 1,504 chars"
                      " · Bash 1/1,200 · Read 1/300 · Agent 1/4 · 1 with an image (not counted)", out)
        self.assertIn("  largest: Bash curl 1,200 · Read src/a.js 300 · Agent sharaqi:reviewer 4", out)
        # Command arguments are never printed: they can hold secrets.
        self.assertNotIn("SECRET", out)
        self.assertNotIn("Bearer", out)
        self.assertIn("AGENT_PROMPTS (written by the orchestrator, part of its output; characters):"
                      " sharaqi:reviewer 2,000 · SendMessage 150 | total 2,150", out)

    def test_cache_rebuilds(self):
        out = self.run_rows(self.session())
        self.assertIn("CACHE_REBUILDS (orchestrator; read < half of the previous prompt): "
                      "3 of 5 requests after the first · compactions recorded 1", out)
        self.assertIn("2026-01-01T10:01:30Z +85s, after compaction, rewrote 3,000", out)
        self.assertIn("2026-01-01T11:30:00Z +5310s, no compaction or model change recorded, "
                      "rewrote 3,000", out)
        self.assertIn("model changed (claude-opus-5 → claude-sonnet-5)", out)
        # r2 and r3 read the previous prompt: not rebuilds.
        self.assertNotIn("10:00:03Z +", out)
        self.assertNotIn("10:00:05Z +", out)

    def test_missing_data_is_not_zero(self):
        # Usage only, no content: the stripped benchmark fixture's shape.
        out = self.run_rows([assistant("2026-01-01T10:00:01Z", "r1", "claude-opus-5",
                                       input_tokens=5, output_tokens=7,
                                       cache_creation_input_tokens=100)])
        self.assertIn("TOOL_OUTPUTS (orchestrator, characters not tokens): not recorded", out)
        self.assertIn("AGENT_PROMPTS (written by the orchestrator, part of its output; "
                      "characters): none sent", out)
        self.assertIn("TTL not recorded 100 (1 requests, priced as 5m)", out)
        self.assertIn("0 of 0 requests after the first", out)

    def test_env_prefix_and_bad_lines_are_safe(self):
        u = {"input_tokens": 0, "cache_creation_input_tokens": 100,
             "cache_read_input_tokens": 0, "output_tokens": 5}
        out = self.run_rows([
            call("2026-01-01T10:00:01Z", "r1", "claude-opus-5", "Bash", "t1", u,
                 command="GH_TOKEN=ghp_SECRET API_KEY='k' /usr/bin/gh pr list"),
            result("2026-01-01T10:00:02Z", "t1", "ok"),
            # A malformed timestamp on a user line and a non-object line are skipped.
            {"type": "user", "timestamp": "not-a-date", "message": {"content": []}},
            "[1, 2]",
        ])
        self.assertIn("largest: Bash gh 2", out)
        self.assertNotIn("SECRET", out)
        self.assertNotIn("GH_TOKEN", out)
        self.assertNotIn("API_KEY", out)

    def test_unpriced_model_has_no_share(self):
        out = self.run_rows([assistant("2026-01-01T10:00:01Z", "r1", "claude-new-9",
                                       input_tokens=5, output_tokens=7)])
        self.assertIn("output 7 ($ n/a: model unpriced)", out)

    def test_benchmark_fixture_prompts_not_recorded(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=BENCH_DIR)
        r = subprocess.run([sys.executable, "-I", SCRIPT, "--session", BENCH_SID, "--since",
                            "2026-10-22T00:00:00Z", "--phases"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        # Subagent threads exist but the prompts were stripped: say so, don't print zero.
        self.assertIn("characters): not recorded (no prompt text in the transcript)", r.stdout)
        self.assertIn("  subagents: not recorded", r.stdout)
        self.assertIn("CACHE_TTL: tokens written 1h 60,445 · 5m 29,850 · TTL not recorded 0", r.stdout)


class BreakevenTest(unittest.TestCase):
    """scripts/breakeven.py on the recorded benchmark session: inputs are measured, not typed in."""

    def run_be(self, *extra):
        return subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts", "breakeven.py"), *extra],
                              capture_output=True, text=True, encoding="utf-8")

    def nstar(self, out, model):
        row = next(l for l in out.splitlines() if l.startswith("| %s |" % model))
        return float(row.split(" | ")[3])

    def test_measured_inputs_and_order(self):
        r = self.run_be()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(15 requests)", r.stdout)
        self.assertIn("implementer first prompt 12829", r.stdout)
        haiku, sonnet, opus = (self.nstar(r.stdout, m) for m in
                               ("claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"))
        # The numbers docs/architecture.md and references/delegation.md quote.
        self.assertEqual((round(haiku, 1), round(sonnet, 1), round(opus, 1)), (2.7, 3.5, 7.3))
        self.assertLess(haiku, sonnet)
        self.assertLess(sonnet, opus)

    def test_other_orchestrator_price(self):
        r = self.run_be("--orchestrator", "claude-opus-5-5")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(round(self.nstar(r.stdout, "claude-sonnet-5"), 1), 5.1)

    def test_unknown_session(self):
        r = self.run_be("--session", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("BREAKEVEN: unavailable", r.stdout)


class ContextTest(unittest.TestCase):
    """--context: the CONTEXT line and exit code (OK 0, WARN 3, STOP 4, unverified 5). The
    window comes only from the session's statusline bridge file, never from the model name."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = self.tmp.name
        self.proj = os.path.join(self.cfg, "projects", "-repo")
        os.makedirs(self.proj)
        os.makedirs(os.path.join(self.cfg, "sharaqi-state"))

    def tearDown(self):
        self.tmp.cleanup()

    def transcript(self, *rows, sid=SID, folder=None):
        path = os.path.join(folder or self.proj, sid + ".jsonl")
        write_jsonl(path, list(rows))
        return path

    def bridge(self, window=200000, model="claude-opus-5-5", raw=None, sid=SID):
        body = raw if raw is not None else json.dumps({
            "window": window, "used_percentage": None, "total_input_tokens": None,
            "model": model, "ts": 0})
        with open(os.path.join(self.cfg, "sharaqi-state", sid + ".ctx"), "w", encoding="utf-8") as fh:
            fh.write(body)

    def run_ctx(self, *extra):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.cfg)
        return subprocess.run([sys.executable, "-I", SCRIPT, "--context", *extra],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_boundaries(self):
        self.bridge()
        cases = [(69800, "34.9", 0, "OK"), (70000, "35.0", 3, "WARN"),
                 (79800, "39.9", 3, "WARN"), (80000, "40.0", 4, "STOP")]
        for tokens, pct, code, status in cases:
            self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5",
                                      input_tokens=tokens))
            r = self.run_ctx("--session", SID)
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
            self.assertEqual(r.stdout.strip(), "CONTEXT %s%% · %d/200000 tokens · window verified "
                             "(statusline, claude-opus-5-5) · %s" % (pct, tokens, status))

    def test_cache_tokens_count(self):
        self.bridge()
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5",
                                  input_tokens=10, cache_creation_input_tokens=1000,
                                  cache_read_input_tokens=2000, output_tokens=500))
        r = self.run_ctx("--session", SID)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(" · 3010/200000 tokens · ", r.stdout)

    def test_last_main_entry_wins_and_sidechain_ignored(self):
        self.bridge()
        side = assistant("2026-01-01T10:00:02Z", "r3", "claude-opus-5-5", input_tokens=999999)
        side["isSidechain"] = True
        self.transcript(
            assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=5000),
            assistant("2026-01-01T10:00:01Z", "r2", "claude-opus-5-5", input_tokens=300),
            side)
        r = self.run_ctx("--session", SID)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(" · 300/200000 tokens · ", r.stdout)

    def test_suffix_matches_and_window_is_the_bridges(self):
        self.bridge(window=1000000, model="claude-opus-5-5")
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5[1m]",
                                  input_tokens=100000))
        r = self.run_ctx("--session", SID)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("100000/1000000 tokens · window verified (statusline, claude-opus-5-5[1m]) · OK",
                      r.stdout)

    def test_session_defaults_from_transcript_stem(self):
        other = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(other)
        self.bridge()
        path = self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5",
                                         input_tokens=1000), folder=other)
        r = self.run_ctx("--transcript", path)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("window verified", r.stdout)

    def assertUnverified(self, r, reason):
        self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
        line = r.stdout.strip()
        self.assertTrue(line.startswith("CONTEXT UNVERIFIED · "), line)
        self.assertIn("if the window were 200000 (estimate) · " + reason, line)

    def test_missing_bridge(self):
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=1000))
        r = self.run_ctx("--session", SID)
        self.assertUnverified(r, "no statusline bridge file")
        self.assertIn("1000 tokens · ~0.5%", r.stdout)

    def test_window_never_inferred_from_model(self):
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5[1m]",
                                  input_tokens=1000))
        r = self.run_ctx("--session", SID)
        self.assertUnverified(r, "no statusline bridge file")

    def test_model_mismatch(self):
        self.bridge(model="claude-sonnet-5")
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=1000))
        self.assertUnverified(self.run_ctx("--session", SID), "model mismatch")

    def test_bad_bridge_json(self):
        self.bridge(raw="{\"window\": 200000,")
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=1000))
        self.assertUnverified(self.run_ctx("--session", SID), "bridge file unreadable or not JSON")

    def test_bridge_window_must_be_positive_int(self):
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=1000))
        for window in ("200000", 0, -5, True):
            self.bridge(window=window)
            self.assertUnverified(self.run_ctx("--session", SID), "bridge file has no positive window size")

    def test_empty_transcript(self):
        self.bridge()
        self.transcript()
        self.assertUnverified(self.run_ctx("--session", SID), "no usage entry in transcript")

    def test_only_sidechain_usage(self):
        self.bridge()
        side = assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens=1000)
        side["isSidechain"] = True
        self.transcript(side)
        self.assertUnverified(self.run_ctx("--session", SID), "no usage entry in transcript")

    def test_unreadable_transcript(self):
        r = self.run_ctx("--transcript", os.path.join(self.tmp.name, "missing.jsonl"))
        self.assertUnverified(r, "transcript not found")

    def test_bad_session_id(self):
        r = self.run_ctx("--session", "../" + SID)
        self.assertUnverified(r, "session id has characters outside")

    def test_usage_field_not_a_count(self):
        self.bridge()
        self.transcript(assistant("2026-01-01T10:00:00Z", "r1", "claude-opus-5-5", input_tokens="many"))
        self.assertUnverified(self.run_ctx("--session", SID), "transcript unreadable")

    def test_context_needs_a_session(self):
        r = self.run_ctx()
        self.assertEqual(r.returncode, 2)

    def test_context_block_in_prices(self):
        with open(os.path.join(ROOT, "scripts", "prices.json"), encoding="utf-8") as fh:
            c = json.load(fh)["context"]
        self.assertEqual((c["max_pct"], c["warn_pct"], c["fallback_window"]), (40, 35, 200000))


if __name__ == "__main__":
    unittest.main()
