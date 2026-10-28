#!/usr/bin/env bash
# Print a git tree hash of the working tree as it is now: tracked files with their unstaged
# edits, plus untracked files that .gitignore doesn't ignore. The real index, HEAD, refs,
# stash and the files themselves are never touched: the snapshot is built in a throwaway copy
# of the index, which is deleted on exit. Its only trace is unreferenced objects in
# .git/objects, which `git gc` removes.
#   usage: bash scripts/snapshot.sh            -> <tree hash>
# Review scope of a task: BASE=snapshot at the start, AFTER=snapshot now, then
#   git diff --stat BASE AFTER; git diff BASE AFTER
# which holds only the task's own hunks and new files, even inside files that were already
# dirty. Exit 2 outside a git work tree.

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "snapshot: not a git work tree" >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)" || exit 2

real=$(git rev-parse --git-path index)
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT
if [ -f "$real" ]; then cp "$real" "$tmp"; else rm -f "$tmp"; fi

GIT_INDEX_FILE="$tmp" git add -A >/dev/null 2>&1 || { echo "snapshot: git add failed" >&2; exit 1; }
GIT_INDEX_FILE="$tmp" git write-tree
