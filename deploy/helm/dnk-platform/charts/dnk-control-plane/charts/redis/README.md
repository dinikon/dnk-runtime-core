# Redis dependency

This chart runs one Redis 7 instance from the official `redis:7-alpine` image.
It exposes a ClusterIP Service on port 6379 and a separate headless Service for
its StatefulSet. It is intended for the application chart and can also be installed on
its own with `auth.password.value` or `auth.password.existingSecret` supplied.

The application connection hostname is returned by `dnk.redis.fullname`. The
default is `<release>-control-plane-redis`. Inline passwords create `<fullname>-auth` with
key `password`; an existing Secret is referenced directly. Existing Secrets must
reside in the same namespace. Credential values are never generated automatically.

Redis requires authentication for the default user. The password is exposed to
the container through `REDISCLI_AUTH`, so local `redis-cli` commands and health
probes authenticate automatically. At startup, the entry command hashes the
password with SHA-256 and writes an ACL containing only its hexadecimal digest
into a private temporary file. Quotes, newlines, and shell syntax in a password
remain literal bytes; the password is not inserted into shell source, Redis
configuration, or process arguments.

Append-only persistence (AOF) is enabled. `persistence.enabled=true` creates a
1Gi ReadWriteOnce claim through the StatefulSet. `storageClass: null` uses the
cluster default; `storageClass: ""` explicitly leaves the claim without a storage
class. Set `existingClaim` to reuse a prepared PVC. Disabling persistence uses an
ephemeral volume and loses Redis data on Pod replacement.

Kubernetes retains claims created by `volumeClaimTemplates` after release
deletion. Keep the release name when reinstalling against them. PVC size, storage
class, and the StatefulSet claim template cannot be changed by a normal Helm
upgrade. Expand supported PVCs using the cluster's documented storage procedure,
or migrate to a separately prepared `existingClaim`.

The password is loaded at startup. Changes to chart-created Secrets update the
Pod checksum; changes to externally managed Secrets require an explicit rollout.
Coordinate password changes with the application backend. The default image has 16
logical databases, numbered 0–15; Control Plane uses database 1 by default.

The default security context uses Alpine's Redis UID 999 / GID 1000. The container
has a read-only root filesystem with writable `/data` and `/tmp` mounts. A
different image family may need different security-context values. This chart
does not provide Redis Sentinel, clustering, backups, or TLS. Use externally
managed Redis when those facilities are required.
