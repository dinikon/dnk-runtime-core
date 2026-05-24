# Модуль Segmentation

## Статус

Roadmap-документ M0 для фиксации границ. `segmentation` пока не реализован в `src/modules`.

Документ фиксирует целевые границы bounded context до добавления runtime objects, API и workers.

## Назначение

`segmentation` владеет tenant-scoped определениями аудиторий и расчетом аудитории. Модуль отвечает на вопрос:

```text
source objects + filters + resolution paths -> target audience subjects
```

Модуль выбирает записи, которые входят в аудиторию. Он не решает, какой телефон, email, provider, template или шаг
workflow будет использовать эту аудиторию.

## Граница ответственности

`segmentation` владеет:

- static и dynamic segment definitions;
- выбором target object;
- include/exclude правилами аудитории;
- валидацией filter DSL относительно runtime object descriptors;
- валидацией resolution paths от source objects к target object;
- ссылками между сегментами и обнаружением циклов;
- preview/count расчетом;
- сохраненными snapshots расчета аудитории;
- дедупликацией target audience subjects;
- жизненным циклом сегмента: `DRAFT`, `ACTIVE`, `PAUSED`, `INVALID`, `ARCHIVED`.

`segmentation` не владеет:

- contact point resolution;
- выбором phone/email/provider/message-template;
- созданием или доставкой outbound messages;
- broadcast throttling, batching, retries или recipient status;
- campaign goals, campaign metrics или CRM-specific campaign lifecycle;
- выполнением workflow graph;
- ingestion внешних событий или нормализацией событий.

## Доменные понятия

- `Segment`: сохраненное правило аудитории или сохраненный static audience list.
- `StaticSegment`: фиксированный список target records.
- `DynamicSegment`: include/exclude rules, вычисляемые во время расчета.
- `TargetObject`: runtime object, который возвращает segment, например `contact` или `company`.
- `SourceObject`: runtime object, по которому применяется правило фильтрации.
- `AudienceSubject`: нормализованный результат: `target_object_id` + `target_record_id`.
- `ResolutionPath`: relation path от source object к target object.
- `SegmentCalculation`: одна preview- или snapshot-попытка расчета.
- `SegmentSnapshot`: сохраненный результат расчета для downstream modules.

## Планируемая application surface

Основные use cases:

| Use Case                          | Вход                                | Выход                      | Примечание о границе                                                            |
|-----------------------------------|-------------------------------------|----------------------------|---------------------------------------------------------------------------------|
| `CreateSegmentUseCase`            | segment metadata и definition       | `SegmentDTO`               | Создает только draft segment.                                                   |
| `UpdateSegmentUseCase`            | segment id и patch                  | `SegmentDTO`               | Изменение definition требует повторной валидации перед активным использованием. |
| `ValidateSegmentUseCase`          | segment id или transient definition | `SegmentValidationDTO`     | Валидирует object descriptors, filters, paths и references.                     |
| `ActivateSegmentUseCase`          | segment id                          | `SegmentDTO`               | Требует успешной валидации.                                                     |
| `PauseSegmentUseCase`             | segment id                          | `SegmentDTO`               | Запрещает новое downstream-использование без удаления snapshots.                |
| `ArchiveSegmentUseCase`           | segment id                          | `SegmentDTO`               | Скрывает segment из будущего использования.                                     |
| `PreviewSegmentUseCase`           | segment id или transient definition | `SegmentPreviewDTO`        | Возвращает count/sample без сохранения members.                                 |
| `CalculateSegmentSnapshotUseCase` | segment id                          | `SegmentCalculationDTO`    | Сохраняет snapshot и snapshot members.                                          |
| `GetSegmentSnapshotUseCase`       | calculation id                      | `SegmentSnapshotDTO`       | Доступ только на чтение для downstream modules.                                 |
| `ResolveAudienceSubjectsUseCase`  | segment id или calculation id       | `list[AudienceSubjectDTO]` | Публичная application boundary для `broadcast` и orchestration.                 |

Все commands и DTO должны жить в `segmentation.application`. HTTP schemas остаются в presentation.

## Направление зависимостей

Разрешенные исходящие зависимости:

| Зависимость       | Для чего используется                                                                                                                        |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `shared`          | `EntityIdVO`, domain errors, `ClockPort`, `UuidPort`, UoW и request context dependencies.                                                    |
| `schema_registry` | Runtime object descriptors, relation metadata, object feature checks и field metadata.                                                       |
| `runtime_data`    | Descriptor-backed filter validation, search, count и загрузка snapshot members.                                                              |
| `contact_point`   | Только optional addressability capability checks; не contact point selection. По возможности использовать `schema_registry` object features. |

Запрещенные исходящие зависимости:

- `broadcast`;
- `campaigns`;
- `workflow`;
- `communication`;
- `external_events`;
- provider adapters или queue workers.

Разрешенные входящие вызовы:

- `broadcast` может получать active segment subjects или использовать сохраненный segment snapshot.
- `campaigns` может выбирать segment как campaign audience через application boundary модуля segmentation.
- `workflow` может вызывать validation/calculation сегмента через generic action port.

## Межмодульный контракт

Публичный результат `segmentation` - список audience subjects или snapshot:

```text
tenant_id
target_object_id
target_object_name
target_record_id
calculation_id
definition_version
```

Результат не должен содержать выбранный `contact_point_id`, channel, provider, template, rendered payload или campaign
metric fields. Это ответственность downstream bounded contexts.

## Правила реализации

- `segmentation.domain` может зависеть только от `shared` primitives и локальных value objects.
- Filter DSL нужно переиспользовать из `runtime_data`; отдельный filter engine создавать нельзя.
- Runtime object и relation metadata должны резолвиться через `schema_registry`.
- Segment references должны валидироваться на совпадение target object и отсутствие циклов.
- Calculation snapshots неизменяемы после создания.
- Static members также должны нормализоваться до `AudienceSubject`.
- Segment может использоваться downstream modules только когда он active или когда явно передан конкретный calculation
  snapshot.

## Связанная документация

- [Broadcast Module](./broadcast.md)
- [Campaigns Module](./campaigns.md)
- [Workflow Module](./workflow.md)
- [Contact Point Module](./contact_point.md)
- [Runtime Data Module](./runtime-data.md)
- [Schema Registry Module](./schema-registry.md)
- [Communication segment lifecycle plan](../plan/communication_segment_lifecycle.md)

## Источник истины

- GitHub issue #36.
- `docs/plan/communication_segment_lifecycle.md`.
- Будущий `src/modules/segmentation/...`.
