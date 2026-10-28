#!/usr/bin/env bash
# UserPromptSubmit: routes a /sharaqi prompt before any model turn (scripts/classify.py --hook)
# and injects the ROUTE, its facts and only that route's steps as additionalContext. Any other
# prompt passes through, except a plain reply while a plan waits for approval, which gets one
# systemMessage (it runs on the session's model, not the Sonnet seat). Never blocks a prompt.
# No python: a /sharaqi prompt gets an explicit "ROUTE UNAVAILABLE" context, never a silent pass.
# Python: python3, then python. SHARAQI_PYTHON overrides it (the tests use a missing path).

here=$(cd "$(dirname "$0")" && pwd)
input=$(cat)
py="${SHARAQI_PYTHON:-}"
[ -z "$py" ] && py=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -n "$py" ] && command -v "$py" >/dev/null 2>&1; then
  out=$(printf '%s' "$input" | "$py" -I "$here/../scripts/classify.py" --hook 2>/dev/null) && {
    [ -n "$out" ] && printf '%s\n' "$out"
    exit 0
  }
fi
# classify.py missing or failed: say so for a /sharaqi prompt only.
if printf '%s' "$input" | tr '\r\n' '  ' | grep -Eq '"prompt"[[:space:]]*:[[:space:]]*"[[:space:]]*/sharaqi(:sharaqi)?([[:space:]"]|\\n)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"SHARAQI ROUTE UNAVAILABLE: the prompt hook could not run scripts/classify.py (python missing or failed). Judge the facts yourself, run scripts/route.py, and say route: model-judged (hook failed) in the report."}}'
fi
exit 0
