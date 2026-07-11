# Runtime Management API

[`openapi.yaml`](openapi.yaml) is the target OpenAPI 3.1 contract between an
installation agent and Runtime Core. Mutations are compact Ed25519 JWS commands
and are independent from the current legacy `/api/admin/create-tenant` route.

The decoded JWS payload must match one of the typed schemas in the contract.
Runtime stores the command digest and result so identical retries are safe and
a reused idempotency key with a different digest is rejected.
