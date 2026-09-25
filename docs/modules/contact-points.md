# Contact points

`contact_points` owns a tenant-local directory of canonical phone/email values, polymorphic bindings and
configurable labels. One `ContactPoint` can be used by multiple contacts, companies and future object types.
Phone and email share storage and lifecycle; each type has its own normalization strategy.

## Ownership and integration

`ContactPoint` is immutable (`type`, `canonical_value`, phone `country_code`). `(type, canonical_value)` is unique
within the tenant schema. `ContactPointBinding` stores `id`, `contact_point_id`, `model_key`, `record_id`, optional
`label_id`, `position` and audit fields. A target cannot bind the same point twice. Changing a value resolves a
new/existing point and preserves the binding identifier; it never edits the value shared with other owners.
Deleting the final binding does not delete the directory entry.

A consumer defines its own application port and DTOs. Its infrastructure adapter maps those into commands and
queries exported by `contact_points/application/api.py`, using the public `domain/api.py` VO exports as needed.
No ORM entity or session crosses this boundary. Specialized VO remain in their owning module; Shared provides
existing neutral identifiers, clock and UoW primitives.

The owner validates access and existence and locks the owner row before update/delete. CRM uses the stable keys
`crm.contact` and `crm.company`. There is no foreign key to a polymorphic target and no universal binding HTTP API.
Future owners must follow the same locking and cleanup discipline, with their own adapter.

All repositories are constructed by presentation dependencies on the same cached shared `UoWDep.session`.
Tenant is explicit on every repository operation and translated to a schema by `TenantSchemaNaming`.
Only the outer shared UoW commits/rolls back. Sync validates the supplied arrays, normalizes values, resolves points
with PostgreSQL `ON CONFLICT`, then replaces target bindings atomically. Stable point resolution order avoids
opposing uniqueness locks. The owner lock serializes replacements, including swaps of two addresses.
Unchanged bindings retain identifiers/audit; an unchanged whole set performs no binding write.

Public operations are sync, batch read (also used for a single target), target cleanup, read-only reverse lookup,
and list/create/update labels. Reverse lookup returns target references; its consumer decides how to display them.
No outbox events are emitted because this version has no event consumer.

## Input and normalization

A CRM create/update can include:

```json
{
  "first_name": "Denis",
  "phones": [{"value": "050 123 45 67", "country_code": "UA", "label_id": null}],
  "emails": [{"value": "Denis@Example.COM", "label_id": null}]
}
```

For an existing row include its `binding_id`. Do not send `contact_point_id`, tenant or actor. Responses include
`binding_id`, `contact_point_id`, normalized `value`, nullable `label_id` and nullable `country_code`.
An omitted array preserves its current state; `[]` clears it; `null` is invalid. The rule applies independently
to phones and emails. An invalid row returns `422` with an indexed field location and rolls back the whole card.

Phones require a country and are validated with `phonenumbers`, then stored as E.164. Country calling code alone
is insufficient, particularly for shared prefixes such as +1. Extensions and phone values embedded in prose are
not supported. Email uses `email-validator`, trims whitespace, normalizes the domain/IDN and preserves local-part
case. DNS is not queried; Gmail dots and aliases are not collapsed. Syntax validation does not verify ownership.

## Labels and Console

Labels belong to one type, have a trimmed 1–100 character name and can be archived/restored. Six labels are seeded:
«Рабочий», «Личный», «Другой» for each type. No label is required. Archived labels remain on existing bindings
but cannot be newly assigned. Label row locks coordinate assignment and archive.

Authenticated tenant members can GET `/api/console/contact-points/labels`, optionally filtered by `?type=phone`
or `?type=email`. Admins can POST `{type, name}` and PATCH `/{label_id}` with `{name?, is_active?}`. Mutations require
CSRF; null patch values are rejected. Labels are managed at `/admin/contact-points` in the existing AdminLayout.

The public Console module exports `ContactPointsWidget`, `PhoneContactPointsField`, `EmailContactPointsField` and
their draft/label/error types. The fields compose existing shadcn-vue components. They are controlled by arrays,
keep stable `clientKey` values and emit changes/validation without fetching or saving. Phone drafts default to UA.
The parent supplies labels, loading/error state and `pending`, and maps indexed server errors against the sent
snapshot. Empty rows must be filled or explicitly removed. A save failure retains the draft; cancel discards it.

## Deployment and verification

Tenant revision `0008_contact_points` follows `0007_crm_contacts_companies`. Upgrade existing tenants with the
[tenant migration management command](../data/tenant-migrations.md) before deploying the new backend/frontend.
New tenant bootstrap applies the same revision transactionally. Existing CRM data stays intact with empty arrays.
There is no backfill from identity emails and no restoration of the removed legacy contact_point module.

Focused tests:

```sh
uv run python -m unittest test.test_contact_points test.test_crm test.test_crm_http test.test_removed_module_boundaries
TEST_POSTGRES_URL=postgresql+asyncpg://... uv run python -m unittest test.test_contact_points_postgres test.test_tenant_migrations_postgres
```

Use a disposable PostgreSQL database. Integration coverage includes shared session identity, atomic rollback,
concurrent resolve/update/delete, tenant isolation, immutable shared values, archival permissions/CSRF, reverse
lookup and transactional migrations. See [the implementation plan](../plan/contact_point_module.md) for scope.
