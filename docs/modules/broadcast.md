# Модуль Broadcast

## Статус

Roadmap-документ M0 для фиксации границ. `broadcast` пока не реализован в `src/modules`.

Документ фиксирует целевые границы bounded context до добавления runtime objects, API и workers.

## Назначение

`broadcast` владеет tenant-scoped массовой отправкой по уже выбранной аудитории. Он принимает segment snapshot или явный
audience input, резолвит recipients для конкретного channel, создает неизменяемый recipient snapshot и делегирует
фактическую отправку сообщений в `communication`.

`broadcast` отвечает на вопрос:

```text
audience snapshot + channel policy + template choice -> recipient send requests
```

## Граница ответственности

`broadcast` владеет:

- broadcast definition и lifecycle;
- привязкой audience snapshot к конкретному run;
- созданием recipient snapshot;
- contact point selection policy для конкретного broadcast;
- recipient-level send state с точки зрения broadcast;
- fan-out в send use cases модуля `communication`;
- throttling и batching на уровне broadcast run;
- cancel/pause/resume broadcast run;
- связями между broadcast recipients и `communication` outbound messages.

`broadcast` не владеет:

- расчетом dynamic segments;
- campaign goals, business metrics или CRM campaign lifecycle;
- выполнением workflow graph;
- provider-specific payload rendering;
- provider connection management;
- прямыми HTTP/SMTP/SMS/Viber send adapters;
- provider webhooks и delivery status mapping;
- нормализацией contact point или lifecycle привязок.

## Доменные понятия

- `Broadcast`: настроенное намерение массовой отправки.
- `BroadcastRun`: конкретное выполнение broadcast definition.
- `BroadcastAudienceSnapshot`: неизменяемый source audience для run.
- `BroadcastRecipient`: recipient snapshot, полученный из audience subject и выбранного contact point.
- `ContactPointSelectionPolicy`: правила выбора contact point по channel/type/primary/fallback.
- `BroadcastDispatchBatch`: batch recipients, запланированных для communication send calls.
- `BroadcastRecipientStatus`: локальный статус run, например `PENDING`, `QUEUED`, `SENT_TO_COMMUNICATION`, `SKIPPED`,
  `FAILED`, `CANCELLED`.

## Планируемая application surface

Основные use cases:

| Use Case                            | Вход                                               | Выход                        | Примечание о границе                                         |
|-------------------------------------|----------------------------------------------------|------------------------------|--------------------------------------------------------------|
| `CreateBroadcastUseCase`            | metadata, audience source, channel/template policy | `BroadcastDTO`               | Создает draft/sendable broadcast definition.                 |
| `PreviewBroadcastRecipientsUseCase` | broadcast id или transient config                  | `BroadcastPreviewDTO`        | Резолвит count/sample без сохранения run.                    |
| `CreateBroadcastRunUseCase`         | broadcast id и audience snapshot                   | `BroadcastRunDTO`            | Фиксирует audience и recipient selection inputs.             |
| `BuildRecipientSnapshotUseCase`     | run id                                             | `BroadcastRunDTO`            | Резолвит contact points и сохраняет recipient rows.          |
| `StartBroadcastRunUseCase`          | run id                                             | `BroadcastRunDTO`            | Помечает run готовым к dispatch.                             |
| `DispatchBroadcastBatchUseCase`     | run id и limit                                     | `BroadcastDispatchResultDTO` | Вызывает `communication` для pending recipients.             |
| `PauseBroadcastRunUseCase`          | run id                                             | `BroadcastRunDTO`            | Останавливает будущий dispatch без удаления recipient state. |
| `CancelBroadcastRunUseCase`         | run id                                             | `BroadcastRunDTO`            | Отменяет undispatched recipients.                            |
| `ListBroadcastRecipientsUseCase`    | run id и paging                                    | `BroadcastRecipientPageDTO`  | Состояние recipients конкретного run в режиме только чтения. |

Все provider-specific rendering и send attempts остаются за `communication.SendCommunicationUseCase`.

## Направление зависимостей

Разрешенные исходящие зависимости:

| Зависимость       | Для чего используется                                                                     |
|-------------------|-------------------------------------------------------------------------------------------|
| `shared`          | IDs, domain errors, clock/UUID ports, UoW и request context dependencies.                 |
| `segmentation`    | Получение active segment subjects или чтение calculation snapshot.                        |
| `contact_point`   | Резолвинг конкретного contact point для audience subject и channel policy.                |
| `communication`   | Создание outbound communication requests и чтение outbound ids/status summaries.          |
| `schema_registry` | Runtime object descriptors и object feature metadata для broadcast-owned runtime objects. |
| `runtime_data`    | Хранение/поиск broadcast runtime rows, если broadcast objects descriptor-backed.          |

Запрещенные исходящие зависимости:

- `campaigns`;
- `workflow`;
- provider HTTP clients, SMTP clients или SMS provider adapters;
- provider connector/connection internals вне публичной application boundary модуля `communication`.

Разрешенные входящие вызовы:

- `campaigns` может создавать или запускать broadcasts как campaign actions.
- `workflow` может вызывать broadcast actions через generic action port.
- `communication` может запрашиваться модулем `broadcast`, но не должен вызывать broadcast обратно для delivery.

## Межмодульный контракт

`broadcast` передает в `communication` нормализованную send command:

```text
tenant_id
initiator_type = BROADCAST
initiator_ref_id = broadcast_run_id or recipient_id
correlation_id
idempotency_key
channel_code
template_id
recipient_address
recipient_snapshot
variables
scheduled_at
priority
```

Broadcast recipient хранит возвращенный `communication_request_id` и/или `outbound_message_id` для traceability. Он не
хранит provider request payloads или provider response payloads как собственное состояние.

## Правила реализации

- `broadcast` не должен импортировать provider sender adapters.
- Recipient snapshots неизменяемы, кроме локальных processing/status fields.
- Contact point resolution выполняется один раз при build recipient snapshot, если не создан новый run.
- `segmentation` является источником audience membership; `broadcast` не выполняет dynamic segment DSL.
- Dispatch должен быть идемпотентным на recipient через deterministic idempotency keys.
- Delivery events остаются в `communication`; `broadcast` может читать summarized communication state или реагировать на
  normalized status events через integration boundary.

## Связанная документация

- [Segmentation Module](./segmentation.md)
- [Communication Module](./communication.md)
- [Contact Point Module](./contact_point.md)
- [Campaigns Module](./campaigns.md)
- [Workflow Module](./workflow.md)
- [Communication segment lifecycle plan](../plan/communication_segment_lifecycle.md)

## Источник истины

- GitHub issue #36.
- `docs/plan/communication_segment_lifecycle.md`.
- Будущий `src/modules/broadcast/...`.
