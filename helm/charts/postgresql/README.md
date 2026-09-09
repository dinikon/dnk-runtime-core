# PostgreSQL dependency

This chart runs one PostgreSQL 16 instance from the official `postgres:16-alpine`
image. It exposes a ClusterIP Service on port 5432 and a separate headless Service
for its StatefulSet. It is intended for the application chart and can also be installed
on its own with `auth.password.value` or `auth.password.existingSecret` supplied.

The application connection hostname is returned by `dnk.postgresql.fullname`.
The default is `<release>-runtime-postgresql`. Inline passwords create
`<fullname>-auth` with key `password`; an existing Secret is referenced directly.
Existing Secrets must reside in the same namespace. Credential values are never
generated automatically.

`persistence.enabled=true` creates an 8Gi ReadWriteOnce claim through the
StatefulSet. `storageClass: null` uses the cluster default; `storageClass: ""`
explicitly leaves the claim without a storage class. Set `existingClaim` to reuse
a prepared PVC. The database lives in its `pgdata` subdirectory. Disabling
persistence uses an ephemeral volume and loses the database on Pod replacement.

Kubernetes retains claims created by `volumeClaimTemplates` after release deletion.
Keep the release name and database credentials when reinstalling against them.
PVC size, storage class, and the StatefulSet claim template cannot be changed by
a normal Helm upgrade. Expand supported PVCs using the cluster's documented
storage procedure, or migrate to a separately prepared `existingClaim`.

The official image initializes `auth.database`, `auth.username`, and the password
only on an empty data directory. Updating the Secret does **not** rotate the
password in an existing database. Rotate database credentials explicitly and
coordinate application and database restarts. Updates to Secrets created by this
chart change the Pod checksum; updates to externally managed Secrets require an
explicit rollout.

The default security context uses Alpine's PostgreSQL UID/GID 70. The container
has a read-only root filesystem with writable data, `/var/run/postgresql`, and
`/tmp` mounts. A different image family may need different security-context values.
This chart does not provide replication, high availability, backups, or TLS.
Use externally managed PostgreSQL when those facilities are required.
