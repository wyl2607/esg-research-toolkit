These offline response snapshots represent the dashboard API contract from the
unknown-vs-zero fix (issue #133, merged commit
`908a53f573d72a6f79ac2d12434392b7779f450e`). They contain synthetic company data
and regression variants; they were not collected from production.

The replay tests check empty and populated unknown metrics, honest zero, mixed
periods, and responses that incorrectly coerce null to zero or zero to null.
The fingerprint records the issue's merged SHA; deployment checks instead compare
the serving fingerprint to the exact selected checkout SHA, including later
revisions containing the fix.

`scripts/deploy.sh` runs the check after its existing startup health retry window
and sends failure through rollback. It checks only the local backend. Comparisons
reread both dashboard stats and all company pages up to three times, with a
one-second pause between failures, to tolerate concurrent data changes.
The optional public dashboard workflow step checks the
public API fingerprint, complete paginated company records, dashboard averages,
and frontend using the same selected SHA; a failure fails the workflow without
rolling back the deploy. Only SHA/image references are logged.

This HTTP check validates API semantics and frontend availability. Browser
rendering of unavailable labels versus `0.0%`, Cloudflare cache freshness, Alembic
readiness, and actual rollback behavior still require deployment review. No
deployment or production request is needed to run the replay tests.
