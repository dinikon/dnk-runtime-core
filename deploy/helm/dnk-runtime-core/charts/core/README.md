# Core

Standalone chart for Django Core, Nuxt and Nginx gateway, with optional embedded
PostgreSQL 16 and Redis 7. It has no dependency on an umbrella release.

Use the settings documented in `values.yaml` directly, without an outer `core`
key. Set image repositories/tags, `application.server.publicOrigin`, signing and
Fernet secrets, database/cache credentials and SMTP. Each secret uses either
`value` or `existingSecret: {name, key}`. No keys/passwords are generated.

```sh
helm upgrade --install dniko-core ./core-0.1.0.tgz \
  --namespace dniko --create-namespace -f core-values.yaml --wait --timeout 10m
```

`postgresql.enabled` and `redis.enabled` independently select embedded services.
When false, fill their `external` settings; PostgreSQL database/user/password stay
in `postgresql.auth`. Redis supports a full URL Secret for TLS/ACL connections.

`ingress.enabled` publishes the gateway through an existing controller/TLS Secret.
The HTTPS domain comes from `application.server.publicOrigin`. Preserve trusted
forwarded headers and configure `application.server.trustedProxyCount` for your
proxy chain (default two: Ingress + gateway).

Backend initContainers serialize schema preparation and migrations on one
PostgreSQL session. Direct or session-pooled PostgreSQL is required. Set
`migrations.enabled=false` only when migrations are managed separately.
The wait timeout bounds database/lock acquisition, not migration execution.

StatefulSet-created PVCs survive uninstall. Keep the original credentials for
reinstallation; values do not rotate passwords inside existing PostgreSQL data.
Upgrades need compatible migrations; Helm rollback does not reverse database
changes. External Secret content changes need workload restarts.

Full operational instructions and example values are in `deploy/helm/README.md`
and `deploy/helm/examples/` in the source repository. Embedded service details are
also documented in the PostgreSQL and Redis child chart READMEs.
