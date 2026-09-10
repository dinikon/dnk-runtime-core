# Модуль Campaigns

## Статус

Roadmap-документ M0 для фиксации границ. `campaigns` пока не реализован в `src/modules`.

Документ фиксирует целевые границы bounded context до добавления runtime objects, API и workers.

## Назначение

`campaigns` владеет CRM/business campaign planning, lifecycle, goals и metrics. Это business layer над audience и
future execution/send orchestration capabilities; модуль не реализует собственный orchestration engine.

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
- mapping из campaign plan в future execution или send orchestration runs;
- business ownership campaign assets и references.

`campaigns` не владеет:

- business orchestration engine или node execution scheduler;
- dynamic segment DSL и audience calculation internals;
- recipient fan-out и dispatch mechanics будущего send orchestration boundary;
- provider payload rendering или provider send attempts;
- external event ingestion и normalization.

## Доменные понятия

- `Campaign`: business aggregate, представляющий marketing/CRM initiative.
- `CampaignGoal`: измеримая цель, например conversion, reply, purchase или custom event.
- `CampaignAudience`: ссылка на segment, segment snapshot или explicit audience input.
- `CampaignPlan`: business configuration, маппящаяся в execution/send orchestration.
- `CampaignRun`: конкретный campaign execution period.
- `CampaignMetric`: агрегированная campaign result projection.
- `CampaignAttributionRule`: правило, которое мапит normalized events или execution outcomes в campaign metrics.

## Планируемая application surface

Основные use cases:

| Use Case                      | Вход                                      | Выход                   | Примечание о границе                                                     |
|-------------------------------|-------------------------------------------|-------------------------|--------------------------------------------------------------------------|
| `CreateCampaignUseCase`       | metadata, goal, audience и plan           | `CampaignDTO`           | Создает draft campaign.                                                  |
| `UpdateCampaignUseCase`       | campaign id и patch                       | `CampaignDTO`           | Меняет business configuration до launch.                                 |
| `ValidateCampaignUseCase`     | campaign id                               | `CampaignValidationDTO` | Валидирует audience, execution/send references и goal config.            |
| `LaunchCampaignUseCase`       | campaign id                               | `CampaignRunDTO`        | Делегирует execution в future orchestration use cases.                   |
| `PauseCampaignUseCase`        | campaign id или run id                    | `CampaignDTO`           | Ставит будущие campaign actions на паузу через orchestration boundaries. |
| `ArchiveCampaignUseCase`      | campaign id                               | `CampaignDTO`           | Убирает campaign из active business usage.                               |
| `RecordCampaignSignalUseCase` | normalized event или execution signal     | `CampaignMetricDTO`     | Обновляет campaign projections через attribution rules.                  |
| `GetCampaignMetricsUseCase`   | campaign id и period                      | `CampaignMetricsDTO`    | Читает business reporting state.                                         |

## Направление зависимостей

Разрешенные исходящие зависимости:

| Зависимость       | Для чего используется                                                                    |
|-------------------|------------------------------------------------------------------------------------------|
| `shared`          | IDs, domain errors, clock/UUID ports, UoW и request context dependencies.                |
| `schema_registry` | Runtime object descriptors для campaign-owned runtime objects.                             |
| `runtime_data`    | Хранение/поиск campaign runtime rows, если campaign objects descriptor-backed.           |

Audience resolution and bulk-send orchestration are future boundaries and are intentionally not documented as current
modules.

Разрешенные входящие данные:

- normalized external events через shared event/outbox contract или application use case;
- summarized execution result signals;
- orchestration run status changes;
- future bulk-send run status changes.

Запрещенные исходящие зависимости:

- provider HTTP clients, SMTP clients или SMS provider adapters;
- orchestration engine internals вне публичной application boundary будущего execution-модуля;
- ingestion internals модуля `external_events`.

Запрещенная ответственность:

- `campaigns` не должен содержать собственный orchestration engine.
- `campaigns` не должен дублировать future audience calculation logic.
- `campaigns` не должен dispatch bulk-send recipients напрямую.

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

Execution target может быть future orchestration run или bulk-send run под управлением отдельного execution boundary.

Campaign metrics хранят business projections и ссылки на external execution ids. Они не хранят provider payloads или
внутреннее состояние orchestration nodes.

## Правила реализации

- Campaign lifecycle является business lifecycle, а не execution run lifecycle.
- Campaign status changes должны вызывать use cases будущего execution/send orchestration boundary, а не
  мутировать их storage напрямую.
- Goals и metrics принадлежат `campaigns`, даже если source signals приходят из execution boundary или `external_events`.
- Campaign-owned runtime objects должны описываться через `schema_registry` и храниться через `runtime_data`, следуя
  существующим module patterns.
- Reporting projections должны быть rebuildable из campaign state плюс normalized signals, когда это практично.

## Связанная документация

- [External Events Module](./external-events.md)

## Источник истины

- GitHub issue #36.
- Будущий `src/modules/campaigns/...`.
