# Engineering Memory (Repo Safety)

## Permanent Rule

- Do not push local-only files to remote branches.
- Do not commit conversational/non-engineering prose (for example: sleep/good-night style text, personal contact blocks).
- Treat `SECURITY.md` as local-only unless there is explicit approval to publish changes.

## Mandatory Push Review

Before each push:

```bash
scripts/review_push_guard.sh origin/main
```

If the guard fails, fix findings first. Do not bypass silently.
