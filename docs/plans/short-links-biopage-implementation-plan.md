# Short Links & BioPage Platform Implementation Plan

Статус: план реализации, не описание уже существующего поведения.

Этот документ адаптирует RFC `Short Links & BioPage Platform` под текущую архитектуру `dnk-runtime-core`: модульные
границы, явную FastAPI DI-композицию, request-scoped `UnitOfWork`, public SQLAlchemy-модели и tenant runtime schema.

## 1. Наблюдения по текущей архитектуре

- Бизнес-модули живут в `src/modules/<module>/` и обычно делятся на `domain`, `application`, `infrastructure`,
  `presentation`.
- HTTP DI собирается явно в `presentation/depends/`, без глобального контейнера.
- Один HTTP request получает один `UnitOfWork` из `src/modules/shared/depends/uow.py`; все repository/adapters должны
  использовать тот же `uow.session`.
- Public/system таблицы описываются SQLAlchemy-моделями на `Base` и подхватываются через
  `src/modules/persistence.py` + `DatabaseHelper.create_all()`.
- Tenant business tables в текущем проекте создаются через `schema_registry` seed/diff flow, а runtime-доступ идет через
  `runtime_data` gateways и `RuntimeObjectResolverProtocol`.
- Client-data endpoints не принимают `tenant_id` из request body/path/query. Tenant scope берется из
  `AuthenticatedRequestContextDep` и прокидывается в application command/query DTO.
- `TenantServiceType.SHORTLINKS = "shortlinks"` уже существует, поэтому отдельную сущность `short_domains` создавать
  не нужно: short domains должны быть строками `tenant_domains` с этим `service_type`.
- Все текущие `/api/...` routes монтируются через `src/modules/router.py` с prefix `/api`; публичный resolve
  `GET /{slug}` нужно подключать отдельно на root-level в `src/app_factory.py`.

## 2. Архитектурное решение

Создать отдельный bounded context `short_link`.

Модуль владеет:

- public routing data: `short_links`, `short_link_platform_targets`;
- tenant content/config access: `bio_pages`, `short_link_templates`, `short_link_template_batches`;
- application orchestration для create/update/resolve/batch/publish;
- platform detection, UTM merge, slug generation и visit-event port.

Модуль не должен напрямую протаскивать чужие use cases в application слой. Для short domains он вводит свой
`ShortDomainRepositoryPort`, а infrastructure adapter реализует его поверх `tenant_domains` / tenancy persistence.
Так `short_link.application` остается независимым от `tenancy.application`.

## 3. Решения для v1

- BioPage public response: JSON only. SSR/HTML вынести в отдельный этап.
- Redirect code: поддержать `302` и `307` сразу, default `302`.
- Batch cap: конфигурируемый hard limit, default `10000`.
- Template versioning: не делать в v1.
- Default TTL: включить через config `SHORT_LINK_DEFAULT_TTL_DAYS`; explicit `expires_at` в request имеет приоритет.
- Visit events: в v1 завести порт и no-op/structured-log adapter; постоянную analytics table можно добавить позже.
- Rate limit: завести порт сразу; первый production-oriented adapter может использовать Redis, test/dev fallback -
  in-memory.

## 4. Target Module Layout

```text
src/modules/short_link/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── short_domain/
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   └── error.py
│   ├── short_link/
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── error.py
│   │   ├── service.py
│   │   └── value_object/
│   │       ├── __init__.py
│   │       ├── platform.py
│   │       ├── short_link_id.py
│   │       ├── slug.py
│   │       └── target_type.py
│   ├── bio_page/
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── error.py
│   │   └── value_object/
│   │       ├── __init__.py
│   │       └── bio_page_id.py
│   └── template/
│       ├── __init__.py
│       ├── entity.py
│       ├── error.py
│       └── value_object/
│           ├── __init__.py
│           ├── batch_id.py
│           └── template_id.py
├── application/
│   ├── __init__.py
│   ├── command/
│   ├── dto/
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── bio_page_repository.py
│   │   ├── platform_detector.py
│   │   ├── rate_limiter.py
│   │   ├── short_domain_repository.py
│   │   ├── short_link_repository.py
│   │   ├── slug_generator.py
│   │   ├── template_repository.py
│   │   ├── url_utm_merger.py
│   │   └── visit_event_writer.py
│   └── use_case/
│       ├── __init__.py
│       ├── create_bio_page.py
│       ├── create_short_domain.py
│       ├── create_short_link.py
│       ├── create_template.py
│       ├── generate_links_from_template.py
│       ├── publish_bio_page.py
│       ├── resolve_incoming_short_link.py
│       └── update_short_link.py
├── infrastructure/
│   ├── __init__.py
│   ├── mapper/
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── public/
│   │   │   ├── __init__.py
│   │   │   ├── short_link.py
│   │   │   ├── short_link_platform_target.py
│   │   │   └── repository.py
│   │   └── tenant/
│   │       ├── __init__.py
│   │       ├── bio_page_runtime_repository.py
│   │       └── template_runtime_repository.py
│   ├── platform_detector/
│   │   ├── __init__.py
│   │   └── user_agent_platform_detector.py
│   ├── rate_limiter/
│   │   ├── __init__.py
│   │   ├── in_memory_resolve_rate_limiter.py
│   │   └── redis_resolve_rate_limiter.py
│   ├── slug/
│   │   ├── __init__.py
│   │   └── random_slug_generator.py
│   ├── tenancy/
│   │   ├── __init__.py
│   │   └── short_domain_repository_adapter.py
│   ├── url/
│   │   ├── __init__.py
│   │   ├── url_validator.py
│   │   └── utm_merger.py
│   └── visit_event/
│       ├── __init__.py
│       └── structured_log_visit_event_writer.py
└── presentation/
    ├── __init__.py
    ├── depends/
    │   ├── __init__.py
    │   ├── application.py
    │   └── infrastructure.py
    └── http/
        ├── __init__.py
        ├── admin_router.py
        ├── public_router.py
        ├── bio_page/
        ├── short_domain/
        ├── short_link/
        └── template/
```

## 5. Persistence Plan

### 5.1 Public Schema

Добавить SQLAlchemy-модели на `Base` и импортировать их из `src/modules/persistence.py`.

`public.short_links`:

- `id UUID PK`
- `tenant_id UUID NOT NULL FK tenants(id)`
- `domain_id UUID NOT NULL FK tenant_domains(id)`
- `slug VARCHAR(64) NOT NULL`
- `target_type VARCHAR(16) NOT NULL`
- `target_ref VARCHAR(128) NULL`
- `template_id UUID NULL`
- `is_active BOOL NOT NULL DEFAULT TRUE`
- `expires_at TIMESTAMPTZ NULL`
- `redirect_code INT NOT NULL DEFAULT 302`
- `created_by UUID NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- unique constraint/index: `(domain_id, slug)`
- checks: `target_type IN ('redirect', 'bio_page')`, `redirect_code IN (302, 307)`

`public.short_link_platform_targets`:

- `id UUID PK`
- `short_link_id UUID UNIQUE NOT NULL FK short_links(id) ON DELETE CASCADE`
- `web_url TEXT NULL`
- `ios_url TEXT NULL`
- `android_url TEXT NULL`
- `fallback_url TEXT NULL`
- `utm_json JSONB NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

Примечание: `tenant_domains` остается источником short domains. Для short-link домена должна выполняться проверка:

- `tenant_domains.service_type == TenantServiceType.SHORTLINKS`
- `tenant_domains.status == TenantDomainStatus.ACTIVE`
- `tenant_domains.tenant_id == principal.tenant_id` для cabinet APIs

### 5.2 Tenant Runtime Schema

Добавить объекты в `src/modules/schema_registry/seed/schema_seed.py` через `ObjectSeed`, чтобы новые tenant-таблицы
создавались bootstrap/diff flow:

- `bio_page` / `bio_pages`
- `short_link_template` / `short_link_templates`
- `short_link_template_batch` / `short_link_template_batches`

Для существующих tenants rollout идет через:

```text
dnk-manage schema-registry diff <tenant_id>
```

Важно: текущий `datetime` seed type рендерится как PostgreSQL `timestamp without time zone`. Если строго нужен
`TIMESTAMPTZ` в tenant tables, сначала расширить `schema_registry` type canonicalizer. Для v1 лучше следовать текущей
runtime schema convention.

`bio_pages` fields:

- `id uuid system default gen_random_uuid()`
- `created_at datetime system default CURRENT_TIMESTAMP`
- `updated_at datetime system default CURRENT_TIMESTAMP`
- `title text required`
- `slug text nullable`
- `content_json json required`
- `is_published bool required default false`

Indexes:

- unique `bio_pages_id_uq` on `id`
- non-unique `bio_pages_slug_idx` on `slug`

`short_link_templates` fields:

- `id uuid system default gen_random_uuid()`
- `created_at datetime system default CURRENT_TIMESTAMP`
- `updated_at datetime system default CURRENT_TIMESTAMP`
- `name text required`
- `default_target_type select required` with options `redirect`, `bio_page`
- `default_web_url text nullable`
- `default_ios_url text nullable`
- `default_android_url text nullable`
- `default_fallback_url text nullable`
- `utm_source_tpl text nullable`
- `utm_medium_tpl text nullable`
- `utm_campaign_tpl text nullable`
- `utm_term_tpl text nullable`
- `utm_content_tpl text nullable`

`short_link_template_batches` fields:

- `id uuid system default gen_random_uuid()`
- `created_at datetime system default CURRENT_TIMESTAMP`
- `updated_at datetime system default CURRENT_TIMESTAMP`
- `template_id uuid required`
- `requested_count int required`
- `status select required` with options `pending`, `running`, `done`, `failed`, `partial`
- `result_json json nullable`

Relations:

- `short_link_template_batches.template_id -> short_link_templates.id` with `restrict`

## 6. Domain Model

Use dataclass entities with concrete id value objects inheriting `EntityIdVO`, matching existing architecture tests.

Core enums should use `StrEnum` and lower-case stored values:

- `ShortLinkTargetType.REDIRECT = "redirect"`
- `ShortLinkTargetType.BIO_PAGE = "bio_page"`
- `ShortLinkPlatform.WEB = "web"`
- `ShortLinkPlatform.IOS = "ios"`
- `ShortLinkPlatform.ANDROID = "android"`
- `TemplateBatchStatus = pending/running/done/failed/partial`

Domain rules:

- `ShortLinkSlugVO` validates non-empty slug, max length 64 and safe charset.
- Reserved slugs are checked in `ShortLinkService`, not in the value object, because blacklist comes from config.
- `ShortLinkTarget.validate_redirect()` requires at least one of web/iOS/Android/fallback URL.
- `ShortLink.validate_resolvable(now)` raises not-found/expired/inactive domain errors.
- `BioPage.publish(now)` only changes state/timestamps; content validation belongs to entity/service.
- Template entity owns precedence materialization helpers:
  `explicit request > template defaults > config defaults`.

## 7. Application Use Cases

### CreateShortDomainUseCase

Input: tenant id, host, optional kind/TLS metadata.

Flow:

1. Normalize host with shared `normalize_host`.
2. Verify host is not taken by any non-deleted tenant domain.
3. Create tenant domain with `service_type=shortlinks`, active/verified policy matching current admin semantics.
4. Return short-domain DTO.

Auth: server-admin/control-plane route only. Prefer extracting a generic `ControlPlaneAuthorizationDep` from the
current tenant-specific `AdminCreateTenantAuthorizationDep` naming before reuse.

### CreateBioPageUseCase / PublishBioPageUseCase

Input tenant id from `AuthenticatedRequestContextDep`.

Flow:

1. Validate title/content.
2. Save through `BioPageRepositoryPort` implemented over runtime data.
3. Publish toggles `is_published=true` and updates timestamp.

### CreateTemplateUseCase

Flow:

1. Validate default target type and optional URL fields.
2. Validate UTM template variables syntactically.
3. Save through tenant runtime repository.

### CreateShortLinkUseCase

Flow:

1. Receive tenant id/current user id from auth context.
2. Load short domain through `ShortDomainRepositoryPort`.
3. Verify domain belongs to tenant and has `service_type=shortlinks`.
4. Resolve template if `template_id` is present.
5. Apply precedence: explicit request fields > template values > config defaults.
6. If slug is absent, generate via `SlugGeneratorPort`; if provided, validate and reject reserved slug.
7. Validate target:
    - `redirect`: at least one target URL and URL policy checks;
    - `bio_page`: `target_ref` points to an existing tenant bio page.
8. Persist `ShortLink` + `ShortLinkPlatformTarget` in public schema.
9. On unique violation `(domain_id, slug)`, retry only for generated slugs; explicit slug returns conflict.

### UpdateShortLinkUseCase

Flow:

1. Load link by id + tenant id.
2. Apply patch fields.
3. Re-run domain invariants.
4. Save link/target records.

Activation/deactivation can be small dedicated use cases or command variants of update; keep controller routes explicit.

### ResolveIncomingShortLinkUseCase

Input: normalized host, slug, query params, user-agent, request ip, current time.

Flow:

1. Rate-limit by host + hashed IP + slug.
2. Load short domain by host and require active `shortlinks` domain.
3. Load link by `(domain_id, slug)`.
4. Verify active/not expired; return not found for inactive and expired links unless product later chooses `410`.
5. Dispatch:
    - `redirect`: detect platform, choose URL, merge missing UTM params, return redirect DTO with status code.
    - `bio_page`: load tenant bio page by `target_ref`, require `is_published`, return JSON DTO.
6. Emit visit event asynchronously through `VisitEventWriterPort`; v1 adapter can structured-log and never fail resolve.

### GenerateLinksFromTemplateUseCase

Flow:

1. Validate `count <= SHORT_LINK_BATCH_MAX_COUNT`.
2. Create batch row with `pending`, then mark `running`.
3. For every item, render template variables and call internal short-link creation service.
4. Catch per-item errors and record detailed result:
    - input index
    - slug if generated
    - short_link_id if created
    - status `done` / `failed`
    - error code/message
5. Final status:
    - all success: `done`
    - all failed: `failed`
    - mixed: `partial`

For v1 this can be synchronous. If request time becomes unacceptable, the same batch table can support an async worker.

## 8. Ports

Application ports:

- `ShortDomainRepositoryPort`
    - `add_short_domain(...)`
    - `get_by_id(...)`
    - `get_active_shortlink_domain_by_host(...)`
    - `exists_by_host(...)`
- `ShortLinkRepositoryPort`
    - `add(link, target)`
    - `update(link, target)`
    - `get_by_id(tenant_id, short_link_id)`
    - `get_by_domain_and_slug(domain_id, slug)`
- `BioPageRepositoryPort`
    - `add`, `update`, `get_by_id`, `get_published_by_id`
- `ShortLinkTemplateRepositoryPort`
    - `add_template`, `get_template_by_id`, `add_batch`, `update_batch`
- `PlatformDetectorPort`
- `SlugGeneratorPort`
- `UrlValidatorPort`
- `UrlUtmMergerPort`
- `ResolveRateLimiterPort`
- `VisitEventWriterPort`

Keep these protocols in `short_link/application/ports/`; infrastructure implements them.

## 9. HTTP Plan

### Public Resolve

Add `src/modules/short_link/presentation/http/public_router.py`:

- `GET /{slug}`

Mount in `src/app_factory.py` at root level, after or alongside API router. Keep reserved slugs to avoid collisions with
`api`, `docs`, `openapi.json`, `redoc`, `health`, `admin`.

Responses:

- redirect target: `RedirectResponse(url=..., status_code=302|307)`
- bio page target: `JSONResponse` with page DTO
- inactive/expired/not-found/unconfigured target: `404`
- rate limited: `429`

### Cabinet/Admin APIs

Mount through `src/modules/router.py` under `/api`:

- `POST /api/short-links`
- `GET /api/short-links/{short_link_id}`
- `PATCH /api/short-links/{short_link_id}`
- `POST /api/short-links/{short_link_id}/activate`
- `POST /api/short-links/{short_link_id}/deactivate`
- `POST /api/short-link-templates`
- `POST /api/short-link-templates/{template_id}/generate`
- `POST /api/bio-pages`
- `PATCH /api/bio-pages/{bio_page_id}`
- `POST /api/bio-pages/{bio_page_id}/publish`
- `POST /api/admin/short-domains`

Controller conventions:

- Use Pydantic request/response schemas near each endpoint area.
- `model_config = ConfigDict(extra="forbid")` for request schemas.
- Map domain/application errors directly in controllers, consistent with current `identity`, `crm`, `inventory`.
- Never accept `tenant_id` in cabinet payloads.

## 10. URL, Platform And UTM Details

Platform resolution:

1. `?platform=ios|android|web` explicit override.
2. User-Agent detector:
    - iPhone/iPad/iPod -> iOS
    - Android -> Android
    - otherwise web
3. URL fallback:
    - selected platform URL
    - fallback URL
    - web URL
    - target-not-configured error

URL validation:

- allow `https` by default;
- allow `http` only in development/test if config permits;
- allow mobile app schemes from config allowlist;
- reject empty/relative URLs for redirect targets;
- do not mutate existing target query params except adding missing UTM keys.

UTM whitelist:

- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_term`
- `utm_content`

UTM merge rules:

- materialize stable template variables at create/generate time;
- at resolve time add missing UTM params to the chosen target URL;
- do not overwrite target URL params by default.

## 11. DI Wiring

`presentation/depends/infrastructure.py`:

- builds public SQLAlchemy repos from `UoWDep.session`;
- builds tenant runtime repos from:
    - `RuntimeObjectResolverProtocol`
    - `PostgresRuntimeGateway`
    - same `uow.session`
- builds short-domain adapter over tenancy persistence from same `uow.session`;
- builds stateless adapters: platform detector, slug generator, UTM merger, URL validator;
- builds rate limiter and visit event writer from app state/config.

`presentation/depends/application.py`:

- composes use cases from ports/services;
- exports typed `Annotated[..., Depends(...)]` aliases, matching existing modules.

Add a session-bound dependency test similar to `test/test_schema_registry_depends.py`.

## 12. Configuration

Add `src/config/feature/short_link/__init__.py` and include it in `FeatureConfig`.

Suggested config:

- `SHORT_LINK_ENABLED: bool = False`
- `SHORT_LINK_PUBLIC_RESOLVE_ENABLED: bool = False`
- `SHORT_LINK_DEFAULT_SLUG_LENGTH: int = 8`
- `SHORT_LINK_DEFAULT_TTL_DAYS: int | None = 365`
- `SHORT_LINK_BATCH_MAX_COUNT: int = 10000`
- `SHORT_LINK_RESERVED_SLUGS: tuple[str, ...]`
- `SHORT_LINK_DEFAULT_REDIRECT_CODE: int = 302`
- `SHORT_LINK_ALLOWED_WEB_SCHEMES: tuple[str, ...] = ("https",)`
- `SHORT_LINK_ALLOWED_APP_SCHEMES: tuple[str, ...] = ()`
- `SHORT_LINK_RATE_LIMIT_PER_MINUTE: int = 120`

Update `docs/interfaces/configuration.md` after implementation, not in this plan-only change.

## 13. Security And Abuse Protection

- Enforce reserved slugs before persistence.
- Rate-limit public resolve before DB-heavy work where possible.
- Hash IP before writing visit events.
- Do not log full raw URLs if they can contain sensitive query params; structured logs should include reason codes and
  route metadata.
- Cabinet routes require authenticated context.
- Short domain creation requires control-plane/server-admin auth.
- Domain ownership check is mandatory for every short-link write/read.

## 14. Observability

Initial implementation:

- structured logs in resolve use case with:
    - domain
    - slug
    - tenant_id
    - target_type
    - platform
    - outcome/reason
- visit writer port with structured-log adapter.

Future:

- metrics counters/histograms once a metrics backend is introduced:
    - resolve requests total
    - latency p50/p95/p99
    - errors by reason
    - redirect vs bio_page ratio
- tracing spans:
    - `resolve_domain`
    - `resolve_link`
    - `resolve_target`
    - `emit_visit_event`

## 15. Implementation Phases

### Phase 1: Domain and Pure Services

- Add value objects, enums and entities.
- Add domain errors.
- Add slug validation, URL target invariant checks and UTM merge unit tests.

### Phase 2: Public Persistence

- Add public SQLAlchemy models/repositories for `short_links` and `short_link_platform_targets`.
- Import new persistence package from `src/modules/persistence.py`.
- Add repository mapper tests.
- Add uniqueness retry behavior tests with fake repository first; DB-backed tests if test DB is available.

### Phase 3: Tenant Runtime Schema

- Extend default schema seed with bio page/template/batch objects.
- Add runtime repositories over `runtime_data` gateways.
- Add seed tests and runtime repository mapping tests.
- Document rollout command for existing tenants.

### Phase 4: Application Use Cases And DI

- Implement use cases.
- Add application dependency builders.
- Add dependency composition tests ensuring shared `uow.session`.
- Add boundary tests so `short_link.application` does not import `tenancy.application` or SQLAlchemy.

### Phase 5: HTTP Surface

- Add public resolve router and mount it at root in `app_factory.py`.
- Add `/api` cabinet/admin routers and include them from `src/modules/router.py`.
- Add router registration tests.
- Add controller error mapping tests.

### Phase 6: Abuse, Events, Feature Flags

- Add config group and feature flags.
- Add rate limiter port/adapters.
- Add visit event writer structured-log adapter.
- Wire public resolve behind `SHORT_LINK_PUBLIC_RESOLVE_ENABLED`.

### Phase 7: Documentation And Rollout

- After implementation, update:
    - `README.md`
    - `docs/index.md`
    - `docs/modules/short-link.md`
    - `docs/interfaces/http-api.md`
    - `docs/interfaces/configuration.md`
    - `docs/quality/test-map.md`
- Rollout:
    1. deploy public tables;
    2. run tenant schema diff for target tenants;
    3. enable write APIs internally;
    4. enable public resolve by domain cohort;
    5. monitor logs/errors;
    6. rollback by disabling feature flags, without destructive data rollback.

## 16. Test Plan

Unit:

- slug validation and reserved slug policy;
- target type invariants;
- platform detection precedence;
- redirect URL fallback chain;
- UTM merge policy;
- template precedence;
- batch per-item status aggregation.

Application:

- create redirect link with explicit slug;
- create redirect link with generated slug retry;
- create bio-page link only for existing tenant page;
- inactive/expired link resolve returns not-found result;
- published vs unpublished bio page resolve;
- update/activate/deactivate ownership checks.

Infrastructure:

- public SQLAlchemy repo mapping and uniqueness;
- tenant runtime repository mapping for bio pages/templates/batches;
- short-domain adapter filters `service_type=shortlinks`;
- rate limiter in-memory behavior.

HTTP:

- route registration for public and admin routers;
- public resolve with `Host` variants;
- redirect response status/location;
- bio page JSON response;
- authenticated cabinet routes reject missing principal;
- `tenant_id` is never accepted in request schemas.

Architecture:

- `short_link.domain` has no SQLAlchemy/FastAPI imports;
- `short_link.application` has no concrete infrastructure imports;
- `short_link.application` does not import `tenancy.application`;
- concrete id VOs live under `domain/**/value_object/` and inherit `EntityIdVO`.

## 17. Main Files To Touch

- `src/modules/short_link/**`
- `src/modules/persistence.py`
- `src/modules/router.py`
- `src/app_factory.py`
- `src/config/feature/__init__.py`
- `src/config/feature/short_link/__init__.py`
- `src/modules/schema_registry/seed/schema_seed.py`
- `test/test_short_link_*.py`
- `test/test_architecture_boundaries.py`

Documentation updates should wait until the feature exists, except this plan file.
