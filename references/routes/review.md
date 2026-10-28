## Route: review (read-only)
1. Code: one command, the target's diff only (`git diff --stat <range> -- <paths>; git diff
   <range> -- <paths> | head -400`; no target = `git diff HEAD`). Doc: the text or path given.
2. Send it to the ROUTE's reviewer with the prompt `Explicit review · Artifact: code|doc ·
   Target · Requirements` (the user's, or "none given"). If the diff shows a CRITICAL
   trigger the text didn't, re-route with `--critical <trigger>` first.
3. Report the verdict and findings. Change nothing; ask before any fix.
