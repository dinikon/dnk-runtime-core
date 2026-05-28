# Communication Module

## Purpose

`communication` - tenant-scoped runtime-data module для отправки и сопровождения сообщений через внешних провайдеров.
Модуль хранит provider connectors, tenant provider connections, message templates, outbound messages, delivery attempts,
delivery events и webhook payloads.

Основной сценарий: другой модуль вызывает send-команду, `communication` находит активный шаблон и активное provider
connection, создает `CommunicationRequest` и `OutboundMessage`, публикует job в очередь при включенном RabbitMQ,
рендерит
provider payload, отправляет его через sender adapter и обновляет delivery state.

## Current Scope

Текущая реализация покрывает несколько subdomain внутри одного bounded context:

- provider connector catalog на базе YAML specs;
- provider connection management с tenant-local config и encoded secrets;
- message template lifecycle с версиями payload;
- outbound send request и concrete provider message state;
- provider delivery attempts и delivery events;
- RabbitMQ/CLI processing для queued outbound messages;
- integration outbox facts for outbound/delivery status changes;
- provider webhook intake и status mapping.

Модуль использует runtime objects из `schema_registry` и `runtime_data`. Собственных SQLAlchemy ORM моделей для
communication runtime objects нет.

В текущей реализации не найдено:

- describe-fields / metadata HTTP endpoints для communication objects;
- отдельный read/list HTTP API для delivery attempts и delivery events;
- scheduled jobs;
- audience/contact/identity/device selection; `communication` принимает уже подготовленный low-level recipient:
  `recipient_identifier_type`, `recipient_address` и immutable `recipient_snapshot`.

## Public Functionality

- Импорт YAML provider connector spec: `POST /api/communication/providers/connectors/import-yaml`.
- Чтение provider connector catalog: `GET /api/communication/providers/connectors`.
- Создание provider connection: `POST /api/communication/providers/connections`.
- Чтение provider connections: `GET /api/communication/providers/connections`.
- Создание message template: `POST /api/communication/templates`.
- Создание template version: `POST /api/communication/templates/{template_id}/versions`.
- Активация template version: `POST /api/communication/templates/{template_id}/versions/{version_id}/activate`.
- Чтение templates: `GET /api/communication/templates`.
- Постановка communication на отправку подготовленному получателю: `POST /api/communication/send`.
- Чтение outbound messages: `GET /api/communication/messages` и
  `GET /api/communication/messages/{outbound_message_id}`.
- Прием provider webhooks: `POST /api/communication/webhooks/{tenant_id}/{provider_code}`.
- Management CLI: `communication process-queued`, `communication publish-queued`, `communication recover-stuck`,
  `communication worker`.

## Main Flows / Use Cases

| Use Case                               | Input                                  | Output                            | Description                                                                                                                                                     |
|----------------------------------------|----------------------------------------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `RegisterProviderConnectorUseCase`     | `RegisterProviderConnectorCommand`     | `ProviderConnectorDTO`            | Парсит YAML через `ProviderYamlLoader`, считает checksum и регистрирует connector/message types через `ProviderConnectorService`.                               |
| `ListProviderConnectorsUseCase`        | `EntityIdVO` tenant id                 | `ProviderConnectorCatalogDTO`     | Возвращает connectors и message types из query repository.                                                                                                      |
| `CreateProviderConnectionUseCase`      | `CreateProviderConnectionCommand`      | `ProviderConnectionDTO`           | Кодирует secrets через `SecretCodec`, валидирует config/secrets по connector schemas и сохраняет connection.                                                    |
| `ListProviderConnectionsUseCase`       | `EntityIdVO` tenant id                 | `list[ProviderConnectionDTO]`     | Возвращает provider connections без раскрытия secrets.                                                                                                          |
| `CreateMessageTemplateUseCase`         | `CreateMessageTemplateCommand`         | `MessageTemplateDTO`              | Создает DRAFT template, проверяет connector/message type binding и channel match.                                                                               |
| `CreateTemplateVersionUseCase`         | `CreateTemplateVersionCommand`         | `TemplateVersionDTO`              | Создает DRAFT version, валидирует `template_payload` и `variables_schema`.                                                                                      |
| `ActivateTemplateVersionUseCase`       | `ActivateTemplateVersionCommand`       | `TemplateVersionDTO`              | Активирует выбранную версию, переводит прежние active versions в `DEPRECATED`, template - в `ACTIVE`.                                                           |
| `ListMessageTemplatesUseCase`          | `EntityIdVO` tenant id                 | `list[MessageTemplateDTO]`        | Возвращает templates с metadata активной версии.                                                                                                                |
| `SendCommunicationUseCase`             | `SendCommunicationCommand`             | `SendCommunicationResultDTO`      | Проверяет idempotency, template/channel/active version/variables/active connection и создает queued request/outbound для уже подготовленного recipient address. |
| `GetOutboundMessageUseCase`            | `GetOutboundMessageQuery`              | `OutboundMessageDTO`              | Возвращает outbound message или поднимает `OutboundMessageNotFoundError`.                                                                                       |
| `ListOutboundMessagesUseCase`          | `ListOutboundMessagesQuery`            | `list[OutboundMessageDTO]`        | Возвращает outbound messages с `limit`/`offset`.                                                                                                                |
| `ProcessOutboundMessageUseCase`        | `ProcessQueuedMessagesCommand`         | `ProcessQueuedResultDTO`          | Batch-claim queued messages и отправляет каждое через provider sender.                                                                                          |
| `ProcessOutboundMessageByIdUseCase`    | `ProcessOutboundMessageByIdCommand`    | `ProcessOutboundMessageResultDTO` | Обрабатывает один outbound id с processing lease token и короткими transaction scopes.                                                                          |
| `PublishQueuedOutboundMessagesUseCase` | `PublishQueuedOutboundMessagesCommand` | `PublishQueuedResultDTO`          | Публикует publishable queued outbounds в RabbitMQ и помечает `queue_published_at`.                                                                              |
| `RecoverStuckOutboundMessagesUseCase`  | `RecoverStuckOutboundMessagesCommand`  | `RecoverStuckResultDTO`           | Помечает истекшие `SENDING` messages как `UNKNOWN` через queue repository.                                                                                      |
| `HandleProviderWebhookUseCase`         | `HandleProviderWebhookCommand`         | `WebhookResultDTO`                | Ищет active connector, извлекает webhook fields JSONPath-ами, матчится по external id и обновляет outbound status.                                              |

## Domain Model

### ProviderConnector

- ID: `ProviderConnectorIdVO`.
- Tenant scope: tenant id не хранится в entity, передается во все repository/service операции.
- Fields: `provider_connector_id`, `provider_code`, `provider_name`, `version`, `connector_type`, `yaml_spec`,
  `yaml_checksum`, `status`, `created_at`, `updated_at`.
- Value Objects: `ProviderConnectorCodeVO`, `ProviderConnectorNameVO`, `ProviderConnectorVersionVO`,
  `ProviderConnectorIdVO`.
- Factory methods: `ProviderConnector.create`.
- Update methods: в entity не найдено.
- Domain errors: `InvalidProviderConnectorTypeError`, `InvalidProviderConnectorStatusError`.
- Invariants: `connector_type` должен быть одним из `YAML_HTTP`, `YAML_SMTP`, `CUSTOM_ADAPTER`; `status` должен быть
  одним из `ACTIVE`, `DISABLED`, `DEPRECATED`; code/name/version нормализуются через VO.

### ProviderMessageType

- ID: `ProviderMessageTypeIdVO`.
- Tenant scope: tenant id передается в repository операции.
- Fields: `provider_message_type_id`, `provider_connector_id`, `message_type_code`, `channel_code`, `name`,
  `field_schema`, `ui_schema`, `is_active`.
- Value Objects: `ProviderMessageTypeCodeVO`, `ProviderMessageTypeNameVO`, `ProviderChannelCodeVO`.
- Factory methods: `ProviderMessageType.create`.
- Update methods: в entity не найдено.
- Domain errors: invalid message type code/name/channel VO errors.
- Invariants: message type связан с provider connector, `message_type_code`, `channel_code`, `name` не должны быть
  пустыми после нормализации.

### ProviderConnectionEntity

- ID: `ProviderConnectionIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `provider_connection_id`, `created_at`, `updated_at`, `tenant_id`, `provider_connector_id`,
  `connection_code`, `connection_name`, `channel_code`, `config`, `secret_ref`, `secrets_b64`, `status`.
- Value Objects: `ProviderConnectionCodeVO`, `ProviderConnectionNameVO`, `ProviderConnectionStatusVO`,
  `ProviderConnectorIdVO`.
- Factory methods: `ProviderConnectionEntity.create`.
- Update methods: в entity не найдено.
- Domain errors: `ProviderConnectionNotFoundError`, `InvalidProviderConnectionCodeError`,
  `InvalidProviderConnectionNameError`, `ProviderSecretsValidationError`, `ProviderConnectorNotFoundError`,
  `CommunicationValidationError`.
- Invariants: connection создается как `ACTIVE`; connector должен существовать; `channel_code` должен входить в
  `yaml_spec.channels`; `config` и `secrets` валидируются по JSON Schema из connector spec.

### MessageTemplateEntity

- ID: `MessageTemplateIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `template_id`, `created_at`, `updated_at`, `tenant_id`, `template_code`, `name`, `description`,
  `provider_connector_id`, `provider_message_type_id`, `channel_code`, `message_class`, `status`.
- Value Objects: `MessageTemplateCodeVO`, `MessageTemplateNameVO`, `ChannelCodeVO`, `MessageClassVO`,
  `TemplateStatusVO`, `ProviderConnectorIdVO`, `ProviderMessageTypeIdVO`.
- Factory methods: `MessageTemplateEntity.create`.
- Update methods: `ensure_message_type_binding`, `mark_active`.
- Domain errors: `MessageTemplateNotFoundError`, `InvalidMessageTemplateCodeError`, `InvalidMessageTemplateNameError`,
  `ProviderConnectorNotFoundError`, `ProviderMessageTypeNotFoundError`, `CommunicationValidationError`.
- Invariants: новая template создается в `DRAFT`; provider message type должен принадлежать выбранному connector;
  channel template должен совпадать с channel message type.

### TemplateVersionEntity

- ID: `TemplateVersionIdVO`.
- Tenant scope: tenant id находится на parent template и передается в repository операции.
- Fields: `template_version_id`, `created_at`, `activated_at`, `template_id`, `version`, `template_payload`,
  `variables_schema`, `status`.
- Value Objects: `TemplateVersionTimestampVO`, `TemplateVersionStatusVO`.
- Factory methods: `TemplateVersionEntity.create`.
- Update methods: `ensure_belongs_to`, `activate`, `deprecate`.
- Domain errors: `TemplateVersionNotFoundError`, `InvalidTemplateVersionTimestampError`.
- Invariants: новая version создается в `DRAFT`; active version получает `activated_at`; неактивные версии не меняются
  при `deprecate`.

### CommunicationRequest

- ID: `CommunicationRequestIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `communication_request_id`, `tenant_id`, `initiator_type`, `initiator_ref_id`, `correlation_id`,
  `idempotency_key`, `message_class`, `channel_code`, `template_id`, `template_version_id`,
  `recipient_identifier_type`, `recipient_address`, `recipient_snapshot`, `variables`, `scheduled_at`, `priority`,
  `status`, timestamps.
- Value Objects: `InitiatorTypeVO`, `IdempotencyKeyVO`, `MessageClassVO`, `ChannelCodeVO`,
  `RecipientIdentifierTypeVO`, `RecipientAddressVO`, `OutboundPriorityVO`.
- Factory methods: `CommunicationRequest.create`.
- Update methods: в entity не найдено.
- Domain errors: invalid initiator/recipient/priority/idempotency errors, `CommunicationValidationError`.
- Invariants: request create нормализует class/channel/recipient/priority; default status в domain factory - `QUEUED`.

### OutboundMessage

- ID: `OutboundMessageIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `outbound_message_id`, `tenant_id`, `communication_request_id`, `provider_connection_id`, `channel_code`,
  `message_class`, `priority`, `recipient_identifier_type`, `recipient_address`, `recipient_snapshot`,
  `rendered_payload`, `provider_request_payload`, `external_message_id`, `external_status`, `internal_status`, errors,
  delivery timestamps, processing lease fields, queue publishing fields, timestamps.
- Value Objects: `OutboundMessageIdVO`, `CommunicationRequestIdVO`, `ProviderConnectionIdVO`, `ChannelCodeVO`,
  `MessageClassVO`, `OutboundPriorityVO`, `RecipientIdentifierTypeVO`, `RecipientAddressVO`.
- Factory methods: `OutboundMessage.create_queued`.
- Update methods: `mark_published`.
- Domain errors: `OutboundMessageNotFoundError`, `ProviderPayloadValidationError`.
- Invariants: queued outbound создается с empty provider snapshots, `internal_status=QUEUED`, `queued_at=now`,
  `queue_publish_count=0`; `mark_published` обновляет `queue_published_at` и увеличивает publish count.

### DeliveryAttempt

- ID: `DeliveryAttemptIdVO`.
- Tenant scope: tenant id передается в repository/service операции.
- Fields: `delivery_attempt_id`, `outbound_message_id`, `provider_connection_id`, `attempt_no`, `status`,
  `request_payload`, `response_payload`, `http_status_code`, `external_message_id`, `error_code`, `error_message`,
  `started_at`, `finished_at`.
- Value Objects: `DeliveryAttemptIdVO`, `OutboundMessageIdVO`, `ProviderConnectionIdVO`, `ExternalMessageId`.
- Factory methods: `DeliveryAttempt.start`.
- Update methods: `complete_success`, `fail`.
- Domain errors: `DeliveryAttemptNotFoundError`, `InvalidExternalMessageIdError`.
- Invariants: started attempt получает `STARTED`; success переводит в `SUCCESS`; failure выбирает
  `RETRYABLE_FAILED` или `NON_RETRYABLE_FAILED`.

### DeliveryEvent

- ID: `DeliveryEventIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `delivery_event_id`, `tenant_id`, `outbound_message_id`, `provider_connection_id`, `external_message_id`,
  `external_status`, `internal_status`, `event_type`, `event_at`, `raw_payload`, `created_at`.
- Value Objects: `DeliveryEventIdVO`, `OutboundMessageIdVO`, `ProviderConnectionIdVO`, `ExternalMessageId`.
- Factory methods: `DeliveryEvent.create_from_webhook`.
- Update methods: в entity не найдено.
- Domain errors: `WebhookPayloadValidationError`, `InvalidExternalMessageIdError`.
- Invariants: unknown event type мапится в `WEBHOOK_RECEIVED`.

## Application Layer

### Commands

- `RegisterProviderConnectorCommand`.
- `CreateProviderConnectionCommand`.
- `CreateMessageTemplateCommand`.
- `CreateTemplateVersionCommand`.
- `ActivateTemplateVersionCommand`.
- `SendCommunicationCommand`.
- `ProcessQueuedMessagesCommand`.
- `ProcessOutboundMessageByIdCommand`.
- `PublishQueuedOutboundMessagesCommand`.
- `RecoverStuckOutboundMessagesCommand`.
- `HandleProviderWebhookCommand`.

Все найденные command classes оформлены как frozen/slotted dataclasses.

### Queries

- `GetOutboundMessageQuery`.
- `ListOutboundMessagesQuery`.

Для provider connectors, provider connections и message templates отдельные query command classes не найдены: list use
cases принимают tenant id напрямую, а `application/**/query/repository.py` содержит repository protocols.

### DTOs

- Provider connector: `ProviderConnectorDTO`, `ProviderMessageTypeDTO`, `ProviderConnectorCatalogDTO`.
- Provider connection: `ProviderConnectionDTO`.
- Message template: `MessageTemplateDTO`, `TemplateVersionDTO`.
- Outbound message: `SendCommunicationResultDTO`, `OutboundMessageDTO`, `ProcessQueuedResultDTO`,
  `ProcessOutboundMessageResultDTO`.
- Queue: `PublishQueuedResultDTO`, `RecoverStuckResultDTO`, `OutboundMessageJob`.
- Delivery: `WebhookResultDTO`.

DTOs оформлены как frozen/slotted dataclasses.

### Use Cases

- Provider connector: `RegisterProviderConnectorUseCase`, `ListProviderConnectorsUseCase`.
- Provider connection: `CreateProviderConnectionUseCase`, `ListProviderConnectionsUseCase`.
- Message template: `CreateMessageTemplateUseCase`, `CreateTemplateVersionUseCase`, `ActivateTemplateVersionUseCase`,
  `ListMessageTemplatesUseCase`.
- Outbound message: `SendCommunicationUseCase`, `GetOutboundMessageUseCase`, `ListOutboundMessagesUseCase`,
  `ProcessOutboundMessageUseCase`, `ProcessOutboundMessageByIdUseCase`.
- Queue: `PublishQueuedOutboundMessagesUseCase`, `RecoverStuckOutboundMessagesUseCase`.
- Delivery: `HandleProviderWebhookUseCase`.

### Application Services

- `ProviderYamlLoader`: парсит YAML через `yaml.safe_load`, валидирует required root fields, `channels`,
  `message_types`, JSON Schemas, transport-specific send spec и считает canonical JSON checksum.
- `JsonSchemaValidationService`: валидирует config, secrets, template payload и variables через Draft 2020-12.
- `TemplateRenderService`: рекурсивно рендерит string leaves через Jinja2 `NativeEnvironment` и `StrictUndefined`.
- `ProviderPayloadBuildService`: строит provider HTTP method/url/headers/body из send spec.
- `ProviderStatusMappingService`: мапит external status в `OutboundMessageStatus`, fallback - `UNKNOWN`.
- `JsonPathService`: извлекает первое значение по JSONPath.
- `SecretCodec`: кодирует/декодирует secrets как base64 JSON.

### Repository Protocols

- `ProviderConnectorRepositoryProtocol`.
- `ProviderConnectorQueryRepositoryProtocol`.
- `ProviderConnectionRepositoryProtocol`.
- `ProviderConnectionProviderLookupProtocol`.
- `ProviderConnectionQueryRepositoryProtocol`.
- `MessageTemplateRepositoryProtocol`.
- `MessageTemplateProviderLookupProtocol`.
- `MessageTemplateQueryRepositoryProtocol`.
- `OutboundMessageRepositoryProtocol`.
- `OutboundMessageQueryRepositoryProtocol`.
- `OutboundProcessingRepositoryProtocol`.
- `OutboundProcessingByIdRepositoryProtocol`.
- `OutboundProcessingRepositoryContextFactoryProtocol`.
- `OutboundQueueRepositoryProtocol`.
- `OutboundMessagePublisherProtocol`.
- `DeliveryAttemptRepositoryProtocol`.
- `DeliveryEventRepositoryProtocol`.
- `DeliveryWebhookLookupProtocol`.
- `DeliveryRepositoryProtocol`.
- `DeliveryAttemptServiceProtocol`.
- `ProviderSenderProtocol`.
- `ProviderSenderRegistryProtocol`.
- `HttpClientProtocol`.

## Infrastructure / Persistence

Communication persistence реализован через runtime objects. Репозитории получают tenant scope параметром `tenant_id`,
резолвят descriptor через `SchemaRegistryRuntimeObjectResolver`/`RuntimeObjectResolverDep` и работают через
`PostgresRuntimeCommandGateway` и `PostgresRuntimeQueryGateway`.

Runtime object names заданы в `src/modules/communication/infrastructure/runtime_object_names.py`.

| Runtime object                        | Назначение                                                                    |
|---------------------------------------|-------------------------------------------------------------------------------|
| `communication_provider_connector`    | YAML provider connector definitions.                                          |
| `communication_provider_message_type` | Message type schemas внутри connector.                                        |
| `communication_provider_connection`   | Tenant provider config, `secret_ref`, `secrets_b64`.                          |
| `communication_message_template`      | Template headers.                                                             |
| `communication_template_version`      | Versioned template payloads и variables schemas.                              |
| `communication_request`               | Inbound send commands.                                                        |
| `communication_outbound_message`      | Concrete provider messages, delivery state, processing lease, queue metadata. |
| `communication_delivery_attempt`      | Provider send attempts.                                                       |
| `communication_delivery_event`        | Provider webhook/delivery events.                                             |

### ProviderConnectorRuntimeRepository

- File: `src/modules/communication/infrastructure/provider_connector/repository.py`.
- Implements: `ProviderConnectorRepositoryProtocol`, `ProviderConnectorQueryRepositoryProtocol`.
- Storage: `runtime_data`.
- Runtime objects: `communication_provider_connector`, `communication_provider_message_type`.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: `provider_connector/row_mapper.py` мапит runtime rows в domain entities и DTOs.
- Errors: runtime gateway/resolver errors пробрасываются в presentation error mapping.

### ProviderConnectionRuntimeRepository

- File: `src/modules/communication/infrastructure/provider_connection/repository.py`.
- Implements: `ProviderConnectionRepositoryProtocol`, `ProviderConnectionProviderLookupProtocol`,
  `ProviderConnectionQueryRepositoryProtocol`; также структурно используется как active connection lookup для send.
- Storage: `runtime_data`.
- Runtime object: `communication_provider_connection`; connector lookup читает `communication_provider_connector`.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: `provider_connection/row_mapper.py`.
- Errors: not found возвращается как `None` на load/find methods; runtime errors пробрасываются выше.

### MessageTemplateRuntimeRepository

- File: `src/modules/communication/infrastructure/message_template/repository.py`.
- Implements: `MessageTemplateRepositoryProtocol`, `MessageTemplateProviderLookupProtocol`.
- Storage: `runtime_data`.
- Runtime objects: `communication_message_template`, `communication_template_version`,
  `communication_provider_connector`, `communication_provider_message_type`.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: `message_template/row_mapper.py`.
- Errors: not found возвращается как `None`; consistency/runtime errors пробрасываются выше.

### MessageTemplateQueryRuntimeRepository

- File: `src/modules/communication/infrastructure/message_template/query_repository.py`.
- Implements: `MessageTemplateQueryRepositoryProtocol`.
- Storage: `runtime_data`.
- Runtime objects: `communication_message_template`, `communication_template_version`.
- Tenant handling: tenant id передается в query method.
- Mapping: query rows собираются в `MessageTemplateDTO` с active version metadata.
- Errors: runtime errors пробрасываются выше.

### OutboundMessageRuntimeRepository

- File: `src/modules/communication/infrastructure/outbound_message/repository.py`.
- Implements: send repository, template lookup, outbound query, queue and processing repository protocols.
- Storage: `runtime_data`.
- Runtime objects: `communication_request`, `communication_outbound_message`, template/connection/connector/message type
  objects для processing context.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: `outbound_message/row_mapper.py`.
- Errors: not found возвращается как `None` в lookup methods; processing methods используют status/lease fields.

### DeliveryRuntimeRepository

- File: `src/modules/communication/infrastructure/delivery/repository.py`.
- Implements: `DeliveryRepositoryProtocol`.
- Storage: `runtime_data`.
- Runtime objects: `communication_delivery_attempt`, `communication_delivery_event`, plus outbound/connector lookup.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: `delivery/row_mapper.py`.
- Query API: list attempts/events supports `limit`, `offset` and indexed filters for outbound/status/event lookup.
- Errors: not found возвращается как `None` в read methods; runtime errors пробрасываются выше.

### OutboundProcessingRuntimeRepository

- File: `src/modules/communication/infrastructure/delivery/processing_repository.py`.
- Implements: `OutboundProcessingByIdRepositoryProtocol`.
- Storage: adapter over `OutboundMessageRuntimeRepository` and `DeliveryService`.
- Runtime object: напрямую делегирует outbound/delivery repositories.
- Tenant handling: tenant id передается в каждый метод.
- Mapping: делегируется underlying repositories.
- Errors: пробрасывает ошибки underlying repositories/services.

### Provider Senders

- `ProviderSenderRegistry`: выбирает sender по `transport`, unknown transport -> `CommunicationValidationError`.
- `YamlHttpProviderSender`: transport `http`; строит request через `ProviderPayloadBuildService`, поддерживает
  bearer/basic
  auth из decoded secrets, вызывает `HttpxProviderHttpClient`, извлекает external id/status через JSONPath и редактирует
  secrets в persisted request snapshot.
- `YamlSmtpProviderSender`: transport `smtp`; строит SMTP payload, использует
  `src.modules.shared.infrastructure.email.smtp_email_transport.SmtpEmailTransport`, возвращает successful synthetic
  response со статусом `SENT`.
- `HttpxProviderHttpClient`: HTTP client adapter for provider requests.

### RabbitMQ

RabbitMQ integration находится в `src/modules/communication/infrastructure/rabbitmq.py`.

- `RabbitMQOutboundMessagePublisher` реализует communication queue port и отправляет `OutboundMessageJob` через общий
  `shared.infrastructure.messaging.RabbitMQMessagePublisher`.
- `build_communication_exchange`, `build_communication_queue`, `build_communication_dlx`, `build_communication_dlq`
  строят durable exchange/queue/DLX/DLQ.
- `ensure_communication_topology` объявляет и биндует topology.
- `build_communication_faststream_app` создает FastStream worker с manual ack.
- `handle_outbound_message_job` парсит payload, запускает `ProcessOutboundMessageByIdUseCase`, invalid payload
  reject-ит без requeue, processing exception nack-ит с requeue.

Job payload:

```json
{
  "tenant_id": "<uuid>",
  "outbound_message_id": "<uuid>",
  "published_at": "<iso-datetime>",
  "source": "send_communication"
}
```

### Integration Events

Communication не использует `shared.events` как transport для отправки сообщений. Доставка идет через
`communication.outbound.send`, а `shared.events` получает только факты после изменения состояния.

Текущий набор outgoing integration events:

- `communication.outbound_message.sent.v1`
- `communication.outbound_message.failed.v1`
- `communication.outbound_message.delivered.v1`
- `communication.delivery_status.changed.v1`

Events пишутся в shared outbox в той же transaction, где фиксируется provider processing или webhook status update.
Публикация наружу выполняется общей командой `dnk-manage events publish-outbox`.

### Schema Seed Facts

`src/modules/schema_registry/seed/schema_seed.py` содержит `COMMUNICATION_OBJECTS` для всех runtime objects модуля.

Важные indexes/relations:

- `communication_provider_connectors_code_version_uq`: unique по `provider_code`, `version`.
- `communication_provider_message_types_connector_code_uq`: unique по `provider_connector_id`, `message_type_code`.
- `communication_provider_message_types_connector`: many-to-one к connector, `on_delete="cascade"`.
- `communication_provider_connections_code_uq`: unique по `connection_code`.
- `communication_provider_connections_connector`: many-to-one к connector, `on_delete="restrict"`.
- `communication_message_templates_code_uq`: unique по `template_code`.
- `communication_message_templates_connector`: many-to-one к connector, `on_delete="restrict"`.
- `communication_message_templates_message_type`: many-to-one к message type, `on_delete="restrict"`.
- `communication_template_versions_template_version_uq`: unique по `template_id`, `version`.
- `communication_template_versions_template`: many-to-one к template, `on_delete="cascade"`.
- `communication_requests_idempotency_uq`: unique по `idempotency_key`.
- `communication_requests_template` и `communication_requests_template_version`: `on_delete="restrict"`.
- `communication_outbound_messages_request`: many-to-one к request, `on_delete="cascade"`.
- `communication_outbound_messages_connection`: many-to-one к provider connection, `on_delete="restrict"`.
- Outbound indexes: request, connection, channel, external message id, internal status, processing token,
  processing deadline, next attempt, queue published timestamp.
- `communication_delivery_attempts_outbound_attempt_uq`: unique по `outbound_message_id`, `attempt_no`.
- `communication_delivery_attempts_outbound`: many-to-one к outbound, `on_delete="cascade"`.
- `communication_delivery_attempts_connection`: many-to-one к provider connection, `on_delete="restrict"`.
- `communication_delivery_events_outbound` и `communication_delivery_events_connection`: `on_delete="set_null"`.

## Presentation / HTTP API

Base prefix:

```text
/api/communication
```

Communication router монтируется в `src/modules/router.py` под `/api`; internal routers добавляют `/communication`.
Protected routes используют `AuthenticatedRequestContextDep` и `require_tenant_id`. Webhook route использует
`OptionalRequestContextDep` и получает tenant id из path.

| Method | Path                                                                        | Controller                       | Use Case                           | Request                                 | Response                                |
|--------|-----------------------------------------------------------------------------|----------------------------------|------------------------------------|-----------------------------------------|-----------------------------------------|
| `POST` | `/api/communication/providers/connectors/import-yaml`                       | `import_provider_connector_yaml` | `RegisterProviderConnectorUseCase` | `ImportYamlRequestSchema`               | `ProviderConnectorResponseSchema`       |
| `GET`  | `/api/communication/providers/connectors`                                   | `list_provider_connectors`       | `ListProviderConnectorsUseCase`    | none                                    | `ListProviderConnectorsResponseSchema`  |
| `POST` | `/api/communication/providers/connections`                                  | `create_provider_connection`     | `CreateProviderConnectionUseCase`  | `CreateProviderConnectionRequestSchema` | `ProviderConnectionResponseSchema`      |
| `GET`  | `/api/communication/providers/connections`                                  | `list_provider_connections`      | `ListProviderConnectionsUseCase`   | none                                    | `ListProviderConnectionsResponseSchema` |
| `POST` | `/api/communication/templates`                                              | `create_message_template`        | `CreateMessageTemplateUseCase`     | `CreateMessageTemplateRequestSchema`    | `MessageTemplateResponseSchema`         |
| `POST` | `/api/communication/templates/{template_id}/versions`                       | `create_template_version`        | `CreateTemplateVersionUseCase`     | `CreateTemplateVersionRequestSchema`    | `TemplateVersionResponseSchema`         |
| `POST` | `/api/communication/templates/{template_id}/versions/{version_id}/activate` | `activate_template_version`      | `ActivateTemplateVersionUseCase`   | path params                             | `TemplateVersionResponseSchema`         |
| `GET`  | `/api/communication/templates`                                              | `list_message_templates`         | `ListMessageTemplatesUseCase`      | none                                    | `ListMessageTemplatesResponseSchema`    |
| `POST` | `/api/communication/send`                                                   | `send_communication`             | `SendCommunicationUseCase`         | `SendCommunicationRequestSchema`        | `SendCommunicationResponseSchema`       |
| `GET`  | `/api/communication/messages`                                               | `list_messages`                  | `ListOutboundMessagesUseCase`      | query `limit`, `offset`                 | `ListOutboundMessagesResponseSchema`    |
| `GET`  | `/api/communication/messages/{outbound_message_id}`                         | `get_message`                    | `GetOutboundMessageUseCase`        | path param                              | `OutboundMessageResponseSchema`         |
| `GET`  | `/api/communication/messages/{outbound_message_id}/attempts`                | `list_message_delivery_attempts` | `ListDeliveryAttemptsUseCase`      | path param, query `limit`, `offset`     | `ListDeliveryAttemptsResponseSchema`    |
| `GET`  | `/api/communication/messages/{outbound_message_id}/events`                  | `list_message_delivery_events`   | `ListDeliveryEventsUseCase`        | path param, query `limit`, `offset`     | `ListDeliveryEventsResponseSchema`      |
| `GET`  | `/api/communication/delivery-attempts`                                      | `list_delivery_attempts`         | `ListDeliveryAttemptsUseCase`      | query filters, `limit`, `offset`        | `ListDeliveryAttemptsResponseSchema`    |
| `GET`  | `/api/communication/delivery-events`                                        | `list_delivery_events`           | `ListDeliveryEventsUseCase`        | query filters, `limit`, `offset`        | `ListDeliveryEventsResponseSchema`      |
| `POST` | `/api/communication/webhooks/{tenant_id}/{provider_code}`                   | `handle_provider_webhook`        | `HandleProviderWebhookUseCase`     | raw JSON object                         | `WebhookResponseSchema`                 |

HTTP status facts:

- Create endpoints return `201` where specified by controllers.
- `/api/communication/send` returns `202` after creating queued request/outbound.
- Webhook endpoint returns `202`.
- Missing tenant context on protected routes maps to `401`.
- `CommunicationNotFoundError` maps to `404`.
- `RuntimeDataPersistenceError`, `RuntimeDataPolicyError`, `RuntimeObjectDescriptorError`, `RuntimeObjectNotFoundError`,
  `SchemaRegistryMetadataInconsistentError`, `CommunicationRuntimeStateError` map to `409`.
- `CommunicationValidationError`, `RuntimeDataValidationError`, `RuntimeDataFilterError`, generic `DomainError` map to
  `422`.
- Outbound controllers use shared `map_outbound_http_error`; delivery read controllers use
  `map_communication_http_error`.

Delivery read filters:

- `delivery-attempts`: `outbound_message_id`, `status`, `limit`, `offset`.
- `delivery-events`: `outbound_message_id`, `external_message_id`, `internal_status`, `event_type`, `limit`, `offset`.

`send_communication` commits UoW after use case success and only then attempts to publish RabbitMQ job. If publisher is
disabled or result is not `QUEUED`, no publish happens. Publish failure is logged, UoW is rolled back for publish
marker,
but already committed send row remains queued for later publishing.

## Dependency Injection

- Infrastructure dependencies in `src/modules/communication/presentation/depends/infrastructure.py` build:
  `RuntimeFieldTypePolicy`, `PostgresRuntimeQueryGateway`, `PostgresRuntimeCommandGateway`, runtime repositories,
  helper services, `HttpxProviderHttpClient`, `ProviderSenderRegistry`, shared outbox repositories and optional
  `RabbitMQOutboundMessagePublisher`.
- Application dependencies in `src/modules/communication/presentation/depends/application.py` build domain services and
  HTTP use cases from repositories/services/clock.
- Management dependencies in `src/modules/communication/presentation/depends/management.py` build processing, publish,
  recover and by-id worker use cases outside FastAPI DI using `AsyncSession`/`UnitOfWorkProtocol`.
- Shared dependencies: `UoWDep`, `ClockDep`, authenticated/optional request context dependencies.

## Dependencies On Other Modules

| Module            | Layer                                          | Used For                                                                                                                |
|-------------------|------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `shared`          | domain/application/presentation/infrastructure | `EntityIdVO`, `DomainError`, clock port, UoW, request context, SMTP transport, messaging publisher, integration outbox. |
| `runtime_data`    | infrastructure/presentation                    | Runtime command/query gateways, type policy, runtime validation/filter/persistence errors.                              |
| `schema_registry` | infrastructure/presentation/management         | Runtime object resolver, object descriptors, schema seed, SQLAlchemy repositories in management builders.               |
| `config`          | presentation/infrastructure/management         | `dnk_config.COMMUNICATION_QUEUE`, RabbitMQ settings.                                                                    |
| `contact_point`   | none direct                                    | Direct use cases/repositories не используются; source refs допускаются только внутри `recipient_snapshot`.              |

External library dependencies found in module code: FastAPI, `uuid6`, PyYAML, `jsonschema`, Jinja2, JSONPath parser,
httpx client adapter, FastStream/RabbitMQ, SQLAlchemy session factory for management builders.

## Events / Background Processing

Found:

- RabbitMQ publishing through `RabbitMQOutboundMessagePublisher`.
- Shared integration outbox writes for outbound sent/failed/delivered and delivery status changed facts.
- FastStream subscriber through `build_communication_faststream_app`.
- Manual ack/nack/reject behavior in `handle_outbound_message_job`.
- Management CLI commands:

```text
dnk-manage communication process-queued --tenant-id <uuid> [--limit 100]
dnk-manage communication publish-queued --tenant-id <uuid> [--limit 100]
dnk-manage communication recover-stuck --tenant-id <uuid> [--older-than-seconds 300] [--limit 100]
dnk-manage communication worker
```

Processing facts:

- `process-queued` batch-claims queued outbound messages and sends them without RabbitMQ.
- `publish-queued` scans publishable queued outbounds, publishes jobs and marks `queue_published_at`.
- `recover-stuck` recovers expired `SENDING` messages.
- `worker` runs FastStream RabbitMQ app and processes one outbound id per job.
- `ProcessOutboundMessageByIdUseCase` uses processing token and processing deadline; HTTP 429 and HTTP 5xx can be
  retried
  according to connector `retry_policy`.

Not found:

- Domain event bus handlers.
- Dedicated event consumer worker in this module.
- Scheduler/cron definitions inside this module.

## Tests Covering This Module

- Domain:
  - `test/test_communication_provider_connector_domain.py`
  - `test/test_communication_provider_connection_domain.py`
  - `test/test_communication_message_template_domain.py`
  - `test/test_communication_outbound_message_domain.py`
  - `test/test_communication_delivery_domain.py`
- Application/services:
  - `test/test_communication_services.py`
  - `test/test_communication_provider_connector_application.py`
  - `test/test_communication_provider_connection_application.py`
  - `test/test_communication_use_cases.py`
- Infrastructure:
  - `test/test_communication_provider_connector_runtime_repository.py`
  - `test/test_communication_provider_connection_runtime_repository.py`
  - `test/test_communication_outbound_message_runtime_repository.py`
  - `test/test_communication_delivery_runtime_repository.py`
  - `test/test_communication_queue.py`
- Presentation/DI:
  - `test/test_communication_http_router.py`
  - `test/test_communication_provider_connector_depends.py`
  - `test/test_communication_provider_connection_depends.py`
  - `test/test_communication_outbound_message_depends.py`
  - `test/test_communication_management_command.py`
- Integration/boundary:
  - `test/test_architecture_boundaries.py`

Verification command:

```bash
uv run python -m unittest test.test_communication_services test.test_communication_provider_connector_domain test.test_communication_provider_connector_application test.test_communication_provider_connector_runtime_repository test.test_communication_provider_connector_depends test.test_communication_provider_connection_domain test.test_communication_provider_connection_application test.test_communication_provider_connection_runtime_repository test.test_communication_provider_connection_depends test.test_communication_message_template_domain test.test_communication_outbound_message_domain test.test_communication_outbound_message_runtime_repository test.test_communication_outbound_message_depends test.test_communication_delivery_domain test.test_communication_delivery_runtime_repository test.test_communication_use_cases test.test_communication_http_router test.test_communication_management_command test.test_communication_queue -v
```

Эта команда проверена после обновления документации: `91 tests OK`.

## Known Gaps / Technical Debt

- `CUSTOM_ADAPTER` есть в `ConnectorType`, но `ProviderYamlLoader` принимает только `YAML_HTTP` и `YAML_SMTP`.
- `secrets_b64` - base64 JSON encoding, а не encrypted secret storage.
- Webhook endpoint получает `tenant_id` из path и использует optional request context; отдельная signature/auth
  validation
  в controller/use case не найдена.
- List responses возвращают `items`/catalog без total/count pagination metadata; `list_messages` принимает
  `limit`/`offset`, но response не содержит total.
- Delivery attempts/events не имеют отдельного public read/list HTTP API.
- `CreateProviderConnectionUseCaseProtocol` типизирован как возвращающий `ProviderConnectionEntity`, тогда как concrete
  use case возвращает `ProviderConnectionDTO`.
- В `ProcessOutboundMessageUseCase` batch processing ловит broad `Exception` для каждого message, считает failure и
  продолжает обработку следующего message.
- `communication` не хранит source-specific recipient columns вроде `contact_id`, `contact_point_id`, owner/context ids
  или identity/device refs. Caller должен сохранить provenance только внутри JSON `recipient_snapshot`.
- Есть raw `dict[str, Any]` payloads в domain/application DTOs для schemas, rendered payloads, provider request/response
  payloads и webhook raw payloads; это отражает текущий transport/runtime contract.

## Related Documentation

- [Develop Style](../develop-style.md)
- [Inventory Module](./inventory.md)
- [HTTP API](../interfaces/http-api.md)
- [Management CLI](../interfaces/management-cli.md)

## Source Of Truth

- `src/modules/communication/domain/...`
- `src/modules/communication/application/...`
- `src/modules/communication/infrastructure/...`
- `src/modules/communication/presentation/...`
- `src/management/commands/communication.py`
- `src/modules/schema_registry/seed/schema_seed.py`
- `test/test_communication_*.py`
- `test/test_architecture_boundaries.py`
