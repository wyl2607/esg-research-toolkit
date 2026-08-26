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
- if provider listing is unavailable, availability is `unknown` and the service is degraded
- a local model-name whitelist is not treated as proof that a credential or provider is usable
- unknown or unavailable models emit warnings but do not hard-crash startup

Warning format in logs:

- `model <name> not in provider list for purpose=<purpose>`

## Runtime Health Endpoints

Use public `GET /health/models` for load balancers and public monitoring. It returns only:

- coarse `status` (`ok` or `degraded`)
- `ready` boolean
- per-purpose `available` booleans

Use protected `GET /health/models/details` with the `X-Admin-Token` header for operator diagnostics. It contains configured model names, token budgets, fallbacks, check source, timestamps, and provider error details.

Provider-list failures, including missing or invalid credentials, never report a ready model. The public endpoint contains no provider exception text or routing configuration.
