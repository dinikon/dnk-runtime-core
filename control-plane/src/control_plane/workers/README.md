# Workers

Reserved for outbox publishing, provisioning, DNS reconciliation, Kubernetes
reconciliation, notification delivery and periodic installation health checks.
Workers use the same application layer as the HTTP API and claim jobs with
retry/backoff and idempotency protection.
