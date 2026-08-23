# TODO

## Commit the pending OPC UA mapper work

The working tree has a large amount of finished, tested work that has never
been committed to git: the entire Python OPC UA <-> AutomationML bidirectional
mapper (`src/automationml/opcua*.py`), its test suites, the 145-case mapper
comparison corpus, the governance docs (mapping profile decision, integration
audit, research report, comparison test plan, review checklist), and CI/repo
governance files. `git status --short` in this repo shows the full list.

Blocked on: this machine has no git author identity configured
(`user.name` / `user.email`), so `git commit` fails with "Author identity
unknown". Set it (locally, in this repo, is enough - no need for `--global`)
before committing:

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
```

Once that's set, everything currently in the working tree was reviewed (no
secrets, no unexpected binaries, `.gitignore` change is just adding
`.ipynb_checkpoints/`) and is ready to `git add -A && git commit`. This is a
**local commit only** - nothing here pushes to GitHub or any remote; that's
a separate decision for whenever you're ready.

Also still open: `docs/opcua-mapping-review-checklist.md` is awaiting
independent domain-expert sign-off on the mapping oracle itself.
