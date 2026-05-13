# Communication Module

## Назначение

`communication` отвечает за tenant-scoped отправку и сопровождение сообщений через внешних провайдеров. Модуль хранит
каталог provider connectors, tenant-specific provider connections, шаблоны сообщений, concrete outbound messages,
попытки отправки, delivery events и обработку provider webhooks.

Модуль нужен как общий слой коммуникаций для других фич проекта: бизнес-модуль формирует команду отправки, а
`communication` выбирает активный шаблон и provider connection, ставит сообщение в очередь, рендерит payload, отправляет
его через provider sender и обновляет delivery state.

## Основные Возможности

- импорт YAML provider connector spec в runtime schema tenant
- хранение provider message types, schemas и transport-specific send spec
- создание и чтение provider connections без отдачи secrets наружу
- создание message templates, версионирование payload и активация версии
- постановка outbound communication на отправку с idempotency support
- чтение outbound messages и их provider/debug snapshots
- обработка очереди через RabbitMQ worker или management CLI
- запись delivery attempts и provider delivery events
- обработка provider webhooks и обновление internal status

## Архитектура

Модуль следует общей слоистой архитектуре проекта и использует runtime objects вместо собственных SQLAlchemy моделей.

- `domain`
  - агрегаты, value objects, enum/status types, доменные ошибки, domain services и repository protocols
  - не зависит от FastAPI, SQLAlchemy, RabbitMQ и concrete runtime gateways
- `application`
  - commands, queries, DTO, use cases и application-level ports
  - содержит helper services для YAML parsing, JSON Schema validation, Jinja rendering, JSONPath extraction, status
    mapping, provider payload building и secret encoding
- `infrastructure`
  - runtime repositories поверх `runtime_data`, row mappers, provider senders, `httpx` client и RabbitMQ
    publisher/worker
  - реализует application/domain ports
- `presentation`
  - FastAPI routers/controllers, dependency builders и management builders
  - конвертирует HTTP/CLI input в commands/queries и мапит доменные/runtime ошибки в HTTP status codes

Основной поток данных:

```text
HTTP/CLI/worker
  -> presentation controller/builder
  -> application use case
  -> domain service/entity
  -> application/domain port
  -> infrastructure runtime repository/provider sender/RabbitMQ adapter
```

## Компоненты Домена

### Provider Connector

Provider connector описывает интеграцию с конкретным провайдером. Источник правды для connector-а - YAML spec,
импортируемый через `RegisterProviderConnectorUseCase`.

Состав:

- `ProviderConnector`
  - `provider_connector_id`
  - `provider_code`
  - `provider_name`
  - `version`
  - `connector_type`
  - `yaml_spec`
  - `yaml_checksum`
  - `status`
  - `created_at`, `updated_at`
- `ProviderMessageType`
  - message type внутри provider connector
  - содержит `message_type_code`, `channel_code`, `field_schema`, `ui_schema`, `is_active`

Поддерживаемые domain enum:

- `ConnectorType`
  - `YAML_HTTP`
  - `YAML_SMTP`
  - `CUSTOM_ADAPTER`
- `ConnectorStatus`
  - `ACTIVE`
  - `DISABLED`
  - `DEPRECATED`

Важные правила:

- YAML loader сейчас поддерживает только `YAML_HTTP` и `YAML_SMTP`.
- `CUSTOM_ADAPTER` есть в enum, но не поддержан текущим YAML loader.
- root-level `send` в YAML запрещён; `send` должен быть описан внутри каждого `message_types[]`.
- `ProviderYamlLoader` валидирует required fields, JSON Schemas и transport-specific send spec.
- checksum считается по canonical JSON версии YAML spec.
- repository делает upsert connector-а по `provider_code + version`.
- message types upsert-ятся по `provider_connector_id + message_type_code`.

Минимальная структура YAML spec:

```yaml
provider_code: resend
provider_name: Resend
version: "1.0"
connector_type: YAML_HTTP
channels:
  - EMAIL
config_schema:
  type: object
secrets_schema:
  type: object
message_types:
  - code: email
    channel: EMAIL
    name: Email
    field_schema:
      type: object
    ui_schema: {}
    send:
      transport: http
      method: POST
      url: "https://api.example.com/messages"
      body: {}
      response_mapping:
        external_message_id: "$.id"
        external_status: "$.status"
status_mapping:
  sent: SENT
webhook:
  external_message_id_path: "$.id"
  external_status_path: "$.status"
  event_time_path: "$.created_at"
```

### Provider Connection

Provider connection - tenant-specific подключение к provider connector. Оно хранит runtime config, ссылку на secret и
encoded secrets, но HTTP response никогда не возвращает сами secrets.

Состав:

- `ProviderConnectionEntity`
  - `provider_connection_id`
  - `tenant_id`
  - `provider_connector_id`
  - `connection_code`
  - `connection_name`
  - `channel_code`
  - `config`
  - `secret_ref`
  - `secrets_b64`
  - `status`
  - `created_at`, `updated_at`

Правила:

- при создании проверяется существование provider connector
- `channel_code` должен входить в `yaml_spec.channels`
- `config` валидируется по `config_schema`
- `secrets` валидируются по `secrets_schema`
- secrets кодируются через `SecretCodec` как base64 JSON
- наружу отдаются только `secret_ref` и `has_secrets`
- active lookup для send-сценария ищет connection по `provider_connector_id + channel_code + ACTIVE`

Статусы:

- `ACTIVE`
- `DISABLED`

### Message Template

Message template описывает tenant-local шаблон сообщения, привязанный к provider connector и provider message type.
Header шаблона отделён от версий payload.

Состав:

- `MessageTemplateEntity`
  - `template_id`
  - `tenant_id`
  - `template_code`
  - `name`
  - `description`
  - `provider_connector_id`
  - `provider_message_type_id`
  - `channel_code`
  - `message_class`
  - `status`
  - `created_at`, `updated_at`
- `TemplateVersionEntity`
  - `template_version_id`
  - `template_id`
  - `version`
  - `template_payload`
  - `variables_schema`
  - `status`
  - `created_at`
  - `activated_at`

Правила:

- при создании template проверяется существование connector и message type
- `provider_message_type_id` должен принадлежать выбранному `provider_connector_id`
- `channel_code` template должен совпадать с channel message type
- новая template version создаётся в `DRAFT`
- `template_payload` валидируется по `ProviderMessageType.field_schema`
- `variables_schema` валидируется как JSON Schema
- активация версии переводит выбранную version в `ACTIVE`, прежние active versions в `DEPRECATED`, а template в `ACTIVE`

Статусы template:

- `DRAFT`
- `ACTIVE`
- `ARCHIVED`

Статусы version:

- `DRAFT`
- `ACTIVE`
- `DEPRECATED`

Классы сообщений:

- `MARKETING`
- `TRANSACTIONAL`
- `SERVICE`
- `OTP`
- `INFO`

Каналы:

- `SMS`
- `VIBER`
- `EMAIL`
- `CUSTOM`

### Outbound Message

Outbound часть разделяет входящий communication request и concrete provider message.

Состав:

- `CommunicationRequest`
  - входящая команда отправки
  - хранит initiator, idempotency key, template, recipient, variables, schedule, priority и request status
- `OutboundMessage`
  - concrete provider message
  - хранит provider connection, rendered payload, provider request payload, external provider ids/statuses, internal
    status, processing lease, retry timestamps и queue publishing metadata

Правила send-сценария:

- `SendCommunicationUseCase` требует `template_id` или `template_code`
- если указан `idempotency_key`, use case сначала ищет существующий send request
- channel команды должен совпадать с channel template
- у template должна быть active version
- `variables` валидируются по `active_version.variables_schema`
- для template channel должен существовать active provider connection
- создаются `CommunicationRequest` со статусом `QUEUED` и `OutboundMessage` со статусом `QUEUED`
- HTTP controller коммитит создание и только после commit публикует job в RabbitMQ, если queue включена

Request statuses:

- `ACCEPTED`
- `REJECTED`
- `QUEUED`
- `PROCESSING`
- `COMPLETED`
- `FAILED`
- `CANCELED`

Outbound statuses:

- `QUEUED`
- `SENDING`
- `SENT`
- `DELIVERED`
- `OPENED`
- `CLICKED`
- `FAILED`
- `EXPIRED`
- `UNDELIVERED`
- `CANCELED`
- `UNKNOWN`

Processing модель:

- `PublishQueuedOutboundMessagesUseCase` публикует publishable `QUEUED` messages в broker
- worker получает job и запускает `ProcessOutboundMessageByIdUseCase`
- by-id processor атомарно claim-ит message через `processing_token` и `processing_deadline_at`
- template payload рендерится через Jinja2 `StrictUndefined`
- provider sender строит persisted-safe request snapshot и выполняет send
- success очищает processing lease, сохраняет rendered/provider payloads, external status и internal status
- failure без retry переводит message/request в failed state
- retryable failure возвращает message в `QUEUED`, выставляет `next_attempt_at` и сбрасывает `queue_published_at`
- `RecoverStuckOutboundMessagesUseCase` помечает истёкшие `SENDING` messages как `UNKNOWN` с ошибкой
  `PROCESSING_LEASE_EXPIRED`

### Delivery

Delivery часть хранит provider attempts и delivery events.

Состав:

- `DeliveryAttempt`
  - одна попытка provider send
  - хранит request/response snapshots, HTTP status, external message id, error и timestamps
- `DeliveryEvent`
  - событие доставки от provider webhook
  - хранит raw payload, external/internal statuses, event type, event time и ссылки на outbound/connection

Attempt statuses:

- `STARTED`
- `SUCCESS`
- `RETRYABLE_FAILED`
- `NON_RETRYABLE_FAILED`
- `TIMEOUT`

Delivery event types:

- `SENT`
- `DELIVERED`
- `FAILED`
- `EXPIRED`
- `OPENED`
- `CLICKED`
- `WEBHOOK_RECEIVED`

Webhook правила:

- webhook route принимает `tenant_id` и `provider_code` в публичном path
- connector ищется по `provider_code + ACTIVE`
- `external_message_id`, `external_status` и event time извлекаются JSONPath выражениями из `yaml_spec.webhook`
- outbound ищется по `external_message_id`
- если outbound не найден, webhook считается accepted, но `matched=false`
- если outbound найден, создаётся `DeliveryEvent` и обновляется status outbound message
- provider status мапится через `yaml_spec.status_mapping`; неизвестные значения дают `UNKNOWN`

## Application Layer

### Use Cases

Provider connector:

- `RegisterProviderConnectorUseCase`
- `ListProviderConnectorsUseCase`

Provider connection:

- `CreateProviderConnectionUseCase`
- `ListProviderConnectionsUseCase`

Message template:

- `CreateMessageTemplateUseCase`
- `CreateTemplateVersionUseCase`
- `ActivateTemplateVersionUseCase`
- `ListMessageTemplatesUseCase`

Outbound message:

- `SendCommunicationUseCase`
- `GetOutboundMessageUseCase`
- `ListOutboundMessagesUseCase`
- `ProcessOutboundMessageUseCase`
- `ProcessOutboundMessageByIdUseCase`
- `PublishQueuedOutboundMessagesUseCase`
- `RecoverStuckOutboundMessagesUseCase`

Delivery:

- `HandleProviderWebhookUseCase`

### Helper Services

- `ProviderYamlLoader`
  - парсит YAML, проверяет contract и считает checksum
- `JsonSchemaValidationService`
  - валидирует config, secrets, template payload и variables по JSON Schema Draft 2020-12
- `TemplateRenderService`
  - рекурсивно рендерит string leaves template payload через Jinja2 `StrictUndefined`
- `ProviderPayloadBuildService`
  - рендерит provider HTTP request method/url/headers/body из YAML send spec
- `ProviderStatusMappingService`
  - мапит external provider status в internal outbound status с fallback `UNKNOWN`
- `JsonPathService`
  - извлекает одно значение из provider response/webhook payload
- `SecretCodec`
  - кодирует/декодирует provider connection secrets как base64 JSON

## Порты Расширения

Domain repository ports:

- `ProviderConnectorRepositoryProtocol`
  - upsert provider connector и message types
- `ProviderConnectionRepositoryProtocol`
  - load/save/find active provider connection
- `ProviderConnectionProviderLookupProtocol`
  - lookup connector для правил connection
- `MessageTemplateRepositoryProtocol`
  - load/save template и template versions
- `MessageTemplateProviderLookupProtocol`
  - lookup connector/message type для правил template
- `OutboundMessageRepositoryProtocol`
  - idempotency lookup и создание send request/outbound message
- `DeliveryRepositoryProtocol`
  - attempts, events, webhook lookup и outbound status update
- `DeliveryAttemptServiceProtocol`
  - service port для processing adapter

Application/query/processing ports:

- `ProviderConnectorQueryRepositoryProtocol`
- `ProviderConnectionQueryRepositoryProtocol`
- `MessageTemplateQueryRepositoryProtocol`
- `OutboundMessageQueryRepositoryProtocol`
- `OutboundProcessingRepositoryProtocol`
- `OutboundProcessingByIdRepositoryProtocol`
- `OutboundProcessingRepositoryContextFactoryProtocol`
- `OutboundQueueRepositoryProtocol`

Provider integration ports:

- `ProviderSenderProtocol`
  - `transport`
  - `build(context) -> ProviderPreparedSend`
  - `send(context, prepared) -> ProviderSendResult`
- `ProviderSenderRegistryProtocol`
  - resolve sender by transport name
- `HttpClientProtocol`
  - outbound HTTP call abstraction
- `OutboundMessagePublisherProtocol`
  - публикация outbound job в broker

## Infrastructure Layer

### Runtime Repositories

Communication persistence реализован через runtime objects из `schema_registry` и gateways из `runtime_data`.
Репозитории резолвят runtime descriptor по `tenant_id + object_name`, затем работают через `RuntimeCommandGateway` и
`RuntimeQueryGateway`.

Runtime repositories:

- `ProviderConnectorRuntimeRepository`
  - implements connector command/query ports
- `ProviderConnectionRuntimeRepository`
  - implements connection command/query ports и connector lookup
- `MessageTemplateRuntimeRepository`
  - implements template command repository и provider lookup
- `MessageTemplateQueryRuntimeRepository`
  - читает templates вместе с active version metadata
- `OutboundMessageRuntimeRepository`
  - implements send, query, queue, processing и template/connection lookup operations
- `DeliveryRuntimeRepository`
  - implements delivery attempts, events и webhook lookup
- `OutboundProcessingRuntimeRepository`
  - adapter, объединяющий outbound repository и delivery attempt service

Row mappers живут рядом с repositories и отвечают за конвертацию runtime row в domain entity или DTO. Domain/application
код не должен работать с raw runtime rows напрямую.

### Runtime Objects

Runtime object names заданы в `src/modules/communication/infrastructure/runtime_object_names.py` и seed-ятся через
`src/modules/schema_registry/seed/schema_seed.py`.

| Runtime object                        | Назначение                                            |
|---------------------------------------|-------------------------------------------------------|
| `communication_provider_connector`    | YAML provider connector definitions                   |
| `communication_provider_message_type` | message type schemas provider connector-а             |
| `communication_provider_connection`   | tenant provider config, secret refs и encoded secrets |
| `communication_message_template`      | template headers                                      |
| `communication_template_version`      | versioned template payloads и variables schemas       |
| `communication_request`               | входящие send commands                                |
| `communication_outbound_message`      | concrete provider messages и processing state         |
| `communication_delivery_attempt`      | provider send attempts                                |
| `communication_delivery_event`        | provider webhook/delivery events                      |

Важные индексы/инварианты runtime schema:

- connector unique по `provider_code + version`
- message type unique по `provider_connector_id + message_type_code`
- provider connection unique по `connection_code`
- template unique по `template_code`
- template version unique по `template_id + version`
- communication request unique по `idempotency_key`
- outbound messages индексируются по request, connection, external message id, internal status, processing lease,
  next attempt и queue published timestamp
- delivery attempt unique по `outbound_message_id + attempt_no`
- delivery event индексируется по outbound, external message id, internal status и event type

### Provider Senders

Provider sender - transport adapter, который строит provider request и нормализует provider response.

Текущие senders:

- `YamlHttpProviderSender`
  - transport: `http`
  - рендерит method/url/headers/body из YAML
  - поддерживает bearer/basic auth из secrets
  - вызывает provider через `HttpxProviderHttpClient`
  - извлекает external id/status через `response_mapping`
  - редактирует secret values в persisted request snapshot
- `YamlSmtpProviderSender`
  - transport: `smtp`
  - рендерит SMTP send spec
  - использует shared `SmtpEmailTransport`
  - синтезирует successful provider response с `SENT`

Provider render context:

- `recipient.address`
- `recipient.snapshot`
- `template`
- `variables`
- `config`
- `secrets`
- `message.outbound_message_id`
- `message.communication_request_id`
- `message.initiator_ref_id`
- `connection.connection_code`
- `connection.channel_code`
- `provider_message_type.code`

### RabbitMQ

RabbitMQ интеграция находится в `src/modules/communication/infrastructure/rabbitmq.py`.

Компоненты:

- `RabbitMQOutboundMessagePublisher`
  - реализует `OutboundMessagePublisherProtocol`
  - публикует `OutboundMessageJob`
- `build_communication_exchange`
- `build_communication_queue`
- `build_communication_dlx`
- `build_communication_dlq`
- `ensure_communication_topology`
- `build_communication_faststream_app`
- `handle_outbound_message_job`

Job payload:

```json
{
  "tenant_id": "<uuid>",
  "outbound_message_id": "<uuid>",
  "published_at": "<iso-datetime>",
  "source": "send_communication"
}
```

Если `COMMUNICATION_QUEUE.enabled=false`, HTTP `/send` создаёт queued message, но publisher dependency возвращает
`None`, и processing нужно запускать CLI командой `communication process-queued` или включить queue.

## Presentation Layer

Все HTTP routes монтируются через `src/modules/router.py` под `/api`, а communication router добавляет
`/communication`.

### HTTP API

Authenticated routes берут `tenant_id` из `AuthenticatedRequestContextDep` через `require_tenant_id`.
Webhook route использует `OptionalRequestContextDep`, потому что провайдеры вызывают его без console session context.

| Method | Path                                                                        | Назначение                                 |
|--------|-----------------------------------------------------------------------------|--------------------------------------------|
| `POST` | `/api/communication/providers/connectors/import-yaml`                       | импорт YAML provider connector             |
| `GET`  | `/api/communication/providers/connectors`                                   | список provider connectors и message types |
| `POST` | `/api/communication/providers/connections`                                  | создание provider connection               |
| `GET`  | `/api/communication/providers/connections`                                  | список provider connections                |
| `POST` | `/api/communication/templates`                                              | создание message template                  |
| `POST` | `/api/communication/templates/{template_id}/versions`                       | создание template version                  |
| `POST` | `/api/communication/templates/{template_id}/versions/{version_id}/activate` | активация template version                 |
| `GET`  | `/api/communication/templates`                                              | список templates с active version metadata |
| `POST` | `/api/communication/send`                                                   | постановка communication на отправку       |
| `GET`  | `/api/communication/messages`                                               | список outbound messages                   |
| `GET`  | `/api/communication/messages/{outbound_message_id}`                         | получение outbound message                 |
| `POST` | `/api/communication/webhooks/{tenant_id}/{provider_code}`                   | provider delivery webhook                  |

Типичные error mappings:

- `401`
  - отсутствует authenticated tenant context для защищённых routes
- `404`
  - domain not found ошибки
- `409`
  - runtime persistence/policy/descriptor state ошибки
- `422`
  - domain validation, runtime validation/filter и shared domain ошибки

### Management CLI

CLI команды регистрируются в `src/management/commands/communication.py`.

```text
dnk-manage communication process-queued --tenant-id <uuid> [--limit 100]
dnk-manage communication publish-queued --tenant-id <uuid> [--limit 100]
dnk-manage communication recover-stuck --tenant-id <uuid> [--older-than-seconds 300] [--limit 100]
dnk-manage communication worker
```

Назначение:

- `process-queued`
  - локально claim-ит и обрабатывает queued outbound messages без RabbitMQ
- `publish-queued`
  - публикует queued outbound messages в RabbitMQ
- `recover-stuck`
  - переводит истёкшие `SENDING` messages в recoverable failed/unknown state
- `worker`
  - запускает FastStream worker, который обрабатывает RabbitMQ jobs по одному outbound id

## Как Работать С Модулем

Типичный setup provider-а:

1. Импортировать YAML connector через `POST /api/communication/providers/connectors/import-yaml`.
2. Получить connector/message type ids через `GET /api/communication/providers/connectors`.
3. Создать provider connection через `POST /api/communication/providers/connections`.
4. Создать template через `POST /api/communication/templates`.
5. Создать template version через `POST /api/communication/templates/{template_id}/versions`.
6. Активировать version через `POST /api/communication/templates/{template_id}/versions/{version_id}/activate`.

Типичная отправка:

1. Бизнес-фича вызывает `POST /api/communication/send` или напрямую `SendCommunicationUseCase`.
2. В command передаются `template_id` или `template_code`, `channel_code`, `message_class`, recipient и variables.
3. Use case валидирует active template version, variables и active provider connection.
4. Создаются `communication_request` и `communication_outbound_message`.
5. При включённой queue HTTP controller публикует RabbitMQ job после commit.
6. Worker claim-ит message, рендерит template, вызывает provider sender и сохраняет result.
7. Provider webhook дополняет delivery state, если provider присылает delivery events.

Для синхронной/ручной обработки без RabbitMQ можно использовать:

```text
dnk-manage communication process-queued --tenant-id <uuid>
```

Для production-like queue flow:

```text
dnk-manage communication publish-queued --tenant-id <uuid>
dnk-manage communication worker
```

## Как Строить Новые Фичи

Новые бизнес-сценарии:

- добавляйте command/query DTO в `application/<area>/command` или `application/<area>/query`
- добавляйте use case в `application/<area>/use_case`
- правила состояния держите в domain entity/service
- persistence оформляйте через repository protocol, а concrete adapter - в `infrastructure`
- HTTP controller должен быть тонким: input mapping, вызов use case, error mapping, response mapping

Новые provider transports:

- добавьте или расширьте YAML validation в `ProviderYamlLoader`
- реализуйте `ProviderSenderProtocol`
- определите `transport` string
- реализуйте `build()` так, чтобы `request_payload` был безопасен для сохранения без secrets
- реализуйте `send()` и возвращайте normalized `ProviderSendResult`
- зарегистрируйте sender в `get_provider_sender_registry` и management `build_provider_sender_registry`
- добавьте tests для loader, sender build/send и processing use case

Новые runtime fields/tables:

- измените seed в `src/modules/schema_registry/seed/schema_seed.py`
- обновите runtime object names при появлении новой table
- обновите runtime repository payloads, filters и row mappers
- проверьте config/diff поведение schema registry
- добавьте tests repository mapping и use case behavior

Интеграция из других модулей:

- предпочтительно использовать application use case, а не infrastructure repository напрямую
- tenant scope передавайте как `EntityIdVO`
- ids внутри domain/application используйте concrete `EntityIdVO` subclasses
- UUID оставляйте на HTTP, CLI, queue и runtime-data boundaries
- не обходите `SendCommunicationUseCase`, если нужна idempotency, template validation и active connection lookup

## Operational Notes

- `CUSTOM_ADAPTER` пока не является рабочим YAML connector type.
- JSON Schema validation использует Draft 2020-12.
- Jinja rendering использует `StrictUndefined`: отсутствующая variable приводит к validation error.
- Provider statuses без mapping или с неизвестным target status становятся `UNKNOWN`.
- Secrets хранятся как base64 JSON в `secrets_b64`; это encoding, не криптографическое шифрование.
- HTTP responses по provider connections возвращают `has_secrets`, но не сами secrets.
- Provider request snapshots должны быть redacted перед сохранением.
- Webhook path содержит `tenant_id`, потому что provider webhook не имеет authenticated console context.
- Queue publish выполняется после commit send operation; если publish не удался, queued row остаётся и может быть
  опубликован republisher-ом.
- Processing by id использует короткие transaction scopes: отдельно claim/build, отдельно persistence result.

## Dependencies On Other Modules

- `shared`
  - `EntityIdVO`, `RequestContext`, authenticated/optional context dependencies, `UnitOfWork`, `ClockPort`, `UtcClock`
- `schema_registry`
  - runtime object descriptors и seed runtime objects
- `runtime_data`
  - runtime command/query gateways, filters, sorting, pagination и atomic claim operations
- `shared.infrastructure.email`
  - SMTP transport для `YamlSmtpProviderSender`
- `config`
  - `COMMUNICATION_QUEUE` settings для RabbitMQ publisher/worker

## Tests Covering This Module

- `test/test_communication_services.py`
  - YAML validation, rendering, JSONPath/status mapping, secret codec
- `test/test_communication_provider_connector_domain.py`
- `test/test_communication_provider_connector_application.py`
- `test/test_communication_provider_connector_runtime_repository.py`
- `test/test_communication_provider_connector_depends.py`
- `test/test_communication_provider_connection_domain.py`
- `test/test_communication_provider_connection_application.py`
- `test/test_communication_provider_connection_runtime_repository.py`
- `test/test_communication_provider_connection_depends.py`
- `test/test_communication_message_template_domain.py`
- `test/test_communication_outbound_message_domain.py`
- `test/test_communication_outbound_message_runtime_repository.py`
- `test/test_communication_outbound_message_depends.py`
- `test/test_communication_delivery_domain.py`
- `test/test_communication_delivery_runtime_repository.py`
- `test/test_communication_use_cases.py`
- `test/test_communication_http_router.py`
- `test/test_communication_management_command.py`
- `test/test_communication_queue.py`
- `test/test_architecture_boundaries.py`

## Related

- [HTTP API](../interfaces/http-api.md)
- [Management CLI](../interfaces/management-cli.md)
- [Configuration](../interfaces/configuration.md)
- [Runtime schema](../data/runtime-schema.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/communication/domain/`
- `src/modules/communication/application/`
- `src/modules/communication/infrastructure/`
- `src/modules/communication/presentation/`
- `src/modules/schema_registry/seed/schema_seed.py`
- `src/management/commands/communication.py`
