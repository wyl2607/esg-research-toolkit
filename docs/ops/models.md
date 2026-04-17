# Model Configuration And Health

This project uses a single registry in `core/models.py` for all model purposes:

- `extraction`
- `validation`
- `audit`

## Source Of Truth

Model names are resolved from environment variables in this order:

1. `OPENAI_EXTRACTION_MODEL`
2. `OPENAI_VALIDATION_MODEL`
3. `OPENAI_AUDIT_MODEL`
4. legacy `OPENAI_MODEL` (extraction fallback only)

Each purpose also has default `max_tokens` and ordered fallback candidates.

## Startup Behavior

At app startup the service checks model availability:

- if OpenAI provider listing works, check configured model names against `/v1/models`
- if provider listing is unavailable, use local whitelist fallback
- unknown models emit warnings and do not hard-crash startup

Warning format in logs:

- `model <name> not in provider list for purpose=<purpose>`

## Runtime Health Endpoint

Use `GET /health/models` to inspect:

- configured model per purpose
- `max_tokens`
- fallback list
- availability status
- check source (`provider` or `whitelist`)
- last check timestamp

Use this endpoint in monitoring to catch typo/deprecation drift before it silently breaks audit or extraction pipelines.
