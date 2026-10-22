#!/usr/bin/env bash
# Session hygiene hints. Hooks cannot run /compact themselves, so this nudges the user:
#   postcompact : count compactions for this session.
#   prompt      : 2+ compactions in this session -> one hint per new compaction to open a new session.
# Messages are \u-escaped JSON so no shell or console code page can mangle the Arabic.
# State: <config>/sharaqi-state/<session>.{compacts,hinted}

mode="$1"
input=$(cat)

sid=$(printf '%s' "$input" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
[ -z "$sid" ] && exit 0

dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state"
mkdir -p "$dir" 2>/dev/null || exit 0
count_f="$dir/$sid.compacts"
hint_f="$dir/$sid.hinted"

if [ "$mode" = "postcompact" ]; then
  n=$(cat "$count_f" 2>/dev/null || echo 0)
  echo $((n + 1)) > "$count_f"
  exit 0
fi

# Slash commands (/compact, /sharaqi, /clear ...) always pass.
if printf '%s' "$input" | grep -q '"prompt"[[:space:]]*:[[:space:]]*"[[:space:]]*/'; then
  exit 0
fi

n=$(cat "$count_f" 2>/dev/null || echo 0)
h=$(cat "$hint_f" 2>/dev/null || echo 0)
if [ "$n" -ge 2 ] && [ "$h" -lt "$n" ]; then
  echo "$n" > "$hint_f"
  printf '{"systemMessage":"%s%s%s"}\n' \
    '\ud83c\udfbc \u0634\u0631\u0627\u0642\u064a \u0628\u064a\u0642\u0648\u0644\u0643: \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u062f\u064a \u0627\u062a\u0639\u0645\u0644\u0647\u0627 compact ' \
    "$n" \
    ' \u0645\u0631\u0627\u062a. \u0627\u0644\u0623\u0641\u0636\u0644 \u062a\u0641\u062a\u062d session \u062c\u062f\u064a\u062f\u0629\u060c \u0644\u0623\u0646 \u062d\u062a\u0649 \u0627\u0644\u0640 compact \u0646\u0641\u0633\u0647 \u0628\u064a\u0633\u062a\u0647\u0644\u0643 \u062a\u0648\u0643\u0646\u0632.'
fi
exit 0
