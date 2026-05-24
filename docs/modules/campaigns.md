# Модуль Campaigns

## Статус

Roadmap-документ M0 для фиксации границ. `campaigns` пока не реализован в `src/modules`.

Документ фиксирует целевые границы bounded context до добавления runtime objects, API и workers.

## Назначение

`campaigns` владеет CRM/business campaign planning, lifecycle, goals и metrics. Это business layer над audience,
broadcast и workflow capabilities; модуль не реализует собственный workflow engine.

`campaigns` отвечает на вопрос:

```text
business campaign goal + audience + schedule + orchestration template -> measurable campaign execution
```

## Граница ответственности

`campaigns` владеет:

- campaign definition и business lifecycle;
- campaign audience selection на business-level;
- campaign goals и conversion definitions;
- campaign-level scheduling intent;
- campaign metrics и reporting projections;
- mapping из campaign plan в workflow runs или broadcast runs;
- business ownership campaign assets и references.

`campaigns` не владеет:

- workflow graph engine или node execution scheduler;
- dynamic segment DSL и audience calculation internals;
- broadcast recipient fan-out и recipient dispatch mechanics;
- provider payload rendering или provider send attempts;
- contact point normalization/resolution internals;
- external event ingestion и normalization.

## Доменные понятия

- `Campaign`: business aggregate, представляющий marketing/CRM initiative.
- `CampaignGoal`: измеримая цель, например conversion, reply, purchase или custom event.
- `CampaignAudience`: ссылка на segment, segment snapshot или explicit audience input.
- `CampaignPlan`: business configuration, маппящаяся в workflow/broadcast execution.
- `CampaignRun`: конкретный campaign execution period.
- `CampaignMetric`: агрегированная campaign result projection.
- `CampaignAttributionRule`: правило, которое мапит normalized events или communication outcomes в campaign metrics.

## Планируемая application surface

Основные use cases:

| Use Case                      | Вход                                      | Выход                   | Примечание о границе                                                     |
|-------------------------------|-------------------------------------------|-------------------------|--------------------------------------------------------------------------|
| `CreateCampaignUseCase`       | metadata, goal, audience и plan           | `CampaignDTO`           | Создает draft campaign.                                                  |
| `UpdateCampaignUseCase`       | campaign id и patch                       | `CampaignDTO`           | Меняет business configuration до launch.                                 |
| `ValidateCampaignUseCase`     | campaign id                               | `CampaignValidationDTO` | Валидирует audience, workflow/broadcast references и goal config.        |
| `LaunchCampaignUseCase`       | campaign id                               | `CampaignRunDTO`        | Делегирует execution в workflow или broadcast use cases.                 |
| `PauseCampaignUseCase`        | campaign id или run id                    | `CampaignDTO`           | Ставит будущие campaign actions на паузу через orchestration boundaries. |
| `ArchiveCampaignUseCase`      | campaign id                               | `CampaignDTO`           | Убирает campaign из active business usage.                               |
| `RecordCampaignSignalUseCase` | normalized event или communication signal | `CampaignMetricDTO`     | Обновляет campaign projections через attribution rules.                  |
| `GetCampaignMetricsUseCase`   | campaign id и period                      | `CampaignMetricsDTO`    | Читает business reporting state.                                         |

## Направление зависимостей

Разрешенные исходящие зависимости:

| Зависимость       | Для чего используется                                                                    |
|-------------------|------------------------------------------------------------------------------------------|
| `shared`          | IDs, domain errors, clock/UUID ports, UoW и request context dependencies.                |
| `segmentation`    | Валидация и резолвинг campaign audience references.                                      |
| `broadcast`       | Создание/запуск broadcast runs для campaign send actions.                                |
| `workflow`        | Создание/publish workflow definitions и запуск workflow runs.                            |
| `communication`   | Чтение summarized communication outcomes только для reporting.                           |
| `schema_registry` | Runtime object descriptors и object feature metadata для campaign-owned runtime objects. |
| `runtime_data`    | Хранение/поиск campaign runtime rows, если campaign objects descriptor-backed.           |

Разрешенные входящие данные:

- normalized external events через shared event/outbox contract или application use case;
- summarized communication delivery signals;
- workflow run status changes;
- broadcast run status changes.

Запрещенные исходящие зависимости:

- provider HTTP clients, SMTP clients или SMS provider adapters;
- workflow engine internals вне публичной application boundary модуля `workflow`;
- ingestion internals модуля `external_events`.

Запрещенная ответственность:

- `campaigns` не должен содержать собственный workflow engine.
- `campaigns` не должен дублировать segment calculation logic.
- `campaigns` не должен dispatch broadcast recipients напрямую.

## Межмодульный контракт

Campaign launch делегирует execution через application boundaries:

```text
campaign_id
campaign_run_id
audience_ref
goal_ref
plan_ref
correlation_id
```

Execution target может быть:

- workflow version/run под управлением `workflow`;
- broadcast run под управлением `broadcast`;
- оба варианта, когда campaign plan мапит business steps в workflow nodes, которые создают broadcasts.

Campaign metrics хранят business projections и ссылки на external execution ids. Они не хранят provider payloads или
workflow node internals.

## Правила реализации

- Campaign lifecycle является business lifecycle, а не workflow run lifecycle.
- Campaign status changes должны вызывать use cases модулей `workflow`/`broadcast`, а не мутировать их storage напрямую.
- Goals и metrics принадлежат `campaigns`, даже если source signals приходят из `communication` или `external_events`.
- Campaign-owned runtime objects должны описываться через `schema_registry` и храниться через `runtime_data`, следуя
  существующим module patterns.
- Reporting projections должны быть rebuildable из campaign state плюс normalized signals, когда это практично.

## Связанная документация

- [Workflow Module](./workflow.md)
- [Segmentation Module](./segmentation.md)
- [Broadcast Module](./broadcast.md)
- [Communication Module](./communication.md)
- [External Events Module](./external-events.md)

## Источник истины

- GitHub issue #36.
- Будущий `src/modules/campaigns/...`.
