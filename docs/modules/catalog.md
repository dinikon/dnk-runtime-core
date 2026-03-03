# Catalog Module

## Текущее состояние

`src/modules/catalog` сейчас является каркасом bounded context без реализованной прикладной логики.

## Предполагаемая роль

Модуль должен содержать tenant-scoped каталоговые сущности и сценарии работы с ними.

## Архитектурная договоренность

При реализации:

- не использовать ORM чужих модулей напрямую
- tenant context получать через application ports/adapters
- правила freeze/read-only учитывать так же, как и в остальных бизнес-модулях

## Пока публичных контрактов нет

- HTTP endpoints: нет
- application use cases: нет
- domain contracts: нет
