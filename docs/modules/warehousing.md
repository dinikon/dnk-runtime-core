# Warehousing: первый срез Warehouse

Модуль владеет структурой хранения. Реализованы создание склада, карточка и список.
Warehouse — самостоятельный Aggregate Root; он не хранит зоны, адреса, количество
товара или коллекции остатков. Зоны, адреса, LocationPolicy, изменение настроек и
статусов, Inventory и Console относятся к следующим срезам
[общего плана](../plan/inventory.md).

## Модель и архитектура

Склад содержит ID, code, title, type, status, policy, revision и аудит
created_at/updated_at/created_by/updated_by. Новый склад имеет status=active и
revision=1. Domain также умеет восстанавливать inactive и archived, но API
изменения статуса пока отсутствует.

Code удаляет крайние пробелы и переводится в верхний регистр: `wh-01` и `WH-01`
обозначают один код внутри tenant. После нормализации длина — 1–64 символа.
Title — непустая строка до 255 символов, type — строковый код до 64 символов без
фиксированного справочника. У title/type также удаляются крайние пробелы;
регистр type сохраняется. Значения с NUL отклоняются.

Policy типизирована и содержит только обязательный `timezone` длиной до 128
символов. Создание проверяет активный IANA-код через публичный Application
сценарий Reference Data `CheckTimeZoneQuery → CheckTimeZoneResultDTO`. Адаптер
не импортирует чужие Domain/SQL-модели и использует тот же UoW. Неизвестный или
неактивный код отклоняется; запрос не загружает IANA из сети.

Все четыре слоя группируются под warehouse. Domain защищает инварианты
фабриками create/restore; persistence mapper только преобразует поля.
Application загружает факт активности timezone через порт, а решение о допустимости
создания принимает Domain. Restore не проверяет текущую активность справочника.
Write repository хранит агрегат, query repository читает отдельные DTO
карточки и списка без восстановления агрегата. Аудит использует aware UTC.

## HTTP-контракты

Общий префикс — `/api/console/warehousing/warehouses`.

| Метод | Вход | Успешный результат |
| --- | --- | --- |
| POST коллекции | code, title, type, policy.timezone | 201: id, нормализованный code, status, revision |
| GET /{warehouse_id} | UUID склада | 200: все поля склада, policy и аудит |
| GET коллекции | status, type, cursor, limit | 200: items и next_cursor |

Пример тела POST:

```json
{
  "code": "wh-01",
  "title": "Основной склад",
  "type": "storage",
  "policy": {"timezone": "Europe/Kyiv"}
}
```

POST отклоняет дополнительные поля, в том числе tenant_id, actor_id, status,
revision и произвольные настройки policy. Tenant и actor берутся из доверенного
Identity-контекста. Все методы требуют authentication и authorization:
resource_type=warehouse, actions=create/read/list; при read передаётся resource_id.
POST дополнительно использует существующую CSRF-зависимость Identity.
Политика авторизации предоставляется Identity; её текущий default остаётся allow-all.

Список имеет отдельные строки id/code/title/type/status/revision. Фильтры status
(active/inactive/archived) и type точные; крайние пробелы type удаляются.
По умолчанию limit=50, допустимы 1–100. Сортировка — code, затем UUID.
Непрозрачный URL-safe cursor содержит последнюю пару code/UUID; следующий запрос
передаёт те же фильтры. next_cursor=null означает конец страницы. Пагинация не
фиксирует отдельный снимок на время обхода нескольких HTTP-запросов.

Доменные ошибки имеют `detail={"code": "...", "message": "..."}`:

- 404: warehouse.not_found.
- 409: warehouse.code_already_exists.
- 422: warehouse.invalid_code/title/type/timezone или warehouse.invalid_list_parameters.
- 403: warehouse.tenant_required или warehouse.forbidden.

Ошибки транспортной валидации используют стандартный FastAPI detail с устойчивым
полем type, например extra_forbidden или uuid_parsing. Authentication/CSRF
сохраняют действующие контракты Identity. Неожиданные сбои не маскируются
бизнес-ошибками.

## Хранение и развёртывание

Tenant-миграция `0017_warehousing_warehouses` следует за `0016_remove_inventory`
и создаёт новую таблицу `warehousing_warehouses`. Исторические warehouses/skus
и их данные не восстанавливаются. Модель зарегистрирована в tenant metadata;
историческое имя новой таблицы сохраняется для migration ownership.

INSERT атомарно проверяет UNIQUE нормализованного code. Конкурентный дубликат
возвращает конфликт без предварительного SELECT. Внешний UoW завершает транзакцию
до HTTP-ответа; handlers/repositories не выполняют commit/rollback. Ошибка commit
не возвращает 201.

Перед запуском обновлённого API применить tenant-миграции:

```sh
dnk-manage tenant-migrations upgrade --all
```

Новые tenant автоматически создаются на новом head. Справочник timezone должен
быть первоначально загружен по правилам Reference Data:

```sh
dnk-manage reference-data sync --dataset time-zones
```

Downgrade до 0016 удаляет только новую таблицу Warehousing и её данные.

## Проверки

Unit/HTTP suites покрывают нормализацию, create/restore, инварианты и аудит,
публичную проверку timezone, DTO, пагинацию, authentication/authorization/CSRF,
ошибки и сбой commit. Отдельная архитектурная suite проверяет импорты, аннотации,
русские docstrings, обязательные файлы, пустые init, post_init только в VO,
разделение write/read side и внешние границы транзакции.

PostgreSQL suite проверяет fresh tenant, upgrade/downgrade, два tenant с
одинаковыми ID/code, отсутствие чужих чтений, реальные фильтры и keyset,
два конкурентных создания одного кода и rollback после INSERT.
Она требует TEST_POSTGRES_URL на одноразовую БД; пропуск не доказывает готовность.

Проверка среза 2026-10-09: все 30 новых проверок прошли, включая PostgreSQL 16
в одноразовом контейнере. Общий unittest discovery: 645 тестов, 612 успешных,
33 пропуска для ненастроенных Control Plane/Redis/Core и внешних sample-окружений.
Black check и проверка diff прошли. Остальные срезы этапа 1 не объявляются готовыми.
