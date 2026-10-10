---
name: http-status-interpretation
description: Use when an HTTP health check returns a status code and the user wants it explained - what the code means, who owns the failure, whether to retry, and what to check next.
---

# HTTP Status Interpretation

Turns a raw health-check result into a plain-English explanation and a next action.

## When to use

- A health check (`http_health_check` / `batch_health_check`) returned a status code.
- The user asks "what does 503 mean here?", "is that bad?", "should we retry?"
- Any endpoint probe came back non-2xx.

## Workflow

1. **Parse first, never from memory.** Call `parse_http_status` with the
   `status_code` from the health check, plus `url` and `latency_ms` when you
   have them. Do not hand-write the reason phrase or retry verdict - the tool
   is the source of truth so the demo stays deterministic.
2. **Explain.** Use the table below to turn `failure_owner` + `retryable` into
   an operator-facing explanation. Lead with the one-line verdict.
3. **Recommend one next step.** Exactly one, scoped to who owns the failure.

## Interpretation table

| Signal from tool | What it means operationally | Next step |
|---|---|---|
| `healthy: true` | Endpoint is serving. Still check `latency_band`. | If `slow`/`very slow`, look at dependency latency before declaring all-clear. |
| `failure_owner: client`, `retryable: false` | Our request is wrong or not permitted. Retrying changes nothing. | 401/403 → check auth, token expiry, IP allowlist. 404 → verify the health path still exists after the last deploy. 405 → probe is using the wrong method. |
| `failure_owner: client`, `retryable: true` (408, 429) | Transient client-side condition. | 429 → back off, honour `Retry-After`, check for a noisy caller. 408 → raise probe timeout, check network path. |
| `failure_owner: server`, `retryable: true` | The service accepted a valid request and failed. Most likely a real incident. | 502/504 → suspect upstream or gateway, check backend pool health. 503 → check instance count, restarts, and whether a deploy is in flight. 500 → pull app logs for the exception. |
| `valid: false` | Not a real HTTP code - probe never completed. | Treat as connectivity/DNS/TLS failure, not an application error. |

## Output shape

Keep it to three lines:

```
Verdict:  503 Service Unavailable - the service is up but refusing traffic.
Owner:    Server side. Retry is worth attempting; this is usually transient.
Next:     Check instance health and whether a deployment is currently rolling.
```

## Notes

- `retryable` is about the *status class*, not about whether a retry is wise
  right now. If the same code has repeated across several probes, stop
  retrying and escalate - the condition is not transient.
- A 2xx only proves the health endpoint answered. It does not prove
  dependencies are healthy.
