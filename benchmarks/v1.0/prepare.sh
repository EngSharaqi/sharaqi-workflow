#!/bin/bash
# Freeze the plugin of each arm into RUNS before any run. No API call, no cost.
#   usage: RUNS=<dir outside this repo> bash prepare.sh
# plugins/v0.9 : `git archive a05e49d`, the exact tree the v0.9 routing results ran
#                (benchmarks/v0.9/ROUTING-RESULTS.md); its .id is the commit.
# plugins/v1.0 : the current working tree of this repo (tracked and untracked, not ignored;
#                tracked files deleted from the working tree are left out on purpose), as the
#                git tree scripts/snapshot.sh builds; its .id is that tree hash, so the same id
#                means the same files, committed or not. The copy is `git archive <tree>`, so
#                it holds exactly the files the id names.
# Each copy is re-hashed after extraction and must equal its tree, or prepare fails. Every
# step's exit status is checked (no pipeline hides one). Plain Claude Code needs no plugin.
# Refuses a RUNS that exists or is inside the repo.
set -u -o pipefail
B=$(cd "$(dirname "$0")" && pwd); R=$(cd "$B/../.." && pwd)
V09=a05e49d
die() { echo "prepare: $*" >&2; exit 1; }
: "${RUNS:?set RUNS to a new directory outside the repo}"
case "$(cd "$(dirname "$RUNS")" 2>/dev/null && pwd)/" in "$R"/*) die "RUNS is inside the repo" ;; esac
[ -e "$RUNS" ] && die "$RUNS exists; use a new one"
( cd "$B/cases" && shasum -a 256 1 2 3 4 5 6 7a 7b 8 9 10 ) | diff -q - "$B/cases.sha256" >/dev/null \
  || die "case files differ from cases.sha256"

# tree hash of a directory's content (files, modes, symlinks), in a throwaway index
tree_of() {
  local idx; idx=$(mktemp) && rm -f "$idx" || return 1
  GIT_DIR="$R/.git" GIT_WORK_TREE="$1" GIT_INDEX_FILE="$idx" git add -A >/dev/null 2>&1 \
    && GIT_DIR="$R/.git" GIT_WORK_TREE="$1" GIT_INDEX_FILE="$idx" git write-tree
  local s=$?; rm -f "$idx"; return $s
}
freeze() { # <tree-ish> <arm>: archive, extract, check the copy against the tree
  local dir="$RUNS/plugins/$2" tar="$RUNS/plugins/$2.tar" want got
  want=$(git -C "$R" rev-parse --verify -q "$1^{tree}") || die "$2: no tree for $1"
  git -C "$R" archive --format=tar -o "$tar" "$1" || die "$2: git archive failed"
  mkdir -p "$dir" && tar -x -f "$tar" -C "$dir" || die "$2: extracting $tar failed"
  got=$(tree_of "$dir") || die "$2: hashing the copy failed"
  [ "$got" = "$want" ] || die "$2: copy is tree $got, want $want"
  echo "$2 files: $(git -C "$R" ls-tree -r --name-only "$want" | wc -l | tr -d ' ')"
}

mkdir -p "$RUNS/plugins" "$RUNS/out" "$RUNS/records" "$RUNS/work" || die "mkdir $RUNS failed"
freeze "$V09" v0.9
git -C "$R" rev-parse --verify "$V09^{commit}" > "$RUNS/plugins/v0.9.id" || die "v0.9 id"
tree=$(cd "$R" && bash scripts/snapshot.sh) || die "snapshot.sh failed"
[ -n "$tree" ] || die "snapshot.sh printed no tree"
freeze "$tree" v1.0
echo "worktree-tree:$tree" > "$RUNS/plugins/v1.0.id" || die "v1.0 id"
deleted=$(git -C "$R" ls-files --deleted | wc -l | tr -d ' ')
echo "v1.0 tracked files deleted in the working tree, left out: $deleted"
claude --version > "$RUNS/claude-version.txt" || die "claude --version failed"
echo "v0.9 $(cat "$RUNS/plugins/v0.9.id")"
echo "v1.0 $(cat "$RUNS/plugins/v1.0.id")"
echo "claude $(cat "$RUNS/claude-version.txt")"
