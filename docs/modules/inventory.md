# Inventory: SKU

Дата: 2026-10-04. Реализован первый срез самостоятельного агрегата SKU.
Архитектура следует [правилам модуля](../architecture/AGENTS.md).

## Назначение и модель

SKU — идентичность учётной позиции Inventory. Будущий Catalog.Variant ссылается
на неё по sku_id. Название SKU относится к учётному справочнику; локализованный
контент карточки будет принадлежать Catalog.

| Поле | Поведение |
| --- | --- |
| id | Стабильный UUID, создаётся сервером |
| code | 1–128 символов после удаления пробельных символов по краям; регистр и внутренние пробелы сохраняются; управляющие символы в итоговом коде запрещены |
| title | Учётное название, 1–255 символов после удаления пробельных символов по краям |
| created_at / updated_at | Время из общего Clock; одинаково при создании |
| created_by / updated_by | ID доверенного пользователя; одинаково при создании |

Code уникален внутри tenant. `OMEGA-100` и `omega-100` — разные коды.
Одинаковые коды у разных tenant допустимы. Уникальность обеспечивается ограничением
PostgreSQL, включая одновременные запросы. Таблица skus находится в tenant-схеме;
отдельного столбца tenant_id у неё нет.

Движения, единицы измерения, складские остатки, резервы и расчёт доступности требуют
следующих срезов Inventory. API не возвращает вымышленное количество;
создание SKU не является поступлением на склад.

## HTTP API

| Метод | Путь | Результат |
| --- | --- | --- |
| POST | `/api/console/inventory/skus` | Создание, 201 |
| GET | `/api/console/inventory/skus/{sku_id}` | Карточка, 200; отсутствующая SKU — 404 |
| GET | `/api/console/inventory/skus?limit=50&offset=0` | Массив карточек, 200; сортировка code, id |

Параметры списка: limit от 1 до 200, по умолчанию 50; offset ≥ 0, по умолчанию 0.
Создание принимает только code и title:

```json
{"code": "VITAMIN-C-1000", "title": "Vitamin C 1000"}
```

Ответ создания и карточки содержит id, code, title и четыре поля аудита.
Невалидные значения, параметры страницы и неизвестные поля дают 422.
Занятый code или ID — 409. Неожиданные ошибки хранения не маскируются под конфликт.

Все методы требуют authentication и tenant-контекста; POST — также существующие
CSRF token и проверку Origin. Tenant и аудит нельзя подменить через body.
AuthorizationService проверяет resource_type `inventory.sku` и action `create`,
`read` или `list`; для read передаётся resource_id. Отказ даёт 403.
Используется настройка AuthorizationService проекта; его существующий default
AllowAll требует замены или настройки для продуктовой политики прав.

## Архитектура и публичный контракт

- domain/sku: агрегат, ID/code/title value objects, ошибки, write repository port.
- application/sku: CreateSku, GetSku, ListSkus, read repository port и публичный lookup.
- infrastructure/sku/persistence: mapper записи, repository и отдельные query repository/mapper.
- infrastructure/persistence/models/sku.py: статическая tenant SQL-модель.
- presentation/sku: composition root, router, отдельные HTTP controller/request/response.

Репозитории используют сессию общего внешнего UoW и не выполняют commit/rollback.
Queries читают проекции без восстановления агрегата. Именованные unique constraints
переводятся в доменные ошибки адаптером хранения и затем в HTTP 409.

```text
SkuLookupProtocol.get_sku(sku_id: UUID) → SkuReferenceDTO | None
SkuReferenceDTO: id, code, title
```

SkuLookupService использует query repository текущего tenant.
В composition root get_sku_lookup / SkuLookupDep связывают его с тем же UoW.
Другие модули используют application contract и DTO без импорта domain entity
или ORM-модели Inventory. Чужой/отсутствующий ID возвращает None.
Количество по SKU этим портом не предоставляется.

## Миграция и проверки

Ревизия `0011_inventory_skus` следует за `0010_crm_company_legal_name`.
Модель зарегистрирована в tenant metadata и в наборе управляемых таблиц.
Существующие tenant нужно обновить до запуска API с новой моделью:

```sh
dnk-manage tenant-migrations upgrade --all
```

Новые tenant получают таблицу при обычном bootstrap. Migration не выбирает
фиксированного tenant и не коммитит транзакцию самостоятельно.

Проверки: test/test_inventory_sku.py, test/test_inventory_sku_http.py,
test/test_inventory_sku_postgres.py и архитектурные тесты. PostgreSQL-набор использует
только явно заданный TEST_POSTGRES_URL одноразовой базы. Проверены конкурентные
дубли, изоляция двух tenant, пагинация, публичный lookup, rollback после вставки,
downgrade/upgrade с сохранением Warehouse и отсутствие drift Alembic metadata.
