# Control Plane contracts

- [`agent-control/openapi.yaml`](agent-control/openapi.yaml): agent bootstrap,
  mTLS lifecycle, heartbeat, long polling and results.
- [`runtime-management/openapi.yaml`](runtime-management/openapi.yaml): signed,
  idempotent Runtime commands and installation inspection.
- [`lifecycle/state-machines.yaml`](lifecycle/state-machines.yaml): canonical
  state and transition catalog.

The OpenAPI files describe target interfaces. The existing Runtime shared-key
tenant endpoint remains a documented implementation gap until the Runtime
provisioning stage.
