"""Tests for scripts/route.py (the routing policy) and for the docs that must agree with it.
Standard library only.

What these prove: given the facts, route.py returns the route the policy defines, and the
skill's text calls it and doesn't contradict it. What they don't prove: that the model
judges the facts correctly or obeys the route at runtime. That takes live runs
(benchmarks/v0.9/routing-cases.md). The context gate itself is tested in test_hooks.sh.

usage: python3 -m unittest discover -s tests
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "route.py")


def route(*args, cwd=None):
    """Run route.py; return (exit code, {key: value} of the ROUTE line, stdout + stderr)."""
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True,
                       cwd=cwd)
    fields = {}
    for line in p.stdout.splitlines():
        if line.startswith("ROUTE "):
            fields = dict(kv.split("=", 1) for kv in line.split()[1:])
    return p.returncode, fields, p.stdout + p.stderr


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


TINY_CSS = ("--track", "coding", "--critical", "none", "--behaviour", "no", "--files", "1",
            "--lines", "1", "--shape", "trivial")
FEATURE = ("--track", "coding", "--critical", "none", "--behaviour", "yes", "--files", "4",
           "--lines", "120", "--checks", "yes", "--shape", "feature")
OPS_ALL = ("install", "test", "deperr", "git-read", "commit", "push", "ado-read", "ado-write",
           "web", "research", "conflict")


def ops(op, *args):
    return route("--track", "ops", "--op", op, *args)[1]


class Policy(unittest.TestCase):
    """Runtime tests of route.py's decisions."""

    def test_1_tiny_css_skips_plan_and_review(self):
        rc, r, _ = route(*TINY_CSS)
        self.assertEqual(rc, 0)
        self.assertEqual((r["tier"], r["plan"], r["approval"], r["review"], r["executor"]),
                         ("tiny", "none", "no", "none", "inline"))
        self.assertEqual(r["checks"], "diff+narrowest")

    def test_1b_tiny_needs_every_condition(self):
        for override in (("--behaviour", "yes"), ("--files", "2"), ("--lines", "30"),
                         ("--shape", "feature"), ("--uncertain", "yes"),
                         ("--critical", "auth"), ("--floor", "STANDARD")):
            args = list(TINY_CSS)
            i = args.index(override[0]) if override[0] in args else None
            if i is None:
                args += override
            else:
                args[i + 1] = override[1]
            rc, r, out = route(*args)
            self.assertEqual(rc, 0, out)
            self.assertNotEqual(r["tier"], "tiny", override)
            self.assertEqual((r["plan"], r["approval"]), ("card", "yes"), override)
            self.assertNotEqual(r["review"], "none", override)

    def test_1c_missing_facts_are_not_tiny(self):
        _, r, _ = route("--track", "coding", "--critical", "none")
        self.assertEqual(r["tier"], "planned")

    def test_2_medium_task_plans_and_waits(self):
        _, r, _ = route(*FEATURE)
        self.assertEqual((r["tier"], r["plan"], r["approval"]), ("planned", "card", "yes"))
        self.assertEqual(r["review"], "reviewer·opus·low")

    def test_3_cheapest_suitable_executor(self):
        cases = {
            FEATURE: "R3·haiku-high",
            FEATURE[:-6] + ("--checks", "no", "--shape", "feature"): "R4·sonnet-high",
            ("--track", "coding", "--critical", "none", "--behaviour", "no", "--files", "40",
             "--lines", "80", "--checks", "yes", "--shape", "mechanical"): "R2·haiku-medium",
            ("--track", "coding", "--critical", "none", "--files", "3", "--lines", "90",
             "--shape", "tricky", "--checks", "yes"): "R4·sonnet-high",
            ("--track", "coding", "--critical", "none", "--files", "3", "--lines", "90",
             "--shape", "judgement"): "R6·opus-medium",
            ("--track", "coding", "--critical", "none", "--files", "1", "--lines", "12",
             "--checks", "yes"): "inline",
        }
        for args, want in cases.items():
            _, r, out = route(*args)
            self.assertEqual(r["executor"], want, out)

    def test_3b_mechanical_but_big_is_fast_planned(self):
        _, r, _ = route("--track", "coding", "--critical", "none", "--behaviour", "no",
                        "--files", "40", "--lines", "80", "--shape", "mechanical")
        self.assertEqual((r["tier"], r["mode"], r["review"]),
                         ("planned", "FAST", "reviewer·opus·low"))

    def test_4_high_risk_small_diff_keeps_safeguards(self):
        for trigger, review in (("auth", "reviewer-high·opus·high"),
                                ("secrets", "reviewer-high·opus·high"),
                                ("parsing", "reviewer-high·opus·high"),
                                ("money", "reviewer-medium·opus·medium"),
                                ("migration", "reviewer-medium·opus·medium"),
                                ("infra", "reviewer-medium·opus·medium")):
            args = list(TINY_CSS)
            args[args.index("--critical") + 1] = trigger
            _, r, out = route(*args)
            self.assertEqual((r["tier"], r["mode"], r["plan"], r["approval"], r["review"]),
                             ("critical", "CRITICAL", "card", "yes", review), out)
            self.assertEqual(r["checks"], "standard+negative")

    def test_4b_floor_never_lowers(self):
        _, r, _ = route(*TINY_CSS, "--floor", "CRITICAL")
        self.assertEqual(r["mode"], "CRITICAL")

    def test_4c_floor_or_trigger_cant_leave_the_code_route(self):
        for args in (("--track", "noncoding", "--floor", "CRITICAL"),
                     ("--track", "noncoding", "--floor", "FAST"),
                     ("--track", "review", "--artifact", "code", "--floor", "CRITICAL"),
                     ("--track", "review", "--artifact", "doc", "--critical", "auth")):
            rc, r, out = route(*args)
            self.assertEqual((rc, r), (2, {}), args)

    def test_5_email_has_no_plan_or_review(self):
        _, r, _ = route("--track", "noncoding")
        self.assertEqual((r["tier"], r["plan"], r["approval"], r["review"], r["executor"]),
                         ("direct", "none", "no", "none", "inline"))

    def test_5b_long_well_specified_writing_goes_to_haiku(self):
        _, r, _ = route("--track", "noncoding", "--turns", "6", "--shape", "mechanical")
        self.assertEqual(r["executor"], "R8·haiku-low")
        _, r, _ = route("--track", "noncoding", "--turns", "6", "--uncertain", "yes")
        self.assertEqual(r["executor"], "inline")

    def test_5c_noncoding_with_a_critical_trigger_is_refused(self):
        rc, _, out = route("--track", "noncoding", "--critical", "deletion")
        self.assertEqual(rc, 2)
        self.assertIn("--track coding or mixed", out)

    def test_6_review_only_when_requested(self):
        for turns in ("1", "8"):
            _, r, _ = route("--track", "noncoding", "--turns", turns)
            self.assertEqual(r["review"], "none")
        _, r, _ = route("--track", "review", "--artifact", "doc")
        self.assertEqual(r["review"], "reviewer·opus·low")

    def test_7_review_code_and_doc(self):
        _, r, _ = route("--track", "review", "--artifact", "code", "--critical", "none")
        self.assertEqual((r["scope"], r["review"], r["fixes"], r["executor"], r["plan"]),
                         ("diff", "reviewer·opus·low", "ask", "none", "none"))
        _, r, _ = route("--track", "review", "--artifact", "doc")
        self.assertEqual((r["scope"], r["fixes"]), ("artifact", "ask"))
        _, r, _ = route("--track", "review", "--artifact", "code", "--critical", "auth")
        self.assertEqual(r["review"], "reviewer-high·opus·high")
        rc, _, _ = route("--track", "review")
        self.assertEqual(rc, 2)

    def test_8_mixed_routes_only_the_code_part(self):
        _, r, _ = route("--track", "mixed", *TINY_CSS[2:])
        self.assertEqual((r["tier"], r["plan"], r["review"], r["writing"]),
                         ("tiny", "none", "none", "direct"))
        _, r, _ = route("--track", "mixed", *FEATURE[2:])
        self.assertEqual((r["tier"], r["approval"], r["writing"]), ("planned", "yes", "direct"))
        args = list(TINY_CSS[2:])
        args[args.index("--critical") + 1] = "money"
        _, r, _ = route("--track", "mixed", *args)
        self.assertEqual((r["tier"], r["approval"]), ("critical", "yes"))
        rc, _, _ = route("--track", "mixed")
        self.assertEqual(rc, 2, "a mixed task must state the code part's CRITICAL fact")

    def test_9_no_route_touches_the_gate(self):
        outs = [route(*TINY_CSS), route(*FEATURE), route("--track", "noncoding"),
                route("--track", "mixed", *FEATURE[2:]),
                route("--track", "review", "--artifact", "doc")]
        outs += [route("--track", "ops", "--op", op) for op in OPS_ALL]
        for _, r, out in outs:
            self.assertEqual(r.get("gate"), "hook", out)
        rc, _, _ = route(*TINY_CSS, "--gate", "off")
        self.assertEqual(rc, 2, "route.py must not accept a gate option")

    def test_10_route_leaves_git_state_alone(self):
        # route.py does no git or file I/O; this guards that it stays so. The skill's own git
        # behaviour (BASE..AFTER snapshots) is tested in test_snapshot.sh.
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
            g("init", "-q")
            with open(os.path.join(d, "a.txt"), "w") as fh:
                fh.write("x\n")
            g("add", "a.txt")
            g("-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "c")
            with open(os.path.join(d, "a.txt"), "a") as fh:
                fh.write("dirty\n")
            with open(os.path.join(d, "new.txt"), "w") as fh:
                fh.write("untracked\n")
            before = g("status", "--porcelain").stdout
            for args in (TINY_CSS, FEATURE, ("--track", "review", "--artifact", "code",
                                             "--critical", "none")):
                route(*args, cwd=d)
            for op in OPS_ALL:
                route("--track", "ops", "--op", op, "--turns", "6", cwd=d)
            self.assertEqual(g("status", "--porcelain").stdout, before)
            self.assertEqual(g("stash", "list").stdout, "")

    def test_bad_input(self):
        for args in (("--track", "coding", "--critical", "none", "--files", "-1"),
                     ("--track", "nope"), ("--track", "coding", "--critical", "maybe")):
            rc, _, _ = route(*args)
            self.assertEqual(rc, 2, args)


class Ops(unittest.TestCase):
    """Runtime tests of route.py's ops track. They test the policy, not which model a
    subagent actually ran (that is in its transcript) or any Web / Azure DevOps integration."""

    def test_o1_routine_ops_are_haiku_and_inline_when_short(self):
        for op in ("install", "test", "git-read"):
            r = ops(op)
            self.assertEqual((r["tier"], r["rung"], r["executor"]),
                             ("ops", "haiku-low", "inline"), op)
        self.assertEqual(ops("install", "--turns", "5")["executor"], "haiku-low")
        self.assertEqual(ops("install", "--turns", "5", "--uncertain", "yes")["executor"],
                         "inline")

    def test_o2_routine_ops_get_no_plan_or_review(self):
        for op in OPS_ALL:
            r = ops(op)
            self.assertEqual((r["plan"], r["approval"], r["review"], r["checks"]),
                             ("none", "no", "none", "exit-code"), op)

    def test_o3_dependency_errors_escalate_only_on_evidence(self):
        self.assertEqual(ops("deperr")["rung"], "haiku-medium")
        self.assertEqual(ops("deperr", "--turns", "9")["rung"], "haiku-medium",
                         "turn count alone never escalates")
        r = ops("deperr", "--failed", "1")
        self.assertEqual((r["rung"], r["escalate"]), ("haiku-high", "one-rung"))
        self.assertEqual(ops("deperr", "--shape", "tricky")["rung"], "sonnet-high")
        r = ops("deperr", "--failed", "2")
        self.assertEqual((r["executor"], r["escalate"]), ("ask", "ask"))
        self.assertEqual(ops("deperr")["fix"], "reroute-coding")

    def test_o3b_never_sonnet_medium_nor_opus(self):
        for op in OPS_ALL:
            for extra in ((), ("--failed", "1"), ("--shape", "tricky"),
                          ("--shape", "tricky", "--failed", "1"), ("--turns", "9")):
                r = ops(op, *extra)
                self.assertNotIn("opus", r["rung"] + r["executor"], (op, extra))
                self.assertNotEqual(r["rung"], "sonnet-medium", (op, extra))

    def test_o5_commit_push_ado_write_need_a_yes_and_stay_inline(self):
        for op in ("commit", "push", "ado-write"):
            r = ops(op, "--turns", "9")
            self.assertEqual((r["authz"], r["executor"], r["delegable"]),
                             ("explicit-yes", "inline", "no"), op)
        for op in ("install", "test", "git-read", "ado-read", "web", "research"):
            self.assertEqual(ops(op)["authz"], "no", op)

    def test_o7_web_and_ado_stay_inline(self):
        for op in ("web", "research", "ado-read", "ado-write"):
            r = ops(op, "--turns", "9")
            self.assertEqual((r["executor"], r["delegable"]), ("inline", "no"), op)

    def test_o9_targeted_web_is_cheap_conflicting_research_is_sonnet(self):
        self.assertEqual(ops("web")["rung"], "haiku-low")
        self.assertEqual(ops("research")["rung"], "sonnet-high")
        self.assertEqual(ops("web", "--shape", "tricky")["rung"], "sonnet-high")

    def test_o11_complex_conflicts_use_sonnet_and_fix_reroutes(self):
        r = ops("conflict")
        self.assertEqual((r["rung"], r["executor"], r["fix"]),
                         ("sonnet-high", "inline", "reroute-coding"))
        self.assertEqual(ops("conflict", "--turns", "4")["executor"], "inline",
                         "sonnet break-even is ~4 turns")
        self.assertEqual(ops("conflict", "--turns", "5")["executor"], "sonnet-high")

    def test_o12_ops_refuses_code_facts_and_needs_an_op(self):
        for args in (("--op", "commit", "--critical", "money"),
                     ("--op", "push", "--floor", "FAST"), (), ("--op", "nope"),
                     ("--op", "test", "--failed", "-1")):
            rc, _, _ = route("--track", "ops", *args)
            self.assertEqual(rc, 2, args)
        rc, _, _ = route(*TINY_CSS, "--op", "push")
        self.assertEqual(rc, 2, "--op belongs to the ops track only")


class Docs(unittest.TestCase):
    """Static checks: the skill text calls route.py and agrees with it. Not runtime behaviour."""

    skill = read("SKILL.md")

    def test_entries_and_hint(self):
        self.assertIn('argument-hint: "do <task> | route <task> | review [target] | setup"',
                      self.skill)
        self.assertIn("`review [target]` → the Review entry below", self.skill)
        self.assertIn("## Review entry — `/sharaqi review [target]`", self.skill)

    def test_step1_command_runs_context_check_and_route(self):
        cmd = next(line for line in self.skill.splitlines()
                   if line.startswith("date -u") and "snapshot.sh" in line)
        self.assertLess(cmd.index("tokens.py\" --context"), cmd.index("route.py"))

    def test_ops_policies_are_written_down(self):
        # Static: the text says it; whether a run follows it is not tested here.
        ops_text = self.skill[self.skill.index("**Ops** (`ops`)"):self.skill.index("## Step 2")]
        for op in OPS_ALL:
            self.assertIn(op, ops_text, op)
        for rule in ("status, diff, log only",            # 4 git-read stays read-only
                     "`git diff --cached`", "stage only the\n  intended files",  # 5 commit
                     "no `--force`",                      # 6 push
                     "only the named items and fields",   # 7 ado-read
                     "changes\n  only the asked fields",  # 8 ado-write
                     "never sonnet-medium", "A small model is not permission"):
            self.assertIn(rule, ops_text, rule)
        self.assertIn("`ops`, `review`) runs this check", self.skill)
        self.assertIn("| Ops `haiku-low`", read("references/delegation.md"))

    def test_every_tier_route_py_emits_is_documented(self):
        for tier in ("tiny", "planned", "critical", "direct", "ops"):
            self.assertRegex(self.skill, r"\| `%s`" % tier)

    def test_gate_applies_to_every_track(self):
        self.assertIn("no route skips it", self.skill)
        review = self.skill[self.skill.index("## Review entry"):self.skill.index("## Step 6")]
        self.assertIn("context check (rule 9)", review)

    def test_plan_template_fits_12_lines(self):
        block = re.search(r"```\n<ROUTE line from route.py>\n(.*?)```", self.skill, re.S)
        self.assertIsNotNone(block)
        self.assertLessEqual(len(block.group(0).splitlines()) - 2, 12)
        self.assertIn("plan ≤ 12 lines", self.skill)

    def test_old_bypass_and_every_change_rule_are_gone(self):
        for f in ("SKILL.md", "references/review.md", "docs/model-effort-plan.md"):
            text = read(f)
            self.assertNotIn("اكتب «نفّذ inline بلا كارت»", text, f)
            self.assertNotIn("No size, mode or cosmetic exception", text, f)
        self.assertNotIn("(every task that changed files)", self.skill)

    def test_reviewer_roles_listed(self):
        d = read("references/delegation.md")
        self.assertIn("| R7+ Critical reviewer, `critical` routes | `reviewer-medium` | `opus` |", d)
        self.assertIn("| R7+ for auth/secrets/parsing | `reviewer-high` | `opus` |", d)
        self.assertNotIn("pass `effort` on the call", d)
        self.assertIn("| R8 Writer, a `direct` (non-coding) route past break-even |"
                      " `implementer-low` | `haiku` |", d)
        self.assertIn("## Explicit review (`/sharaqi review`)", read("references/review.md"))
        self.assertIn("## Explicit review", read("agents/reviewer.md"))

    def test_critical_reviewer_named_wherever_a_review_is_called(self):
        review_entry = self.skill[self.skill.index("## Review entry"):
                                  self.skill.index("## Step 6")]
        step5 = self.skill[self.skill.index("## Step 5"):self.skill.index("## Review entry")]
        r = read("references/review.md")
        for name, text in (("SKILL.md Review entry", review_entry),
                           ("SKILL.md step 5", step5), ("review.md", r)):
            self.assertIn("`reviewer-high`", text, name)
        self.assertNotIn("Reviewer | opus | low (configured)", r)
        self.assertNotIn("`reviewer` · opus · low with the previous findings", r)


if __name__ == "__main__":
    unittest.main()
