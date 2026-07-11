# ADR-0004: Kubernetes routing and environment isolation

- Status: Accepted
- Date: 2026-07-11

## Context

Preprod and production initially share one Kubernetes cluster. Tenant domains
need routing and cert-manager certificates without giving Control Plane or an
agent cluster-admin access.

## Decision

- Routing uses `networking.k8s.io/v1` `Ingress`.
- The supported first controller is `ingress-nginx`.
- Preprod and production use distinct namespaces, service accounts, agents,
  ingress controllers/classes, load balancers, databases, Redis/brokers,
  secrets and DNS zones.
- Ingress classes are `nginx-preprod` and `nginx-prod`.
- cert-manager uses separate `letsencrypt-staging` and
  `letsencrypt-production` `ClusterIssuer` references.
- Agent RBAC is limited to approved resource kinds and namespaces for its own
  environment.
- Managed resources require deterministic names and ownership labels. The
  agent cannot delete resources without matching ownership identity and UID.
- Agent mTLS terminates on a dedicated ingress. Verified certificate identity
  headers are accepted only from ingress-nginx over a NetworkPolicy-protected
  path; client-supplied copies are stripped.

## Consequences

- Namespace isolation is an accepted risk and is not equivalent to separate
  clusters.
- A future move to separate clusters does not change Control Plane domain or
  agent contracts.
- Gateway API support requires a separate adapter and ADR.
