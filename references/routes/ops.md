## Route: ops
Run the operation inline; no plan, no review. Report the command, exit code and the relevant
lines (`| tail -40`). Never call an unrun test passed. `authz=explicit-yes` (commit, push,
work-item write): show what will happen and wait for the user's yes, every time. Commit:
stage only the intended files. Push: no `--force`, no history rewrite. `fix=reroute-coding`:
a fix that edits files re-routes as code. `escalate=ask`: stop and ask.
