# Sourced by the hooks: read fields from hook JSON with a real parser.
#   json_fields <json> <dotted.path>...
# prints the fields on one line, separated by \x1f (missing or null -> empty; objects as JSON
# text; newlines inside a value become spaces). Returns 3 if the input isn't a JSON object,
# 4 if no parser is available or python fails for another reason (the caller falls back to
# text matching). Parser: jq, else python3, else python.
# SHARAQI_JSON_PARSER=jq|python3|python|none forces one (the tests use it).

json_parser() {
  local p
  case "${SHARAQI_JSON_PARSER:-}" in
    none) return 4 ;;
    jq | python3 | python) command -v "$SHARAQI_JSON_PARSER" >/dev/null 2>&1 && echo "$SHARAQI_JSON_PARSER" && return 0; return 4 ;;
  esac
  for p in jq python3 python; do
    command -v "$p" >/dev/null 2>&1 && echo "$p" && return 0
  done
  return 4
}

json_fields() {
  local json="$1" p f="" x
  shift
  p=$(json_parser) || return 4
  if [ "$p" = jq ]; then
    for x in "$@"; do
      f="$f${f:+, }((try getpath([\"${x//./\",\"}\"]) catch null) // \"\" | if type == \"string\" then . else tojson end | gsub(\"[\\r\\n]\"; \" \"))"
    done
    printf '%s' "$json" | jq -er "if type == \"object\" then [$f] | join(\"\\u001f\") else error end" 2>/dev/null || return 3
  else
    printf '%s' "$json" | "$p" -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    sys.exit(3)
if not isinstance(d, dict):
    sys.exit(3)
out = []
for path in sys.argv[1:]:
    v = d
    for k in path.split("."):
        v = v.get(k) if isinstance(v, dict) else None
    if v is None or v is False:
        v = ""
    elif not isinstance(v, str):
        v = json.dumps(v)
    out.append(v.replace("\r", " ").replace("\n", " "))
print("\x1f".join(out))
' "$@" 2>/dev/null
    case $? in 0) ;; 3) return 3 ;; *) return 4 ;; esac
  fi
}
