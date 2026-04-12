# Deployment Guardrails (Universal)

This document is the long-term "do not repeat failures" standard for remote build/deploy tasks.

## 1. Non-negotiable Rules

1. Always run preflight before remote execution.
2. Always use explicit `user@ip` or `user@fqdn`, not local SSH aliases.
3. Always detect Docker compose variant first (`docker compose` vs `docker-compose`).
4. Always use POSIX-safe remote shell syntax.
5. Frontend local probing must include `Host` header.
6. DNS mismatch is warning by default (unless task explicitly requires direct-IP DNS).
7. Any SSH permission/sandbox failure must switch to escalated path immediately.

## 2. Standard Script

Use:

```bash
bash scripts/preflight_safe_exec.sh \
  --target root@192.227.130.69 \
  --remote-dir /opt/esg-research-toolkit \
  --domain esg.meichen.beauty \
  --expected-ip 192.227.130.69 \
  --preflight-only
```

Then execute actions via the same script:

```bash
bash scripts/preflight_safe_exec.sh \
  --target root@192.227.130.69 \
  --remote-dir /opt/esg-research-toolkit \
  --domain esg.meichen.beauty \
  --expected-ip 192.227.130.69 \
  --exec "cd /opt/esg-research-toolkit && {{COMPOSE}} -f docker-compose.prod.yml ps" \
  --exec "curl -sf http://127.0.0.1:8001/health"
```

## 3. Failure Taxonomy (for logs)

- `SSH_BLOCKED_OR_SANDBOX`
- `HOSTNAME_RESOLUTION_FAILURE`
- `AUTH_OR_PERMISSION_DENIED`
- `DOCKER_COMPOSE_VARIANT_MISMATCH`
- `REMOTE_SHELL_NOT_BASH`
- `HOST_HEADER_OR_ROUTE_MISMATCH`
- `NON_JSON_RESPONSE_TO_JQ`
- `UNKNOWN`

## 4. Mandatory Logging

Every deployment run must produce one main log under `logs/` and include:

1. preflight status
2. each command attempt + retry index
3. classified failure reason
4. final status

## 5. Team Enforcement

For any future deployment task (Task 10+ style):

1. preflight pass is a gate
2. parallel subtasks are allowed only after gate pass
3. failed subtasks must retry up to 3 times
4. all subagent logs must be merged into one task log
