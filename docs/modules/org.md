# Org Module

## Текущее состояние

`src/modules/org` сейчас является каркасом bounded context без реализованной логики.

## Предполагаемая роль

Модуль должен отвечать за tenant-scoped организационные сущности и операции.

## Архитектурная договоренность

При реализации:

- не тянуть ORM других модулей
- tenant context получать через application boundary
- учитывать различие между `active` и `freeze`

## Пока публичных контрактов нет

- HTTP endpoints: нет
- application use cases: нет
- domain contracts: нет
