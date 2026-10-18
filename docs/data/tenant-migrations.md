# Tenant migrations

The revision history below describes the current code. The current
[Catalog simplification](../plan/catalog.md) requires recreated tenant schemas
and onboarding; no Catalog data migration is provided.

## Ownership

Alembic owns both global and static tenant tables. Global revisions live in `migrations/global/`; run `dnk-manage database upgrade` before starting API and workers. Startup only checks their version. The fresh global baseline refuses an existing unversioned database rather than adopting or deleting its tables. No dynamic object subsystem is active.

Global revision `0006_reference_data` adds the four public reference catalogs, country/time-zone links and synchronization state. It also permits `scheduled_jobs.tenant_id=NULL` for global jobs. After upgrading and before exposing the reference-data GET routes, run `dnk-manage reference-data sync --dataset all`; subsequent refreshes are registered by the shared jobs worker every seven days. The catalogs do not require tenant migrations.

Global head `0007_remove_channel_jobs` deletes only rows whose exact
`job_type` is `channels.publication_import` from `public.scheduled_jobs`,
in every status and for every tenant. Other jobs and shared resources remain.
Stop all old API and worker processes before applying this revision; otherwise
an old process can recreate jobs. Downgrade does not restore deleted jobs.

Tenant models use `TenantBase` with logical schema `tenant`. `src/modules/tenant_persistence.py` registers model imports and historical table names. Retain historical names after removing a model so autogenerate can detect its removal. Unregistered legacy tables are excluded from reflection candidates; they are never adopted or deleted automatically.

## Schema identity

`TenantSchemaNaming` builds `SCHEMA_PREFIX + tenant_id.uuid.hex`. `SCHEMA_PREFIX` defaults to `dnk_` and must remain stable for an installation. Changing it requires an explicit schema relocation; there is no datasource metadata lookup or fallback schema discovery.

## New tenants

`CreateTenantHandler` validates the requested base currency against active Reference Data before creating resources, creates the tenant and primary domain, invokes the tenancy-owned bootstrap port, initializes `tenant_currency_settings` in that schema, then provisions the administrator and email and initializes Catalog through its public Application facade. Catalog writes use that administrator UUID for audit and generate separate UUIDv7 identifiers for Default and its title/body blocks. Repeated initialization preserves a complete existing schema and rejects an incomplete one. The currency-settings migration seeds existing schemas with UAH; new onboarding replaces that initial value with the validated selection in the same transaction. `AlembicTenantSchemaBootstrapAdapter` uses the same UoW session to acquire a schema lock, reject an existing schema, create it and upgrade to `head`.

The adapter and migrator never commit. PostgreSQL DDL, Alembic version writes, tenant, domain, owner identity and cloud connection writes commit together. Any failure rolls everything back. The Control Plane installer records accepted-command errors in its durable attempt state and reconciles actual resources before declaring absence.

## Revisions

Files live in `migrations/tenant/versions/`; each tenant schema has its own `alembic_version`. The first revision is
`0001_warehouses`; `0002_identity_users` adds tenant-local `users` and `user_emails` with a same-schema foreign key.
`0003_identity_cloud_access` adds roles, session epochs, cloud identities, invitations and live normalized-email
uniqueness. Revisions `0004` through `0006` add partner price-list ingestion and management. Revision
`0007_crm_contacts_companies` adds the static CRM `contacts` and `companies` tables, validation checks and stable-sort
indexes. Revision `0008_contact_points` creates the tenant-local directory, bindings and labels with same-schema
foreign keys. It seeds six labels with fixed identifiers and timestamps; seed actors are null. Upgrade existing
tenants before running code that reads the new CRM arrays. Existing CRM rows are preserved with empty arrays.
Revision `0011_inventory_skus`, after `0010_crm_company_legal_name`, adds the tenant-local
Inventory `skus` directory with unique codes and audit fields; this revision remains
in the migration history after removal of the module.
Catalog uses a rewritten `0023_catalog_item` baseline after
`0022_tenant_currency_settings`. It creates `catalog_item`, normalized content/media
and ProductType/block tables. Roles simple/variable/variant and their parent
constraints remain in SQL; attributes, options, classification, metadata and
selections/defaults have no runtime models or fresh-schema tables.
The baseline contains no Catalog seed. `CatalogProvisioningFacade` creates the
system type `default` and blocks `title` (required text) and `body` (optional rich text)
only during tenant onboarding. Queries and item creation never seed missing data.

Revision identity remains `0023_catalog_item`; `0024_currency_exchange_rates`
still depends on it. Revision `0026_catalog_attribute_ids` is removed;
`0027_remove_channels` now follows `0025_user_display_currency`. One tenant head
remains. Unrelated module migrations are preserved. Downgrade to 0022 removes
only Catalog; upgrade recreates its empty structure without system values.
Historical table ownership names remain for autogenerate.

This change requires recreated tenant schemas and repeated onboarding. It does
not transfer existing Catalog data. Deploy backend and Console together. Schema
reset is an operational rollout step; migration commands do not drop the database.

Revision `0016_remove_inventory`, after `0014_channel_publications`, retires
the Inventory schema; its own upgrade/downgrade behavior is preserved.
Catalog no longer references Inventory SKUs or warehouses.

Tenant head `0027_remove_channels`, after `0025_user_display_currency`, drops
`channel_publications`, `channel_publication_import_runs`, then `channels`,
without CASCADE. It removes stored credentials, observed publications and import
progress. The whole tenant migration rolls back if an unexpected dependency
blocks a drop. Other module tables remain. Downgrade recreates the empty
historical structure, including foreign keys, checks and indexes, through
`0013_channels` and `0014_channel_publications`; it cannot recover deleted data.
Both historical revisions and their table ownership names stay in the project.
Fresh tenants also reach this head and have no Channels tables.

## Transition from shared identity tables

The shared-users transition requires recreating development/test databases and repeating tenant onboarding. `0002_identity_users` creates empty tables; it does not migrate or delete records in `public.users` or `public.user_emails`. Startup no longer creates those shared tables, and runtime identity access has no legacy fallback. Running `upgrade --all` on an old installation creates the new tables but does not make its old users available.

## Existing tenants

```sh
dnk-manage tenant-migrations current <tenant_id>
dnk-manage tenant-migrations current --all
dnk-manage tenant-migrations upgrade <tenant_id>
dnk-manage tenant-migrations upgrade --all
```

Commands verify tenant existence and require its calculated schema to exist. They never create missing schemas. `current` reports `base` for an unversioned schema without creating `alembic_version`.

`--all` processes tenants sequentially, one transaction per tenant. It continues after failures, retains successful upgrades and exits 2 if any tenant failed. Re-running upgrades is safe. No mass upgrade runs at application startup.

## Authoring migrations

```sh
dnk-manage tenant-migrations revision --autogenerate --tenant-id <tenant_id> -m "Add a warehouse field"
```

Use a development tenant already at the current head. Change the ORM model, generate a candidate revision, review it and then apply it. Include newly managed table names in the registration history; do not delete names when retiring tables.

Autogenerate uses a separate engine and a schema-free metadata copy, rewriting tenant foreign keys to the same copy. The application's metadata and engine dialect are not modified. SQL types and server defaults are compared; shared `StringUUID` renders as `sa.UUID()` to keep revisions independent of application decorators.

Review renames, destructive changes and CHECK expressions manually. Longer warehouse cycles remain outside this version's guarantees. Downgrade is available through the internal migrator/Alembic environment for reviewed operations and tests; no bulk downgrade command is exposed.

## Verification and deployment

CI starts PostgreSQL 16 and sets `TEST_POSTGRES_URL` to a disposable database. Tests cover full onboarding, rollback, two tenants, constraints, upgrades/downgrades, generated revision execution and concurrency across processes. Local integration tests skip only when this variable is absent; they do not fall back to the application's database URL.

Control Plane v1 targets a fresh database. Migration or adoption of existing installations is outside this release; no command automatically deletes an old database. For subsequent releases on a versioned v1 database, deploy the migration files, upgrade global tables and use `upgrade --all` for tenant revisions before starting the matching workers. New tenants use the deployed head automatically.

### Channels removal release

This release requires a maintenance window. A rolling update can leave old
processes reading dropped tables or recreating import jobs. Take a restorable
database backup and retain the corresponding encryption keys before the window.

1. Block incoming application traffic and provisioning/onboarding. Stop old
   API, shared jobs workers and other writers, including any manual jobs
   commands. Wait for admitted operations and database transactions to finish.
   Keep automatic reconciliation from restarting the old workloads during
   maintenance; verify that no old API or worker replicas remain.
2. Run these commands from the new runtime image against the existing database:

   ```sh
   dnk-manage database upgrade
   dnk-manage tenant-migrations upgrade --all
   dnk-manage tenant-migrations current --all
   ```

   Require global head `0007_remove_channel_jobs` and tenant head
   `0027_remove_channels` for every remaining tenant. The CLI commits each
   tenant separately; fix failures and retry without reopening traffic.
   Confirm that no exact `channels.publication_import` jobs or retired tenant
   tables remain. Unmanaged schemas are not migration targets.
3. Deploy the matching backend, worker and Console, then resume onboarding and
   traffic. Check readiness, Catalog/CRM/Files access and normal jobs. Remove
   dedicated Channels environment settings, secret references and mounts.
   Keep backup decryption material according to the backup retention policy.

With Helm/Argo CD, perform the same stop-and-drain step before allowing the new
migration Job to run. Its sync wave `-10` orders the new resources but does not
stop old workloads. The existing migration runner applies public and tenant
revisions under its deployment lock; start the new workloads only after the Job
succeeds. Do not treat the migration lock as a worker shutdown mechanism.

A failure keeps maintenance active. The manual commands can retain successful
tenant upgrades while another fails; resume with the same image and retry.
Do not roll back only the application image after dropping tables. Restore the
required schema revisions and backup data before starting an older runtime;
downgrade alone returns empty tables and cannot restore credentials or snapshots.

## Related

- [Files](../modules/files.md): `0020_files` creates tenant registry tables;
  `dnk-manage files prepare --all` prepares private buckets after SQL migrations.
- [Tenancy](../modules/tenancy.md)
- [Persistence and UoW rules](../architecture/backend.md#unit-of-work)
