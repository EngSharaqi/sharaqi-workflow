#!/usr/bin/env python3
"""Deterministic routing for a /sharaqi prompt: task text in, route.py facts and route out.

Runs in the UserPromptSubmit hook (hooks/route-prompt.sh), before any model turn. No model
call, no repository reads beyond an optional BASE snapshot (scripts/snapshot.sh) for routes
that plan. Every fact is either `stated` (a phrase in the task matched a rule, named in the
output) or `assumed` (route.py's safe default). The seat may correct a fact after its first
reads and re-run route.py; a CRITICAL trigger found here stays as the floor.

usage:
  classify.py "<prompt text>"        print the injected context (for tests and debugging)
  classify.py --hook                 read the hook JSON on stdin; print the hook output JSON
Env: SHARAQI_DEBUG=1 adds the debug reference; SHARAQI_NO_ROUTE_HOOK=1 makes --hook a no-op.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route as policy  # noqa: E402

VERSION = "1.0.0-exp"
ROOT = os.path.dirname(HERE)
ROUTES = os.path.join(ROOT, "references", "routes")
COMMAND = re.compile(r"^\s*/sharaqi(?::sharaqi)?(?=\s|$)(.*)$", re.S)
ENTRIES = ("do", "route", "review", "setup", "go")
SESSION = re.compile(r"[A-Za-z0-9_-]+")

# --- text rules. Each is (name, regex); the first match is quoted in the FACTS line.
I = re.I
PATH = re.compile(
    r"(?<![\w/.-])((?:\.?[\w-]+/)*[\w.-]+\.(?:tsx?|jsx?|mjs|cjs|py|rb|go|rs|java|kt|cs|php|"
    r"vue|svelte|css|scss|less|html?|ya?ml|json|toml|ini|sql|sh|ps1|tf|md|txt|rst|xml|gradle|"
    r"lock))\b")
# Writing needs a writing verb and a deliverable: a noun alone ("instead of the email") never
# makes a task non-code.
WRITING = re.compile(
    r"^\s*summari[sz]e\b|\b(?:write|draft|compose|prepare|summari[sz]e|reply|respond|rewrite|"
    r"proofread|translate|announce|edit|update|polish)\b.{0,60}?\b(?:e-?mail|message|note|notes|"
    r"report|summary|bullets?|bullet points|announcement|letter|memo|minutes|proposal|section|"
    r"documentation|docs|post|paragraph|plan|reply|response|readme|changelog entry)\b", I)
CODE = re.compile(
    r"\b(fix|bug|add|implement|refactor|rename|change|update|remove|delete|drop|replace|migrate|"
    r"bump|upgrade|create|build|wire|hook up|extract|move|port|show|display|hide|make|let|allow|"
    r"set|use|support|handle|return|enable|disable|paginate|sort|filter|validate|cache)\b.{0,80}?\b(function|method|class|"
    r"component|components|prop|props|endpoint|api|route|handler|test|tests|module|button|page|"
    r"screen|form|query|schema|table|column|field|type|interface|script|config|workflow|"
    r"pipeline|dependency|dependencies|package|style|css|role|permission|serializer|export|"
    r"import|footer|header|copyright|colour|color|font|label|variable|constant|hook|"
    r"middleware|model|controller|service|view|template|step)\b", I)
QUESTION = re.compile(r"^\s*(what|why|how|when|where|which|who|explain|describe|compare|"
                      r"should|can you explain|tell me)\b", I)
OPS_RULES = (
    ("commit", re.compile(r"^\s*(?:git\s+)?commit\b|\bcommit (?:the|these|my|all) changes\b", I)),
    ("push", re.compile(r"^\s*(?:git\s+)?push\b|\bpush (?:the|this|my) branch\b", I)),
    ("install", re.compile(r"^\s*(?:npm|pnpm|yarn|pip|composer|bundle)\s+(?:install|i|ci)\b|"
                           r"^\s*install (?:the )?(?:dependencies|packages|requirements)\b", I)),
    ("test", re.compile(r"^\s*(?:run|rerun|re-run) (?:the |all )?(?:unit |e2e )?tests?\b(?!.*\bfix)", I)),
    ("git-read", re.compile(r"^\s*(?:show |check )?git (?:status|diff|log)\b|"
                            r"^\s*(?:what changed|show (?:me )?the diff)\b", I)),
    ("ado-write", re.compile(r"\b(?:update|create|close|assign|comment on) (?:the )?"
                             r"(?:work item|ticket|bug|task) #?\d+\b", I)),
    ("ado-read", re.compile(r"\b(?:azure devops|ado)\b|\bwork item #?\d+\b", I)),
    ("web", re.compile(r"^\s*(?:search the web|search online|look up online|google)\b", I)),
)
CRITICAL_RULES = (  # security first: route.py gives them the strongest reviewer
    ("auth", re.compile(r"(?:^|[\s/`'\"(])auth/|\bauth(?:n|z|entication|orization|orisation)?\b|"
                        r"\blog-?in\b|\bsign[- ]?in\b|\bpasswords?\b|\bpermissions?\b|\broles?\b|"
                        r"\brbac\b|\bacl\b|access control|\bjwt\b|\boauth\b|\bcsrf\b|\bcors\b|"
                        r"\bsessions? (?:token|cookie)s?\b", I)),
    ("secrets", re.compile(r"\bsecrets?\b|\bapi[ _-]?keys?\b|\bcredentials?\b|\bprivate key\b|"
                           r"(?:^|\s)\.env\b|\baccess tokens?\b|\bcertificates?\b", I)),
    ("parsing", re.compile(r"\bsql\b|raw quer|shell command|\bexec\(|\beval\b|innerhtml|"
                           r"dangerouslysetinnerhtml|\bv-html\b|deserializ|uploaded? files?|"
                           r"untrusted input|user[- ]supplied|html from (?:user|input)", I)),
    ("migration", re.compile(r"\bmigrations?\b(?! test)|\bmigrate (?:the )?(?:db|database|data|"
                             r"schema|users)\b|schema change|alter table|\bbackfill", I)),
    ("deletion", re.compile(r"\bdrop (?:the )?(?:[\w.]+ )?(?:tables?|columns?|database|index|"
                            r"collection)\b|\btruncate\b|\b(?:delete|purge|wipe|erase|remove) "
                            r"(?:all |the |old |every )?(?:[\w.]+ )?(?:data|records|rows|users|"
                            r"accounts|files|backups|tables?|columns?)\b|rm -rf", I)),
    ("irreversible", re.compile(r"\birreversibl|force[- ]push|rewrite (?:git )?history|"
                                r"production (?:data|database)|\bprod (?:db|database)\b", I)),
    ("money", re.compile(r"\bpayments?\b|\bcharge (?:the )?(?:card|customer|user)|\brefunds?\b|"
                         r"\bpayouts?\b|\bbilling\b|\bstripe\b|\bpaypal\b|\binvoic", I)),
    ("infra", re.compile(r"\.github/workflows|\bci\b|ci/cd|\bpipelines?\b|\bdeploy|dockerfile|"
                         r"docker-compose|kubernetes|\bk8s\b|\bhelm\b|terraform|package\.json|"
                         r"requirements\.txt|\blockfile|package-lock|\bdependenc(?:y|ies)\b|"
                         r"\bbump (?:the )?\w|\bupgrade (?:the )?(?:package|library|framework|"
                         r"dependency|sdk)|vite\.config|webpack\.config|\bnginx\b", I)),
)
COSMETIC = re.compile(r"\b(colou?r|font|css|styl(?:e|ing)|label|wording|text|typo|spelling|"
                      r"copy ?(?:text|change)?|copyright|year|comment|docstring|spacing|margin|"
                      r"padding|icon|rename|renaming|indent|whitespace|title|placeholder)\b", I)
LOGIC = re.compile(r"\b(fix|bug|off-by-one|logic|calculat|validat|feature|implement|add|"
                   r"handle|support|behaviou?r|return|throw|error|export|import|serializ|"
                   r"endpoint|api|query|let\b|allow|enable|disable|remove|delete)\w*", I)
TRIVIAL = re.compile(r"\b(one|1|single) (?:css )?(?:rule|line|value|word|character)\b|"
                     r"\btypo\b|\bcopyright year\b|\bcolou?r\b|\bfont size\b|\blabel\b", I)
MECHANICAL = re.compile(r"\brenam(?:e|ing)\b|\breplace (?:all|every)\b|\bsame (?:edit|change)\b|"
                        r"\bin (?:\d+|all|every) (?:components|files|places|modules|screens)\b|"
                        r"\bacross (?:the )?(?:repo|codebase|files|components)\b", I)
TRICKY = re.compile(r"\b(timezones?|dates?|daylight|concurren\w*|race condition|deadlock|"
                    r"state machine|parser|regex|cache invalidation|retry logic|locking)\b", I)
JUDGEMENT = re.compile(r"\b(architect\w*|redesign|design (?:the|a|an)|choose between|"
                       r"decide (?:how|whether|between)|trade-?offs?|evaluate (?:approaches|"
                       r"options))\b", I)
UNCERTAIN = re.compile(r"\b(investigate|figure out|find out why|root cause|intermittent\w*|"
                       r"flaky|sometimes|randomly|not sure|unclear|somehow|debug why)\b", I)
CHECKS = re.compile(r"\b(tests? (?:exist|cover|are there)|the repo has (?:vitest|jest|pytest|"
                    r"tests)|vitest|jest|pytest|mocha|phpunit|rspec|unit tests?|typescript "
                    r"checks|type ?check\w*|tsc\b|compiler (?:checks|catches))", I)
N_FILES = re.compile(r"\b(\d+)\s+(?:files|components|modules|screens|places|pages)\b", I)
N_LINES = re.compile(r"~?\b(\d+)\s*(?:changed )?lines?\b", I)
ONE_LINE = re.compile(r"\b(?:one|single|1)[ -](?:line|rule)\b|\(one (?:line|rule)\)", I)
SPLIT_WRITING = re.compile(r"\s*(?:\band\b|,|;)\s*(?=(?:then\s+)?(?:write|draft|compose|"
                           r"prepare|send|post|summari[sz]e|announce)\b)", I)
DOC_TARGET = re.compile(r"[\"“”]|\b(document|doc|email|report|draft|text|message|proposal|"
                        r"plan|spec)\b", I)
DOC_PATH = re.compile(r"\.(?:md|txt|rst|adoc)$", I)
CODE_TARGET = re.compile(r"^(?:HEAD(?:[~^]\d*)?|[0-9a-f]{7,40}|[\w./-]+\.\.\.?[\w./-]+|"
                         r"working tree|staged|origin/[\w./-]+)$|" + PATH.pattern, I)


def hit(rx, text):
    m = rx.search(text)
    return m.group(0).strip() if m else None


def parse_command(prompt):
    """(entry, args, debug) for a /sharaqi prompt, or None for any other prompt."""
    m = COMMAND.match(prompt or "")
    if not m:
        return None
    words = m.group(1).strip()
    debug = False
    while True:
        if words.startswith("--debug") and (len(words) == 7 or words[7].isspace()):
            debug, words = True, words[7:].lstrip()
            continue
        break
    first, _, rest = words.partition(" ")
    if first.lower() in ENTRIES:
        entry, args = first.lower(), rest.strip()
    else:
        entry, args = "do", words
    if args.startswith("--debug") and (len(args) == 7 or args[7].isspace()):
        debug, args = True, args[7:].strip()
    return entry, args, debug


class Facts:
    """Facts for route.py with where each came from."""

    def __init__(self):
        self.vals, self.why = {}, {}

    def set(self, key, val, why):
        self.vals[key], self.why[key] = val, why

    def argv(self):
        out = []
        for k, v in self.vals.items():
            out += ["--" + k, str(v)]
        return out

    def line(self):
        parts = []
        for k, v in self.vals.items():
            w = self.why[k]
            parts.append(f"{k}={v}({'assumed' if w is None else 'stated: ' + w})")
        return " ".join(parts)


def classify_task(text):
    """(track, Facts, confidence) for a do/route task."""
    f = Facts()
    for op, rx in OPS_RULES:
        m = hit(rx, text)
        if m and not hit(CODE, text):
            f.set("op", op, repr(m))
            turns = 1
            f.set("turns", turns, None)
            return "ops", f, "high"
    clauses = SPLIT_WRITING.split(text, maxsplit=1)
    code_part = clauses[0]
    writing_part = clauses[1] if len(clauses) > 1 else ""
    code_paths = [p for p in PATH.findall(code_part) if not DOC_PATH.search(p)]
    code = hit(CODE, code_part) or (code_paths[0] if code_paths else None)
    doc_only = PATH.search(text) and not any(not DOC_PATH.search(p) for p in PATH.findall(text))
    if not code:
        writing = hit(WRITING, text) or (doc_only and "doc paths only")
        if writing or hit(QUESTION, text):
            f.set("turns", 1, None)
            return "noncoding", f, "high" if writing else "low"
        track, conf = "coding", "low"  # nothing matched: the safe side (plan + approval)
    else:
        track, conf = ("mixed" if hit(WRITING, writing_part) else "coding"), "high"
    t = code_part if track == "mixed" else text

    trig = None
    for name, rx in CRITICAL_RULES:
        m = hit(rx, t)
        if m:
            trig = (name, m)
            break
    f.set("critical", trig[0] if trig else "none", repr(trig[1]) if trig else "no trigger word")

    logic, cosmetic = hit(LOGIC, t), hit(COSMETIC, t)
    if cosmetic and not logic:
        f.set("behaviour", "no", repr(cosmetic))
    elif logic:
        f.set("behaviour", "yes", repr(logic))
    else:
        f.set("behaviour", "yes", None)

    unc = hit(UNCERTAIN, t)
    f.set("uncertain", "yes" if unc else "no", repr(unc) if unc else None)

    paths = sorted(set(PATH.findall(t)))
    n = N_FILES.search(t)
    if n:
        f.set("files", int(n.group(1)), repr(n.group(0)))
    elif paths:
        f.set("files", len(paths), "paths named: " + ", ".join(paths[:3]))
    else:
        f.set("files", 2, None)
        conf = "low" if conf == "low" else conf

    shape = None
    for name, rx in (("judgement", JUDGEMENT), ("tricky", TRICKY), ("mechanical", MECHANICAL)):
        m = hit(rx, t)
        if m:
            shape = (name, m)
            break
    if shape is None and f.vals["behaviour"] == "no":
        m = hit(TRIVIAL, t) or (cosmetic if f.vals["files"] <= 1 else None)
        if m:
            shape = ("trivial", m)
    f.set("shape", shape[0] if shape else "feature", repr(shape[1]) if shape else None)

    ln = N_LINES.search(t)
    one = hit(ONE_LINE, t)
    if ln:
        f.set("lines", int(ln.group(1)), repr(ln.group(0)))
    elif one:
        f.set("lines", 1, repr(one))
    elif f.vals["files"] <= 1 and paths:
        f.set("lines", 10, None)  # one named file, no size given: small, but assumed
    else:
        f.set("lines", policy.INLINE_LINES, None)

    chk = hit(CHECKS, t)
    f.set("checks", "yes" if chk else "no", repr(chk) if chk else None)
    return track, f, conf


def classify_review(target):
    """(Facts, confidence) for /sharaqi review [target]."""
    f = Facts()
    target = target.strip()
    if not target:
        f.set("artifact", "code", "no target: the working tree")
        f.set("critical", "none", "no target named")
        return f, "low"
    is_code = hit(CODE_TARGET, target)
    is_doc = hit(DOC_TARGET, target)
    if is_doc and not (is_code and not hit(re.compile(r"[\"“”]"), target)):
        f.set("artifact", "doc", repr(is_doc))
        return f, "high"
    f.set("artifact", "code", repr(is_code) if is_code else None)
    trig = None
    for name, rx in CRITICAL_RULES:
        m = hit(rx, target)
        if m:
            trig = (name, m)
            break
    f.set("critical", trig[0] if trig else "none",
          repr(trig[1]) if trig else "none in the target text; judge the diff's paths")
    return f, "high" if is_code else "low"


def run_policy(track, facts):
    """(ROUTE line, WHY line, route dict) via route.py itself, so one policy decides."""
    f = policy.parse(["--track", track] + facts.argv())
    out, why = policy.route(f)
    return policy.route_line(track, out), "WHY " + why, out


def snapshot(cwd):
    """(tree, problem). BASE for routes that plan: the working tree before the seat edits."""
    try:
        r = subprocess.run(["bash", os.path.join(HERE, "snapshot.sh")], cwd=cwd or None,
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "snapshot failed (%s)" % e.__class__.__name__
    tree = r.stdout.strip()
    if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40,64}", tree):
        return None, (r.stderr.strip() or "snapshot failed (exit %d)" % r.returncode)[:120]
    return tree, None


def ref(name):
    with open(os.path.join(ROUTES, name + ".md"), encoding="utf-8") as fh:
        return fh.read().strip().replace("${SKILL}", ROOT)


def build(entry, args, debug, cwd=None, take_base=True):
    """(context text, event dict). Raises on internal failure; the hook reports it."""
    head = f"SHARAQI v{VERSION} · entry={entry} · routed by the prompt hook from the text alone"
    ev = {"event": "route", "entry": entry, "debug": debug}
    if entry == "setup":
        return head + "\n" + ref("setup"), ev
    if entry == "go":
        return None, ev  # filled in by the hook from the session's pending route
    if not args:
        ev["route"] = "none"
        return head + "\nNo task or target given: ask the user what to do; run nothing.", ev
    if entry == "review":
        facts, conf = classify_review(args)
        track = "review"
    else:
        track, facts, conf = classify_task(args)
    rline, wline, out = run_policy(track, facts)
    ev.update(route=rline, why=wline[4:], facts=facts.line(), confidence=conf)
    parts = [head, rline, wline, "FACTS " + facts.line() + f" · confidence={conf}"]
    if entry == "route":
        parts.append(ref("route-only"))
        return "\n".join(parts), ev
    if out.get("plan", "none") != "none" and take_base:
        tree, problem = snapshot(cwd)
        parts.append(f"BASE {tree}" if tree else f"BASE unavailable: {problem}; the review "
                     "scope is not isolated, say so in the report")
        ev["base"] = "ok" if tree else "unavailable"
    tier = out["tier"]
    parts.append(ref({"tiny": "tiny", "planned": "planned", "critical": "critical",
                      "direct": "direct", "review": "review", "ops": "ops"}[tier]))
    delegated = out.get("executor", "inline") not in ("inline", "none", "ask") \
        or out.get("review", "none") != "none" or out.get("plan", "card") not in ("card", "none")
    if delegated:
        parts.append(ref("delegate"))
    if debug:
        parts.append(ref("debug"))
    return "\n".join(parts), ev


def state_dir():
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(root, "sharaqi-state")


def log_event(sid, ev):
    """Append one JSON line to <state>/<session>.events.jsonl. Never raises."""
    if not sid or not SESSION.fullmatch(sid):
        return
    try:
        d = state_dir()
        os.makedirs(d, exist_ok=True)
        ev = dict(ev, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), v=VERSION)
        with open(os.path.join(d, sid + ".events.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError:
        pass


def hook_main(raw):
    """UserPromptSubmit: route a /sharaqi prompt; warn once about a plain approval."""
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    sid = d.get("session_id") if isinstance(d.get("session_id"), str) else ""
    sid = sid if SESSION.fullmatch(sid or "") else ""
    prompt = d.get("prompt") if isinstance(d.get("prompt"), str) else ""
    sdir = state_dir()
    pending = os.path.join(sdir, sid + ".pending") if sid else None
    cmd = parse_command(prompt)
    if cmd is None:
        # A plain reply while a plan waits for approval runs on the session's model, not
        # the Sonnet seat. Tell the user once; never block the prompt.
        if pending and os.path.isfile(pending) and not prompt.lstrip().startswith("/"):
            try:
                os.remove(pending)
            except OSError:
                pass
            log_event(sid, {"event": "plain-approval"})
            return {"systemMessage": "sharaqi: this reply runs on the session's model, not "
                    "the Sonnet seat. To approve on Sonnet, send /sharaqi go."}
        return None
    entry, args, debug = cmd
    debug = debug or os.environ.get("SHARAQI_DEBUG") == "1"
    if entry == "go":
        try:
            with open(pending, encoding="utf-8") as fh:
                saved = fh.read().strip()
            os.remove(pending)
        except (OSError, TypeError):
            saved = ""
        log_event(sid, {"event": "approve", "found": bool(saved)})
        if not saved:
            ctx = (f"SHARAQI v{VERSION} · entry=go · no plan is waiting for approval in this "
                   "session: ask the user what to continue; run nothing.")
        else:
            ctx = (f"SHARAQI v{VERSION} · entry=go · the user approved the plan for:\n{saved}\n"
                   + (args and f"User's notes on the approval: {args}\n" or "")
                   + "Continue from Implement, under the same ROUTE and BASE.")
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                       "additionalContext": ctx}}
    try:
        ctx, ev = build(entry, args, debug, d.get("cwd"))
    except Exception as e:  # noqa: BLE001 - any failure must reach the model as such
        log_event(sid, {"event": "route-error", "entry": entry, "error": e.__class__.__name__})
        ctx = (f"SHARAQI v{VERSION} · ROUTE UNAVAILABLE: the prompt hook failed "
               f"({e.__class__.__name__}). Judge the facts yourself and run "
               "scripts/route.py; say 'route: model-judged (hook failed)' in the report.")
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                       "additionalContext": ctx}}
    log_event(sid, ev)
    route = ev.get("route", "")
    if pending and entry == "do" and " approval=yes " in route + " ":
        try:
            os.makedirs(sdir, exist_ok=True)
            base = [ln for ln in ctx.splitlines() if ln.startswith("BASE ")]
            with open(pending, "w", encoding="utf-8") as fh:
                fh.write("\n".join([route] + base) + "\n")
        except OSError:
            pass
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                   "additionalContext": ctx}}


def main(argv):
    if argv[:1] == ["--hook"]:
        if os.environ.get("SHARAQI_NO_ROUTE_HOOK") == "1":
            return 0
        out = hook_main(sys.stdin.read())
        if out:
            print(json.dumps(out, ensure_ascii=False))
        return 0
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = parse_command(argv[0]) or ("do", argv[0], False)
    ctx, _ = build(*cmd, take_base=False)
    print(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
