# Security checklist

Required in CRITICAL; use any item that applies in the other modes. Check
every item the diff touches and mark the rest n/a. Passing this list lowers
risk but proves nothing: report what was checked, not that the change "is
secure".

- **Injection:** raw or string-built SQL with user input; shell execution with
  user input; `eval`; deserialization of user data; path traversal in file
  paths.
- **Authorization:** every new route or action requires authentication and a
  server-side permission check; no IDOR (an id from the request loads a record
  without checking it belongs to the user or tenant); role checks on the
  server, not only hidden in the UI.
- **Input validation:** server-side validation on every new input; no mass
  assignment of raw request data.
- **Output / XSS:** `v-html`, `innerHTML`, `dangerouslySetInnerHTML`, `{!! !!}`
  or unescaped values in JS or attributes carrying user data.
- **CSRF and sessions:** state-changing requests aren't GET and are
  protected the way the repo protects them; no auth tokens in URLs, and no
  tokens in `localStorage` where the repo uses cookies.
- **Secrets and data exposure:** no keys, passwords or tokens in code, config
  or logs; responses and logs don't leak personal data, hashes or internal
  ids beyond what the screen needs.
- **Files:** uploads validate type and size and are stored outside the public
  root or under generated names; downloads check ownership.
- **Dependencies:** a new package is real, maintained and pinned; there is
  no lockfile churn that wasn't asked for.

Every finding cites `file:line` and an attack scenario: who sends what, and
what they get. Report a secret by location and name only, never its value,
and tell the user it must be rotated: removing it from the code doesn't undo
the leak.
