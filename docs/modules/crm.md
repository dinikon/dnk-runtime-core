# CRM

The `crm` module provides tenant-scoped contacts and companies for Console. It is a static module: its tables,
domain model and HTTP contracts are owned by the application and do not use the removed dynamic schema/runtime APIs.

## Domain model

`Contact` and `Company` are independent aggregates. Contact owns an immutable set of CompanyIdVO references, changed only through link_company, unlink_company and replace_companies. A link has no separate entity or repository. Duplicate selections and stale membership snapshots are domain errors.

- A contact has required `first_name`, optional `last_name` and `middle_name`, and audit fields.
- A company has required display `name` and the same audit fields.
- Names are trimmed. Required values must contain `1..255` characters after trimming; empty optional contact name
  parts become `null`.
- Names are not unique. A no-op update preserves `updated_at` and `updated_by`.
- Deletion is physical and irreversible.

Phone/email arrays are owned by [contact_points](contact-points.md). CRM application uses its own
`ContactPointsPort` and DTOs; an infrastructure adapter calls the public contact_points application API.
Create/update saves the aggregate and bindings in the same shared request UoW. Update/delete lock the owner;
delete removes its bindings before deleting the owner. Shared contact points remain available for other owners.
Contact-company membership is owned by Contact; Company exposes its reverse projection. Statuses and tags are outside this version.

## Persistence

Tenant migration `0007_crm_contacts_companies` creates `contacts` and `companies` inside every tenant schema. The
tables do not contain `tenant_id`; repositories select the schema from the trusted request tenant and require a
tenant identifier for every operation. Database checks reject blank required names, and indexes support stable
name-then-id ordering.

The models are registered in tenant migration metadata. Their table names also remain in the historical managed
table set so future model retirement can be detected by autogeneration.

## Application and HTTP API

Each aggregate has separate create, get, list, update and delete use cases. UUIDv7 identifiers and timestamps come
from shared ports. Actor and tenant identifiers come only from `AuthenticatedRequestContextDep`.

Console endpoints live below `/api/console/crm`:

| Method | Path                              | Result                          |
|--------|-----------------------------------|---------------------------------|
| GET    | `/contacts?q=&limit=25&offset=0`  | Stable, searchable contact page |
| GET    | `/contacts/{id}`                  | One contact                     |
| POST   | `/contacts`                       | Create a contact (`201`)        |
| PUT    | `/contacts/{id}`                  | Update a contact                |
| DELETE | `/contacts/{id}`                  | Delete a contact (`204`)        |
| GET    | `/companies?q=&limit=25&offset=0` | Stable, searchable company page |
| GET    | `/companies/{id}`                 | One company                     |
| POST   | `/companies`                      | Create a company (`201`)        |
| PUT    | `/companies/{id}`                 | Update a company                |
| DELETE | `/companies/{id}`                 | Delete a company (`204`)        |

List responses use `{items, total, limit, offset}` and accept a limit from 1 through 100. Contact search is
case-insensitive across the displayed full name and each name part; company search is case-insensitive by name.
All authenticated tenant users may use the module. Mutations use the shared CSRF protection. Domain validation,
missing rows and persistence conflicts are returned as `422`, `404` and `409` respectively.

POST/PUT accept optional `phones` and `emails` arrays. On update, an omitted array is preserved, `[]` clears it,
and `null` is invalid. A row has `value`, optional `binding_id`/`label_id`, and an explicit `country_code` for phones.
GET, list and mutation responses include both arrays with `binding_id`, `contact_point_id`, canonical `value`,
`label_id` and `country_code`. Reads enrich a whole page with one binding query. An invalid row returns `422`
with `detail[].loc = ["body", "phones" | "emails", index, field]` and rolls back the entire card.

## Console

The Console routes are `/crm/contacts` and `/crm/companies`. Each page provides debounced URL-backed search,
server pagination, loading/error/empty states, create and edit dialogs, and an irreversible delete confirmation.
Successful mutations invalidate both CRM aggregates' TanStack Query keys and show a `vue-sonner` notification. Deleting
the final row of a page moves to the previous available page.

Dialogs compose the reusable `ContactPointsWidget`, with independently exported phone and email fields built
from existing shadcn-vue primitives. Draft edits do not issue mutations; all changes are saved with the card.
Phone country defaults to UA; the server validates country and stores E.164. Labels are optional, loaded through
the contact-points query hook and administered at `/admin/contact-points`. Archived labels remain on existing rows.

## Contact–company links

Both create/edit dialogs support multiple links, removal of a link without deleting its target, and navigation to the linked card.
Cards open at `/crm/contacts?card=<id>` or `/crm/companies?card=<id>`. Details are fetched before editing; query-cache refreshes do not replace an open draft.
Closing or navigating away from a modified card asks to discard changes. All edits, including phones/emails and links, are submitted once with the card.

POST/PUT contacts accept `company_ids`; companies accept `contact_ids`. Omission preserves membership; `[]` clears it; `null` is invalid.
PUT with a membership array also requires `expected_company_ids` or `expected_contact_ids`, containing the original IDs from the loaded card.
A changed current set returns `409`, rolling back the entire card. The UI retains the draft and offers explicit reload. Snapshot comparison uses sets, so reordering is a no-op.
GET details and POST/PUT responses include `companies` or `contacts` with `{id, name}` summaries. List response shapes are unchanged.

Candidate endpoints are `GET /contacts/{id}/available-companies` and `GET /companies/{id}/available-contacts` below the CRM prefix.
They accept the usual search/pagination parameters and exclude stored links before counting/pagination. The UI also excludes draft selections and allows reselecting locally removed items.
For unsaved owners the normal opposite-object list supplies candidates. All existing same-tenant objects are eligible; cross-tenant and missing IDs return `404`.

Migration `0009_crm_contact_companies` creates tenant-local `contact_companies` with a composite primary key, cascading same-schema foreign keys and a company-first reverse index.
ContactRepository persists only the membership delta. Company edits coordinate Contact aggregates, preserving their other memberships; Company deletion unlinks through those aggregates before deleting the company.
Commands acquire Contact locks in UUID order before Company locks and recheck reverse membership after locking. A deletion whose initially observed set changed returns `409` for retry.

One cached HTTP UoW/session includes CRM, contact_points and all links. The original request-scoped dependency is retained: commit failures roll back, but the HTTP response may already have been sent.
The existing UoW protocol remains in Infrastructure and is re-exported by Application, exposing the SQLAlchemy session, context management and commit/rollback. No ordinary CRM use case or repository commits, and no events/outbox are needed for these local operations.
Separate query repositories map SQL rows directly to DTOs, without reconstructing Contact or Company.

Tests: `test_crm_relations.py` covers Domain/Application; `test_crm_relations_postgres.py` covers actual HTTP/DI, rollback, concurrency, candidate pagination, schema constraints and isolation with identical UUIDs.
Run PostgreSQL tests only with `TEST_POSTGRES_URL` pointing to a disposable database. HTTPS HTTP fixtures require `AUTH='{"allow_insecure_http":false}'` if local development configuration enables insecure HTTP.

## Related

- [HTTP API](../interfaces/http-api.md)
- [Console frontend](../frontends/console.md)
- [Tenant migrations](../data/tenant-migrations.md)
- [Develop style](../develop-style.md)
