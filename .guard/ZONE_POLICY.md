# Zone Policy (Planning -> Development -> Push)

## Goal

Separate product deliverables from local development artifacts and prevent accidental publication.

## Zones

- `public`: can be pushed to GitHub after review.
- `local`: must stay local; never pushed.
- `unclassified`: not allowed. Must be classified before commit/push.

## Mandatory Workflow

1. Planning stage: mark new outputs as `public` or `local`.
2. Development stage: place local artifacts under local prefixes (`dev-local/`, `logs/`, `data/`, etc.).
3. Pre-commit: `scripts/security_check.sh` (includes file-zone audit).
4. Pre-push: `scripts/review_push_guard.sh origin/main`.

## Classification Sources

- Public prefixes: `.guard/public-prefixes.txt`
- Local prefixes: `.guard/local-prefixes.txt`
- Local-only file list: `.guard/local-only-files.txt`

If a file is `unclassified`, update policy files first, then commit.
