# Communication Module

## Purpose

`communication` manages tenant-scoped provider connectors, provider connections, message templates, outbound messages and
provider delivery webhooks. Provider behavior is described by YAML connector specs and stored in runtime schema tables.

## Public Functionality

- import YAML provider connector specs
- list provider connectors and message types
- create and list provider connections without exposing stored secrets
- create templates, create template versions and activate versions
- enqueue outbound communication sends
- list and inspect outbound messages
- accept provider webhooks and update outbound delivery state
- publish/process/recover outbound work through management commands and RabbitMQ workers

## Main Flows / Use Cases

- `RegisterProviderConnector`, `ListProviderConnectors`
- `CreateProviderConnection`, `ListProviderConnections`
- `CreateMessageTemplate`, `CreateTemplateVersion`, `ActivateTemplateVersion`, `ListMessageTemplates`
- `SendCommunication`, `GetOutboundMessage`, `ListOutboundMessages`
- `ProcessOutboundMessage`, `PublishQueuedOutboundMessages`, `RecoverStuckOutboundMessages`
- `HandleProviderWebhook`

## Domain Model

- provider connector and provider message type definitions
- tenant provider connection with config, write-only encoded secrets and status
- message template header plus versioned template payloads
- communication request plus concrete outbound provider message
- delivery attempt and delivery event history

Communication ids are concrete `EntityIdVO` subclasses in the communication domain. Tenant scope still uses shared
`EntityIdVO`; HTTP, queue and runtime-data boundaries expose UUID values.

## Infrastructure / Persistence

- persistence uses tenant runtime tables from the schema seed, not public SQLAlchemy communication models
- provider connector, provider connection, message template and outbound message aggregates use dedicated runtime
  repositories with explicit row-to-entity/DTO mapping
- outbound send, query, queue publication and worker processing use `OutboundMessageRuntimeRepository`; delivery webhook
  operations remain in `CommunicationRepository`
- provider senders implement application ports for YAML HTTP and YAML SMTP transports
- RabbitMQ publisher/worker code lives in infrastructure and is wired from presentation/management builders
- HTTP and management wiring assemble session-bound repositories from the active `UnitOfWork`

## Presentation / Entry Points

All HTTP routes are mounted under `/api/communication`:

- `POST /providers/connectors/import-yaml`
- `GET /providers/connectors`
- `POST /providers/connections`
- `GET /providers/connections`
- `POST /templates`
- `POST /templates/{template_id}/versions`
- `POST /templates/{template_id}/versions/{version_id}/activate`
- `GET /templates`
- `POST /send`
- `GET /messages`
- `GET /messages/{outbound_message_id}`
- `POST /webhooks/{tenant_id}/{provider_code}`

Authenticated routes derive `tenant_id` from request context. Webhooks keep the tenant id in the public path because
providers call them without console session context.

## Dependencies On Other Modules

- uses `shared` request context, `UnitOfWork`, clock and domain id primitives
- uses `schema_registry` to resolve runtime object descriptors
- uses `runtime_data` gateways for tenant-scoped CRUD over communication runtime objects
- uses shared email SMTP transport for YAML SMTP provider sends

## Tests Covering This Module

- communication service tests for YAML validation, rendering, JSONPath/status mapping and secret encoding
- provider connector domain/application/runtime/DI tests for YAML import aggregation and catalog listing
- outbound message domain/runtime/DI tests for value objects, entity factories, repository mapping and dependency wiring
- communication use case tests for send idempotency, outbound processing, retry behavior and webhooks
- communication HTTP router tests for routes, publish-after-commit and controller error mapping
- communication management command tests for process/publish/recover/worker wiring
- architecture boundary tests for application/infrastructure separation and mapper removal

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
