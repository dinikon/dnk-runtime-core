# ADR-0003: Installation agent protocol and command security

- Status: Accepted
- Date: 2026-07-11

## Context

Cluster and Single/Box installations may be behind NAT and must not expose a
central inbound management port. A compromised transport agent must not be able
to modify Runtime commands.

## Decision

- Every managed environment runs an agent with environment-scoped permissions.
- Agents use one outbound cursor-based long-poll protocol for Cluster and Box.
- Bootstrap uses a one-time HMAC-protected token with a 15-minute TTL.
- After bootstrap, agent-to-Control-Plane authentication uses mTLS.
- Agent certificates live for 30 days and rotate after 20 days.
- Control Plane does not store cluster kubeconfigs or call Kubernetes directly.
- The agent acknowledges commands and reports immutable result digests.

Runtime mutation commands are compact JWS artifacts:

- protected algorithm: `EdDSA` with Ed25519 keys;
- mandatory `kid` and type `dnk-command+jws`;
- audience: `dnk-runtime-management`;
- command TTL: 5 minutes;
- accepted clock skew: 60 seconds;
- claims include command, operation and installation IDs, schema version,
  idempotency key and payload SHA-256.

Runtime validates the signature, key ID, audience, installation ID, expiry and
payload digest. The agent transports the JWS unchanged. Runtime stores the
idempotency result by command ID and key.

## Consequences

- Replayed commands return the stored result and do not repeat side effects.
- A reused idempotency key with a different payload is a conflict.
- Public keys must overlap during rotation so offline installations can catch
  up safely.
- The management contract is command-oriented instead of exposing the Runtime
  persistence model.
