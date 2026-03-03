# CRM Module

## Текущее состояние

`src/modules/crm` сейчас является каркасом bounded context без реализованных application use cases, domain entities и HTTP API.

## Предполагаемая роль

Модуль должен отвечать за CRM-сущности и бизнес-операции tenant.

## Архитектурная договоренность

Когда в `crm` появятся write/read сценарии, модуль должен:

- получать tenant context через отдельный dependency/use case, а не из raw host вручную
- использовать правила `Tenant.allows_read_business_data()` и `Tenant.allows_write_business_data()`
- трактовать `freeze` как read-only режим:
  - чтение допустимо
  - запись запрещена

## Пока публичных контрактов нет

- HTTP endpoints: нет
- application use cases: нет
- domain contracts: нет
