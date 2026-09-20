# Tenant deletion protocol v1

Runtime advertises `deletion_protocol_version: 1` and `owner_deletion_supported: true` in management status. Provisioning
v1 remains supported. Deploy the global migrations through `0005_access_roles` and restart
all API, integration event and control-plane worker processes before Core enables
new deletion requests. Keep the existing management hostname, ingress mTLS and
certificate fingerprint checks; deletion endpoints never accept browser authority.

| Endpoint | Meaning |
|---|---|
| `GET /internal/v1/tenants/{core_id}/deletion-capability/{global_user_id}/` | Current access snapshot and authority check; optional `authorization_basis=owner` is set only by trusted Core |
| `POST /internal/v1/tenant-deletions/` | Authorize and durably accept an irreversible block; `Idempotency-Key` equals operation UUID |
| `GET /internal/v1/tenant-deletions/{operation_id}/` | Current state or minimal completion receipt |
| `POST /internal/v1/tenant-deletions/{operation_id}/purge/` | Separate purge command with core tenant UUID and confirmed version 2 |

Commands fix Core tenant UUID, Runtime tenant UUID when known, hostname, operation,
source and global initiator. User commands default to `authorization_basis=runtime_admin`:
an active local `admin` with the trusted Core issuer/sub is required. Core may instead
send `authorization_basis=owner` after checking its authoritative `Tenant.owner`.
This ownership right survives local demotion, revocation and cloud unlinking; Runtime
still verifies placement and an active/frozen tenant. Browser claims never supply this
basis. Both user paths retain Core's mandatory action-specific identity proof.
The omitted/default admin basis preserves the digest of pre-upgrade accepted commands. Operator source is set
only by Core after checking Django permissions. It can fence an installation that
has not yet reached this Instance. A missing operation (`404`) never proves the
absence of resources. A semantic command hash detects changed retries even after
the original command has been erased. A matching accepted retry does not recheck
the initiator's subsequently changed role.

Acceptance holds the same `cp:tenant` transaction lock as provisioning and the
membership lock used by access changes. It records `deletion_pending`, prevents
further provisioning and changes the local Tenant status in the same transaction.
The schema name is derived from the verified **Runtime** UUID, not the Core UUID.

`TenantGate` uses a session-level PostgreSQL shared advisory lock for each admitted
HTTP handler or background operation, with a fresh Tenant-state check. HTTP UoWs
reuse its checked-out connection; commits inside handlers do not release admission.
The gate spans the complete ASGI response, external calls and worker final commits.
Use direct PostgreSQL connections or session pooling; transaction pooling cannot
preserve these session advisory locks across commits.
New operations fail after acceptance. Management deletion and technical unavailable
responses remain reachable. Unmatched routes still return a technical 404/405.
CLI migration of a named unavailable Tenant is refused; migration enumeration
skips deleting tenants. `freeze` continues to retain its existing semantics and is
not used for deletion.

The SQL-driven deletion worker first acquires the exclusive admission lock. Only
then does it report `blocked`, version 2: existing operations have drained. Busy
locks and unavailable services do not satisfy that condition. The separate purge
command moves to `purging`, version 3. The same worker retries interrupted work;
failure is recorded separately and never restores access.

Purge deletes these exact Redis namespaces for this Runtime UUID:
`session`, `otp_login`, `oidc_state`, `invitation_otp`, and `csrf` for its verified
hosts. Redis failure leaves PostgreSQL intact and blocked. Under the admission,
provisioning and schema migration locks, one PostgreSQL transaction drops the
tenant schema and deletes domains, jobs, inbox/outbox, the Tenant, installation,
provisioning attempts, cloud connection, access projections and delivery outbox.
It records `deleted`, version 4, in that same transaction.

The receipt retains only Core/Runtime UUIDs, operation UUID, command hash, version,
result, completion time and `creation_succeeded`. The latter lets Core preserve
creation quota even when Runtime's successful provisioning response was lost.
The original command, users, names, payload and credentials are erased. Receipts
must survive rollback; the migration intentionally refuses destructive downgrade.
Old provisioning commands are rejected by Core UUID. Messages for a deleted Runtime
UUID are discarded before handlers or inbox payload writes; the console consumer
acks valid obsolete events without logging their payload.

Contracts and synthetic examples live in `docs/contracts/runtime-v1`; regenerate
with `PYTHONPATH=. python scripts/export_runtime_contracts.py` and verify with
`--check`. The focused integration suite is:

```sh
python -m unittest test.test_tenant_deletion test.test_control_plane_runtime
```

Set `TEST_CP_POSTGRES_URL` to an **isolated** asyncpg test database, and
`TEST_DELETION_REDIS_URL` to disposable Redis for namespace cleanup checks.
The suite checks transaction races, all public business routes, background
consumption/publication, real Redis cleanup and a neighboring tenant. The sibling
Control Plane suite can launch `test.deletion_peer` for real cross-project mTLS,
MFA, manual Django Admin purge and retained history; see its `docs/tenant-deletion.md`.

Purge covers current project PostgreSQL/Redis stores. Existing backup and historical
operational-log retention remains unchanged, and already delivered external data
cannot be recalled. Old messages in shared queues are dropped when consumed.


## Role projection and cached capabilities

Core lists never fan out to Instances. The existing access PUT now carries
`role: admin | member | null` alongside `available`; unlinking clears the role.
Role-only changes advance the same per-user sequence and commit with the local
membership change and delivery outbox. Retries retain the exact event payload.

Management capability checks return `access_snapshot` with event ID, version,
availability and role, under the same admission/membership locks as changes.
They repair a stale projection before returning; Core applies snapshots using the
same version boundary as delivered events. The final deletion command always checks
Admin authority again, or accepts Core's authenticated ownership assertion.

`RoleProjectionSync` runs in the existing control-plane worker. Migration
`0005_access_roles` marks old rows unsynchronized; batches of at most 100 reconcile
real bound identities and roles, produce new events, and persist completion. An
attempt timestamp rotates failed work so one failing tenant cannot starve others.
The partial index excludes already synchronized rows. Deleting tenants are excluded
and admission prevents races with purge.

Deploy the compatible Core backend/migration before this Runtime update, then the
new Core frontend. Old Core receivers reject role-bearing events. Until the Instance
advertises Owner support, Core may use the legacy Admin path but cannot assert Owner.
No provisioning protocol bump or new broker/periodic browser poll is required.
