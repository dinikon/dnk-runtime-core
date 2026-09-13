# Control Plane v1 implementation validation

Validated locally on 2026-09-13 against this Runtime checkout and the sibling Control Plane checkout. Production tenant creation remains disabled by default. The implementation targets a fresh database; no existing installation was migrated or deleted.

## Completed checks

| Check | Result |
| --- | --- |
| Complete Runtime suite | 257 tests passed, no skips; disposable PostgreSQL, Redis and RabbitMQ, including real-Core interoperability |
| Companion Core suite | 51 tests passed on PostgreSQL, no skips; operation ID mismatch, contract HTTP errors, OIDC and row-lock concurrency |
| Helm | 72 tests passed; management ingress, secret mounts, independent worker credentials, migration gates and NetworkPolicy |
| Console | Type checking, production build and changed-file lint passed; browser checks covered desktop/mobile, invitations, OTP acceptance and cloud-link initiation with a mock API |
| Contract artifacts | Five JSON schemas and nine synthetic examples; generation check and actual-router fixture tests passed |
| Formatting | Black checked 465 Python files; compilation and whitespace checks passed |

The actual Core RuntimeClient sent concurrent provisioning commands through nginx mTLS to Runtime API and RabbitMQ workers backed by PostgreSQL. Both wildcard zones were ready before the first installation; each installed tenant passed its public HTTPS probe. A third zone without a matching certificate remained unavailable. Missing certificates, foreign fingerprints, forged certificate headers, public access to `/internal/`, conflicting payloads and unknown tenant hosts were rejected. Certificate rotation overlap worked.

Abrupt worker termination removed stale readiness. Commands accepted while the worker was down survived API restart and completed after recovery. Saved results and encrypted connections survived restart. PostgreSQL tests cover rollback after owner creation, expired/replaced fencing tokens, missing attempt records, resource reconciliation, duplicate notifications and retry backoff.

Real Core authorization, token and JWKS endpoints were exercised both through a test bridge and over HTTPS. Owner login, key rotation, invitation OTP followed by explicit cloud linking without TenantAccess, and local access revocation passed. The cross-repository bridge uses temporary Core SQLite storage; the separate Core suite above also verifies its PostgreSQL concurrency behavior.

Actual Runtime outbox delivery through nginx mTLS to Core preserved ordering: revoke version 2, late grant version 1, relink version 3, then replay of the same version 3 event. Core retained version 3 and exactly three events; all three Runtime events were acknowledged. No HTTP transport substitute was used for this check.

The exact backend NetworkPolicy rendered from Helm was tested twice with kind 0.29.0, Kubernetes 1.33.1 and Calico 3.30.0. Before applying it, all four clients could reach the backend. Afterward, the selected ingress-controller pod remained allowed while same-namespace, foreign-namespace and incorrectly labelled ingress pods timed out. Both Pod IP and Service paths were checked.

## Reproduction and release boundary

See the [test map](test-map.md), [contract artifacts and access verifier](../contracts/runtime-v1/README.md), and [HTTPS/NetworkPolicy deployment checks](../deployment/control-plane-v1.md). The CI service helper also passed a real startup/connect/cleanup check with its own PostgreSQL databases, Redis and RabbitMQ.

Local HTTPS checks use synthetic names, generated test certificates and process-local DNS mapping. They do not validate a production DNS provider or the target cluster's ingress/CNI configuration. Before enabling `CORE_TENANT_CREATION_ENABLED`, register the real Instance/zones/certificate fingerprints, run the joint flow in both production zones, and verify recovery of the database together with its original encryption key. Disabling new creation must preserve existing installations, credentials and undelivered events.

Test processes, kind clusters, databases, queues and temporary credentials were scoped to this work and cleaned up. No production deployment or feature enablement was performed.
