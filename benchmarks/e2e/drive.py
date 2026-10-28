#!/usr/bin/env python3
"""ONE PAID RUN of one task in one arm, through one live `claude -p` process (stream-json in/out).

usage: python3 -I drive.py <plugin|plain> <report|medium|complex> <runs-dir>

  plugin: prompt `/sharaqi:sharaqi do <task>`, no --model / --effort (the user's defaults and the
          skill's frontmatter decide), plugin loaded from <runs>/plugin (git archive of HEAD).
          When a turn ends on a waiting plan (<config>/sharaqi-state/<sid>.pending, or the reply
          asks for `/sharaqi go`), the driver sends `/sharaqi:sharaqi go` in the same process.
  plain:  prompt `<task>` verbatim, `--model claude-opus-5-5 --effort medium`.

Identical for both: a fresh git repo copied from fixtures/<task>, acceptEdits, the same tool
allow-list, `sharaqi@skills-dir` disabled, a $15 budget, a 30-minute limit, and
SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=1000000 (the window Claude Code reports for
claude-sonnet-5-5 and claude-opus-5-5; only the plugin reads it).
Writes <runs>/<arm>-<task>/{work/, stream.jsonl, stderr.txt, run.json}.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_GO = 3
TIMEOUT_S = 1800
TOOLS = ["Read", "Glob", "Grep", "Edit", "Write", "Agent", "Bash", "WebSearch", "WebFetch",
         "TodoWrite"]
STATE = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")),
                     "sharaqi-state")


def user_msg(text):
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n"


def waiting_plan(sid, result_text):
    if sid and os.path.exists(os.path.join(STATE, sid + ".pending")):
        return "pending-file"
    if "/sharaqi go" in (result_text or "") or "/sharaqi:sharaqi go" in (result_text or ""):
        return "reply-asks-go"
    return None


def main():
    arm, task, runs = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
    text = open(os.path.join(HERE, "tasks", task + ".txt"), encoding="utf-8").read().strip()
    out = os.path.join(runs, f"{arm}-{task}")
    if os.path.exists(out):
        sys.exit(f"{out} exists")
    work = os.path.join(out, "work")
    shutil.copytree(os.path.join(HERE, "fixtures", task), work)
    git = ["git", "-c", "user.email=bench@example.invalid", "-c", "user.name=bench"]
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run(git + ["commit", "-qm", "fixture"], cwd=work, check=True)

    cmd = ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json",
           "--verbose", "--permission-mode", "acceptEdits", "--max-budget-usd", "15",
           "--settings", json.dumps({"enabledPlugins": {"sharaqi@skills-dir": False}}),
           "--allowedTools", *TOOLS]
    if arm == "plugin":
        cmd += ["--plugin-dir", os.path.join(runs, "plugin")]
        prompt = "/sharaqi:sharaqi do " + text
    elif arm == "plain":
        cmd += ["--model", "claude-opus-5-5", "--effort", "medium"]
        prompt = text
    else:
        sys.exit("arm: plugin or plain")
    env = dict(os.environ, SHARAQI_BENCHMARK="1", SHARAQI_CONTEXT_WINDOW="1000000")

    stream = open(os.path.join(out, "stream.jsonl"), "w", encoding="utf-8")
    err = open(os.path.join(out, "stderr.txt"), "w", encoding="utf-8")
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=err, text=True, encoding="utf-8")
    sent = [{"t": 0.0, "text": prompt}]
    p.stdin.write(user_msg(prompt))
    p.stdin.flush()
    sid, results, gos, closed = None, [], 0, False
    watchdog = threading.Timer(TIMEOUT_S, p.kill)
    watchdog.start()
    for line in p.stdout:
        stream.write(line)
        stream.flush()
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            sid = ev.get("session_id")
        if ev.get("type") != "result":
            continue
        results.append(ev)
        why = waiting_plan(sid, ev.get("result")) if arm == "plugin" else None
        if why and gos < MAX_GO and not ev.get("is_error") and not closed:
            gos += 1
            go = "/sharaqi:sharaqi go"
            sent.append({"t": round(time.time() - t0, 1), "text": go, "why": why})
            p.stdin.write(user_msg(go))
            p.stdin.flush()
            continue
        if not closed:
            p.stdin.close()
            closed = True
    rc = p.wait()
    timed_out = not watchdog.is_alive() and rc != 0
    watchdog.cancel()
    wall = round(time.time() - t0, 1)
    stream.close()
    err.close()
    events = os.path.join(STATE, f"{sid}.events.jsonl") if sid else None
    if events and os.path.exists(events):
        shutil.copy(events, os.path.join(out, "sharaqi-events.jsonl"))
    last = results[-1] if results else {}
    run = {
        "arm": arm, "task": task, "session_id": sid, "exit_code": rc, "timed_out": timed_out,
        "wall_s": wall, "messages_sent": sent,
        "results": [{k: r.get(k) for k in ("subtype", "is_error", "total_cost_usd", "duration_ms",
                                            "duration_api_ms", "num_turns", "modelUsage")}
                    for r in results],
        "final_text": last.get("result"),
    }
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)
    print(json.dumps({"arm": arm, "task": task, "rc": rc, "wall_s": wall, "gos": gos,
                      "cost": [r.get("total_cost_usd") for r in results]}))


if __name__ == "__main__":
    main()
