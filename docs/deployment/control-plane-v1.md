# Runtime v1 deployment

The Runtime integration is disabled by default (`CONTROL_PLANE__ENABLED=false`).
Core keeps `CORE_TENANT_CREATION_ENABLED=false` until joint acceptance. Runtime does
not change Core settings or DNS records.

## Database and worker lifecycle

Start with an empty PostgreSQL database. Run `dnk-manage database upgrade` before
starting API or workers. This installs `migrations/global` and upgrades every
registered tenant through the unchanged `migrations/tenant` track. Both use the
same deployment transaction and advisory lock. `dnk-manage database check`
validates the installed public revision without DDL. API startup now checks this
revision and never invokes `create_all`.

The public baseline does not adopt an unversioned database. Such a deployment
fails without stamping or deleting existing tables. There is no reset command or
automatic downgrade. Preserve databases and tenant schemas on application rollback.

Helm runs the existing migration Job and deployment-token gate before API and
workers. The migration process has its own ConfigMap with integration disabled and
does not mount encryption/private-key material. The lifecycle deployment runs
`python -m src.modules.control_plane.worker`; its health probe runs the same module
with `--healthcheck`. PostgreSQL attempts, resource records, fencing tokens, delivery
outbox and observations are authoritative. Broker messages only wake UUID work.

Use an independent RabbitMQ user and non-default vhost for provisioning/access,
even when reusing a RabbitMQ server inside this Runtime cluster. Grant that user
configure/write/read only within its vhost. Provide its encoded URL through
`controlPlane.rabbitmqUrl.existingSecret`. It must not be Core's broker or the
ordinary integration-event user/vhost. The queues are `dnk.runtime.installation`
and `dnk.runtime.access`. Helm does not create external RabbitMQ users/vhosts.
Compose's optional integration overlay creates a separate local RabbitMQ service.

## Credentials and trust

Configure `controlPlane.publicOrigin` and `managementOrigin` as exact trusted Core
HTTPS origins. `managementHost` is the distinct Runtime management hostname.
`instanceId` is the UUID registered in Core. `allowedCoreFingerprints` holds
normalized SHA-256 leaf-certificate fingerprints; include both old and new entries
during rotation. Register the Runtime outbound client fingerprint in Core as well.

Create `controlPlane.credentialsSecret` with these keys:

| Key | Purpose |
| --- | --- |
| `encryption.key` | Persistent URL-safe base64 Fernet key for OIDC credentials and accepted commands |
| `tls.crt` | Runtime Instance outbound mTLS certificate |
| `tls.key` | Runtime Instance outbound private key |
| `ca.crt` | CA bundle for outbound Core HTTPS |

The chart mounts that Secret read-only at `/var/run/dnk/control-plane`. Store the
key with recoverable backups; recreating it destroys access to encrypted OIDC
connections. Do not generate a new key per deployment. Set either
`CONTROL_PLANE__SECRET_ENCRYPTION_KEY` or `CONTROL_PLANE__ENCRYPTION_KEY_PATH` for
non-Helm deployments, never both. Certificates/key files must be readable by the
configured container user (chart default root with mode 0400).

`controlPlane.clientCaSecret` is a separate existing Secret containing `ca.crt`
for Core client verification by the management ingress. Its TLS server certificate
is configured independently via `controlPlane.ingress.tls`.

The management ingress exposes only `/internal/v1/`, requires a valid client
certificate, and forwards the verified leaf certificate. The Runtime then verifies
the original socket peer, exact management Host, successful ingress verification
and allowed fingerprint. Uvicorn uses `--no-proxy-headers`; the application owns
proxy trust. `trustedProxyNetworks` must describe actual ingress source addresses,
never `0.0.0.0/0` or `::/0`.

NetworkPolicy permits backend/frontend connections only from the selected ingress
namespace and controller pods. Actual enforcement is covered locally by the
kind/Calico check below. Adapt both selectors to the target cluster and verify
that its production CNI enforces NetworkPolicy as well. Direct backend bypass, forged forwarding
headers, wrong client identity and missing certificate must all fail. Keep the
management DNS route direct to the mTLS terminator. Public ingress access logging
is disabled so authorization codes and invitation query tokens are not recorded.

## Zones and readiness

List every zone in `allowedBaseDomains` and its wildcard in `ingress.hosts`.
Supply a public certificate covering that list or an operator-owned cert-manager
issuer capable of issuing it. Runtime never manages a DNS provider. The chart
routes `/api` and both `/.well-known/dnk/tenant-ready` and
`/.well-known/dnk/instance-routing` to the backend without rewriting paths.

Set `ingressProbeAddress` to the reachable public ingress/LB address with port.
The worker probes that address with SNI/Host
`dnk-probe-<instance_uuid_without_hyphens>.<zone>` and validates TLS plus the
expected Runtime response. These names do not require a Tenant or prior DNS
allocation. The Core public tenant probe separately validates the real tenant DNS.
For a private test CA, set `SSL_CERT_FILE` for the worker's public-ingress verifier.

Worker heartbeat verifies both its RabbitMQ connection and the local Redis auth
store every 10 seconds, with TTL 30 seconds. These are bounded read-only checks;
unavailable Redis also makes tenant readiness fail, without any Core request.
Zone observations run
every 30 seconds with TTL 60 seconds. Status reads persisted facts quickly; a
stopped worker, stale observation or missing certificate removes readiness.
Installation uses a 180-second lease and a 120-second step timeout. Dispatch runs
every 5 seconds, reconciliation every 30 seconds, and outbound requests are bounded
to 10 seconds. Access retries use backoff/jitter capped at 300 seconds; contract
failures remain stored for operator reconciliation.

After correcting an identity/contract problem, retry a blocked delivery with
`python -m src.modules.control_plane.worker --retry-event <event-uuid>`. It retains
the original event identity, payload and version. To inspect/reconcile an uncertain
installation, run `python -m src.modules.control_plane.worker --reconcile-attempt
<attempt-uuid>`; this uses the same attempt and never allocates a replacement over
unknown resources. Neither command deletes tenant data.

Tenant readiness requires committed local resources and decryptable credentials.
It never obtains Core tokens. Keep Core token availability out of the placement
and public-readiness path to avoid activation deadlock. Metrics are available to
authorized mTLS scrapers at `/internal/v1/metrics/`; configure the scraper's Core
identity certificate and Runtime CA, never expose that path on tenant ingress.

## Local Compose acceptance

Copy `temaplate.dev.env` to a private `.env`, set the complete integration settings
and `CONTROL_PLANE_SECRET_DIRECTORY`, and use Docker Compose 2.24.4 or newer:

```sh
docker compose -f docker-compose.yml -f docker-compose.control-plane.yml up --build
```

The credential directory additionally contains `server.crt`/`server.key`, covering
the management host and both zone wildcards, plus `core-client-ca.crt`. Set
`RUNTIME_TENANT_HOSTS` to space-separated wildcard names. Set the independent broker
URL to the `provisioning-rabbitmq` service, with the configured username/password
and `/runtime-provisioning` vhost. Escape credentials as URL components.
The overlay removes exposed API/frontend ports; only nginx exposes HTTPS. The
dedicated ingress network uses `172.30.66.0/24` and trusts nginx at `.2/32`.

Before enabling Core creation, verify fresh Instance status in two zones, real
provisioning through Core RuntimeClient, public readiness, Owner cloud login, OTP
invitation acceptance/linking, immediate revoke, duplicate/out-of-order access
events, and recovery after API/worker/broker restarts. A zone without valid TLS
must stay unavailable. Manifests/unit tests alone do not prove mTLS or routing.

## Reproduce the local HTTPS acceptance test

Install this checkout's dependencies and those of the sibling Core checkout.
Make a local `nginx:1.27-alpine` image available to Docker; the harness uses
`--pull=never`. Point the following variables to isolated test PostgreSQL,
RabbitMQ (dedicated user/vhost) and Redis services, then run:

```sh
export DNK_TEST_DATABASE_URL='postgresql://test-user:test-password@127.0.0.1:55439/test-admin'
export DNK_TEST_RABBITMQ_URL='amqp://test-user:test-password@127.0.0.1:56739/runtime-testing'
export DNK_TEST_REDIS_URL='redis://127.0.0.1:56389/12'
.venv/bin/python test/integration/runtime_https.py \
  --core-repository ../dnk-control-plane \
  --output /tmp/runtime-https-result.json
```

The PostgreSQL test account must be able to create/drop its own temporary database.
The harness generates temporary CA/client/server certificates, allocates local
ports, creates a unique database and queues, runs the actual Core RuntimeClient
over nginx mTLS and starts actual Runtime API/workers. It verifies both wildcard
zones, a missing-certificate zone, certificate rejection and rotation, concurrent
replays, saved results, worker heartbeat expiry and recovery after abrupt worker
termination/API restart. It edits neither system hosts nor trust stores. Only
its own processes, container, database, queues and temporary secret directory are
removed afterward; the optional JSON output has no credentials.

## Reproduce Kubernetes network isolation

The HTTPS harness above does not exercise a Kubernetes CNI. Run this separate
acceptance check with Docker, Helm, kubectl and an official `kind` executable:

```sh
.venv/bin/python test/integration/network_policy.py \
  --kind /path/to/kind \
  --output /tmp/runtime-network-policy-result.json
```

The script creates a uniquely named cluster with Kubernetes `v1.33.1` and Calico
`v3.30.0`, renders the actual backend NetworkPolicy from this chart, and establishes
successful access from every test source before applying it. After application,
only a controller-labelled pod in the ingress namespace may reach the backend;
a pod in the Runtime namespace, a controller-labelled pod in another namespace,
and an incorrectly labelled pod in the ingress namespace must time out. Both
Service and direct Pod IP paths are tested. The check uses a small HTTP backend
with the chart's exact target labels, separately from application authentication.

Container images and the official Calico manifest require network access unless
cached. `--calico-manifest /path/to/calico.yaml` accepts a previously downloaded
manifest; image versions can also be overridden explicitly. The script uses its
own temporary kubeconfig and deletes only its own cluster on success or failure.
It never selects an existing cluster or changes the user's Kubernetes context.
The JSON result includes the applied policy and before/after connectivity evidence.
