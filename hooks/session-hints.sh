#!/usr/bin/env bash
# Session state for sharaqi. Never blocks a prompt.
#   prompt      : a prompt whose first non-blank text is /sharaqi or /sharaqi:sharaqi (then a
#                 space or the end) marks this session as a sharaqi run (<session>.run), which
#                 makes cap-model.sh --in-run active here. A prompt that only mentions sharaqi
#                 doesn't. Any later prompt in a marked session refreshes the marker, so the
#                 ceiling stays on for follow-up messages until SessionEnd.
#                 Otherwise, after 2+ compactions: one hint per new compaction to open a new
#                 session. Hooks cannot run /compact themselves, so this only nudges.
#   postcompact : count compactions for this session; delete state older than 7 days.
#                 In a sharaqi run, also check the summary Claude Code passes (compact_summary)
#                 for a BASE tree hash and the route.py ROUTE line (SKILL.md rule 9). That is
#                 a presence check, not a check that the values or the rest are right. A miss,
#                 or no summary to check, is written to <session>.handoff; the next prompt
#                 (not a slash command) tells the model once, as additionalContext, and the
#                 user, as systemMessage. A new /sharaqi prompt clears it. Never blocks.
#   end         : (SessionEnd) remove this session's run marker, handoff flag and pending
#                 approval (scripts/classify.py). The events log stays for the run record.
# A crashed session never reaches SessionEnd. Its marker is ignored by cap-model.sh once it is
# older than RUN_TTL_MIN (24 hours since the session's last prompt), and every event here
# deletes markers past that age.
# Messages are \u-escaped JSON so no shell or console code page can mangle the Arabic.
# State: <config>/sharaqi-state/<session>.{run,compacts,hinted}
# Hints off: SHARAQI_NO_HINTS=1 (the run marker is still written).

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"

mode="$1"
input=$(cat)

summary=""
parsed=0
line=$(json_fields "$input" session_id prompt compact_summary)
case $? in
  0) IFS=$'\x1f' read -r sid prompt summary <<<"$line"; parsed=1 ;;
  3) exit 0 ;;
  *)
    sid=$(printf '%s' "$input" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    prompt=$(printf '%s' "$input" | grep -o '"prompt"[[:space:]]*:[[:space:]]*"[^"]*' | head -1 | sed 's/^"prompt"[[:space:]]*:[[:space:]]*"//')
    # Raw JSON text: a leading newline or tab is still escaped (\n, \t).
    while :; do
      case "$prompt" in
        [[:space:]]*) prompt="${prompt#?}" ;;
        '\n'* | '\r'* | '\t'*) prompt="${prompt#??}" ;;
        *) break ;;
      esac
    done
    ;;
esac
case "$sid" in "" | *[!A-Za-z0-9_-]*) exit 0 ;; esac

dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state"
run_f="$dir/$sid.run"
RUN_TTL_MIN=1440 # keep equal to cap-model.sh
find "$dir" -type f -name '*.run' -mmin +"$RUN_TTL_MIN" -delete 2>/dev/null

handoff_f="$dir/$sid.handoff"

if [ "$mode" = "end" ]; then
  rm -f "$run_f" "$handoff_f" "$dir/$sid.pending" 2>/dev/null
  exit 0
fi

mkdir -p "$dir" 2>/dev/null || exit 0
count_f="$dir/$sid.compacts"
hint_f="$dir/$sid.hinted"

if [ "$mode" = "prompt" ]; then
  if printf '%s' "$prompt" | grep -Eq '^[[:space:]]*/sharaqi(:sharaqi)?([[:space:]]|$)'; then
    : > "$run_f"
    rm -f "$handoff_f" 2>/dev/null
    exit 0
  fi
  [ -f "$run_f" ] && touch "$run_f"
fi

# Handoff check after a compaction in a run. Runs before the hints switch: it is not a hint.
if [ "$mode" = "postcompact" ] && [ -f "$run_f" ]; then
  miss=""
  if [ "$parsed" != 1 ] || [ -z "$summary" ]; then
    miss="unverified"
  else
    printf '%s' "$summary" | grep -Eq 'BASE.{0,60}[0-9a-f]{40}' || miss="BASE"
    printf '%s' "$summary" | grep -Eq 'ROUTE[[:space:]]+track=' || miss="${miss:+$miss }ROUTE"
  fi
  if [ -n "$miss" ]; then
    printf '%s\n' "$miss" > "$handoff_f" 2>/dev/null
  else
    rm -f "$handoff_f" 2>/dev/null
  fi
fi

if [ "$mode" = "prompt" ] && [ -f "$run_f" ] && [ -f "$handoff_f" ]; then
  case "${prompt#"${prompt%%[![:space:]]*}"}" in
    /*) ;; # slash commands (/compact, /context ...) keep the flag for the next real prompt
    *)
      miss=$(head -1 "$handoff_f" 2>/dev/null | tr -cd 'A-Za-z ')
      rm -f "$handoff_f" 2>/dev/null
      if [ "$miss" = "unverified" ]; then
        ctx="sharaqi: the last compaction's summary was not available to the hook, so BASE and the ROUTE line were not checked. Before any edit, confirm both are in the conversation."
        msg='sharaqi: the compaction summary could not be checked for BASE and ROUTE.\n\u0634\u0631\u0627\u0642\u064a: \u0645\u0627 \u0642\u062f\u0631\u062a\u0634 \u0623\u062a\u0623\u0643\u062f \u0625\u0646 \u0645\u0644\u062e\u0635 \u0627\u0644\u0640 compact \u0641\u064a\u0647 BASE \u0648 ROUTE.'
      else
        ctx="sharaqi: the last compaction's summary has no $miss (rule 9 handoff). Before any edit: ROUTE: re-run route.py with the same facts and --floor. BASE: use the tree hash only if it is still in the conversation; never take a new snapshot as BASE (it would include this task's changes); if it is lost, say the review scope is not isolated."
        msg="sharaqi: the compaction summary is missing $miss; the model was told to restore it before editing.\\n\\u0634\\u0631\\u0627\\u0642\\u064a: \\u0645\\u0644\\u062e\\u0635 \\u0627\\u0644\\u0640 compact \\u0646\\u0627\\u0642\\u0635 \\u0641\\u064a\\u0647 $miss\\u060c \\u0648\\u0646\\u0628\\u0651\\u0647\\u062a \\u0627\\u0644\\u0645\\u0648\\u062f\\u064a\\u0644 \\u064a\\u0631\\u062c\\u0651\\u0639\\u0647 \\u0642\\u0628\\u0644 \\u0623\\u064a \\u062a\\u0639\\u062f\\u064a\\u0644."
      fi
      printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' \
        "$msg" "$ctx"
      exit 0
      ;;
  esac
fi

[ "${SHARAQI_NO_HINTS:-0}" = "1" ] && exit 0

if [ "$mode" = "postcompact" ]; then
  find "$dir" -type f \( -name '*.compacts' -o -name '*.hinted' \) -mtime +7 -delete 2>/dev/null
  n=$(cat "$count_f" 2>/dev/null || echo 0)
  echo $((n + 1)) > "$count_f"
  exit 0
fi

# Slash commands (/compact, /clear ...) get no hint.
case "${prompt#"${prompt%%[![:space:]]*}"}" in /*) exit 0 ;; esac

n=$(cat "$count_f" 2>/dev/null || echo 0)
h=$(cat "$hint_f" 2>/dev/null || echo 0)
if [ "$n" -ge 2 ] && [ "$h" -lt "$n" ]; then
  echo "$n" > "$hint_f"
  printf '{"systemMessage":"%s%s%s%s%s"}\n' \
    'sharaqi: this session has been compacted ' \
    "$n" \
    ' times. A new session is cheaper: each compaction costs tokens too. (SHARAQI_NO_HINTS=1 turns this off)\n\u0634\u0631\u0627\u0642\u064a: \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u062f\u064a \u0627\u062a\u0639\u0645\u0644\u0647\u0627 compact ' \
    "$n" \
    ' \u0645\u0631\u0627\u062a. \u0627\u0644\u0623\u0641\u0636\u0644 \u062a\u0641\u062a\u062d session \u062c\u062f\u064a\u062f\u0629\u060c \u0644\u0623\u0646 \u062d\u062a\u0649 \u0627\u0644\u0640 compact \u0646\u0641\u0633\u0647 \u0628\u064a\u0633\u062a\u0647\u0644\u0643 \u062a\u0648\u0643\u0646\u0632.'
fi
exit 0
