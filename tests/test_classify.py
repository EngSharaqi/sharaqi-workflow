"""Tests for scripts/classify.py: the prompt hook's deterministic routing. Standard library only.

What these prove: for the 11 pre-registered routing cases (benchmarks/v0.9/routing-cases.md,
text unchanged) and a set of other prompts, the classifier's facts give the expected route;
each fact says whether it was stated or assumed; only the route's own steps are injected; the
hook never blocks and says so when it fails; approval state survives to `/sharaqi go`.
What they don't prove: accuracy on prompts unlike these. The 11 cases were visible while the
rules were written, so they are not a held-out test; the OTHER prompts below were written
after, and two of them caught real misses (a deletion trigger and an email-as-noun).

usage: python3 -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import classify  # noqa: E402

CASES = os.path.join(ROOT, "benchmarks", "v1.0", "cases")


def case_text(cid):
    with open(os.path.join(CASES, cid), encoding="utf-8") as fh:
        return fh.read().strip()


def route_of(prompt):
    ctx, _ = classify.build(*classify.parse_command(prompt), take_base=False)
    line = next(ln for ln in ctx.splitlines() if ln.startswith("ROUTE "))
    return dict(kv.split("=", 1) for kv in line.split()[1:]), ctx


# Expected v1.0 route per case: benchmarks/v1.0/expected.json (the scorer reads it too).
with open(os.path.join(ROOT, "benchmarks", "v1.0", "expected.json"), encoding="utf-8") as _fh:
    _EXP = json.load(_fh)
EXPECTED = _EXP["v1.0"]
ENTRY = _EXP["entry"]

# Written after the rules; (prompt, expected fields).
OTHER = [
    ("Drop the legacy_orders table and its model", dict(tier="critical", escalate="critical")),
    ("Remove all records older than 2020 from the audit log", dict(tier="critical")),
    ("Show the user's display name in the header instead of the email",
     dict(track="coding", tier="planned")),
    ("Fix the login bug where users get logged out randomly",
     dict(tier="critical", plan="planner·opus·high", review="reviewer·opus·high")),
    ("Bump lodash to 4.17.21", dict(tier="critical", review="reviewer·opus·medium")),
    ("Add a refund endpoint to the payments API", dict(tier="critical")),
    ("Change the submit button label to Save in src/components/Form.tsx",
     dict(tier="tiny", executor="inline")),
    ("Refactor the date parsing in src/utils/date.ts to handle timezones across 6 files",
     dict(tier="planned", executor="R4·sonnet-high")),
    ("Update docs/install.md with the new Node version", dict(track="noncoding")),
    ("Update the README section on installation", dict(track="noncoding")),
    ("Write a report on Q3 sales for the board", dict(track="noncoding", tier="direct")),
    ("Explain how the auth middleware works", dict(track="noncoding")),
    ("commit the changes", dict(track="ops", op="commit", authz="explicit-yes")),
    ("run the tests", dict(track="ops", op="test")),
    ("Add pagination to the users list", dict(tier="planned", approval="yes")),
    # A constraint, not a change (v1.0 benchmark: "no new dependencies" routed critical).
    ("Update the landing page in page.js to the new layout, no new dependencies",
     dict(tier="planned")),
    ("Add a sidebar to the docs page without adding any new packages", dict(tier="planned")),
    ("Remove the dependency on moment, no new dependencies", dict(tier="critical")),
    ("Fix the login form, no new dependencies", dict(tier="critical", escalate="critical")),
]


class Cases(unittest.TestCase):
    def test_the_11_cases_route_as_registered(self):
        for cid, want in EXPECTED.items():
            r, ctx = route_of("/sharaqi %s %s" % (ENTRY.get(cid, "route"), case_text(cid)))
            for k, v in want.items():
                self.assertEqual(r.get(k), v, "case %s field %s\n%s" % (cid, k, ctx))
            self.assertEqual(r["seat"], "sonnet")

    def test_case_texts_are_the_v09_texts(self):
        # The case files must hold the routing-cases.md table text, unchanged.
        with open(os.path.join(ROOT, "benchmarks", "v0.9", "routing-cases.md"),
                  encoding="utf-8") as fh:
            table = fh.read()
        for cid in EXPECTED:
            text = case_text(cid)
            row = "| %s | %s%s |" % (cid, "(review) " if cid in ENTRY else "", text)
            self.assertIn(row, table, cid)

    def test_other_prompts(self):
        for prompt, want in OTHER:
            r, ctx = route_of("/sharaqi route " + prompt)
            for k, v in want.items():
                self.assertEqual(r.get(k), v, "%r field %s\n%s" % (prompt, k, ctx))

    def test_a_noun_never_makes_code_noncoding(self):
        for p in ("Hide the email field on the profile page",
                  "Show the report total in src/report.ts",
                  "Make the summary card collapsible"):
            r, _ = route_of("/sharaqi route " + p)
            self.assertNotEqual(r["track"], "noncoding", p)

    def test_unknown_text_takes_the_safe_side(self):
        r, ctx = route_of("/sharaqi route frobnicate the widget")
        self.assertEqual((r["track"], r["approval"]), ("coding", "yes"))
        self.assertIn("confidence=low", ctx)


class Facts(unittest.TestCase):
    def test_every_fact_says_where_it_came_from(self):
        _, ctx = route_of("/sharaqi route " + case_text("2"))
        facts = next(ln for ln in ctx.splitlines() if ln.startswith("FACTS "))
        self.assertIn("files=4(stated: '4 files')", facts)
        self.assertIn("lines=150(stated: '~150 lines')", facts)
        self.assertIn("uncertain=no(assumed)", facts)
        self.assertIn("shape=feature(assumed)", facts)

    def test_writing_clause_doesnt_set_code_facts(self):
        _, ctx = route_of("/sharaqi route " + case_text("10"))
        self.assertNotIn("two-line", ctx.split("FACTS")[1].split("·")[0])


class Command(unittest.TestCase):
    def test_parse(self):
        p = classify.parse_command
        self.assertIsNone(p("hello /sharaqi do x"))
        self.assertIsNone(p("/sharaqix do x"))
        self.assertEqual(p("/sharaqi"), ("do", "", False))
        self.assertEqual(p("  /sharaqi:sharaqi review HEAD"), ("review", "HEAD", False))
        self.assertEqual(p("/sharaqi --debug do fix it"), ("do", "fix it", True))
        self.assertEqual(p("/sharaqi do --debug fix it"), ("do", "fix it", True))
        self.assertEqual(p("/sharaqi fix the bug"), ("do", "fix the bug", False))
        self.assertEqual(p("/sharaqi go looks good"), ("go", "looks good", False))
        self.assertEqual(p("/sharaqi\nroute x"), ("route", "x", False))


class Injection(unittest.TestCase):
    def test_only_this_routes_steps(self):
        _, ctx = route_of("/sharaqi do " + case_text("1"))
        self.assertIn("## Route: tiny", ctx)
        for other in ("## Route: planned", "## Route: critical", "## Delegation rules",
                      "## Debug mode"):
            self.assertNotIn(other, ctx)
        _, ctx = route_of("/sharaqi do " + case_text("4"))
        self.assertIn("## Route: critical", ctx)
        self.assertIn("## Delegation rules", ctx, "an Opus reviewer is a delegation")
        self.assertIn(os.path.join(ROOT, "references", "security-checklist.md"), ctx)
        self.assertNotIn("${SKILL}", ctx)

    def test_debug_is_opt_in(self):
        _, ctx = route_of("/sharaqi do " + case_text("2"))
        self.assertNotIn("▶", ctx)
        _, ctx = route_of("/sharaqi --debug do " + case_text("2"))
        self.assertIn("## Debug mode", ctx)

    def test_injection_stays_small(self):
        # The per-route context replaces v0.9's 18.5 KB SKILL.md; keep it bounded.
        for cid in EXPECTED:
            for entry in ("route", "do"):
                e = ENTRY.get(cid, entry)
                _, ctx = route_of("/sharaqi %s %s" % (e, case_text(cid)))
                limit = 1200 if e == "route" else 4000
                self.assertLess(len(ctx.encode("utf-8")), limit, (cid, e))


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.tmp.name})
        self.env.start()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        g = lambda *a: subprocess.run(["git", *a], cwd=self.repo, capture_output=True)
        g("init", "-q")
        with open(os.path.join(self.repo, "a.txt"), "w") as fh:
            fh.write("x\n")
        g("add", "a.txt")
        g("-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "c")
        self.set_bridge(True)

    def set_bridge(self, on):
        path = os.path.join(self.tmp.name, "settings.json")
        cmd = 'bash "/p/hooks/statusline-bridge.sh"' if on else "my-statusline"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"statusLine": {"type": "command", "command": cmd}}, fh)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def hook(self, prompt, sid="s1", cwd=None):
        return classify.hook_main(json.dumps({"session_id": sid, "prompt": prompt,
                                              "cwd": cwd or self.repo}))

    def ctx(self, out):
        return out["hookSpecificOutput"]["additionalContext"]

    def events(self, sid="s1"):
        path = os.path.join(self.tmp.name, "sharaqi-state", sid + ".events.jsonl")
        with open(path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh]

    def test_other_prompts_untouched(self):
        self.assertIsNone(self.hook("hello"))
        self.assertIsNone(classify.hook_main("not json"))
        self.assertIsNone(classify.hook_main("[1]"))

    def test_planned_route_takes_base_and_waits_for_go(self):
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo,
                                capture_output=True, text=True).stdout
        c = self.ctx(self.hook("/sharaqi do " + case_text("2")))
        base = [ln for ln in c.splitlines() if ln.startswith("BASE ")]
        self.assertEqual(len(base), 1)
        self.assertRegex(base[0], r"^BASE [0-9a-f]{40}$")
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=self.repo,
                                        capture_output=True, text=True).stdout, status,
                         "the snapshot never touches the index or the files")
        go = self.ctx(self.hook("/sharaqi go ship it"))
        self.assertIn("the user approved the plan", go)
        self.assertIn(base[0], go)
        self.assertIn("ROUTE track=coding tier=planned", go)
        self.assertIn("ship it", go)
        again = self.ctx(self.hook("/sharaqi go"))
        self.assertIn("no plan is waiting", again, "one approval per plan")
        kinds = [e["event"] for e in self.events()]
        self.assertEqual(kinds, ["route", "approve", "approve"])
        self.assertTrue(self.events()[0]["route"].startswith("ROUTE "))

    def test_plain_reply_while_waiting_warns_once(self):
        self.hook("/sharaqi do " + case_text("2"))
        out = self.hook("yes")
        self.assertIn("systemMessage", out)
        self.assertNotIn("hookSpecificOutput", out, "the model isn't told anything")
        self.assertIsNone(self.hook("yes again"))
        self.assertIsNone(self.hook("/compact"))

    def test_tiny_route_has_no_base_and_nothing_pending(self):
        self.hook("/sharaqi do " + case_text("1"))
        self.assertIsNone(self.hook("ok"))
        self.assertIn("no plan is waiting", self.ctx(self.hook("/sharaqi go")))

    def test_base_unavailable_outside_git(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)
        c = self.ctx(self.hook("/sharaqi do " + case_text("2"), cwd=plain))
        self.assertIn("BASE unavailable", c)
        self.assertIn("not isolated", c)

    def test_failure_is_reported_not_hidden(self):
        with mock.patch.object(classify, "build", side_effect=RuntimeError("boom")):
            c = self.ctx(self.hook("/sharaqi do anything"))
        self.assertIn("ROUTE UNAVAILABLE", c)
        self.assertIn("model-judged (hook failed)", c)
        self.assertEqual(self.events()[-1], dict(self.events()[-1], event="route-error",
                                                 error="RuntimeError"))

    def test_bad_session_id_writes_no_state(self):
        self.hook("/sharaqi do " + case_text("2"), sid="../evil")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "evil.events.jsonl")))
        state = os.path.join(self.tmp.name, "sharaqi-state")
        self.assertFalse(os.path.isdir(state) and os.listdir(state))

    def test_go_after_session_end_finds_the_plan(self):
        # claude -p / --resume: the same session id in a new process; SessionEnd keeps .pending.
        self.hook("/sharaqi do " + case_text("2"))
        self.assertIn("the user approved the plan", self.ctx(self.hook("/sharaqi go")))

    def test_go_ignores_an_expired_plan(self):
        self.hook("/sharaqi do " + case_text("2"))
        pending = os.path.join(self.tmp.name, "sharaqi-state", "s1.pending")
        old = time.time() - classify.PENDING_TTL_S - 60
        os.utime(pending, (old, old))
        self.assertIn("no plan is waiting", self.ctx(self.hook("/sharaqi go")))

    def test_gate_preflight_stops_before_any_work(self):
        self.set_bridge(False)
        out = self.hook("/sharaqi do " + case_text("2"))
        self.assertTrue(self.ctx(out).startswith("CONTEXT GATE UNVERIFIABLE"))
        self.assertIn("/sharaqi setup", out["systemMessage"])
        self.assertIn("ROUTE ", self.ctx(out), "the route is still there for the record")
        self.assertIn("CONTEXT GATE", self.ctx(self.hook("/sharaqi go")))
        self.assertNotIn("systemMessage", self.hook("/sharaqi route " + case_text("2")))
        self.assertNotIn("systemMessage", self.hook("/sharaqi do commit the changes"))

    def test_gate_preflight_passes_with_a_bridge_file_or_benchmark_window(self):
        self.set_bridge(False)
        state = os.path.join(self.tmp.name, "sharaqi-state")
        os.makedirs(state, exist_ok=True)
        open(os.path.join(state, "s1.ctx"), "w").close()
        self.assertNotIn("systemMessage", self.hook("/sharaqi do " + case_text("2")))
        with mock.patch.dict(os.environ, {"SHARAQI_BENCHMARK": "1",
                                          "SHARAQI_CONTEXT_WINDOW": "1000000"}):
            self.assertNotIn("systemMessage", self.hook("/sharaqi do " + case_text("2"), sid="s2"))

    def test_no_case_task_asks(self):
        c = self.ctx(self.hook("/sharaqi do"))
        self.assertIn("ask the user what to do", c)


if __name__ == "__main__":
    unittest.main()
