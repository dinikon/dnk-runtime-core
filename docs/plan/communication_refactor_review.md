# Communication Module Review & Refactoring Proposal

## Scope

This review covers `src/modules/communication` with focus on layering (`domain/application/infrastructure/presentation`), use-case boundaries, dependency wiring, and module-level maintainability.

## What is already good

- **Clear bounded context and rich decomposition**: communication capabilities are split by subdomain (`provider_connector`, `provider_connection`, `message_template`, `outbound_message`, `delivery`) consistently across layers.
- **Layered architecture discipline**: domain entities/value-objects and application use-cases are separated from runtime repositories and HTTP controllers.
- **Explicit command/query/use_case structure** in application layer improves discoverability for handlers.
- **Runtime mapping isolation** (`row_mapper.py`) keeps ORM/runtime format conversion out of domain logic.
- **Comprehensive test surface**: dedicated tests across domain, application, runtime repositories, HTTP and management command paths.
- **Connector-driven provider model** is flexible: YAML spec + schema validation + templated send config allows providers without code changes.

## Current structural issues

### 1) Folder depth and duplication overhead

There is high nesting and repeated patterns in each slice:

- `presentation/http/<feature>/{controller,requests,responses,router}`
- `application/<feature>/{command,dto,query,use_case}`
- mirrored `__init__.py` in nearly every folder

This is architecturally clean, but operationally heavy for everyday changes (many files touched for one endpoint).

### 2) Mixed responsibilities in `application/services.py`

`ProviderYamlLoader`, JSON schema validation, templating, JSONPath and secret encoding live in one broad utility module. It risks becoming a “god service” and makes dependency ownership less explicit.

### 3) Inconsistent naming style for handlers

Presentation uses `controller/<verb_object>.py` while application uses `use_case/<verb_object>.py`; mostly aligned, but some names are transport-centric (e.g. `import_provider_connector_yaml`) while others are intent-centric (`register_provider_connector`).

### 4) Boundary leakage risk in dependency wiring

`presentation/depends/*` wires many layer-specific implementations. As module grows, this can become a hidden composition root with strong coupling to concrete infrastructure types.

### 5) Repeated response/request mapping code

Each HTTP feature has dedicated response DTO conversion modules. Good for strictness, but much of code likely follows near-identical mapping template.

## Refactoring proposals (prioritized)

## P0 (high impact / low-moderate risk)

1. **Split `application/services.py` into cohesive services**:
   - `provider_yaml_loader.py`
   - `json_schema_validator.py`
   - `template_render_service.py`
   - `provider_secrets_codec.py`
   - `response_mapping_service.py` (JSONPath/status mapping)

   Benefits: smaller change surface, better test focus, clearer DI contracts.

2. **Add explicit module composition root** (`src/modules/communication/bootstrap.py`):
   - centralize factories for repositories, use-cases, queue publisher/worker services
   - presentation and management commands depend on composition root instead of reconstructing dependencies ad hoc

   Benefits: lower wiring duplication, easier future replacement/testing.

3. **Introduce feature-level `mappers.py` in presentation**:
   - consolidate request->command and dto->response transforms
   - keep controllers thin and mostly orchestration

   Benefits: reduce repeated boilerplate and standardize HTTP mapping conventions.

## P1 (medium impact)

4. **Flatten shallow folder levels where possible**:
   - in application: consider `handlers/commands`, `handlers/queries` or `use_cases` + `dto` only
   - in presentation: merge tiny `controller` directories into feature package when each file contains one function

   Benefits: faster navigation, less file churn.

5. **Unify naming conventions around intent**:
   - prefer business verbs: `register_connector`, `create_connection`, `enqueue_outbound`, `handle_webhook`
   - avoid transport-specific names in application layer (`import_yaml` can stay in presentation only)

6. **Define stricter port contracts for provider senders**:
   - one port per capability (send, webhook parse/verify if needed)
   - support future providers beyond YAML transports with minimal branching.

## P2 (incremental quality)

7. **Add architecture tests for layer import rules**:
   - domain must not import application/infrastructure/presentation
   - application must not import presentation

8. **Document “change cookbook”** in docs:
   - “How to add new provider message type”
   - “How to add new outbound status mapping”
   - “How to add new endpoint with command/use-case/query flow”

9. **Add module metrics baseline**:
   - number of files per slice
   - average files touched per feature change
   - track after refactors to validate simplification.

## Suggested target structure (example)

```text
communication/
  domain/
  application/
    provider_connector/
      commands.py
      queries.py
      dto.py
      handlers.py
    outbound_message/
      commands.py
      queries.py
      dto.py
      handlers.py
    services/
      provider_yaml_loader.py
      template_render_service.py
      json_schema_validator.py
      provider_secrets_codec.py
      response_mapping.py
    bootstrap.py
  infrastructure/
    runtime/
      provider_connector_repository.py
      provider_connection_repository.py
      ...
    messaging/
      rabbitmq_publisher.py
      rabbitmq_worker.py
    provider_senders/
      yaml_http_sender.py
      yaml_smtp_sender.py
  presentation/
    http/
      provider_connector.py
      provider_connection.py
      message_template.py
      outbound_message.py
      delivery.py
    depends.py
```

## Practical migration plan

1. Extract `application/services.py` into small modules without behavior changes.
2. Move DI wiring into `bootstrap.py`; keep old imports as compatibility wrappers for one release.
3. Standardize naming in new files first; defer mass rename until stable.
4. Consolidate repetitive HTTP mappers.
5. Run existing communication test suite after each step.

## Summary assessment

- **Architecture quality**: high (well-bounded and layered).
- **Maintainability today**: medium-high (strong patterns, but too much structural verbosity).
- **Main risk**: architectural ceremony turns into delivery friction.
- **Main opportunity**: reduce file/directory overhead and centralize composition while preserving clean boundaries.
