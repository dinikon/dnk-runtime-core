# Control Plane threat model

## Assets and trust boundaries

Protected assets include global identities, sessions, tenant ownership,
installation credentials, command signing keys, provider secret references,
DNS/Kubernetes desired state and audit evidence.

Trust boundaries exist between browser and API, API and providers, Control
Plane and agent, agent and Runtime, agent and Kubernetes, preprod and production,
and the application database and external secret store.

## Threats and required controls

| Area | Threats | Required controls |
| --- | --- | --- |
| Email/Telegram OTP | Enumeration, brute force, replay, delivery spoofing | Uniform responses, keyed hashes, 5-minute TTL, five attempts, resend/rate limits, single-use consume, verified Telegram Gateway responses |
| OAuth linking | State replay, login CSRF, email collision takeover | State, nonce, PKCE, stable provider subject, explicit linking and recent authentication |
| Browser session | Cookie theft, fixation, CSRF | Rotated opaque session, hashed server token, Secure/HttpOnly/SameSite cookie, CSRF token, idle/absolute expiry and revocation |
| Owner transfer | CSRF, stale re-auth, race, recipient substitution | 10-minute re-auth grant, 24-hour acceptance, tenant row lock, membership recheck, atomic owner change and audit |
| Tenant deletion | Accidental/hostile purge, partial cleanup | Explicit confirmation, 30-day reversible state, immutable operation steps, retries and per-system cleanup confirmation |
| Bootstrap | Token theft/replay | HMAC token, 15-minute TTL, single consumption, installation binding, rate limit and audit |
| Agent mTLS | Certificate theft, stale identity, spoofed forwarded headers | 30-day cert, rotation after 20 days, revocation, SAN-to-installation binding, dedicated ingress and header stripping |
| Runtime command | Modification, replay, wrong installation, unknown key | Ed25519 JWS, mandatory kid, 5-minute TTL, 60-second skew, audience/installation checks, payload digest and durable idempotency |
| Provider secrets | DB/log leakage, excessive privileges | External secret references, least-privilege provider tokens, redaction and rotation |
| Kubernetes | Cluster-admin escalation, cross-environment mutation, unsafe delete | Namespace RBAC, separate service accounts/controllers, NetworkPolicy, ownership labels and UID preconditions |
| Environment split | Preprod compromise reaches prod | Separate namespaces, ingress classes/LBs, stores, credentials, zones and explicit accepted-risk monitoring |
| Audit | Tampering or secret leakage | Append-only writer, no application update/delete, redacted allowlist payload and 365-day retention |

## Security invariants

- Client-supplied customer, tenant or installation identifiers are never an
  authorization authority by themselves.
- Runtime validates signed commands independently of agent behavior.
- A failed external call never advances desired state to a confirmed actual
  state.
- Destructive retries use the same command and idempotency identifiers.
- Secrets, OTPs, cookies, private keys and raw provider credentials never appear
  in logs, problem details or audit payloads.

## Residual risks

Preprod and production share one Kubernetes control plane. Namespace and
credential isolation reduce but do not remove the blast radius of a cluster or
cluster-admin compromise. Moving production to a separate cluster remains the
preferred future hardening step.
