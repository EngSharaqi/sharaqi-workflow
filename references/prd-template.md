# PRD — <title>

> Run: <run folder> · Repo: <repo> · Base: <sha> · Date: <YYYY-MM-DD>

## 1. Goal
One or two sentences: what the user can do after this that they cannot do now.

## 2. Out of scope
Bullets. Everything a builder might be tempted to "also fix".

## 3. Users and roles
Who triggers this, which roles/permissions are involved, who must NOT get access.

## 4. Current behaviour (evidence)
What happens today, with `file:line` for each claim. No claim without a location.

## 5. Required behaviour
Numbered rules. Each rule is testable and has one meaning. Write the edge cases
explicitly: empty, null, duplicate, unauthorised, RTL/Arabic text, large lists.

## 6. Acceptance criteria
`AC-1 … AC-n`, each Given / When / Then. The reviewer checks these one by one.

## 7. Data and contracts
Tables/columns touched, migrations (yes/no, reversible?), request/response shapes,
events, config keys, translation keys (en + ar).

## 8. Conventions to follow
Named examples in this repo to copy (`path` of the sibling file), naming, error
handling, where validation lives, how permissions are checked.

## 9. Risks
What could break elsewhere, with the file that depends on the changed code.

## 10. Decisions
Every choice made while planning, with the reason. Questions answered by the user
go here with the date. **Open questions section must be empty before build.**
