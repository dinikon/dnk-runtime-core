# Runtime Schema Module

## Ответственность

`src/modules/runtime_schema` — bounded context, который владеет:

- `object_metadata`
- `field_metadata`
- registry системных объектов tenant schema
- bootstrap системных таблиц в tenant schema
- будущим DDL orchestration для custom objects и custom fields

`runtime_schema` не владеет tenant lifecycle. Создание tenant остается в `tenancy`, но `tenancy` вызывает bootstrap этого модуля через application port.

## Текущее состояние

Сейчас модуль реализует:

- public metadata models `object_metadata` и `field_metadata`
- `BootstrapTenantSystemSchemaUseCase`
- статический provider системных CRM объектов
- `SqlAlchemyTenantSchemaManager`, который создает системные таблицы в PostgreSQL tenant schema

## Архитектурная договоренность

- `name_singular` у object metadata immutable
- `name_field` у field metadata immutable
- физическая tenant schema одна на tenant
- все tenant tables живут в этой одной schema
- системные объекты bootstrap'ятся автоматически при создании tenant

## Следующие шаги

- custom objects
- custom fields для системных объектов
- DDL jobs / locking / reconciliation
- явные CRUD use cases для metadata management
