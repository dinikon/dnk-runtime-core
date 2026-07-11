# ADR-0005: Authentication and retention policy

- Status: Accepted
- Date: 2026-07-11

## Context

Control Plane supports passwordless identities and destructive ownership and
tenant operations. The initial policy must be explicit before persistence and
provider integrations are added.

## Decision

- Email authentication uses single-use OTP.
- Phone OTP uses the official Telegram Gateway API.
- Google and GitHub use authorization-code flows; account linking never relies
  only on a matching email claim.
- Browser sessions use `HttpOnly`, `Secure`, `SameSite=Lax` cookies and CSRF
  protection.
- A re-authentication grant for destructive actions lasts 10 minutes.
- Owner transfer is two-phase and expires after 24 hours.
- Tenant deletion has a 30-day reversible retention period.
- During deletion retention, tenant login and writes are disabled.
- Security and administrative audit records are retained for at least 365 days.
- OTP codes, sessions, bootstrap tokens and provider credentials are stored only
  as keyed hashes, encrypted envelopes or external secret references.

Default OTP policy is a 5-minute TTL, five confirmation attempts and a
60-second resend cooldown. Provider and IP/account rate limits are applied
without revealing whether an account exists.

## Consequences

- Telegram delivery failures are explicit provider failures; SMS is not an
  implicit fallback in v1.
- Cancelling tenant deletion restores the recorded previous stable state.
- After retention expires, cleanup is irreversible and retries until Runtime,
  DNS and Kubernetes resources confirm deletion.
