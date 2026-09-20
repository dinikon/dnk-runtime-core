# Currency

Currency owns the ISO directory, organization policy, functional currency periods,
manual rate revisions and globally imported NBU rates. Other contexts use the
async `CurrencyFacade` from `src.modules.currency.application`. They do not access
Currency tables or make HTTP requests during conversion.

## Policy and conversion

An organization has no policy until an administrator explicitly completes
`/settings/currency`. The initial form suggests UAH, NBU, `previous_available`,
`ROUND_HALF_UP`, a UAH bridge and `Europe/Kyiv`. Saving creates the enabled currency
set, policy, timezone and first period in one UoW. The first period may be backdated;
subsequent changes must start in the future after the last scheduled period.
Periods are inclusive, and scheduling closes the prior period on the preceding day.

A code is three ASCII letters, normalized to uppercase. `shared.Money` is immutable,
uses finite Decimal values and refuses floats and arithmetic between different
currencies. It never rounds to currency minor units implicitly. The former local
`price_lists.MoneyVO` is now `ImportPriceVO`; its NUMERIC(19,4) validation and state
hash representation are unchanged.

The facade receives an explicit tenant and business date. `get_business_date(s)`
uses the configured organization timezone for UTC timestamps. Resolution reads
local data in order: identity, direct, inverse, cross, typed error. It uses only
the configured provider. Cross rates use two revisions from one provider and the
same effective date; `previous_available` selects their latest common date at or
before the requested date. Inverse/cross division uses 38 significant digits;
amount multiplication retains intermediate precision. `MoneyQuantizer` explicitly
separates calculation, booking and display. Booking/display require minor units or
an explicitly supplied precision; calculation retains the unquantized amount.

`ConvertedMoney` contains original and converted Money plus a frozen
`ConversionSnapshot`: requested/effective dates, rate, derivation, provider, all
source revision IDs, conversion timestamp, bridge and policy version. Identity
conversion also has a snapshot, with provider `INTERNAL` and no source revision IDs.

## Persistence and concurrency

| Scope | Tables |
| --- | --- |
| Global | `currency`, `fx_provider_rate`, `fx_rate_import` |
| Tenant | `currency_policy`, `enabled_currency`, `functional_currency_period`, `manual_exchange_rate` |
| Price lists tenant | `partner_offer_money_snapshots` |

Global revision `0006_currency` seeds 178 codes from the checked-in SIX ISO 4217
snapshot (`migrations/global/data/iso4217.json`, published 2026-09-17). It performs no
network access. Re-running upgrades is safe; seed inserts use `ON CONFLICT`.
Tenant revisions `0007_currency` and `0008_offer_money` install currency settings
and consumer-owned offer snapshots. Models participate in tenant bootstrap and
historical table-name checks. Tenant repositories use Core statements and
`schema_translate_map`; they receive the caller's session and never commit.

Policy writes require the expected version. Transaction advisory locks serialize
settings/period changes and rate revisions; unique indexes allow one current rate
per provider/pair/date and sequential revision numbers. A PostgreSQL exclusion
constraint forbids overlapping functional currency periods. Old rate values are
never overwritten. Required policy currencies and current/future functional
currencies cannot be disabled. Historical reads remain available.

Tenant settings/rate changes enter the existing outbox in the same transaction.
Global provider imports use `fx_rate_import` because the outbox requires a tenant.
Each import commits its audit attempt before fetching, validates the whole batch,
then atomically publishes revisions and success. Failure finalization occurs in a
separate UoW after rollback. Same-value provider imports create no revisions;
corrections create new immutable rows. NBU effective and calculation dates are
stored separately; rates are normalized per unit. HTTP transport/429/5xx retries
are bounded, and malformed responses cannot partially publish.

## HTTP and Console

All paths below are relative to `/api/console/currency`:

| Method | Path | Access |
| --- | --- | --- |
| GET | `/directory`, `/settings`, `/periods` | member, admin |
| GET | `/functional-currency?business_date=...` | member, admin |
| GET | `/rates?provider=NBU&source=USD&target=UAH&limit=50&offset=0` | member, admin |
| GET | `/quote?source=USD&target=UAH&business_date=...` | member, admin |
| POST | `/convert` | member, admin; read-only operation |
| POST | `/initialize`, `/periods`, `/rates/manual` | admin + CSRF |
| PUT | `/policy`, `/enabled/{code}` | admin + CSRF |

Access uses authenticated principal roles and `currency.*` permissions with no
allow-all fallback. Tenant and actor come from trusted request context; request
models reject extra fields. Amounts and rates cross HTTP as decimal strings.
Version conflicts return 409 with `currency_conflict`; Console preserves edits
and offers an explicit reload. Global sync is not an HTTP mutation. Console shows
its latest audit state and available rate date.

## Price lists

Application orchestration creates purchase-price and RRP snapshots only for new
OfferState records, in the same publication transaction. The historical business
date comes from `observed_at` in the organization timezone. An absent policy, rate,
functional period or enabled currency records an explicit `unavailable` reason
without discarding the raw price. Infrastructure failures still roll back the
import. A state imported without policy remains unavailable after later setup;
pre-migration states are reported as `legacy_state`. Nothing backfills history.

Current conversion runs separately on the requested `business_date`; omitting it
uses the organization's current day. The offers UI exposes this date and shows
source prices, historical conversions and current equivalents separately.
Conversions de-duplicate pair/date lookups per batch. Changing a rate and repeating
an otherwise identical import does not create an OfferState or update its snapshot.

## Deployment

1. Apply global migrations, then tenant migrations, before serving the new app.
   `dnk-manage database upgrade` already performs these steps in order; targeted
   tenant upgrades remain available through `tenant-migrations upgrade --all`.
2. Deploy backend and Console with NBU scheduling disabled.
3. Administrators explicitly configure each organization, including timezone and
   the start of its first functional currency period.
4. Load the required dates, for example:

   ```sh
   dnk-manage currency sync-rates --date-from 2026-09-01 --date-to 2026-09-21
   ```

5. Enable `application.currency.nbu.syncEnabled` when ready. The separate Helm
   CronJob defaults to `15 18 * * *` UTC, forbids concurrent jobs and honors the
   migration gate. It does not use tenant-only scheduled jobs.

Without date arguments, CLI refreshes the previous seven UTC days through tomorrow.
`--scheduled` respects `CURRENCY__NBU__SYNC_ENABLED=false`; explicit CLI runs do not
require enabling the schedule. An import range is limited to 367 inclusive days.
Other configuration: `CURRENCY__NBU__API_URL`, `TIMEOUT_SECONDS` (15), `RETRY_COUNT`
(2), and `SYNC_SCHEDULE`. Nonzero CLI exit means the import failed; inspect global
audit before retrying. No migrations or tenant setup run implicitly during conversion.

## Validation

`test_currency.py` covers domain rules, conversion, batching, timezone, NBU fixtures
and CLI; `test_currency_http.py` covers principal roles, CSRF, trusted tenant input
and decimal strings. `test_currency_postgres.py` creates isolated temporary databases
under **TEST_POSTGRES_URL only** and exercises migrations, two tenants, revision
concurrency, rollback, optimistic locking, common-date cross rates, exclusion
constraints and failed audit persistence. `test_price_list_bulk_postgres.py` also
checks immutable snapshots/current conversion through actual import publication.
`helm/tests/test_currency_sync.py` verifies the disabled default and rendered CronJob.

Browser checks use mocked HTTP fixtures for initial setup, empty states, conflict
recovery, manual rates, periods and member access; backend authorization and database
behavior are tested separately. Future contexts can consume the facade; additional
providers, provider-specific tenant storage, Redis and dynamic plugins are extensions.
