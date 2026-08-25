# Disclosure Fetch Egress Policy

Automatic redirects are disabled for disclosure source fetching. Each redirect destination is parsed, resolved, and checked before another request is sent.

The fetch policy is:

- HTTPS only with the default port 443 in normal deployments.
- HTTP is allowed only when `ESG_LOCAL_FETCH_TEST_MODE=1` and `APP_ENV` is a local/test environment.
- Hostnames resolving to private, loopback, link-local, reserved, unspecified, multicast, IPv4-mapped IPv6, or known cloud metadata ranges are rejected.
- DNS resolution is repeated for every redirect hop.
- At most five redirects are followed.
- Response bodies are streamed and capped at 25 MiB.
- `httpx.Client` uses `follow_redirects=False` and `trust_env=False`; ambient proxy variables are not used.

Rejections are recorded with a sanitized scheme/host/port label and an exception type, never the full source URL or provider response.
