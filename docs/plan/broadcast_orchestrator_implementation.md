# План реализации Broadcast Orchestrator

## Цель

Реализовать модуль `broadcast` как оркестратор массовых рассылок. Модуль должен:

- вести lifecycle рассылки от `DRAFT` до `READY`/`RUNNING`/`COMPLETED`;
- закреплять за рассылкой выбранный или созданный шаблон из `communication`;
- принимать аудиторию из paste/file/future universal lists, парсить ее адаптером и сохранять только нормализованные
  recipient rows;
- считать total/unique/valid/invalid/duplicate;
- строить расписание отправки по правилам оркестрации;
- передавать due recipients в `communication.SendCommunicationUseCase`;
- хранить traceability на `communication_request_id`/`outbound_message_id`;
- не хранить исходные файлы рассылки и не держать ссылку на загруженный файл/list source для MVP import flow.

`broadcast` не должен рендерить provider payload, работать с provider adapters, принимать provider webhooks или маппить
delivery statuses. Это остается ответственностью `communication`.

## Проверка текущего состояния

Текущее состояние в репозитории:

- `docs/modules/broadcast.md` описывает `broadcast` как roadmap boundary, но в `src/modules/broadcast` уже есть
  начальные папки и доменные заготовки.
- `src/modules/broadcast/application`, `infrastructure`, `presentation/http`, `presentation/depends` сейчас пустые.
- `BroadcastEntity` не импортируется: используются отсутствующие `BroadcastMappingConfigVO` и `BroadcastSettingsVO`.
- `BroadcastEntity.create_draft()` передает `source_id=None`, но поле `source_id` не объявлено в dataclass.
- `BroadcastStatus` смешивает значения: `DRAFT = "DRAFT"`, остальные lower-case. Для runtime/API лучше унифицировать
  uppercase.
- `BroadcastRecipientEntity` не импортируется: ссылается на отсутствующий
  `src.modules.broadcast.domain.recipient.enum.BroadcastRecipientStatus`.
- `BroadcastRecipientEntity` уже содержит полезные поля под MVP: `variables`, `recipient_snapshot`, `scheduled_at`,
  `communication_request_id`, `outbound_message_id`, счетчики attempts/status.
- В `src/modules/router.py` нет подключения `broadcast_router`.
- В `src/modules/schema_registry/seed/schema_seed.py` нет runtime objects для broadcast.
- `communication` уже имеет публичный send-контракт `SendCommunicationCommand` с нужными полями: `initiator_type`,
  `initiator_ref_id`, `correlation_id`, `idempotency_key`, `channel_code`, `template_id`, `recipient_identifier_type`,
  `recipient_address`, `recipient_snapshot`, `variables`, `scheduled_at`, `priority`.
- `communication` template flow уже возвращает provider `field_schema`/`ui_schema` и принимает `template_payload` +
  `variables_schema`.
- `communication` сохраняет `scheduled_at` в `communication_request`, но текущий claim/publish flow ориентируется на
  `communication_outbound_message.next_attempt_at` и не использует `scheduled_at` как deferred delivery gate. Поэтому в
  MVP `broadcast` должен вызывать `communication` только когда recipient уже due, либо надо отдельно доработать
  `communication` queue semantics.

## Целевой бизнес-flow

1. Пользователь нажимает "Создать рассылку".
2. UI создает или открывает `DRAFT` broadcast.
3. Пользователь выбирает готовый шаблон из `communication` или создает новый.
4. Если шаблон создается, боковая панель:
    - показывает provider connectors/message types;
    - позволяет выбрать provider, channel/message type;
    - строит форму по `field_schema`/`ui_schema`;
    - сохраняет `message_template`, `template_version`;
    - активирует версию или требует активации перед подготовкой.
5. Выбранный/созданный шаблон закрепляется за `broadcast`.
6. UI строит список обязательных колонок:
    - `recipient_address` всегда обязателен;
    - остальные поля берутся из `active_template_version.variables_schema`.
7. Пользователь прикрепляет аудиторию:
    - paste text: одна строка - один контакт, значения в строке разделены `,`;
    - upload `.txt`/`.csv`: файл читается, парсится и не сохраняется;
    - universal lists: future adapter, без сохранения ссылки на source в MVP.
8. Backend парсит input через adapter, валидирует, сохраняет recipient rows в broadcast и возвращает stats.
9. UI показывает таблицу получателей, total rows, unique recipients, valid recipients, invalid/duplicate counts.
10. Пользователь задает параметры оркестрации:
    - равномерно растянуть рассылку по времени;
    - ограничить дни недели и daily window;
    - или задать скорость в штуках в минуту/час.
11. Пользователь нажимает "Создать".
12. Backend переводит broadcast `DRAFT -> PREPARING`, фиксирует active template version, валидирует audience/settings,
    строит `scheduled_at` для recipients.
13. Если подготовка успешна, broadcast переходит в `READY`; если нет - `FAILED` с reason или возвращается в editable
    state по решению API.
14. Пользователь нажимает `START`.
15. Backend переводит broadcast в `SCHEDULED`/`RUNNING`.
16. Scheduler/worker claim-ит due recipients и вызывает `communication.SendCommunicationUseCase`.
17. Для каждого recipient сохраняются `communication_request_id` и `outbound_message_id`.
18. Когда все valid recipients dispatched или terminal, broadcast переходит в `COMPLETED`.

## Границы модулей

`broadcast` владеет:

- broadcast definition;
- attached template reference;
- import parsing orchestration;
- recipient snapshot rows;
- validation status на уровне audience;
- dedupe;
- orchestration settings;
- calculated recipient `scheduled_at`;
- dispatch locks;
- idempotency keys для communication calls;
- mapping recipient -> communication request/outbound ids;
- pause/cancel/resume semantics на уровне будущих dispatches.

`broadcast` не владеет:

- provider connectors/connections;
- provider-specific template payload rendering;
- HTTP/SMTP/SMS/Viber adapters;
- delivery attempts/events/webhooks;
- persistent file storage for uploaded audience files;
- dynamic CRM/universal list membership lifecycle in MVP.

`communication` владеет:

- provider catalog;
- provider connections;
- message templates and versions;
- JSON schema validation of template variables;
- communication request/outbound persistence;
- provider rendering;
- send attempts and delivery events.

## MVP data model

Для первого релиза достаточно двух runtime objects. `BroadcastRun` можно не вводить, пока одна рассылка означает одно
выполнение. Если позже нужна повторная отправка той же definition по новой аудитории, добавить `broadcast_run` и
перенести recipient rows под run.

### `broadcast`

Поля:

- `id`;
- `tenant_id` через runtime tenant scope;
- `name`;
- `description`;
- `status`;
- `template_id`;
- `template_version_id`;
- `provider_connector_id`;
- `provider_message_type_id`;
- `channel_code`;
- `message_class`;
- `mapping_config`;
- `orchestration_config`;
- `total_rows`;
- `unique_recipients_count`;
- `valid_recipients_count`;
- `invalid_recipients_count`;
- `duplicate_recipients_count`;
- `prepared_at`;
- `scheduled_at`;
- `started_at`;
- `paused_at`;
- `completed_at`;
- `cancelled_at`;
- `failed_at`;
- `failure_reason`;
- `created_at`;
- `updated_at`.

Indexes:

- unique `id`;
- `status`;
- `template_id`;
- `channel_code`;
- `created_at`;
- optional `(status, scheduled_at)` for scheduler scans.

Relations:

- many-to-one `template_id -> communication_message_template.id`;
- many-to-one `template_version_id -> communication_template_version.id`.

### `broadcast_recipient`

Поля:

- `id`;
- `broadcast_id`;
- `row_number`;
- `recipient_address`;
- `recipient_identifier_type`;
- `recipient_raw_value`;
- `recipient_normalized_value`;
- `recipient_hash`;
- `variables`;
- `recipient_snapshot`;
- `status`;
- `validation_errors`;
- `dedupe_key`;
- `duplicate_of_recipient_id`;
- `scheduled_at`;
- `processing_started_at`;
- `processing_lock_until`;
- `processing_token`;
- `sent_to_communication_at`;
- `communication_request_id`;
- `outbound_message_id`;
- `attempt_count`;
- `last_error`;
- `created_at`;
- `updated_at`.

Indexes:

- unique `id`;
- `(broadcast_id, row_number)`;
- `(broadcast_id, status)`;
- `(broadcast_id, scheduled_at)`;
- `(broadcast_id, dedupe_key)`;
- `(processing_token)`;
- `(status, scheduled_at)` for dispatch scans.

Relations:

- many-to-one `broadcast_id -> broadcast.id`;
- optional reference `communication_request_id -> communication_request.id`;
- optional reference `outbound_message_id -> communication_outbound_message.id`.

## Domain model

Добавить/починить:

- `domain/broadcast/value_object/broadcast_status.py`
    - `DRAFT`, `PREPARING`, `READY`, `SCHEDULED`, `RUNNING`, `PAUSED`, `COMPLETED`, `CANCELLED`, `FAILED`.
- `domain/broadcast/value_object/broadcast_settings.py`
    - legacy alias или заменить на `BroadcastOrchestrationConfigVO`.
- `domain/broadcast/value_object/broadcast_mapping_config.py`
    - mapping source columns to `recipient_address` and template variables.
- `domain/broadcast/entity.py`
    - объявить `source_id` только если нужен; для MVP лучше убрать source object и хранить только recipients.
    - заменить `ValueError` на domain errors.
    - запретить редактирование после `PREPARING`, кроме allowed pause/cancel.
- `domain/recipient/enum.py`
    - `DRAFT`, `READY`, `INVALID`, `DUPLICATE`, `SCHEDULED`, `CLAIMED`, `SENT_TO_COMMUNICATION`, `FAILED`, `CANCELLED`.
- `domain/recipient/entity.py`
    - использовать единый import style `src.modules...`;
    - добавить methods `mark_invalid`, `mark_duplicate`, `schedule`, `claim`, `mark_sent_to_communication`,
      `mark_failed`, `cancel`.
- `domain/source`
    - не хранить файл/source. Оставить только value objects для `AudienceImportType`: `PASTE`, `CSV_FILE`, `TXT_FILE`,
      `UNIVERSAL_LIST`.
- `domain/stats`
    - DTO/value object для total/unique/valid/invalid/duplicate.

## Application layer

### Use cases

1. `CreateBroadcastDraftUseCase`
    - input: name, description, optional `template_id`, optional settings.
    - output: `BroadcastDTO`.
    - status: `DRAFT`.

2. `AttachBroadcastTemplateUseCase`
    - input: `broadcast_id`, `template_id`.
    - validates template exists and has compatible channel.
    - clears existing audience/schedule if variables schema changed.

3. `ImportBroadcastAudienceUseCase`
    - input: `broadcast_id`, `import_type`, text/file stream/list ref, `mapping_config`.
    - uses adapter by `import_type`;
    - never writes uploaded file to `file_storage` or runtime table;
    - stores normalized recipient rows and stats;
    - replaces previous draft audience unless API explicitly supports append.

4. `PreviewBroadcastAudienceUseCase`
    - same parser/validator, but no persistence.
    - useful before save and for frontend table preview.

5. `UpdateBroadcastOrchestrationUseCase`
    - input: schedule mode, timezone, weekday windows, rate/spread config.
    - validates that config is internally consistent.

6. `PrepareBroadcastUseCase`
    - status: `DRAFT -> PREPARING -> READY` or `FAILED`.
    - locks broadcast;
    - loads active template version from `communication`;
    - validates all recipient variables by `variables_schema`;
    - calculates `scheduled_at`;
    - marks invalid/duplicate rows non-dispatchable;
    - stores `template_version_id` snapshot.

7. `StartBroadcastUseCase`
    - status: `READY -> SCHEDULED`.
    - does not call providers directly.
    - enables dispatch worker to process due recipients.

8. `DispatchDueRecipientsUseCase`
    - input: tenant_id, limit, now.
    - claim due `broadcast_recipient` rows with `status=SCHEDULED` and `scheduled_at <= now`;
    - calls `SendCommunicationUseCase`;
    - uses deterministic ids/idempotency;
    - saves communication ids and status.

9. `PauseBroadcastUseCase`
    - stops future claims.
    - already claimed recipients may finish.

10. `CancelBroadcastUseCase`
    - marks undispatched recipients `CANCELLED`.
    - does not cancel already accepted communication outbound messages unless a separate communication cancel API
      appears.

11. `ListBroadcastsUseCase`
12. `GetBroadcastUseCase`
13. `ListBroadcastRecipientsUseCase`
14. `GetBroadcastStatsUseCase`

### Ports

`broadcast` should depend on application ports, not communication infrastructure:

- `MessageTemplateLookupPort`
    - get template;
    - get active template version;
    - expose variables schema, channel, message_class.
- `CommunicationSendPort`
    - wraps `SendCommunicationUseCase`.
- `AudienceImportAdapter`
    - parse `PASTE`, `CSV_FILE`, `TXT_FILE`, future `UNIVERSAL_LIST`.
- `BroadcastRepositoryProtocol`
- `BroadcastRecipientRepositoryProtocol`
- `ClockPort`
- `IdProvider`.

## Import adapters

All import adapters return normalized in-memory parse result:

```text
AudienceImportResult
  rows: list[AudienceImportRow]
  errors: list[AudienceImportError]
  stats: AudienceImportStats
```

`AudienceImportRow`:

```text
row_number
recipient_address
raw_values
variables
recipient_snapshot
```

Paste adapter:

- input: string;
- split by line breaks;
- skip empty lines;
- split each row by comma;
- trim whitespace;
- support optional header row;
- without header use expected columns: `recipient_address`, then template variable names in deterministic order.

CSV/TXT adapter:

- input: uploaded stream;
- validate extension and max size at HTTP boundary;
- parse stream;
- do not write file to disk/runtime/file_storage;
- return rows/errors.

Universal lists adapter:

- future only;
- input: list id/filter snapshot id;
- resolve records through a public application boundary of that module;
- store resolved recipient rows only;
- do not keep live source link for dispatch.

## Validation and dedupe

Required:

- `recipient_address` non-empty;
- `recipient_address` normalized for channel:
    - email channel -> lowercase/trim and email shape;
    - sms/viber/phone channels -> phone normalization through `contact_point` normalizer if available;
    - fallback -> trim only.
- variables validate against active template `variables_schema`.
- unknown columns are allowed only if mapping says to include them in `recipient_snapshot`; they should not be sent as
  template variables by default.
- duplicates are detected by `dedupe_key = channel_code + recipient_normalized_value`.

Stats:

- `total_rows`: parsed rows before invalid filtering;
- `unique_recipients_count`: unique normalized recipients;
- `valid_recipients_count`: valid and non-duplicate rows;
- `invalid_recipients_count`: rows with validation errors;
- `duplicate_recipients_count`: rows duplicated by dedupe key.

Dispatch policy:

- `INVALID` and `DUPLICATE` rows are visible in table but not scheduled.
- Only `SCHEDULED` rows are claimable by worker.

## Orchestration settings

Use one config object:

```json
{
  "mode": "SPREAD_EVENLY",
  "timezone": "Europe/Kiev",
  "start_at": "2026-06-05T10:00:00+03:00",
  "end_at": "2026-06-05T18:00:00+03:00",
  "allowed_windows": [
    {
      "weekday": 1,
      "from": "09:00",
      "to": "18:00"
    },
    {
      "weekday": 2,
      "from": "09:00",
      "to": "18:00"
    }
  ],
  "rate": null
}
```

Alternative rate config:

```json
{
  "mode": "RATE_LIMIT",
  "timezone": "Europe/Kiev",
  "start_at": "2026-06-05T10:00:00+03:00",
  "allowed_windows": [
    {
      "weekday": 1,
      "from": "09:00",
      "to": "18:00"
    }
  ],
  "rate": {
    "amount": 120,
    "unit": "HOUR"
  }
}
```

Rules:

- `SPREAD_EVENLY` requires finite `start_at` and `end_at`.
- `RATE_LIMIT` requires `rate.amount > 0` and `unit in MINUTE/HOUR`.
- weekdays and local time windows are interpreted in config timezone.
- persist `scheduled_at` in UTC.
- if no allowed slot exists for a recipient, preparation fails before `READY`.

Scheduling algorithm:

- Build ordered list of dispatchable recipients by `row_number`.
- Build allowed timeline slots from `start_at/end_at` and weekday windows.
- `SPREAD_EVENLY`: distribute recipients across available seconds with stable spacing.
- `RATE_LIMIT`: calculate interval from rate, e.g. `60 / amount` seconds for minute or `3600 / amount` for hour, then
  move timestamps forward to next allowed slot.
- Save each recipient `scheduled_at`.

## Dispatch to communication

For each due recipient call:

```text
SendCommunicationCommand(
  tenant_id=broadcast.tenant_id,
  initiator_type="BROADCAST",
  initiator_ref_id=str(recipient.id),
  correlation_id=broadcast.id,
  idempotency_key=f"broadcast:{broadcast.id}:{recipient.id}",
  channel_code=broadcast.channel_code,
  template_id=broadcast.template_id,
  recipient_identifier_type=recipient.recipient_identifier_type,
  recipient_address=recipient.recipient_address,
  recipient_snapshot=recipient.recipient_snapshot,
  variables=recipient.variables,
  scheduled_at=recipient.scheduled_at,
  priority=calculated_or_default,
)
```

Important MVP rule:

- Do not enqueue all future recipients into `communication` at `START`, because current `communication` claim/publish
  logic does not use request `scheduled_at` as a delay gate.
- The broadcast worker should call `communication` only when `recipient.scheduled_at <= now`.
- If a later change makes `communication` respect `scheduled_at`, `broadcast` may enqueue all rows at start and let
  `communication` own deferred processing.

## HTTP API

Add `src/modules/broadcast/presentation/http/router.py` and include it in `src/modules/router.py`.

Recommended endpoints:

- `POST /api/broadcasts`
    - create draft.
- `GET /api/broadcasts`
    - list broadcasts.
- `GET /api/broadcasts/{broadcast_id}`
    - get details.
- `PATCH /api/broadcasts/{broadcast_id}`
    - update name/description while editable.
- `POST /api/broadcasts/{broadcast_id}/template`
    - attach selected template.
- `POST /api/broadcasts/{broadcast_id}/audience/preview`
    - parse and validate without persistence.
- `POST /api/broadcasts/{broadcast_id}/audience/import`
    - paste or multipart file upload, parse and persist recipient rows.
- `GET /api/broadcasts/{broadcast_id}/recipients`
    - paginated table with filters by status/search.
- `PATCH /api/broadcasts/{broadcast_id}/orchestration`
    - set schedule/rate rules.
- `POST /api/broadcasts/{broadcast_id}/prepare`
    - `DRAFT -> PREPARING -> READY`.
- `POST /api/broadcasts/{broadcast_id}/start`
    - `READY -> SCHEDULED`.
- `POST /api/broadcasts/{broadcast_id}/pause`
- `POST /api/broadcasts/{broadcast_id}/resume`
- `POST /api/broadcasts/{broadcast_id}/cancel`
- `GET /api/broadcasts/{broadcast_id}/stats`

For the UI "Создать" button, call `prepare`. If the first page creates a draft automatically, final "Создать" should
mean "prepare final broadcast", not "insert first row".

## Background processing

Add management commands:

```text
dnk-manage broadcast prepare --tenant-id <uuid> --broadcast-id <uuid>
dnk-manage broadcast dispatch-due --tenant-id <uuid> [--limit 100]
dnk-manage broadcast worker
```

MVP worker loop:

1. scan broadcasts in `SCHEDULED`/`RUNNING`;
2. claim due recipients;
3. mark broadcast `RUNNING` once first recipient is claimed;
4. call communication;
5. update recipient status;
6. recalculate completion when no dispatchable rows remain.

Use runtime gateway atomic claim with processing token/lease. Do not claim rows for paused/cancelled broadcasts.

## Frontend plan

Create `frontends/apps/console/src/modules/broadcast`.

Files:

- `routes.ts`;
- `index.ts`;
- `api/broadcast.api.ts`;
- `api/types.ts`;
- `pages/BroadcastsPage.vue`;
- `pages/BroadcastEditorPage.vue`;
- `components/BroadcastHeader.vue`;
- `components/TemplateStep.vue`;
- `components/TemplateEditorSheet.vue`;
- `components/AudienceImportStep.vue`;
- `components/RecipientsTable.vue`;
- `components/RecipientStatsBar.vue`;
- `components/OrchestrationStep.vue`;
- `components/BroadcastStatusBadge.vue`.

Wire:

- add `broadcastRoutes` to `frontends/apps/console/src/app/router.ts`;
- add nav item under current CDP group in `workspace-navigation.ts`.

UX:

- first screen is broadcasts list, not marketing page;
- editor is a dense workflow screen with steps: Template, Audience, Orchestration, Review;
- template creation opens side sheet and uses communication provider catalog;
- audience import supports paste textarea and file input;
- recipients table shows row number, `recipient_address`, variables, status/errors;
- stats always visible: total, unique, valid, invalid, duplicates;
- final action label: "Создать" while draft, "Start" when ready.

## Implementation milestones

### M0. Stabilize current broadcast skeleton

- Fix missing imports/types in `BroadcastEntity`.
- Add missing recipient enum.
- Normalize status values.
- Add domain errors.
- Add focused unit tests that import broadcast domain entities.

Acceptance:

-
`uv run python -c "import src.modules.broadcast.domain.broadcast.entity; import src.modules.broadcast.domain.recipient.entity"`
succeeds.

### M1. Runtime objects and repositories

- Add broadcast runtime object seeds.
- Add runtime object name constants.
- Implement row mappers.
- Implement `BroadcastRuntimeRepository`.
- Implement recipient repository with list/replace/claim methods.

Acceptance:

- schema seed applies;
- repository tests cover save/get/list/claim.

### M2. Template boundary

- Add `MessageTemplateLookupPort`.
- Implement adapter using communication application/query repository or public use cases.
- Ensure prepare stores active `template_version_id`.
- Validate channel/message class from template.

Acceptance:

- broadcast can attach an active communication template and read variables schema.

### M3. Audience import

- Implement paste parser.
- Implement CSV/TXT stream parser.
- Implement mapping config.
- Implement preview and import use cases.
- Add validation/dedupe/stats.

Acceptance:

- uploaded file is not persisted;
- import stores only recipient rows;
- stats match table rows.

### M4. Orchestration preparation

- Implement schedule config VO and validation.
- Implement spread/rate scheduling.
- Implement `PrepareBroadcastUseCase`.

Acceptance:

- `DRAFT -> PREPARING -> READY`;
- invalid config fails before `READY`;
- all valid recipients get UTC `scheduled_at`.

### M5. Dispatch

- Implement `CommunicationSendPort`.
- Implement due-recipient claim.
- Implement deterministic idempotency.
- Implement `DispatchDueRecipientsUseCase`.
- Add management command/worker.

Acceptance:

- due recipients call `SendCommunicationUseCase`;
- communication ids are stored;
- repeated worker run is idempotent.

### M6. HTTP API

- Add request/response schemas.
- Add controllers and router.
- Wire router under `/api`.
- Add HTTP tests.

Acceptance:

- create/import/prepare/start/list recipients flow passes via TestClient.

### M7. Frontend

- Add broadcast module routes/nav/API.
- Build editor workflow.
- Reuse communication provider/template endpoints for template creation/selection.
- Add recipient table and stats.
- Add orchestration controls.

Acceptance:

- user can create draft, attach/create template, import audience, prepare, start.

### M8. Observability and docs

- Update `docs/modules/broadcast.md` from roadmap to implemented status.
- Document API contracts.
- Add known gap: universal lists future adapter.
- Add worker command docs.

## Test plan

Backend:

- domain status transitions;
- import adapters for paste/csv/txt;
- mapping config;
- variables schema validation;
- dedupe and stats;
- scheduling algorithms;
- repository persistence;
- claim idempotency;
- dispatch to communication mock port;
- HTTP endpoints;
- architecture boundary test: `broadcast` must not import provider senders/adapters.

Frontend:

- API client type tests if available;
- component tests for stats and recipient table;
- Playwright/manual browser check for wizard flow once implemented.

Useful commands:

```bash
uv run python -m compileall src/modules/broadcast
uv run python -m unittest test.test_broadcast_domain -v
uv run python -m unittest test.test_broadcast_import -v
uv run python -m unittest test.test_broadcast_scheduler -v
uv run python -m unittest test.test_broadcast_http_router -v
```

## Open decisions

- Whether one `broadcast` can be started only once, or whether repeated runs require `BroadcastRun` now.
- Whether duplicates are skipped by default or user can choose to include them.
- Whether invalid rows keep broadcast in `READY` with skipped rows, or make prepare fail.
- Whether `communication` should be enhanced to respect `scheduled_at`, or broadcast remains the sole scheduler.
- Exact universal lists public contract when that module appears.
