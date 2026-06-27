# Модуль External Events

## Статус

Roadmap-документ M0 для фиксации границ. `external_events` пока не реализован в `src/modules`.

Файл документации называется `external-events.md`, чтобы соответствовать существующему стилю именования docs, а Python
module name должен использовать `external_events`.

## Назначение

`external_events` владеет ingestion, validation, idempotency и normalization событий, полученных извне runtime. Он
превращает provider/application/webhook-specific payloads в стабильные normalized events, которые могут потреблять
другие
модули.

`external_events` отвечает на вопрос:

```text
external payload + source config -> normalized tenant event
```

## Граница ответственности

`external_events` владеет:

- external source registration и source-level config;
- inbound event endpoint contracts;
- raw event persistence для audit и replay;
- event schema validation;
- idempotency/deduplication;
- payload normalization в canonical event fields;
- event type catalog и versioning;
- публикацией normalized events через shared event/outbox boundaries;
- replay сохраненных raw или normalized events.

`external_events` не владеет:

- campaign goals или metrics;
- выполнением workflow graph;
- future bulk recipient dispatch;
- communication provider delivery webhooks, которые принадлежат `communication`;
- CRM record mutation policies;
- provider-specific outbound send adapters.

## Доменные понятия

- `ExternalEventSource`: настроенная система-источник или интеграция.
- `ExternalEventType`: tenant-visible event type и schema/version.
- `ExternalEventRawPayload`: исходный inbound payload с headers/source metadata.
- `NormalizedExternalEvent`: canonical event, публикуемый для других bounded contexts.
- `ExternalEventDedupKey`: source-scoped idempotency key.
- `ExternalEventReplay`: controlled replay сохраненных events.

## Планируемая application surface

Основные use cases:

| Use Case                                | Вход                          | Выход                           | Примечание о границе                                            |
|-----------------------------------------|-------------------------------|---------------------------------|-----------------------------------------------------------------|
| `RegisterExternalEventSourceUseCase`    | source metadata и auth/config | `ExternalEventSourceDTO`        | Создает definition источника.                                   |
| `RegisterExternalEventTypeUseCase`      | event type code и schema      | `ExternalEventTypeDTO`          | Определяет допустимую normalized event shape.                   |
| `IngestExternalEventUseCase`            | source id/code и raw payload  | `ExternalEventIngestResultDTO`  | Валидирует, дедуплицирует, нормализует и сохраняет event.       |
| `NormalizeExternalEventUseCase`         | raw event id                  | `NormalizedExternalEventDTO`    | Повторно запускает normalization при необходимости.             |
| `PublishNormalizedExternalEventUseCase` | normalized event id           | `ExternalEventPublishResultDTO` | Публикует через shared event/outbox boundary.                   |
| `ReplayExternalEventsUseCase`           | source/type/time filter       | `ExternalEventReplayDTO`        | Повторно публикует stored events под явным контролем оператора. |
| `ListExternalEventsUseCase`             | filters и paging              | `ExternalEventPageDTO`          | Доступ к audit/read model.                                      |

## Направление зависимостей

Разрешенные исходящие зависимости:

| Зависимость       | Для чего используется                                                                       |
|-------------------|---------------------------------------------------------------------------------------------|
| `shared`          | IDs, domain errors, clock/UUID ports, UoW, request context и shared event/outbox ports.     |
| `schema_registry` | Опциональные event object descriptors, source metadata descriptors и event schema metadata. |
| `runtime_data`    | Опциональное descriptor-backed event/source storage и audit search.                         |

Разрешенные входящие consumers:

- `workflow` может запускать runs из normalized event triggers.
- `campaigns` может обновлять business metrics из normalized events.
- другие business modules могут реагировать на normalized events через shared event consumers.

Запрещенные исходящие зависимости:

- `campaigns`;
- `workflow`;
- future bulk-send orchestration modules;
- `communication` provider sender internals;
- CRM/business modules, которые потребляют normalized events.

Особый случай:

- Provider delivery webhooks остаются в `communication`, потому что они обновляют outbound delivery state.
  `external_events` предназначен для external business/product events, а не provider delivery lifecycle callbacks.

## Межмодульный контракт

Normalized event payload, публикуемый `external_events`, должен включать:

```text
tenant_id
event_id
source_id
source_event_id
event_type
event_version
occurred_at
received_at
subject_object_id
subject_record_id
correlation_id
payload
```

Consumers должны использовать этот normalized contract. Они не должны зависеть от raw source payload shape, если только
они явно не владеют source-specific interpretation вне `external_events`.

## Правила реализации

- `external_events` не должен вызывать campaign use cases напрямую.
- Normalization должна быть идемпотентной по source и source event id/dedup key.
- Хранилище raw payload является append-only, кроме retention/cleanup policies.
- Normalized events должны быть неизменяемыми после publication; corrections должны создавать новую version или
  correction event.
- Event publication должна использовать shared event/outbox boundary, чтобы consumers могли развиваться независимо.
- Source auth, request signature checks и payload schema validation принадлежат event ingestion boundary.

## Связанная документация

- [Workflow Module](./workflow.md)
- [Campaigns Module](./campaigns.md)
- [Communication Module](./communication.md)
- [Runtime Data Module](./runtime-data.md)
- [Schema Registry Module](./schema-registry.md)

## Источник истины

- GitHub issue #36.
- Будущий `src/modules/external_events/...`.
