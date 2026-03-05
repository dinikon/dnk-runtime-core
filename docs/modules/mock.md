# Mock Module

## Ответственность

`src/modules/mock` предоставляет frontend-friendly mock endpoints с фиксированными контрактами для быстрой интеграции UI до появления реальной бизнес-логики.

## Текущее состояние

Сейчас модуль отдает mock-ответы для фронтенда по путям:

- `GET /api/mock/workplaces`
- `GET /api/mock/workplaces/crm`
- `GET /api/mock/workplaces/crm/entities/{entity_key}`

Для `crm/entities/{entity_key}` сейчас подготовлены mock-записи:

- `lead`
- `deal`
- `contact`
- `company`

Ответы статические и не зависят от БД, tenant context или внешних сервисов.

## Структура

- `application/workplaces` — use case и DTO для mock-контрактов workplace navigation
- `presentation/api` — HTTP route и response schemas
- `presentation/depends` — сборка use case через FastAPI dependency

`domain` и `infrastructure` пока остаются пустыми, чтобы модуль соответствовал общей модульной структуре проекта и мог расширяться без перестройки каталогов.

## Ограничения

- модуль не должен становиться местом для бизнес-логики `crm`, `support`, `org` и других bounded contexts;
- при появлении реальных backend-сценариев mock-ответы должны либо удаляться, либо переводиться в изолированные feature-специфичные use cases с явным контрактом.
