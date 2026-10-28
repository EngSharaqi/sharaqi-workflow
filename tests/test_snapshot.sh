#!/usr/bin/env bash
# Tests for scripts/snapshot.sh: the real index and existing work stay untouched, and the
# BASE..AFTER diff holds only the task's own changes.
# usage: bash tests/test_snapshot.sh
root="$(cd "$(dirname "$0")/.." && pwd)"
snap="$root/scripts/snapshot.sh"
fail=0
pass=0
tmp=$(mktemp -d)

check() { # name expected actual
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "FAIL: $1 (expected $2, got $3)"; fi
}

fp() { # fingerprint of everything the user owns in the repo
  { shasum .git/index; git diff --cached; git diff; git status --porcelain --ignored; cat ignored.log; } | git hash-object --stdin
}

cd "$tmp" || exit 1
git init -q .
printf 'a1\na2\na3\na4\na5\na6\na7\na8\n' > a
echo b > b
echo '*.log' > .gitignore
git add . && git -c user.name=t -c user.email=t@t commit -qm init

# --- pre-existing work: staged edit, unstaged edit, untracked file, ignored file
echo b-staged >> b && git add b
sed 's/a1/A1-pre/' a > a.t && mv a.t a
echo pre > untracked_pre
echo ig > ignored.log
before=$(fp)
stash_before=$(git stash list | wc -l)

base=$(bash "$snap")
check "snapshot prints a tree" "tree" "$(git cat-file -t "$base" 2>/dev/null)"
check "snapshot leaves index and files untouched" "$before" "$(fp)"
check "no task changes: empty scope" "" "$(git diff --name-only "$base" "$(bash "$snap")")"

# --- task: edit another hunk of an already dirty file, add a file
sed 's/a8/A8-task/' a > a.t && mv a.t a
echo new > task_new
after=$(bash "$snap")
check "scope: only task files" "a task_new" "$(git diff --name-only "$base" "$after" | tr '\n' ' ' | sed 's/ $//')"
check "scope: pre-existing hunk excluded" "-a8 +A8-task" \
  "$(git diff "$base" "$after" -- a | grep '^[-+][^-+]' | tr '\n' ' ' | sed 's/ $//')"
check "scope: ignored file excluded" "" "$(git diff --name-only "$base" "$after" -- ignored.log)"
check "stash untouched" "$stash_before" "$(git stash list | wc -l)"
check "staged diff untouched" "b" "$(git diff --cached --name-only)"

# --- from a subdirectory: same tree
mkdir -p sub && echo s > sub/f
top=$(bash "$snap")
check "subdirectory: same tree as top level" "$top" "$(cd sub && bash "$snap")"

# --- no index yet (fresh repo with files)
mkdir "$tmp/fresh" && cd "$tmp/fresh" && git init -q . && echo x > x
check "fresh repo: tree with the file" "x" "$(git ls-tree --name-only "$(bash "$snap")")"
check "fresh repo: no index created" "no" "$([ -e .git/index ] && echo yes || echo no)"

# --- not a git repo
plain=$(mktemp -d) && cd "$plain"
bash "$snap" >/dev/null 2>&1
check "not a repo: exit 2" "2" "$?"

cd / && rm -rf "$tmp" "$plain"
echo "snapshot: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
