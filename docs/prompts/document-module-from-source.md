# Инструкция по написанию документации модуля из исходного кода

Этот документ содержит строгий промпт для Codex/AI-агента, который должен создать или обновить опорную документацию по
модулю на основе фактического состояния кода.

## Role

Ты technical writer + senior backend engineer в проекте с DDD + Clean Architecture.

Твоя задача — перечитать код модуля `<MODULE_NAME>`, собрать фактический контекст и создать/обновить опорный файл
документации:

`docs/modules/<module_name>.md`

Это НЕ задача на redesign.
Это НЕ задача на изменение кода.
Это НЕ задача на добавление функциональности.
Это задача на factual documentation from source code.

## Source Of Truth

Главный источник истины — текущий код модуля:

`src/modules/<module_name>/`

Дополнительные источники:

- `docs/develop-style.md`
- `docs/modules/crm.md`
- существующий `docs/modules/<module_name>.md`, если он уже есть
- `tests`, если они покрывают поведение модуля

Если документация конфликтует с кодом — код важнее.
Если поведение не найдено в коде или тестах — не выдумывай.

## Target

Создать или обновить файл:

`docs/modules/<module_name>.md`

Документ должен быть опорным описанием модуля:

- для разработчика;
- для Codex/AI-агента;
- для code review;
- для дальнейшего refactoring-to-standard;
- для понимания границ bounded context.

Документ должен быть достаточно детальным, чтобы следующий агент мог понять:

- зачем существует модуль;
- какие публичные сценарии он поддерживает;
- какие aggregate/domain models есть;
- какие use cases есть;
- какие repositories/adapters используются;
- какие HTTP routes есть;
- какие зависимости на другие модули есть;
- какие тесты покрывают модуль;
- где находится source of truth.

## Strict Rules

Запрещено:

- выдумывать поведение, которого нет в коде;
- описывать желаемую архитектуру как уже существующую;
- скрывать архитектурные проблемы;
- добавлять roadmap как факт;
- менять код;
- создавать новые source files;
- переименовывать файлы;
- удалять файлы;
- менять tests;
- писать marketing-style описание;
- писать слишком общие фразы без привязки к файлам;
- писать “модуль отвечает за всё”;
- смешивать текущую реализацию и будущие планы.

Разрешено:

- создать `docs/modules/<module_name>.md`;
- обновить существующий `docs/modules/<module_name>.md`;
- добавить раздел `Known Gaps / Technical Debt`, если код не соответствует `develop-style`;
- добавить ссылки на реальные файлы;
- явно указать “не найдено”, если информация отсутствует.

## Workflow

Перед написанием документации выполни аудит.

Обязательно прочитай:

1. Структуру модуля:

   `src/modules/<module_name>/`

2. Domain layer:

   `src/modules/<module_name>/domain/`

3. Application layer:

   `src/modules/<module_name>/application/`

4. Infrastructure layer:

   `src/modules/<module_name>/infrastructure/`

5. Presentation layer:

   `src/modules/<module_name>/presentation/`

6. DI:

   `src/modules/<module_name>/presentation/depends/`

7. HTTP routes:

   `src/modules/<module_name>/presentation/http/`

8. Tests:

    - `tests/`
    - `tests/modules/`
    - любые тесты, где упоминается `<module_name>`

9. Существующую документацию:

    - `docs/modules/<module_name>.md`
    - `docs/modules/crm.md`
    - `docs/develop-style.md`

## Context Collection Checklist

Собери факты по следующим вопросам.

### 1. Purpose

- Зачем существует модуль?
- Какую бизнес-область он покрывает?
- Является ли модуль узким bounded context или содержит несколько subdomain?
- Это runtime-data module, ORM module, integration module или orchestration module?

### 2. Public Functionality

- Какие пользовательские/внешние действия поддерживает модуль?
- Какие CRUD-сценарии есть?
- Есть ли describe fields / metadata endpoints?
- Есть ли background jobs / management commands / event handlers?
- Есть ли read-only сценарии?

### 3. Main Flows / Use Cases

Перечисли фактические use cases из:

`src/modules/<module_name>/application/**/use_case/`

Для каждого use case укажи:

- имя класса;
- назначение;
- основной input command/query;
- output DTO/result;
- какие domain services/repositories использует.

### 4. Domain Model

Опиши aggregate/entities из:

`src/modules/<module_name>/domain/**/entity.py`

Для каждой entity укажи:

- имя;
- ключевой id VO;
- tenant scope, если есть;
- основные поля;
- create/update методы;
- основные business invariants;
- domain errors;
- value objects.

### 5. Application Contracts

Опиши:

- command classes;
- query classes;
- DTO classes;
- repository Protocol;
- use case classes.

Укажи:

- где используются dataclass;
- где immutable command;
- какие DTO возвращаются;
- есть ли нарушения style guide.

### 6. Infrastructure / Persistence

Опиши фактические adapters/repositories из:

`src/modules/<module_name>/infrastructure/`

Для каждого repository/adaptor укажи:

- какой Protocol реализует;
- использует runtime_data или SQLAlchemy/ORM;
- как получает tenant scope;
- хранит ли tenant_id в instance;
- какие runtime object names использует;
- как мапит row/entity/DTO;
- какие внешние gateways/services использует;
- какие ошибки поднимает.

### 7. Presentation / HTTP API

Изучи routers/controllers.

Для каждого route укажи:

- HTTP method;
- path;
- controller function;
- request schema;
- response schema;
- use case;
- auth/context dependency;
- какие ошибки мапятся в HTTP.

Формат:

| Method | Path | Controller | Use Case | Request | Response |
|--------|------|------------|----------|---------|----------|

### 8. Dependency Injection

Изучи:

`src/modules/<module_name>/presentation/depends/`

Опиши:

- какие repositories создаются;
- какие services создаются;
- какие use cases создаются;
- какие shared dependencies используются;
- где подключается UoW/session/gateway/resolver;
- есть ли нарушения layering.

### 9. Dependencies On Other Modules

Перечисли реальные зависимости:

- `shared`
- `schema_registry`
- `runtime_data`
- `crm`
- `communication`
- `workflow`
- любые другие

Для каждой зависимости укажи:

- зачем используется;
- в каком слое;
- через какой файл/класс.

### 10. Events / Commands / Background Processing

Если есть, опиши:

- event handlers;
- message consumers;
- scheduled jobs;
- management commands;
- CLI commands;
- outbox/inbox;
- queues.

Если нет — напиши:

> В текущей реализации не найдено.

### 11. Tests Covering This Module

Найди тесты.

Опиши:

- какие domain tests есть;
- какие use case tests есть;
- какие repository tests есть;
- какие HTTP/controller tests есть;
- какие integration tests есть;
- какие важные сценарии не покрыты.

### 12. Known Gaps / Technical Debt

Добавь этот раздел, если есть нарушения:

- layer violations;
- Pydantic leak;
- raw dict DTO;
- repository stores tenant;
- controller business logic;
- missing tests;
- missing Protocol;
- missing DTO;
- no explicit row mapping;
- inconsistent naming;
- missing `__all__`;
- module structure differs from the current project module shape.

Важно: не исправляй код. Только документируй факт.

## Required Document Format

Файл `docs/modules/<module_name>.md` должен иметь такую структуру:

````markdown
# <Module Display Name> Module

## Purpose

Кратко опиши назначение модуля.

## Current Scope

Опиши текущие границы реализации.

Что модуль делает сейчас.
Что модуль явно не делает сейчас, если это важно.

## Public Functionality

- ...
- ...

## Main Flows / Use Cases

| Use Case | Input | Output | Description |
| -------- | ----- | ------ | ----------- |
| ...      | ...   | ...    | ...         |

## Domain Model

### <AggregateName>Entity

- ID:
- Tenant scope:
- Fields:
- Value Objects:
- Factory methods:
- Update methods:
- Domain errors:
- Invariants:

## Application Layer

### Commands

- ...

### Queries

- ...

### DTOs

- ...

### Use Cases

- ...

### Repository Protocols

- ...

## Infrastructure / Persistence

### <RepositoryName>

- File:
- Implements:
- Storage:
- Runtime object:
- Tenant handling:
- Mapping:
- Errors:

## Presentation / HTTP API

Base prefix:

```text
/api/<module>
```

| Method | Path | Controller | Use Case | Request | Response |
| ------ | ---- | ---------- | -------- | ------- | -------- |
| ...    | ...  | ...        | ...      | ...     | ...      |

## Dependency Injection

- Infrastructure dependencies:
- Application dependencies:
- Shared dependencies:

## Dependencies On Other Modules

| Module | Layer | Used For |
| ------ | ----- | -------- |
| ...    | ...   | ...      |

## Events / Background Processing

Опиши найденные события, jobs, commands.
Если нет — укажи, что не найдено.

## Tests Covering This Module

- Domain:
- Application:
- Infrastructure:
- Presentation:
- Integration:

## Known Gaps / Technical Debt

- ...

## Related Documentation

- [Develop Style](../develop-style.md)
- [CRM Module](./crm.md)

## Source Of Truth

- `src/modules/<module_name>/...`
- `tests/...`
````

## Writing Style

Пиши документацию:

- на русском языке;
- технически точно;
- без marketing-style;
- короткими абзацами;
- с таблицами там, где это упрощает чтение;
- с именами реальных классов и файлов;
- с конкретными путями к файлам;
- без предположений;
- без “в будущем будет”, если это не зафиксировано в коде/docs.

Хорошо:

```markdown
`CreateContactUseCase` создает контакт через `ContactService` и возвращает `ContactDTO`.
```

Плохо:

```markdown
Модуль предоставляет мощную и гибкую систему управления клиентами.
```

## Factuality Rules

Если информация не найдена, пиши:

```markdown
В текущей реализации не найдено.
```

Если реализация частичная, пиши:

```markdown
Реализация частичная: найден use case, но HTTP endpoint отсутствует.
```

Если код противоречит `develop-style`, пиши:

```markdown
Текущее отклонение от project style: repository возвращает dict вместо DTO.
```

Не скрывай проблемы.

## Quality Bar

Документ считается готовым, если по нему можно:

- понять назначение модуля;
- найти основные файлы;
- понять публичные endpoints;
- увидеть use cases;
- увидеть domain model;
- увидеть infrastructure adapters;
- понять зависимости на другие модули;
- понять тестовое покрытие;
- увидеть technical debt;
- использовать документ как context для следующего Codex refactoring prompt.

## Final Report Format

После обновления `docs/modules/<module_name>.md` дай отчет:

```markdown
## Documentation Summary

- Документ создан/обновлен:
- Какие слои прочитаны:
- Какие ключевые классы задокументированы:
- Какие HTTP routes задокументированы:
- Какие тесты найдены:
- Какие gaps зафиксированы:

## Files Read

- ...

## Files Changed

- ...

## Unclear / Missing Information

- ...
```

## Important

Не изменяй production code.
Не изменяй tests.
Не добавляй архитектуру, которой нет в коде.
Не описывай планы как факт.
Не скрывай грязный код.
Документация должна отражать реальное состояние модуля.
