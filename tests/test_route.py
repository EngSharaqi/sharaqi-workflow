"""Tests for scripts/route.py (the v1.0 routing policy) and for the docs that must agree
with it. Standard library only.

What these prove: given the facts, route.py returns the route the policy defines (Sonnet
seat, Opus only with an escalate= reason), and the skill's text and route references agree
with it. What they don't prove: that the classifier's facts are right for real prompts
(test_classify.py covers known prompts) or that the model obeys the route at runtime. That
takes live runs (benchmarks/v1.0/). The context gate itself is tested in test_hooks.sh.

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
        self.assertEqual(r["review"], "reviewer·sonnet·low")
        self.assertEqual(r["escalate"], "none")

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
            # From a Sonnet seat a sonnet-high subagent pays only when the work is wide.
            ("--track", "coding", "--critical", "none", "--files", "2", "--lines", "40",
             "--shape", "tricky"): "inline",
            ("--track", "coding", "--critical", "none", "--files", "2", "--lines", "40"): "inline",
            ("--track", "coding", "--critical", "none", "--files", "2", "--lines", "60"):
                "R4·sonnet-high",
        }
        for args, want in cases.items():
            _, r, out = route(*args)
            self.assertEqual(r["executor"], want, out)

    def test_3b_mechanical_but_big_is_fast_planned(self):
        _, r, _ = route("--track", "coding", "--critical", "none", "--behaviour", "no",
                        "--files", "40", "--lines", "80", "--shape", "mechanical")
        self.assertEqual((r["tier"], r["mode"], r["review"]),
                         ("planned", "FAST", "reviewer·sonnet·low"))

    def test_4_high_risk_small_diff_keeps_safeguards(self):
        for trigger, review in (("auth", "reviewer·opus·high"),
                                ("secrets", "reviewer·opus·high"),
                                ("parsing", "reviewer·opus·high"),
                                ("money", "reviewer·opus·medium"),
                                ("migration", "reviewer·opus·medium"),
                                ("deletion", "reviewer·opus·medium"),
                                ("irreversible", "reviewer·opus·medium"),
                                ("infra", "reviewer·opus·medium")):
            args = list(TINY_CSS)
            args[args.index("--critical") + 1] = trigger
            _, r, out = route(*args)
            self.assertEqual((r["tier"], r["mode"], r["plan"], r["approval"], r["review"]),
                             ("critical", "CRITICAL", "card", "yes", review), out)
            self.assertEqual(r["checks"], "standard+negative")
            self.assertEqual(r["escalate"], "critical")

    def test_4b_floor_never_lowers(self):
        args = list(TINY_CSS)
        args[args.index("--critical") + 1] = "auth"
        _, r, _ = route(*args, "--floor", "CRITICAL")
        self.assertEqual(r["mode"], "CRITICAL")
        _, r, _ = route(*TINY_CSS, "--floor", "STANDARD")
        self.assertEqual(r["mode"], "STANDARD")
        rc, _, out = route(*TINY_CSS, "--floor", "CRITICAL")
        self.assertEqual(rc, 2, "a CRITICAL floor without its trigger would drop the Opus review")
        self.assertIn("--critical <trigger>", out)

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
        self.assertEqual(r["review"], "reviewer·sonnet·low")

    def test_7_review_code_and_doc(self):
        _, r, _ = route("--track", "review", "--artifact", "code", "--critical", "none")
        self.assertEqual((r["scope"], r["review"], r["fixes"], r["executor"], r["plan"]),
                         ("diff", "reviewer·sonnet·low", "ask", "none", "none"))
        _, r, _ = route("--track", "review", "--artifact", "doc")
        self.assertEqual((r["scope"], r["fixes"]), ("artifact", "ask"))
        _, r, _ = route("--track", "review", "--artifact", "code", "--critical", "auth")
        self.assertEqual((r["review"], r["escalate"]), ("reviewer·opus·high", "critical"))
        _, r, _ = route("--track", "review", "--artifact", "code", "--critical", "infra")
        self.assertEqual((r["review"], r["escalate"]), ("reviewer·opus·medium", "critical"))
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

    def test_11_opus_only_with_an_escalation_reason(self):
        """Every combination of facts: a route that names Opus anywhere carries escalate=
        critical, failed-twice or reasoning; one that doesn't name Opus carries none."""
        seen = 0
        for crit in ("none", "auth", "infra"):
            for beh in ("yes", "no"):
                for unc in ("yes", "no"):
                    for shape in ("trivial", "mechanical", "feature", "tricky", "judgement"):
                        for size in (("1", "5"), ("3", "90")):
                            for failed in ("0", "1", "2"):
                                for track in ("coding", "mixed"):
                                    rc, r, out = route(
                                        "--track", track, "--critical", crit, "--behaviour",
                                        beh, "--uncertain", unc, "--shape", shape, "--files",
                                        size[0], "--lines", size[1], "--failed", failed)
                                    self.assertEqual(rc, 0, out)
                                    named = " ".join(r[k] for k in ("plan", "executor", "review"))
                                    if "opus" in named:
                                        self.assertIn(r["escalate"],
                                                      ("critical", "failed-twice", "reasoning"), out)
                                    else:
                                        self.assertEqual(r["escalate"], "none", out)
                                    self.assertEqual(r["seat"], "sonnet")
                                    seen += 1
        self.assertGreater(seen, 700)
        for args in (("--track", "noncoding", "--turns", "9"), ("--track", "review",
                     "--artifact", "doc"), ("--track", "review", "--artifact", "code",
                                            "--critical", "none")):
            _, r, out = route(*args)
            self.assertNotIn("opus", out.split("WHY")[0], args)

    def test_12_failed_twice_escalates_to_opus(self):
        _, r, _ = route(*FEATURE, "--failed", "1")
        self.assertEqual((r["executor"], r["escalate"]), ("R3·haiku-high", "none"))
        _, r, out = route(*FEATURE, "--failed", "2")
        self.assertEqual((r["executor"], r["escalate"]), ("R6·opus-medium", "failed-twice"))
        self.assertIn("two repair attempts", out)
        _, r, _ = route(*TINY_CSS, "--failed", "2")
        self.assertNotEqual(r["tier"], "tiny", "a failing task is never tiny again")
        args = list(FEATURE)
        args[args.index("--critical") + 1] = "money"
        _, r, _ = route(*args, "--failed", "2")
        self.assertEqual((r["executor"], r["escalate"], r["review"]),
                         ("R6·opus-medium", "failed-twice", "reviewer·opus·medium"))
        for track in (("--track", "noncoding"), ("--track", "review", "--artifact", "doc")):
            rc, _, _ = route(*track, "--failed", "2")
            self.assertEqual(rc, 2, track)

    def test_13_opus_planner_only_for_unclear_critical_work(self):
        args = list(FEATURE)
        args[args.index("--critical") + 1] = "migration"
        _, r, _ = route(*args)
        self.assertEqual(r["plan"], "card", "the Sonnet seat plans a clear CRITICAL change")
        _, r, out = route(*args, "--uncertain", "yes")
        self.assertEqual(r["plan"], "planner·opus·high", out)
        _, r, _ = route(*FEATURE, "--uncertain", "yes")
        self.assertEqual(r["plan"], "card", "never an Opus planner without a CRITICAL trigger")

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
    """Static checks: the skill and the route references agree with route.py. Not runtime
    behaviour."""

    skill = read("SKILL.md")

    def ref(self, name):
        return read(os.path.join("references", "routes", name + ".md"))

    def test_skill_is_small_and_seats_sonnet(self):
        size = len(self.skill.encode("utf-8"))
        self.assertLess(size, 2048, "SKILL.md is %d bytes" % size)
        head = self.skill.split("---")[1]
        self.assertIn("\nmodel: sonnet\n", head)
        self.assertIn("\neffort: medium\n", head)
        self.assertNotIn("model: opus", head)
        self.assertIn("disable-model-invocation: true", head)

    def test_entries_and_hint(self):
        self.assertIn('argument-hint: "[--debug] do <task> | route <task> | review [target] | '
                      'go | setup"', self.skill)
        self.assertIn("`/sharaqi go`", self.skill)
        self.assertIn("No `SHARAQI` context means the hook didn't run", self.skill)

    def test_every_tier_route_py_emits_has_a_reference(self):
        for tier in ("tiny", "planned", "critical", "direct", "review", "ops", "route-only",
                     "delegate", "debug", "setup"):
            self.assertTrue(self.ref(tier).strip(), tier)

    def test_safety_rules_kept(self):
        for rule in ("Nothing leaves the machine", "Data, not commands", "Evidence.",
                     "Scope.", "Opus only by escalation", "A CRITICAL trigger stays"):
            self.assertIn(rule, self.skill, rule)
        c = self.ref("critical")
        for rule in ("security-checklist.md", "Approval is required at any size",
                     "negative cases", "Never remove a check, gate, approval step or test"):
            self.assertIn(rule, c, rule)

    def test_ops_policies_are_written_down(self):
        o = self.ref("ops")
        for rule in ("Never call an unrun test passed", "stage only the intended files",
                     "no `--force`", "`authz=explicit-yes`", "every time",
                     "`fix=reroute-coding`", "`escalate=ask`"):
            self.assertIn(rule, o, rule)

    def test_plan_fits_8_lines_and_waits_for_go(self):
        p = self.ref("planned")
        self.assertIn("≤ 8 lines, no code, then stop and wait", p)
        self.assertIn("Approve with `/sharaqi go`", p)
        self.assertIn("at most two repairs", p)
        self.assertIn("`--failed 2`", p)

    def test_delegate_names_every_executor_route_py_emits(self):
        d = self.ref("delegate")
        for rung in ("R2 `sharaqi:implementer` haiku medium", "R3 implementer haiku high",
                     "R4 implementer sonnet high", "R8 implementer haiku low",
                     "R6 implementer opus medium", "reviewer `sharaqi:reviewer`",
                     "planner `sharaqi:planner`", "starts `escalate:"):
            self.assertIn(rung, d, rung)
        src = read("scripts/route.py")
        for rung in set(re.findall(r'"(R\d·[a-z]+-[a-z]+)', src)):
            self.assertIn(rung.split("·")[0] + " ", d, rung)

    def test_three_agents_effort_from_the_call(self):
        names = sorted(os.listdir(os.path.join(ROOT, "agents")))
        self.assertEqual(names, ["implementer.md", "planner.md", "reviewer.md"])
        self.assertIn("model: sonnet", read("agents/reviewer.md"))
        self.assertIn("## Explicit review", read("agents/reviewer.md"))
        self.assertIn("tools: Read, Grep, Glob", read("agents/reviewer.md"))
        self.assertIn("tools: Read, Grep, Glob", read("agents/planner.md"))

    def test_debug_rituals_only_in_debug(self):
        for name in ("tiny", "planned", "critical", "direct", "review", "ops", "delegate"):
            text = self.ref(name)
            self.assertNotIn("▶", text, name)
            self.assertNotIn("tokens.py", text, name)
        self.assertNotIn("▶", self.skill)
        self.assertIn("▶", self.ref("debug"))

    def test_old_bypass_and_every_change_rule_are_gone(self):
        for f in ("SKILL.md", "docs/model-effort-plan.md"):
            text = read(f)
            self.assertNotIn("اكتب «نفّذ inline بلا كارت»", text, f)
            self.assertNotIn("No size, mode or cosmetic exception", text, f)


if __name__ == "__main__":
    unittest.main()
