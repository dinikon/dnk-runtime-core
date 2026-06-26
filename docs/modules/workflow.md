# Модуль Workflow

## Статус

Roadmap-документ M0 для фиксации границ и текущего domain skeleton.
`workflow` частично реализован в `src/modules/workflow/domain`.

Документ фиксирует целевые границы bounded context до добавления runtime objects, API и workers.

## Назначение

`workflow` владеет generic graph orchestration и node execution. Он предоставляет tenant-scoped engine для definitions,
versions, runs и node attempts без встраивания CRM campaign semantics или provider-specific messaging logic.

`workflow` отвечает на вопрос:

```text
workflow definition + trigger + runtime context -> ordered node executions
```

## Граница ответственности

`workflow` владеет:

- workflow definitions и immutable published versions;
- graph structure, node definitions и edge rules;
- graph validation;
- run lifecycle;
- node execution lifecycle;
- retry, timeout и compensation policy на уровне node execution;
- trigger registration model;
- execution context и run state persistence;
- generic action-port dispatch для вызовов внешних bounded contexts.

`workflow` не владеет:

- campaign business concepts, campaign goals или campaign metrics;
- segment definition/calculation DSL;
- broadcast recipient fan-out;
- provider-specific message delivery;
- provider webhook processing;
- external event ingestion и normalization;
- CRM object semantics за пределами того, что node adapter получает через input contract.

## Доменные понятия

- `WorkflowApplication`: приложение/контейнер workflow, владеющий активной definition.
- `WorkflowDefinition`: редактируемый draft workflow.
- `WorkflowVersion`: неизменяемый опубликованный graph.
- `WorkflowNode`: типизированный step в graph.
- `WorkflowEdge`: transition rule между nodes.
- `WorkflowRun`: один execution instance.
- `NodeExecution`: дочерняя entity внутри `WorkflowRun`, представляющая выполнение node.
- `WorkflowTrigger`: abstract trigger descriptor, например manual, schedule или normalized event.
- `WorkflowAction`: generic action, запрошенный node через зарегистрированный port.

## Текущая доменная структура

Domain код сгруппирован по Aggregate Root:

```text
src/modules/workflow/domain/
├── workflow_application/
├── workflow_definition/
└── workflow_run/
```

`NodeExecutionEntity` хранится в `workflow_run/entities/node_execution.py`, потому что относится к consistency boundary
`WorkflowRun`, а не является самостоятельным aggregate root.

## Планируемая application surface

Основные use cases:

| Use Case                            | Вход                         | Выход                    | Примечание о границе                                         |
|-------------------------------------|------------------------------|--------------------------|--------------------------------------------------------------|
| `CreateWorkflowDefinitionUseCase`   | metadata и draft graph       | `WorkflowDefinitionDTO`  | Создает редактируемую definition.                            |
| `UpdateWorkflowDefinitionUseCase`   | definition id и graph patch  | `WorkflowDefinitionDTO`  | Держит изменения в draft до публикации.                      |
| `ValidateWorkflowDefinitionUseCase` | definition id или graph      | `WorkflowValidationDTO`  | Валидирует graph shape, node configs и action contracts.     |
| `PublishWorkflowVersionUseCase`     | definition id                | `WorkflowVersionDTO`     | Фиксирует version для execution.                             |
| `StartWorkflowRunUseCase`           | version id и trigger context | `WorkflowRunDTO`         | Запускает run от version.                                    |
| `AdvanceWorkflowRunUseCase`         | run id                       | `WorkflowRunDTO`         | Выбирает executable nodes и schedules/executes их.           |
| `ExecuteWorkflowNodeUseCase`        | node run id                  | `WorkflowNodeRunDTO`     | Выполняет один node через local или external action adapter. |
| `CancelWorkflowRunUseCase`          | run id                       | `WorkflowRunDTO`         | Отменяет pending work.                                       |
| `HandleWorkflowTriggerUseCase`      | trigger type и payload       | `WorkflowRunDTO \| None` | Резолвит matching versions и запускает runs.                 |

Node-specific adapters должны быть узкими и заменяемыми. Domain model workflow должен оставаться generic.

## Направление зависимостей

Разрешенные исходящие зависимости для workflow core:

| Зависимость       | Для чего используется                                                                            |
|-------------------|--------------------------------------------------------------------------------------------------|
| `shared`          | IDs, domain errors, clock/UUID ports, UoW и request context dependencies.                        |
| `schema_registry` | Опциональные runtime object descriptors для workflow-owned runtime objects и node input schemas. |
| `runtime_data`    | Опциональное descriptor-backed storage/search для workflow definitions и run records.            |

Разрешенные исходящие зависимости только для node adapters:

| Зависимость       | Для чего используется                                                  |
|-------------------|------------------------------------------------------------------------|
| `segmentation`    | Segment calculation или audience resolution nodes.                     |
| `broadcast`       | Broadcast creation/start nodes.                                        |
| `communication`   | Прямые one-off communication nodes, если нужны.                        |
| `external_events` | Event schema lookup, только если это не покрыто shared event contract. |

Запрещенные исходящие зависимости:

- `campaigns`;
- provider HTTP clients, SMTP clients или SMS provider adapters;
- direct writes в module-owned tables модулей `segmentation`, `broadcast`, `communication`, `campaigns` или
  `external_events`.

Разрешенные входящие вызовы:

- `campaigns` может создавать/publish workflow definitions и запускать runs.
- `external_events` или event-consumer adapter может вызывать `HandleWorkflowTriggerUseCase` с normalized event
  payloads.
- Operators или management commands могут запускать, advance, cancel или retry runs.

## Межмодульный контракт

Workflow nodes вызывают другие bounded contexts через application-level ports:

```text
node_type
tenant_id
run_id
node_run_id
correlation_id
input_payload
idempotency_key
```

Adapters возвращают нормализованный node result:

```text
status
external_ref_type
external_ref_id
result_payload
retry_after
error_code
error_message
```

Workflow module хранит нормализованный результат. Он не должен сохранять foreign module internals как workflow-owned
state.

## Правила реализации

- `campaigns` является клиентом `workflow`, а не зависимостью `workflow`.
- Workflow domain entities не должны импортировать concrete node adapters.
- Node adapters могут жить в infrastructure/integration code и зависеть от application ports внешних bounded contexts.
- Published workflow versions неизменяемы.
- Runs выполняются по workflow version, а не по mutable definition.
- Node execution должен быть идемпотентным по `node_run_id` или explicit idempotency key.
- Failed node не должен частично мутировать workflow graph definitions.

## Связанная документация

- [Campaigns Module](./campaigns.md)
- [Segmentation Module](./segmentation.md)
- [Broadcast Module](./broadcast.md)
- [External Events Module](./external-events.md)
- [Develop Style](../develop-style.md)

## Источник истины

- GitHub issue #36.
- `src/modules/workflow/...`.
