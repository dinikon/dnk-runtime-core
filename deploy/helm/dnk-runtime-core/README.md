# dnk-runtime-core

Umbrella chart for dNiko. Version 0.1.0 includes full Core; Runtime is a future
subpackage. Core consists of Django, Nuxt and Nginx plus optional local PostgreSQL
16 and Redis 7 charts. No third-party chart repositories are required.

All settings are grouped under `core` in `values.yaml`. Both infrastructure
services are embedded by default; set `core.postgresql.enabled=false` and/or
`core.redis.enabled=false` and fill the corresponding `external` connection fields
to use external services. `core.enabled=false` disables the entire Core package.

Before installing, configure application image repositories/tags,
`core.application.server.publicOrigin`, permanent signing/Fernet secrets,
PostgreSQL/Redis credentials and SMTP. Secret fields accept `value` OR
`existingSecret: {name, key}`. No credentials are generated automatically.

Requires Helm 3.19+, Kubernetes 1.25+, a StorageClass or existing PVCs, and accessible
application images. Optional Ingress uses an existing controller and TLS Secret.

```sh
helm upgrade --install dniko ./dnk-runtime-core-0.1.0.tgz \
  --namespace dniko --create-namespace -f my-values.yaml --wait --timeout 10m
```

For detailed image builds, Secret preparation, external connections, upgrades and
troubleshooting, see `deploy/helm/README.md` and `deploy/helm/examples/` in the
source repository. Standalone Core is available as `charts/core` or `core-0.1.0.tgz`.

Backend pods run serialized migrations before startup. PostgreSQL schema `core`
is isolated from runtime schemas. StatefulSet-created PVCs survive uninstall;
reuse the original credentials when reinstalling. Helm rollback does not reverse
schema/data migrations. External Secret changes require restarting affected pods.
