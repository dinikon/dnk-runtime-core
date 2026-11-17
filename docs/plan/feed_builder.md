# **FeedBuilder — полный технический план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript, TanStack Vue Query\
**Хранение схем и политик:** версионируемые JSONB-документы\
**MVP-экспорт:** Generic CSV и Generic XML

Документ объединяет базовый план FeedBuilder и уточнения по мультиязычности,
мультивалютности и наценкам. Это самостоятельное описание целевой реализации:
все обязательные контракты, границы MVP, этапы и критерии собраны здесь.
Примеры описывают целевое поведение, а не наличие реализованного API.

## **1. Цель и границы модуля**

`FeedBuilder` — самостоятельный bounded context, создающий пользовательские
прайс-листы на основании Catalog и рассчитанных Pricing цен.

Пользователь должен иметь возможность:

1. Создать Feed с названием, кодом и настройками экспорта.
2. Визуально собрать схему публикации drag-and-drop конструктором.
3. Задать каждому полю тип, источник, ограничения, transforms и экспортное имя.
4. Выбрать язык каждого текстового поля и валюту каждого денежного поля.
5. Назначить Feed ценовую политику: источник базовой цены и процентную наценку.
6. Привязать товары Catalog, наследовать значения или переопределять отдельные поля.
7. Проверять готовность публикаций, ошибки и результат расчёта цены.
8. Просматривать публикации и будущий экспорт до запуска генерации.
9. Асинхронно получать CSV и XML по постоянным ссылкам.

### **1.1. Функциональные границы MVP**

| Тип поля | Доменное значение | Применение |
| --- | --- | --- |
| `STRING` | `str` | Название и другие короткие строки |
| `TEXT` | `str` | Описание |
| `MONEY` | `MoneyVO` с `Decimal` | Цена в валюте конкретного поля |

Схема динамическая: можно добавлять поля этих типов, менять порядок, названия,
источники, constraints и transforms. Список колонок не зашит в сериализаторы.
Один Feed может содержать, например, `title_uk`, `title_ru`, `description_uk`,
`description_ru`, `price_uah`, `price_usd`, `price_eur`.

В MVP входят:

- Независимые языки и валюты полей, несколько текстовых и денежных полей в одном Feed.
- Явная политика отсутствующих переводов; автоматическая подмена языка запрещена.
- Отдельная версионируемая PricePolicy для прайс-листа и возможность явно
  использовать одну политику в нескольких Feed.
- Выбор базовой цены Catalog, режимы `NONE` и `PERCENT` для основной наценки.
- Конвертация через Currency Provider и один snapshot курсов на выполнение генерации.
- Округление на уровне денежного поля, независимые overrides каждой языковой
  версии и каждой валютной цены.
- Черновик и неизменяемые опубликованные версии схемы, проекции, валидация,
  история генераций, постоянные ссылки, ротация ключей и tenant isolation.
- Фиксация версии схемы, настроек Feed, ценовой политики и использованных курсов.

Варианты товаров, категории, изображения, характеристики, AI-генерация,
динамический подбор ассортимента, расписания и специализированные контракты
Prom/Rozetka не входят в MVP. Фиксированные надбавки, целевая маржа, правила
категорий/SKU/поставщиков, дополнительные валютные наценки, налоги, комиссии
и сложные комбинации правил описаны как расширение Pricing, а не обязательство
первого релиза. Контракты должны позволять добавить их без изменения основы.

### **1.2. Стартовая схема и обязательные поля**

При создании Feed пользователь выбирает начальный язык и валюту для шаблона.
Backend создаёт три поля с ключами `title`, `description`, `price`, типами
`STRING`, `TEXT`, `MONEY` и `constraints.required=true`. Язык записывается
непосредственно в определения `title` и `description`, валюта — в `price`.
Эти параметры создания не становятся общими настройками разрешения значений Feed.

Чтобы совместить обязательные поля с независимыми языковыми и валютными версиями,
вводится стабильная семантическая роль `system_role`: `TITLE`, `DESCRIPTION`,
`PRICE` либо `null`. Это уточнение контракта объединённого плана.

- Ровно одно поле каждой системной роли обязательно присутствует в схеме,
  имеет совместимый тип, `required=true` и `export.enabled=true`.
- Системное поле нельзя удалить, лишить роли или изменить на несовместимый тип.
- Его ключ можно переименовать, например `title` → `title_uk`, сохранив
  `field_id` и `system_role`. Экспортное имя настраивается независимо.
- Дополнительные поля, например `title_ru` и `price_usd`, имеют `system_role=null`;
  их обязательность задаётся индивидуально. Их можно добавлять и удалять.
- После первой публикации изменение языка или валюты поля с сохранением `field_id`
  запрещено: это меняет смысл сохранённых overrides. Нужно создать новое поле
  либо выполнить отдельную явную миграцию. В MVP перенос системной роли на
  другое поле не реализуется; для другого основного языка/валюты создаётся Feed.
  До первой публикации, пока overrides отсутствуют, язык и валюту стартовых
  полей можно настраивать в draft.

Таким образом, обязательность определяется ролью, а не буквальными ключами
`title`, `description`, `price`. Стабильный `field_id` остаётся идентичностью поля.

### **1.3. Границы контекстов**

```text
Catalog → локализованный контент и базовые цены
    │
    ├──→ Pricing ← Currency / FX Provider
    │       │
    │       ├──→ FeedBuilder → Resolved Publication → CSV / XML
    │       └──→ Channels → API площадок
    └──→ FeedBuilder: текстовые источники
```

| Контекст | Ответственность |
| --- | --- |
| Catalog | Товары, локализованный контент, базовые цены, ревизии источников |
| Pricing | PricePolicy, выбор исходной цены, наценки, получение PriceQuote |
| Currency / FX Provider | Курсы, их источники, snapshot и правила конвертации |
| FeedBuilder | Схемы, языки и валюты полей, публикации, overrides, проекции, генерации |
| Channels | API-синхронизация с площадками с использованием согласованной PricePolicy |
| reference_data | Глобальные read-only справочники валют и BCP 47 локалей |

Pricing — самостоятельный bounded context. В MVP достаточно PricePolicy,
чистого PriceCalculator и адаптеров чтения базовых цен и курсов. Если выделение
Pricing временно невозможно, допустима реализация FeedPricePolicy за тем же
`PriceCalculationPort` внутри FeedBuilder; это временный адаптер, который нужно
вынести до подключения нескольких независимых способов синхронизации цен.
Целевой вариант этого плана — отдельный Pricing.

FeedBuilder не изменяет Catalog и не реализует API-синхронизацию товаров или
получение заказов. Он не импортирует ORM-модели и внутренние агрегаты других
контекстов. Внешние данные поступают через Application Ports и immutable snapshots.
Настройки PricePolicy можно показывать внутри Feed UI, но её изменение выполняют
сценарии Pricing. Справочник кодов валют не смешивается с tenant-данными FX-курсов.

## **2. Основные архитектурные решения**

| Вопрос | Решение |
| --- | --- |
| Кому принадлежит публикация? | Конкретному Feed |
| Как хранится схема? | Типизированный JSONB, отдельный draft и неизменяемые версии |
| Где хранятся исходные значения? | В Catalog; коммерческие правила — в Pricing |
| Где хранится ручное значение? | В overrides конкретной FeedPublication по field_id |
| Как идентифицируется поле? | Стабильный UUID field_id; key и export.name — отдельные свойства |
| Где задаются язык и валюта? | В FieldDefinition; у Feed нет общей валюты/языка вычислений |
| Что определяет цену? | PricePolicy → PriceQuote → override → transforms → constraints |
| Где хранятся вычисленные значения? | В materialized read model; это кеш, не источник истины |
| Как меняется схема? | Draft → Validate → Publish |
| CSV/XML имеют разные схемы? | Одна FeedSchema, один набор ExportRecord, разные сериализаторы |
| Как учитываются площадки? | Через отдельный FormatProfile, не смешанный с FeedSchema |
| Как создаются файлы? | Асинхронный worker, staging, неизменяемые артефакты |
| Что происходит при ошибке? | Предыдущая успешная генерация остаётся активной |
| Где хранятся файлы? | ArtifactStorage; в SQL — метаданные и указатели |

### **2.1. Definition, Override и Resolved Value**

**Definition** — определение поля, одинаковое для всех публикаций версии схемы:
тип, системная роль, язык/валюта, источник, fallback, constraints, transforms, экспорт.

**Override** — индивидуальное ручное значение поля публикации. Остальные данные
Catalog не копируются. Отсутствие override означает применение default_mode поля.

**Resolved Value** — значение после выбора источника/override, приведения типа,
transforms и validation. Используется для предпросмотра и экспорта.

Это разделение сохраняется в Domain, Application, Infrastructure и Presentation.

### **2.2. Применимые архитектурные требования**

Нормативные документы: [backend](../architecture/backend.md) и
[frontend](../architecture/frontend.md). При реализации и проверке всего diff
использовать следующий перечень:

1. Модуль → слой → Aggregate Root → ответственность. FeedBuilder содержит
   `feed`, `publication`, `generation`; Pricing с одним корнем PricePolicy
   может не иметь дополнительного каталога корня в каждом слое.
2. Domain не зависит от FastAPI, Pydantic, SQLAlchemy, I/O и логирования.
   Чистые бизнес-правила находятся в агрегатах, VO и Domain Services/Policies;
   Application координирует внешние порты и вызывает Domain.
3. Агрегаты/Entity имеют явные фабрики create/restore; состояние меняют только
   domain-методы. `__post_init__` разрешён только VO. Mapper не переносит на себя
   инварианты и не создаёт события повторного создания при restore.
4. Write Repository contracts находятся в Domain и работают с агрегатами.
   Query/projection/external ports находятся в Application; Query не восстанавливает
   агрегаты только ради списка. Репозиторий не создаётся автоматически для таблицы.
5. Каждый сценарий имеет Command или Query, Handler с типизированным execute,
   собственный DTO результата либо None. Все методы аннотированы, включая
   __init__; публичные классы/методы документируются по-русски.
6. Обычный UoW открывается внешней сборкой Depends/worker, репозитории используют
   одну сессию. Application не открывает uow_factory и не получает AsyncSession.
   Управление commit/rollback через абстрактный UoW port передаётся только при
   реальной необходимости. Outbox записывается до commit в той же транзакции.
7. HTTP controller, request и response каждого метода находятся в отдельных
   файлах; router регистрирует маршруты, Depends собирает зависимости.
   Импорты прямые, __init__.py пустые. Identity и Tenancy используются через
   установленные публичные границы; tenant нельзя выбирать из пользовательского SQL.
8. Frontend разделяет api/DTO/mapper, чистые модели, queries, mutations, page state,
   Page и UI. Page оркестрирует; обычный UI работает через props/emits.
9. Серверный кеш принадлежит TanStack Vue Query. Query keys учитывают tenant и
   все параметры; черновик отделён от кеша, refetch не стирает ввод.
   API использует общий HTTP client, передаёт AbortSignal и сохраняет Decimal строками.
10. Права и бизнес-инварианты проверяет backend. Frontend не дублирует Pricing
    и FieldValueResolver; общие semantic tokens и UI-компоненты переиспользуются.
11. Логи содержат безопасные ID/коды и корреляцию; committed фиксируется только
    после commit. Секреты и содержимое публикаций целиком не логируются.
12. Проверяются согласованность контрактов, tenant isolation, конкуренция,
    ссылки документации и весь diff. Для изменения только этого плана сборка
    приложений не требуется; проверки реализации перечислены в разделе тестирования.

### **2.3. Организация файлов**

```text
src/modules/feed_builder/
  domain/{feed,publication,generation}/
    aggregate.py, repository.py, error.py, value_object/, event/
  application/{feed,publication,generation}/
    command/<scenario>/{command.py,handler.py,dto.py}
    query/<scenario>/{query.py,handler.py,dto.py}
    port/
  application/service/
  infrastructure/{feed,publication,generation}/persistence/
    mapper.py, repository.py, query_mapper.py, query_repository.py
  infrastructure/persistence/models/<table>.py
  infrastructure/{catalog,pricing,currency,storage,serialization}/
  presentation/{feed,publication,generation}/
    router.py, depends.py
    http/{controller,request,response}/<scenario>.py
  presentation/depends/
```

`dto.py` создаётся только при наличии результата. Отдельные опубликованные схемы
и draft — объекты хранения агрегата Feed, не новые Aggregate Roots. Результаты
генерации принадлежат FeedGeneration; проекции обслуживают read-side. Внешний
worker bootstrap использует общие jobs/UoW механизмы shared, не копирует их в модуль.

## **3. Domain Layer**

### **3.1. Агрегаты и границы**

| Aggregate Root | Управляет | Инварианты |
| --- | --- | --- |
| Feed | Настройки, draft и версии схемы, назначение политики, активная генерация | Структура схемы, конфигурация, допустимая активация |
| FeedPublication | Связь товара с Feed, участие, overrides | Одна публикация товара на Feed, допустимые изменения |
| FeedGeneration | Состояние задания, зафиксированный контекст, результаты | Переходы, счётчики, неизменяемость завершённого результата |
| PricePolicy в Pricing | Источник цены, правила и версии политики | Допустимая арифметика, совместимость источника и правил |

FeedSchema, FieldDefinition, FieldConstraints, TransformDefinition и
FieldOverride — VO либо дочерние объекты соответствующего агрегата.
FeedPublicationProjection — read model, не Aggregate Root. FeedArtifact и
GenerationIssue — результаты FeedGeneration. Между агрегатами хранятся ID,
а не ссылки на чужие Python-объекты.

### **3.2. Aggregate Feed**

| Свойство | Тип / смысл |
| --- | --- |
| id, name, code | FeedIdVO, название, уникальный FeedCodeVO |
| status | DRAFT / ACTIVE / PAUSED / ARCHIVED |
| pricing_policy_id | PricePolicyIdVO или None: явный NO_ADJUSTMENT |
| active_schema_version, draft_schema | Опубликованная версия и отдельный рабочий draft |
| active_generation_id, latest_generation_sequence | Текущая выдача и порядок запросов |
| configuration_version | Ревизия влияющих на экспорт настроек Feed |
| version | Версия агрегата для optimistic locking |
| default_locale, default_currency | Необязательные UI-подсказки для новых полей |

Методы: create/restore, rename, replace_draft_schema, publish_schema,
assign_pricing_policy, update_export_settings, request_generation,
activate_generation_if_current, pause/archive. Параметры и результаты методов
типизированы отдельными VO/контрактами; изменения полей из Application запрещены.

Инварианты:

- Одна активная версия схемы; опубликованная версия неизменяема.
- Схема содержит обязательные системные роли, уникальные field_id/key/export.name.
- Генерация возможна только с опубликованной схемой.
- Более старая генерация не заменяет более новую; успешно завершиться и стать
  активной — разные операции.
- Смена политики или настроек экспорта увеличивает configuration_version.
  Переименование Feed и правка UI-подсказок не меняют результат вычислений.
- У Feed нет общей валюты или языка вычисления; defaults не подменяют настройки поля.

### **3.3. FeedSchema и FieldDefinition**

```python
@dataclass(frozen=True)
class FieldDefinition:
    """Определяет независимое типизированное поле версии схемы Feed."""

    id: UUID
    key: str
    label: str
    system_role: SystemFieldRole | None
    value_type: FieldValueType
    locale: LocaleCodeVO | None
    currency: CurrencyCodeVO | None
    source: SourceReference | None
    default_mode: ValueMode
    fallback_policy: LocaleFallbackPolicy | None
    constraints: FieldConstraints
    transforms: tuple[TransformDefinition, ...]
    export: FieldExportSettings
    ai_instruction: str | None


@dataclass(frozen=True)
class FeedSchema:
    """Хранит неизменяемый упорядоченный набор определений полей."""

    fields: tuple[FieldDefinition, ...]
    schema_format_version: int = 1
```

Для локализованных текстовых источников locale обязателен, для языконезависимого
текста допустим null. Для MONEY currency обязателен, locale и fallback отсутствуют.
Текстовое поле не имеет currency. Поддерживаемые коды проверяются через
Application-контракты reference_data; VO проверяет собственный формат значения.

Методы схемы: get_field, validate_structure, reorder_fields, used_locales,
used_currencies. Языки fallback-chain также включаются в потребности чтения Catalog.
В MVP поля scalar внутри корня publication. Будущие kind/children/item_schema
позволят добавить объекты и массивы без универсальных классов под каждый объект.

### **3.4. Constraints**

```python
@dataclass(frozen=True)
class FieldConstraints:
    """Задаёт проверки итогового значения, не преобразуя его."""

    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
```

| Constraint | STRING | TEXT | MONEY |
| --- | --- | --- | --- |
| required | Да | Да | Да |
| min_length / max_length | Да | Да | Нет |
| min_amount / max_amount | Нет | Нет | Да |

Ограничения индивидуальны для каждого поля, языка и валюты. Они проверяют
результат после transforms; не обрезают строку и не исправляют сумму автоматически.

### **3.5. Transforms и Money**

TransformDefinition содержит operation и типизированные JSON parameters.
Операции выполняются в порядке массива transforms зарегистрированными handlers.

| Операция MVP | Назначение |
| --- | --- |
| string.trim | Удаление крайних пробелов |
| string.truncate | Явное ограничение длины |
| money.ceil_step | Округление суммы вверх с положительным шагом |

MONEY использует существующий MoneyVO и Decimal, никогда float. В JSON amount —
десятичная строка. Валюта полученной или ручной цены должна совпадать с
FieldDefinition.currency; иначе CURRENCY_MISMATCH. Конвертация выполняется Pricing
до получения значения поля, а не transform внутри FeedBuilder. Наценка — правило
Pricing, округление — transform, форматирование числа — ответственность Serializer.

### **3.6. Aggregate FeedPublication**

Поля: id, feed_id, catalog_item_id, catalog_variant_id, status,
`overrides: dict[UUID, FieldOverride]`, version, created_at, updated_at.
Методы: create/restore, set_override, reset_override, enable, pause, archive.

Для простого товара catalog_variant_id=None. Один товар/вариант имеет одну
публикацию на Feed. В MVP варианты не добавляются, но поле сохраняет расширяемость.

Если source задан, default_mode=INHERIT; без source — MANUAL. Для отсутствующего
ручного значения required-поле требует ввода. Запись override создаётся только
при явном сохранении ручного значения. Пустое значение в override не означает
reset: reset — отдельная операция удаления записи.

Override независим для каждого field_id. Изменение title_ru не влияет на title_uk;
ручная цена price_usd не отключает расчёт price_uah. Наценка и конвертация не
применяются к ручной окончательной цене; допустимые transforms и constraints применяются.

### **3.7. Состояния и готовность публикации**

PublicationStatus: DRAFT, ENABLED, PAUSED, ARCHIVED — пользовательское участие.
PublicationReadiness: READY, NEEDS_INPUT, INVALID, STALE — вычисленная готовность.
ENABLED + INVALID допустимо: товар включён, но имеет ошибки.

- INVALID: ошибка типа, валюты, transform, constraints, отсутствующая базовая
  цена или обязательный FX-курс для наследуемого денежного поля.
- NEEDS_INPUT: отсутствует обязательный текст/перевод или ручное значение без
  других ошибок. MANUAL_REQUIRED требует ручного ввода даже у необязательного
  текстового поля, если перевод отсутствует.
- READY: все обязательные значения корректны, блокирующих ошибок нет.
- STALE: сохранённая проекция устарела; это не результат текущего resolve.

Отсутствующий необязательный перевод при fallback NONE допустим. Техническая
недоступность Catalog/Pricing/Currency — отдельная ошибка зависимости, не обычное
пустое поле. При валидном ручном override отсутствие исходной цены, перевода или
курса не блокирует это поле: для конечного значения источник не требуется.

В MVP действует только STRICT: ошибка или незаполненное обязательное поле у
ENABLED-публикации блокирует новую генерацию всего файла. Молча исключать товары
нельзя. Предыдущая успешная выдача при этом сохраняется.

### **3.8. Aggregate FeedGeneration**

Поля: id, feed_id, schema_version, configuration_version, request_sequence,
pricing_policy_id, pricing_policy_version, fx_rate_snapshot_id,
export_settings_snapshot, status, attempt_count, attempt_token, lease_until,
total_items, exported_items, rejected_items, artifacts и timestamps.

Жизненный цикл: PENDING → RUNNING → SUCCEEDED / FAILED. Повторная попытка
RUNNING после истечения lease выполняется только по протоколу claim; истёкшая
попытка не имеет права завершать или активировать результат.

Методы: create/restore, start, renew_lease, capture_rate_snapshot, complete, fail.
После завершения данные результата и контекст расчёта неизменяемы. Контекст курса
фиксируется до первого расчёта; повтор того же задания использует тот же snapshot.
Для обновлённых входных параметров создаётся новая генерация.

Успешная генерация может не стать активной, если схема, конфигурация, назначение
или активная версия политики уже изменились. Проверки активации описаны отдельно.

## **4. Формат типизированной схемы**

Схема декларативна: JSON хранит определения и параметры, а не исполняемый код.
Все source paths и операции разрешены только через зарегистрированные handlers.

### **4.1. Пример JSON-документа**

```json
{
  "schema_format_version": 1,
  "root": {
    "key": "publication",
    "kind": "object",
    "fields": [
      {
        "id": "11111111-1111-4111-8111-111111111111",
        "key": "title_uk",
        "label": "Назва українською",
        "system_role": "TITLE",
        "value_type": "string",
        "locale": "uk",
        "currency": null,
        "source": {"provider": "catalog", "path": "item.title"},
        "default_mode": "INHERIT",
        "fallback_policy": {"mode": "NONE"},
        "constraints": {"required": true, "max_length": 160},
        "transforms": [{"op": "string.trim", "params": {}}],
        "export": {"enabled": true, "name": "title_uk"},
        "ai": {"instruction": null}
      },
      {
        "id": "22222222-2222-4222-8222-222222222222",
        "key": "description_uk",
        "label": "Опис українською",
        "system_role": "DESCRIPTION",
        "value_type": "text",
        "locale": "uk",
        "currency": null,
        "source": {"provider": "catalog", "path": "item.description"},
        "default_mode": "INHERIT",
        "fallback_policy": {"mode": "NONE"},
        "constraints": {"required": true, "max_length": 5000},
        "transforms": [],
        "export": {"enabled": true, "name": "description_uk"},
        "ai": {"instruction": null}
      },
      {
        "id": "33333333-3333-4333-8333-333333333333",
        "key": "price_uah",
        "label": "Цена в гривне",
        "system_role": "PRICE",
        "value_type": "money",
        "locale": null,
        "currency": "UAH",
        "source": {"provider": "pricing", "path": "final_price"},
        "default_mode": "INHERIT",
        "fallback_policy": null,
        "constraints": {"required": true, "min_amount": "0.01"},
        "transforms": [{"op": "money.ceil_step", "params": {"step": "1"}}],
        "export": {"enabled": true, "name": "price_uah"},
        "ai": {"instruction": null}
      },
      {
        "id": "44444444-4444-4444-8444-444444444444",
        "key": "title_ru",
        "label": "Название на русском",
        "system_role": null,
        "value_type": "string",
        "locale": "ru",
        "currency": null,
        "source": {"provider": "catalog", "path": "item.title"},
        "default_mode": "INHERIT",
        "fallback_policy": {"mode": "NONE"},
        "constraints": {"required": false, "max_length": 160},
        "transforms": [],
        "export": {"enabled": true, "name": "title_ru"},
        "ai": {"instruction": null}
      },
      {
        "id": "55555555-5555-4555-8555-555555555555",
        "key": "price_usd",
        "label": "Цена в долларах",
        "system_role": null,
        "value_type": "money",
        "locale": null,
        "currency": "USD",
        "source": {"provider": "pricing", "path": "final_price"},
        "default_mode": "INHERIT",
        "fallback_policy": null,
        "constraints": {"required": true, "min_amount": "0.01"},
        "transforms": [{"op": "money.ceil_step", "params": {"step": "0.1"}}],
        "export": {"enabled": true, "name": "price_usd"},
        "ai": {"instruction": null}
      }
    ]
  }
}
```

### **4.2. Семантика свойств и локализация**

| Свойство | Назначение |
| --- | --- |
| id | Стабильный UUID, сохраняется при переименовании и перестановке |
| key | Уникальный внутренний ключ, не идентичность override |
| label | Отображаемое название |
| system_role | Защищённая роль TITLE / DESCRIPTION / PRICE либо null |
| value_type | Зарегистрированный тип string / text / money |
| locale | BCP 47 локаль текстового поля либо null для языконезависимого текста |
| currency | Код валюты MONEY-поля |
| source | Пара provider + зарегистрированный логический path |
| default_mode | INHERIT при наличии source, иначе MANUAL |
| fallback_policy | Явное поведение при отсутствии перевода |
| constraints | Проверки результата |
| transforms | Упорядоченные преобразования |
| export.enabled / name | Участие в экспорте и имя колонки CSV / тега XML |
| ai.instruction | Метаданные будущего AI-сценария; в MVP не исполняются |

`item.title` и `item.description` не содержат язык в строке пути. Локаль передаётся
отдельно, поэтому реестр источников не размножается на uk/ru/en. Экспортное имя
может отличаться от key: например title_uk → name_ua для будущего FormatProfile.

| fallback.mode | Поведение |
| --- | --- |
| NONE | Перевод отсутствует → значение отсутствует; это режим по умолчанию |
| LOCALE_CHAIN | После целевой локали последовательно проверить locales |
| MANUAL_REQUIRED | При отсутствии целевого перевода требуется ручной ввод |

Пример явного fallback: `{"mode": "LOCALE_CHAIN", "locales": ["uk"]}` для поля
с locale=ru. Исходная фактически использованная локаль возвращается в preview;
подмена не скрывается от пользователя. Цепочка конечна, содержит поддерживаемые
локали без повторов; рекурсивное применение fallback другого поля запрещено.

### **4.3. Валидация схемы**

Draft проверяется синтаксически при сохранении; publish выполняет полную
семантическую проверку:

- Уникальность field_id, key, экспортных имён и наличие трёх системных ролей.
- Типы/required/export.enabled системных полей и совместимость старых overrides.
- Корректность locale/currency/fallback для типа и зарегистрированного источника.
- Поддержка кода локали/валюты через reference_data, а не ограничения Tenancy.
- Совместимость source, constraints и transforms с типом; min ≤ max.
- Поддержка операций и допустимость их параметров; шаг округления положителен.
- Соответствие default_mode наличию source, корректность export settings.
- Безопасные имена XML: например title, price_uah, description_uk; без namespace,
  произвольного XPath, исполняемых выражений и URL пользовательских источников.
- Лимиты числа полей, длины ключей/текста и общего размера JSON-документа.

Чистая FeedSchemaPolicy проверяет структуру и инварианты в Domain. Application
получает метаданные реестров и справочников через порты и передаёт необходимые
immutable snapshots политике; Domain не выполняет I/O.

Изменение типа, языка или валюты уже опубликованного field_id, несовместимое с его
смыслом или overrides, запрещается. Для такого изменения создаётся другое поле
либо вводится отдельный механизм миграции, не входящий в MVP.

## **5. Infrastructure Layer — PostgreSQL**

### **5.1. Состав SQL-моделей**

Состав таблиц FeedBuilder для MVP:

| Таблица                      | Ответственность                    |
| ---------------------------- | ---------------------------------- |
| `fb_feeds`                   | Основные настройки Feed            |
| `fb_schema_drafts`           | Редактируемая схема                |
| `fb_schema_versions`         | Неизменяемые опубликованные версии |
| `fb_publications`            | Привязки товаров и overrides       |
| `fb_publication_projections` | Вычисленные значения и готовность  |
| `fb_generations`             | Запуски генераций                  |
| `fb_generation_issues`       | Ошибки и предупреждения            |
| `fb_artifacts`               | Метаданные CSV/XML                 |
| `fb_access_keys`             | Ключи доступа по URL               |

Дополнительно в `public` schema нужен реестр публичных идентификаторов Feed для маршрутизации в tenant.

**Draft хранится отдельно от опубликованных версий.** Это упрощает редактирование, блокировки и обеспечение неизменяемости опубликованной конфигурации. Все SQL-фрагменты ниже задают целевую структуру и реализуются tenant-миграциями Alembic с SQLAlchemy-моделями, mapper и репозиториями.

### **5.2. Таблица Feed**

```
CREATE TABLE fb_feeds (
    id UUID PRIMARY KEY,

    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,

    pricing_policy_id UUID NULL,
    configuration_version BIGINT NOT NULL DEFAULT 1,
    default_locale TEXT NULL,
    default_currency CHAR(3) NULL,

    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN (
            'DRAFT', 'ACTIVE', 'PAUSED', 'ARCHIVED'
        )),

    active_schema_version INTEGER NULL,
    active_generation_id UUID NULL,

    generation_sequence BIGINT NOT NULL DEFAULT 0,
    row_version BIGINT NOT NULL DEFAULT 1,

    export_settings JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

```

`export_settings` в MVP хранит параметры:

```
{
  "formats": ["csv", "xml"],
  "csv": {
    "delimiter": ",",
    "encoding": "utf-8",
    "include_header": true
  },
  "xml": {
    "root_name": "catalog",
    "item_name": "product",
    "encoding": "utf-8"
  },
  "validation_policy": "STRICT"
}
```

Для первого релиза `STRICT` — единственная политика: нельзя опубликовать новый файл с ошибочными товарами.

### **5.3. Таблицы Schema**

```
CREATE TABLE fb_schema_drafts (
    feed_id UUID PRIMARY KEY
        REFERENCES fb_feeds(id),

    definition JSONB NOT NULL
        CHECK (jsonb_typeof(definition) = 'object'),

    row_version BIGINT NOT NULL DEFAULT 1,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fb_schema_versions (
    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    version INTEGER NOT NULL CHECK (version > 0),

    definition JSONB NOT NULL
        CHECK (jsonb_typeof(definition) = 'object'),

    content_hash CHAR(64) NOT NULL,

    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (feed_id, version)
);

ALTER TABLE fb_feeds
ADD CONSTRAINT fk_fb_active_schema
FOREIGN KEY (id, active_schema_version)
REFERENCES fb_schema_versions(feed_id, version);

```

`fb_schema_drafts` содержит единственную рабочую версию для каждого Feed.

При публикации в одной транзакции:

1. Валидируем текущий draft.
2. Создаём новую строку `fb_schema_versions`.
3. Обновляем `active_schema_version`.
4. Удаляем draft.
5. Через domain-метод фиксируем FeedSchemaPublished; интеграционное сообщение записываем в Outbox той же транзакции до commit.

При повторном открытии редактора без сохранённого draft UI получает активную
схему и создаёт её локальную редактируемую копию. Query не изменяет БД.
SaveFeedSchemaDraft создаёт строку при первом сохранении с expected_version=null
и expected_schema_version; конкурентно созданный draft или смена активной схемы
возвращают 409. Следующие сохранения проверяют row_version существующего draft.

В дальнейшем можно реализовать несколько параллельных веток схем, но для MVP это не требуется.

### **5.4. FeedPublication**

```
CREATE TABLE fb_publications (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    catalog_item_id UUID NOT NULL,
    catalog_variant_id UUID NULL,

    status TEXT NOT NULL DEFAULT 'ENABLED'
        CHECK (status IN (
            'DRAFT', 'ENABLED',
            'PAUSED', 'ARCHIVED'
        )),

    overrides JSONB NOT NULL DEFAULT '{}'
        CHECK (jsonb_typeof(overrides) = 'object'),

    row_version BIGINT NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE NULLS NOT DISTINCT (
        feed_id,
        catalog_item_id,
        catalog_variant_id
    )
);

CREATE INDEX ix_fb_publications_feed_status
ON fb_publications(feed_id, status);

```

Это определение рассчитано на PostgreSQL 15+. `NULLS NOT DISTINCT` предотвращает создание нескольких публикаций одного простого товара, для которого `catalog_variant_id IS NULL`.

В MVP при добавлении проверяем, что Catalog Item является поддерживаемой простой товарной позицией. Поле `catalog_variant_id` не используется функционально, но сохраняет возможность расширения идентичности.

**Формат overrides:**

```
{
  "11111111-1111-4111-8111-111111111111": {
    "mode": "MANUAL",
    "value": "Хлорофіл NOW Foods, 473 мл"
  },
  "33333333-3333-4333-8333-333333333333": {
    "mode": "MANUAL",
    "value": {
      "amount": "650.00",
      "currency": "UAH"
    }
  }
}

```

Если поле наследуется, запись в `overrides` не требуется.

В будущем `FieldOverride` может поддерживать дополнительные режимы: `CLEAR`, `EXPRESSION`, `GENERATED`, не меняя физическую модель.

### **5.5. Материализованная проекция**

```
CREATE TABLE fb_publication_projections (
    publication_id UUID PRIMARY KEY
        REFERENCES fb_publications(id),

    schema_version INTEGER NOT NULL,
    publication_version BIGINT NOT NULL,

    catalog_revision TEXT NULL,
    configuration_version BIGINT NOT NULL,
    pricing_policy_id UUID NULL,
    pricing_policy_version INTEGER NULL,
    fx_rate_snapshot_id UUID NULL,
    price_source_revision TEXT NULL,

    resolved_values JSONB NOT NULL DEFAULT '{}',
    field_states JSONB NOT NULL DEFAULT '{}',
    issues JSONB NOT NULL DEFAULT '[]',

    readiness TEXT NOT NULL
        CHECK (readiness IN (
            'READY', 'NEEDS_INPUT',
            'INVALID', 'STALE'
        )),

    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_fb_projection_readiness
ON fb_publication_projections(readiness);

```

Здесь `resolved_values` — данные для списков и предпросмотра, но не источник истины.

`field_states` содержит происхождение каждого значения:

```
{
  "11111111-1111-4111-8111-111111111111": {
    "origin": "MANUAL",
    "status": "VALID"
  },
  "33333333-3333-4333-8333-333333333333": {
    "origin": "INHERITED",
    "status": "VALID"
  }
}
```

Проекция устаревает при несовпадении schema_version, publication_version,
configuration_version, назначения/активной версии PricePolicy, ревизии источника
цены или используемого набора FX-курсов. При наличии событий Catalog также
сравнивается catalog_revision. Метаданные актуальности получаются через публичные
порты; прямого JOIN к таблицам Catalog/Pricing/Currency нет. События изменения
политики/курсов инвалидируют кеш, а проверка версий остаётся защитой от пропущенного
события. Для полностью ручных денежных полей зависимость от курса не требуется.

Не требуется массово обновлять все 100 тысяч строк сразу после публикации новой схемы. Их устаревание можно выявлять по несовпадающим версиям.

### **5.6. Генерации, ошибки, артефакты**

```
CREATE TABLE fb_generations (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    schema_version INTEGER NOT NULL,
    configuration_version BIGINT NOT NULL,
    pricing_policy_id UUID NULL,
    pricing_policy_version INTEGER NULL,
    fx_rate_snapshot_id UUID NULL,
    export_settings_snapshot JSONB NOT NULL,
    request_sequence BIGINT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN (
            'PENDING', 'RUNNING',
            'SUCCEEDED', 'FAILED'
        )),

    attempt_count INTEGER NOT NULL DEFAULT 0,
    attempt_token UUID NULL,
    lease_until TIMESTAMPTZ NULL,

    total_items INTEGER NOT NULL DEFAULT 0,
    exported_items INTEGER NOT NULL DEFAULT 0,
    rejected_items INTEGER NOT NULL DEFAULT 0,

    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    finished_at TIMESTAMPTZ NULL,

    UNIQUE (feed_id, request_sequence),
    UNIQUE (feed_id, id),

    FOREIGN KEY (feed_id, schema_version)
        REFERENCES fb_schema_versions(feed_id, version)
);

CREATE TABLE fb_generation_issues (
    id UUID PRIMARY KEY,

    generation_id UUID NOT NULL
        REFERENCES fb_generations(id),

    publication_id UUID NULL,
    field_id UUID NULL,

    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX ix_fb_generation_issues_generation
ON fb_generation_issues(generation_id);

CREATE TABLE fb_artifacts (
    id UUID PRIMARY KEY,

    generation_id UUID NOT NULL
        REFERENCES fb_generations(id),

    format_code TEXT NOT NULL
        CHECK (format_code IN ('csv', 'xml')),

    storage_key TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,

    sha256 CHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (generation_id, format_code)
);

ALTER TABLE fb_feeds
ADD CONSTRAINT fk_fb_active_generation
FOREIGN KEY (id, active_generation_id)
REFERENCES fb_generations(feed_id, id);

```

Таким образом, `Feed.active_generation_id` указывает на конкретную успешную генерацию, а она — на оба файла.

При ошибке новой генерации указатель не изменяется.

### **5.7. Доступ по URL**

```
CREATE TABLE fb_access_keys (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    token_hash BYTEA NOT NULL,

    status TEXT NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ NULL
);

```

В `public` schema создаётся дополнительная таблица `feed_public_routes` с полями `public_id`, `tenant_id`, `feed_id`, `status`.

Она позволяет по публичному URL найти нужный tenant, не допуская прямого выбора SQL-схемы из пользовательского ввода.

### **5.8. PricePolicy и версии в Pricing**

```sql
CREATE TABLE pricing_policies (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    active_version INTEGER NULL,
    row_version BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pricing_policy_versions (
    policy_id UUID NOT NULL REFERENCES pricing_policies(id),
    version INTEGER NOT NULL CHECK (version > 0),
    definition JSONB NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (policy_id, version)
);

CREATE TABLE pricing_policy_drafts (
    policy_id UUID PRIMARY KEY REFERENCES pricing_policies(id),
    definition JSONB NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
    row_version BIGINT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE pricing_policies
ADD CONSTRAINT fk_pricing_active_version
FOREIGN KEY (id, active_version)
REFERENCES pricing_policy_versions(policy_id, version);
```

Это tenant-таблицы контекста Pricing; FeedBuilder не управляет ими напрямую.
В definition хранятся источник базовой цены, default_rule и будущие currency_rules.
Draft политики хранится отдельно: publish в одной транзакции валидирует draft,
создаёт версию, меняет active_version через метод PricePolicy, удаляет draft
и записывает Outbox. Опубликованная версия политики неизменяема.
Ссылки на Pricing и Currency в Feed,
проекциях и генерациях логические: физический FK между bounded contexts не нужен.
Назначение политики проверяется через Application Port в том же tenant.

При pricing_policy_id=null используется явный NO_ADJUSTMENT: базовый источник
Catalog item.regular_price, нулевая наценка; конвертация в валюту поля сохраняется.
Удаление политики, версии или FX-snapshot, на которые ссылается история генераций,
запрещается политикой хранения владельца данных.

### **5.9. Snapshot курсов и версия контекста**

В Currency/Pricing хранится неизменяемый FxRateSnapshot: id, исходная и целевая
валюта, Decimal-курс, направление котировки, источник, дата/время действия и
время получения. Источники НБУ и ручного курса имеют разные идентификаторы.
FeedBuilder хранит ссылку на snapshot, не копирует справочник курсов.

В PENDING snapshot может отсутствовать. При первом запуске worker фиксирует
единый snapshot для всех валют до расчёта первой позиции; повторы используют
его же. Если конвертация не требуется, fx_rate_snapshot_id может быть null.
Отсутствующий необходимый курс даёт FX_RATE_MISSING, не условный или устаревший курс.

configuration_version изменяется только для влияющих на выгрузку настроек
(назначение политики, export settings, validation policy). row_version защищает
любое конкурентное изменение агрегата. Эти версии имеют разные назначения.

## **6. Application Layer — структура и Use Cases**

### **6.1. Контракты и порты**

Write Repository contracts принадлежат Domain соответствующего агрегата:
FeedRepositoryProtocol, FeedPublicationRepositoryProtocol,
FeedGenerationRepositoryProtocol; PricePolicyRepositoryProtocol — Domain Pricing.
Они возвращают агрегаты и не предоставляют универсальный CRUD для всех таблиц.
Draft и опубликованные схемы сохраняются через контракт хранения Feed; отдельный
SchemaVersionReaderProtocol в Application предоставляет immutable версии для чтения.

| Application Port / Service | Ответственность |
| --- | --- |
| FeedQueryRepositoryProtocol | Списки и детали Feed в DTO |
| FeedPublicationQueryRepositoryProtocol | Карточки/страницы публикаций, фильтры и статистика |
| FeedGenerationQueryRepositoryProtocol | История, результаты, issues и активные артефакты |
| SchemaVersionReaderProtocol | Чтение draft/опубликованной схемы и хеша |
| PublicationProjectionPort | Запись/инвалидация read model с проверкой актуальности |
| CatalogProductReader | Batch-чтение immutable snapshots с набором локалей |
| PriceCalculationPort | Batch PriceQuote по зафиксированной политике и FX-контексту |
| PricingPolicyReaderPort | Проверка назначения, чтение версии и ревизии политики |
| FxRateSnapshotPort | Фиксация/чтение единого набора курсов |
| ReferenceDataReaderPort | Проверка кодов валют/локалей |
| SourcePathRegistry | Метаданные разрешённых источников и выбор адаптера |
| FieldTypeRegistry / TransformRegistry | Выбор чистых доменных handlers |
| FeedSerializerRegistry / FormatProfileRegistry | Допустимые форматы, профили и сериализаторы |
| ArtifactStorage / ExportStagingPort | Потоковое хранение артефактов и промежуточных записей |
| GenerationJobPort / ProjectionJobPort | Транзакционная постановка и захват задач |
| OutboxRepositoryProtocol | Запись интеграционных сообщений до общего commit |
| PublicFeedRoutePort / FeedAccessPort | Доверенная маршрутизация и проверка ключа |

Чистые parse/transform/constraint/markup policies находятся в Domain.
Application-реестры собирают их и координируют обращения к внешним портам.
Инфраструктурные типы не входят в контракты. Обычный handler получает только
нужные порты; управление UoW остаётся во внешней сборке.

### **6.2. Команды FeedBuilder: входы и результаты**

Имена в таблице обозначают сценарии; каждый реализуется отдельными
`<Scenario>Command`, `<Scenario>Handler` и DTO результата при его наличии.
Для всех команд передаются доверенные tenant_id/actor_id и необходимые
expected_version; HTTP Request не передаётся в Application.

| Сценарий | Вход кроме контекста | Результат |
| --- | --- | --- |
| CreateFeed | name, code, initial_locale, initial_currency, export settings, policy_id? | CreateFeedResultDTO: feed_id, draft_version, row_version |
| UpdateFeedSettings | feed_id, expected_version, явный набор изменяемых настроек | UpdateFeedSettingsResultDTO: версии |
| AssignFeedPricingPolicy | feed_id, policy_id или null, expected_version | AssignFeedPricingPolicyResultDTO: назначение и configuration_version |
| SaveFeedSchemaDraft | feed_id, schema definition, expected draft version или null, expected_schema_version | SaveFeedSchemaDraftResultDTO: draft_version, issues |
| PublishFeedSchema | feed_id, expected feed/draft versions | PublishFeedSchemaResultDTO: schema_version, content_hash |
| AddCatalogItemsToFeed | feed_id, item_ids | AddCatalogItemsToFeedResultDTO: item_id → publication_id, существующие/новые |
| RemoveFeedPublication | publication_id, expected_version | None |
| SetPublicationOverride | publication_id, field_id, value, expected_version | SetPublicationOverrideResultDTO: publication_version |
| ResetPublicationOverride | publication_id, field_id, expected_version | ResetPublicationOverrideResultDTO: publication_version |
| ChangePublicationStatus | publication_id, status, expected_version | ChangePublicationStatusResultDTO: status, version |
| RefreshPublicationProjection | publication_id | None; устаревшая запись не перезаписывает новую |
| RequestFeedGeneration | feed_id, ожидаемая конфигурация | RequestFeedGenerationResultDTO: generation_id, PENDING |
| ExecuteFeedGeneration | generation_id, attempt_token | None; результат сохраняется в FeedGeneration |
| CreateFeedAccessKey | feed_id | CreateFeedAccessKeyResultDTO: key_id и секрет однократно |
| RotateFeedAccessKey | feed_id, key_id | RotateFeedAccessKeyResultDTO: новый ключ однократно |
| RevokeFeedAccessKey | feed_id, key_id | None |

Сценарии настройки PricePolicy принадлежат Pricing: CreatePricePolicy,
SavePricePolicyDraft, PublishPricePolicyVersion, ListPricePolicies,
GetPricePolicy, PreviewPriceCalculation. В MVP политика проверяется и публикуется
явным действием; сохранённые опубликованные версии не редактируются на месте.
Каждый сценарий имеет собственные Command/Query, Handler, DTO и HTTP-схемы.

| Сценарий Pricing | Вход кроме доверенного контекста | Результат |
| --- | --- | --- |
| CreatePricePolicy | name, base_source, default_rule | CreatePricePolicyResultDTO: policy_id, draft_version, row_version |
| SavePricePolicyDraft | policy_id, definition, expected draft version или null, expected_active_version | SavePricePolicyDraftResultDTO: draft_version, issues |
| PublishPricePolicyVersion | policy_id, expected policy/draft versions | PublishPricePolicyVersionResultDTO: policy_id, active_version |
| ListPricePolicies | фильтры и пагинация | Page[PricePolicyListItemDTO] |
| GetPricePolicy | policy_id, ACTIVE / DRAFT / version | PricePolicyDetailsDTO |
| PreviewPriceCalculation | policy_id, schema_mode, item_ids, target_currencies | PriceCalculationPreviewDTO: quotes, issues, версии и FX snapshot |

CreatePricePolicy создаёт первоначальный draft. После публикации новый локальный
draft строится из активной версии и сохраняется отдельной командой с проверкой
отсутствия/ожидаемой версии; Query не создаёт draft в БД. Publish не включает
автоматическое назначение Feed. Все сценарии Pricing проверяют тот же tenant.

### **6.3. Queries**

| Query | Вход | Результат |
| --- | --- | --- |
| ListFeeds | фильтры, сортировка, пагинация | Page[FeedListItemDTO] |
| GetFeed | feed_id | FeedDetailsDTO |
| GetFeedSchema | feed_id, ACTIVE / DRAFT / version | FeedSchemaDetailsDTO |
| ListFieldTypes / ListSourcePaths / ListTransforms | контекст/тип/профиль | Собственные DTO метаданных каждого сценария |
| ListFeedPublications | feed_id, фильтры, сортировка, пагинация | Page[FeedPublicationListItemDTO] |
| GetFeedPublication | publication_id | FeedPublicationDetailsDTO |
| PreviewFeedPublication | publication_id, ACTIVE / DRAFT | PublicationPreviewDTO |
| PreviewFeed | feed_id, schema_mode, limit | FeedPreviewDTO |
| GetGeneration / ListGenerations | generation_id / feed_id и пагинация | GenerationDetailsDTO / Page[GenerationListItemDTO] |
| ListGenerationIssues | generation_id, фильтры, пагинация | Page[GenerationIssueDTO] |
| GetActiveFeedArtifact | feed_id, format | ActiveFeedArtifactDTO |
| DownloadPublicFeed | public_id, token, format | ArtifactDownloadDTO с метаданными для потоковой выдачи |

List/detail Queries читают готовые проекции. Preview координирует чтение
snapshot и resolve без изменения бизнес-состояния; не требует сохранения проекции.
HTTP responses создаются отдельно из Application DTO.

### **6.4. Транзакции и границы сценариев**

Обычный handler выполняется в UoW, открытом Depends. Репозитории Feed,
публикаций, генераций и Outbox атомарного процесса используют одну сессию.
Handler не создаёт `uow_factory`, не обращается к ORM и не коммитит репозиторий.
После успешного handler внешний UoW выполняет commit до ответа, при ошибке — rollback.

PublishFeedSchema: загрузить Feed и draft с проверкой ожидаемых версий →
получить метаданные зависимостей → вызвать доменную проверку и publish_schema →
сохранить новую неизменяемую версию и Feed, удалить draft → записать Outbox →
завершить внешнюю транзакцию. Все изменения состояния выполняются методами Feed.

Создание PricePolicy и назначение её Feed — два явных сценария разных владельцев.
UI назначает политику после успешного создания/публикации. Сбой назначения не
должен маскироваться как успех всего действия; созданную политику можно выбрать
повторно. Handler не вызывает другой handler; общая оркестрация использует порты
и небольшие Application services соответствующих модулей.

Долгая генерация разделена на claim, чтение/расчёт/staging, complete и activate.
Каждый короткий DB-этап собирается внешним worker bootstrap со своим UoW;
request-scoped сессия в worker не передаётся. Между этапами нет открытой долгой
SQL-транзакции. Запись во внешний storage завершается до активации ссылок.

### **6.5. Версии и конкуренция**

row_version обязателен для Feed, draft, FeedPublication и PricePolicy.
Обычные ORM-обновления могут использовать version_id_col; массовые UPDATE/DELETE
обязаны явно проверять ожидаемую версию и число изменённых строк.

Несовпадение версии возвращает VERSION_CONFLICT / HTTP 409, не last-write-wins.
Сохранение overrides и схемы не теряет конкурентный ввод. Keyset pagination,
идемпотентные команды привязки, attempt_token и условная активация защищают worker.
Версии schema/configuration/policy и FX snapshot имеют отдельный смысл и не
подменяются единым timestamp.

## **7. Value Resolution Engine**

Application Service PublicationResolver получает версию схемы, snapshot товара,
overrides и ResolutionContext, координирует источники и возвращает
ResolvedPublication. FieldValueResolver применяет чистые типы, transforms и
constraints. I/O выполняют Application resolvers/ports, а не Domain policies.

### **7.1. SourcePathRegistry**

| provider / path | Тип | Контекст |
| --- | --- | --- |
| catalog / item.title | STRING | field.locale + fallback_policy |
| catalog / item.description | TEXT | field.locale + fallback_policy |
| catalog / item.regular_price | MONEY | Базовая цена без наценки, только явный выбор |
| pricing / final_price | MONEY | PricePolicy + target field.currency + FX snapshot |

Стандартный источник денежных полей — pricing/final_price. Прямой базовый
Catalog-источник не выполняет скрытую конвертацию: валюта должна совпадать с
валютой поля; при необходимости расчёта/конвертации выбирается Pricing.
Метаданные source содержат допустимый тип, необходимость locale/currency и
поддерживаемые параметры. Реестр не зависит от числа языков.

Нельзя исполнять eval, пользовательский SQL, произвольный URL, динамический
доступ к атрибутам Python. SourcePath — только зарегистрированный идентификатор.

### **7.2. Контракт CatalogProductReader**

CatalogProductSnapshot содержит id, локализованные title/description по нужным
локалям, regular_price: MoneyVO | None, revision. Это immutable snapshot для
конкретного потребителя, не агрегат и не ORM-модель Catalog.

```python
class CatalogProductReader(Protocol):
    """Предоставляет FeedBuilder снимки Catalog через публичную границу чтения."""

    async def get_many(
        self,
        *,
        item_ids: tuple[UUID, ...],
        locales: frozenset[str],
    ) -> dict[UUID, CatalogProductSnapshot]:
        """Возвращает товары с запрошенными переводами без запросов на каждое поле."""
        ...
```

Набор locales включает целевые локали и fallback-chain схемы. Не используется
один locale всего Feed. Для больших каталогов чтение идёт пакетами, без N+1.
Описание в MVP — plain text. Если Catalog хранит HTML, адаптер предоставляет
plain-text проекцию либо используется явно зарегистрированное безопасное
преобразование; HTML не передаётся в XML без определённого контракта.

### **7.3. ResolutionContext и происхождение значения**

Контекст содержит tenant/feed/publication/item IDs, schema_version,
configuration_version, policy_id/version, FxRateSnapshot, временной контекст
расчёта и идентификатор генерации при экспорте. Язык и валюта берутся из поля.

ResolvedField содержит field_id, key, тип, source_value при доступности,
override_value, resolved_value, origin, validation issues, фактически
использованную локаль, валюту, ревизии и необязательный PriceQuote trace.
Origin различает INHERITED, MANUAL и локализованный fallback в метаданных.

### **7.4. FieldTypeRegistry и TransformRegistry**

StringFieldHandler, TextFieldHandler и MoneyFieldHandler реализуют parse и validate.
Текстовые типы могут делить чистую базовую реализацию. Money parse сохраняет Decimal
и currency. Входы/результаты handlers имеют конкретные типы; универсальный dict
не заменяет доменные контракты.

TransformRegistry выбирает TrimTransform, TruncateTransform,
MoneyCeilStepTransform и применяет их в порядке схемы. Добавление transform
не требует изменения FeedPublication или SQL. Доступные параметры и ограничения
типов выдаёт backend; frontend не поддерживает второй независимый реестр.

### **7.5. Полный алгоритм разрешения**

1. Определить режим поля по наличию override, иначе взять default_mode.
2. Для MANUAL выбрать override.value; без override получить отсутствующее ручное
   значение. Не запрашивать Pricing/FX для получения окончательного ручного значения.
3. Для INHERIT получить source: локализованный Catalog либо PriceQuote Pricing.
   Поле без source возвращает отсутствующее значение.
4. Отличить отсутствие значения от SOURCE_UNAVAILABLE. Отсутствующая базовая цена
   даёт BASE_PRICE_MISSING; отсутствующий нужный курс — FX_RATE_MISSING.
5. Parse: привести значение к типу поля, не используя float для MONEY.
6. Проверить соответствие валюты денежного значения field.currency.
7. Применить упорядоченные transforms.
8. Проверить constraints, required и политику MANUAL_REQUIRED.
9. Вернуть значение, origin, trace и issues; собрать readiness публикации.

Для preview исходное значение можно получить дополнительно для сравнения.
Ошибка необязательного диагностического чтения источника при валидном override
показывается отдельно и не делает ручное итоговое значение ошибочным.

### **7.6. Локализация, пустые значения и ошибки**

Целевая локаль проверяется первой; LOCALE_CHAIN последовательно проверяет только
явно заданные локали. При NONE нет скрытой подстановки. Отсутствующий обязательный
перевод — REQUIRED_VALUE_MISSING / NEEDS_INPUT. MANUAL_REQUIRED сообщает
TRANSLATION_MANUAL_REQUIRED и требует override, если целевого перевода нет.
Для языконезависимого текста locale=null, fallback не применяется.

Не смешиваются null, пустая строка, отсутствие override и reset. Required
проверяется после string.trim, поэтому строка из пробелов не удовлетворяет
обязательности. Непарсящееся значение — INVALID_VALUE_TYPE, constraints —
MAX_LENGTH_EXCEEDED и другие конкретные коды.

Missing price/rate у наследуемого MONEY — INVALID даже для необязательного
денежного поля с выбранным источником: это ошибка расчёта, а не разрешение
использовать устаревшее значение. Источник недоступен технически — отдельный
сбой зависимости с retry по правилам worker, не REQUIRED_VALUE_MISSING.

### **7.7. MoneyCeilStepTransform**

```python
from decimal import Decimal, ROUND_CEILING


def ceil_money_step(value: MoneyVO, step: Decimal) -> MoneyVO:
    """Округляет сумму вверх с положительным шагом, сохраняя её валюту."""
    if step <= 0:
        raise InvalidTransformParametersError()
    units = (value.amount / step).to_integral_value(rounding=ROUND_CEILING)
    return MoneyVO(amount=units * step, currency=value.currency)
```

Совместимость валюты проверяется с FieldDefinition.currency, не с Feed.
590.21 при step=0.1 даёт 590.3; в экспорте для UAH/USD/EUR — 590.30.
Два знака — начальные настройки этих валют, не универсальная точность всех валют.
Для иных поддерживаемых валют точность определяется явной настройкой профиля
или справочника, а не float и не повторным коммерческим округлением Serializer.

### **7.8. PublicationResolver и проекции**

1. Получить snapshot Catalog для требуемых локалей/полей.
2. Собрать валюты только наследуемых pricing-полей без override.
3. Получить PriceQuote пакетно для всех этих валют, один раз рассчитав основную наценку.
4. Разрешить каждое поле и собрать issues с привязкой к field_id.
5. INVALID имеет приоритет над NEEDS_INPUT; при отсутствии блокирующих issues — READY.

STALE определяется только актуальностью сохранённой проекции. Проекция
содержит версии схемы/публикации/конфигурации, ревизии Catalog/цены, политику
и FX snapshot. Новый worker не перезаписывается результатом старого:
upsert выполняется условно по всему контексту и ревизии задачи проекции.
Для списка используется кеш; preview и экспорт вычисляют значения заново.

## **8. Pricing: политики, наценки и валютные расчёты**

### **8.1. Распределение ответственности**

| Операция | Владелец |
| --- | --- |
| Хранение закупочной/базовой продажной цены | Catalog / Supplier Sourcing / Pricing согласно контракту источника |
| Выбор исходной цены | PricePolicy |
| Коммерческая наценка, фиксированная надбавка, целевая маржа | Pricing Engine |
| Курсы и конвертация | Pricing + Currency Provider |
| Дополнительная валютная корректировка | PricePolicy |
| Ручная окончательная цена товара | FeedPublication override |
| Округление с шагом | Transform конкретного MONEY-поля |
| Представление 590.30 в CSV/XML | Serializer |

Одна политика может использоваться несколькими Feed и Channels. FeedBuilder
хранит policy_id и запрашивает результат через PriceCalculationPort; не изменяет
чужой агрегат и не копирует «+20%» в каждое поле цены.

### **8.2. Aggregate PricePolicy и версии**

Поля: id, name, base_price_source: PriceSourceRef,
default_rule: MarkupRule, currency_rules: tuple[CurrencyPriceRule, ...],
active_version, version. Методы: create/restore, replace_draft, publish_version.
После publish создаётся неизменяемая версия definition; история сохраняется.

| Тип правила | Формула | Этап |
| --- | --- | --- |
| NONE | P = B | MVP |
| PERCENT | P = B × (1 + r) | MVP |
| FIXED_AMOUNT | P = B + A | Расширение |
| TARGET_MARGIN | P = C / (1 − m) | Расширение |

B — выбранная базовая цена, C — себестоимость, r — доля наценки, A — фиксированная
надбавка, m — целевая валовая маржа. Наценка 30% и маржа 30% различаются.
TARGET_MARGIN требует источник себестоимости и 0 ≤ m < 1; его нельзя считать
из произвольной розничной цены. Налоги, скидки и комиссии требуют явной политики.

В JSON PERCENT.value задаётся процентами: «20» означает r=0.20. В MVP значение
неотрицательно; скидочные отрицательные правила требуют отдельного расширения.
Неизвестный/ещё не поддержанный тип правила отклоняется при publish.

```json
{
  "name": "Основной прайс +20%",
  "base_source": {"provider": "catalog", "path": "item.regular_price"},
  "default_rule": {"type": "PERCENT", "value": "20"},
  "currency_rules": {},
  "rounding": {"mode": "FIELD_DEFINED"}
}
```

Это исполнимый набор MVP. Контракт будущего currency_rules может содержать
`{"USD": {"extra_markup_percent": "5"}}`: дополнительная наценка после конвертации,
а не замена default_rule. В MVP непустые currency_rules отклоняются как
неподдерживаемая возможность; скрытое игнорирование запрещено. Будущая замена
основного правила должна иметь отдельный явный режим REPLACE_DEFAULT.

### **8.3. Разные прайс-листы и общий Catalog**

| Feed | Политика | Базовая цена | Основная наценка |
| --- | --- | --- | --- |
| Prom — основной | policy-prom | Catalog regular_price | +20% |
| Rozetka — основной | policy-rozetka | Catalog regular_price | +30% |
| Оптовый | policy-wholesale | Catalog regular_price | +5% |
| Партнёрский | policy-partner | Catalog regular_price | +12% |

Имена Feed здесь обозначают назначение прайс-листа, не реализацию контрактов
площадок в MVP. Изменение политики не меняет Catalog и не требует редактировать
каждое поле схемы. Новая версия политики инвалидирует зависимые проекции.

При исходной цене 1000 UAH и условном курсе 40 UAH за 1 USD:

| Feed | UAH | USD |
| --- | --- | --- |
| +20% | 1200.00 | 30.00 |
| +30% | 1300.00 | 32.50 |

Курс только иллюстративный; пример не включает валютные надбавки и налоги.

### **8.4. Порядок расчёта**

```text
Catalog Base Price с валютой
  → основная PricePolicy наценка, один раз
  → конвертация в валюты полей по одному FX snapshot
  → дополнительные валютные правила (последующие релизы)
  → PriceQuote для каждой валюты
  → окончательный override поля, если задан
  → transforms поля, включая округление
  → constraints и проверка валюты
  → ResolvedField
```

Основная наценка не повторяется для каждого поля или при переходе между валютами.
PriceCalculator.calculate_base вызывается один раз на товар, источник и версию
политики в расчётном контексте. calculate_targets получает набор целевых валют.
PriceCalculationPort поддерживает batch, а адаптер кеширует quotes в рамках
контекста без смешивания tenant, версии политики или snapshot курсов.

Override применяется вместо quote. Если price_usd вручную задан 35.00 USD,
экспорт получает эту цену после transforms/validation, без +20% и без конвертации.
price_uah продолжает вычисляться независимо. Для полностью ручного поля не нужны
ни исходная цена, ни курс; диагностическое сравнение в UI необязательно.

### **8.5. PriceQuote и FX snapshot**

PriceQuote содержит MoneyVO, catalog_item_id, базовую цену и её ревизию,
policy_id/version или NO_ADJUSTMENT, применённые правила, исходную/целевую валюту,
FX snapshot ID, использованный курс и источник, время расчёта. Trace отдаётся
preview с учётом прав; закупочная цена не раскрывается пользователю без разрешения.

PriceCalculator — чистый Domain Service Pricing. Он получает цену, immutable
политику/правила и snapshot курсов; не вызывает repository/HTTP. Application Pricing
получает входы через порты и возвращает Quote DTO/snapshot потребителю.
FeedBuilder не получает сам агрегат PricePolicy.

Один snapshot фиксируется на начало выполнения генерации и используется всеми
позициями и форматами. Текущий курс не перечитывается на каждый товар.
Ошибки BASE_PRICE_MISSING и FX_RATE_MISSING делают наследуемое поле INVALID;
техническая недоступность зависимости даёт отдельный retryable сбой.

### **8.6. Расширения и приоритеты**

Будущие правила уровня категории/SKU/поставщика требуют явной специфичности:
самое специфичное заменяет общее, а не суммируется автоматически. Дополнительная
валютная надбавка применяется только при явном extra_markup. FIXED_AMOUNT
имеет собственную валюту и проверяемый порядок конвертации; TARGET_MARGIN
проверяет источник себестоимости. Эти возможности добавляются отдельными срезами
с тестами и версией policy definition; MVP не содержит частично работающих правил.

## **9. Use Cases управления публикациями**

### **9.1. AddCatalogItemsToFeed**

1. Проверить права и получить Feed с опубликованной схемой.
2. Batch-прочитать Catalog Items через порт с нужным набором локалей.
3. Проверить поддержку простых товарных позиций; catalog_variant_id=None.
4. Для каждого нового товара вызвать FeedPublication.create, существующий вернуть.
5. Сохранить публикации и транзакционно поставить задачи проекций.
6. Завершить внешний UoW и вернуть mapping item_id → publication_id.

Идемпотентность обеспечивается UNIQUE(feed_id, catalog_item_id, catalog_variant_id)
с NULLS NOT DISTINCT и корректной обработкой конкурентной вставки. Повторный
запрос не создаёт дубль и не стирает overrides существующей публикации.
Если источник Catalog недоступен, это отдельная ошибка, не отсутствие товара.

### **9.2. SetPublicationOverride**

1. Загрузить публикацию и актуальную опубликованную схему Feed.
2. Проверить expected_version и принадлежность field_id этой схеме.
3. Проверить базовую совместимость значения с типом. Money содержит amount-строку
   и currency; непарсящаяся сумма отклоняется без сохранения повреждённых данных.
4. Вызвать publication.set_override, сохранить агрегат и инвалидировать проекцию
   в общей транзакции.
5. Вернуть publication_version; UI запрашивает новый preview.

Превышение max_length/min_amount можно сохранить, чтобы не терять пользовательский
ввод; результат становится INVALID. Синтаксически корректная, но неверная валюта
также показывается как CURRENCY_MISMATCH относительно валюты поля. Ручная цена
окончательна до transforms: Pricing не начисляет на неё наценку повторно.

### **9.3. ResetPublicationOverride**

Проверить field_id и expected_version → вызвать publication.reset_override →
сохранить и инвалидировать проекцию → вернуть новую publication_version.
Отсутствие записи после reset возвращает default_mode схемы. Для поля без source
это может означать NEEDS_INPUT. Ручной null и reset имеют разный смысл.

### **9.4. PreviewFeedPublication и PreviewFeed**

Preview читает публикацию, схему, Catalog и Pricing через порты, получает
ResolutionContext и возвращает PublicationPreviewDTO без обязательного сохранения
проекции. ACTIVE использует опубликованную схему; DRAFT позволяет проверить
изменения, не затрагивая активные CSV/XML. При отсутствии draft UI явно сообщает
об этом, не переключается на другую версию незаметно.

PreviewFeed возвращает ограниченные первые N публикаций в стабильном порядке,
контекст расчёта и фрагменты выбранных форматов. Он использует тот же resolver,
профиль и serializer, что и генерация. Лимит ограничивается backend.

### **9.5. RefreshPublicationProjection**

Загрузить snapshot контекста, получить Catalog и PriceQuote, разрешить поля →
в короткой транзакции записать проекцию только если всё ещё актуальны версии
публикации, схемы, конфигурации, политики и ревизия задачи расчёта.
Результат устаревшего worker отбрасывается; при необходимости планируется новый.

Смена схемы не требует немедленно обновлять все 100 тысяч строк: STALE выявляется
по несовпадению версий. События Catalog/Pricing/FX ускоряют инвалидацию, но не
заменяют проверку актуальности. Списки используют проекции, экспорт — новый resolve.

### **9.6. Участие и удаление**

ChangePublicationStatus вызывает domain-метод с проверкой допустимого перехода.
В генерацию входят только ENABLED. RemoveFeedPublication удаляет привязку и её
кеш, не изменяет Catalog. Исторические GenerationIssue сохраняют идентификатор
и безопасные сведения о позиции даже после удаления; физический FK на текущую
публикацию для истории необязателен. Смена участия влияет на следующий проход
генерации по правилам согласованности источников.

## **10. Генерация CSV/XML**

### **10.1. Внутренняя экспортная модель**

Не следует жёстко привязывать сериализатор к классу с тремя атрибутами. Это усложнит добавление новых полей.

Лучше использовать динамический список типизированных значений.

```python
@dataclass(frozen=True)
class ExportCell:
    """Передаёт одно проверенное значение для сериализации."""

    field_id: UUID
    export_name: str
    value_type: FieldValueType
    value: DomainValue | None


@dataclass(frozen=True)
class ExportRecord:
    """Передаёт упорядоченные ячейки одной публикации обоим сериализаторам."""

    publication_id: UUID
    cells: tuple[ExportCell, ...]
```

Порядок `cells` совпадает с порядком полей FeedSchema.

Это позволит добавлять новые поля без изменения сериализаторов CSV/XML.

### **10.2. CSV Serializer**

Контракт сериализатора:

```python
class FeedSerializer(Protocol):
    """Преобразует проверенный поток записей в выбранный экспортный формат."""

    def serialize(
        self,
        *,
        records: AsyncIterator[ExportRecord],
        schema: FeedSchema,
        settings: ExportFormatSettings,
    ) -> AsyncIterator[bytes]:
        """Возвращает байты без изменения значений, бизнес-правил и источников."""
        ...
```

CsvFeedSerializer создаёт header из schema.exported_fields, затем потоково
записывает значения cells. Он получает настройки delimiter/encoding/include_header
из зафиксированного export settings, а не хардкодит общие настройки Feed.

Правила:

- UTF-8.
- Разделитель `,` по умолчанию.
- Колонки формируются в порядке схемы.
- Строковые значения корректно экранируются при наличии запятых, кавычек и переносов.
- Цена сериализуется в десятичном формате без валютного символа.
- Для значений, которые могут восприниматься электронными таблицами как формулы, предусмотрена отдельная политика безопасности CSV, не искажающая машинный импорт молча.

### **10.3. XML Serializer**

XmlFeedSerializer потоково записывает XML declaration, корневой элемент,
элемент каждой публикации и теги exported cells. root_name/item_name берутся
из зафиксированных настроек. Для отсутствующего необязательного значения
Generic CSV записывает пустую ячейку, Generic XML опускает элемент; профиль
может явно задать другое представление, не меняя FieldValueResolver.

`write_element()` должен экранировать спецсимволы XML и отклонять недопустимые символы XML 1.0. Имена тегов валидируются при публикации схемы.

### **10.4. Пример результата**

Для title_uk, title_ru, price_uah, price_usd после настройки экспортируемых полей:

```csv
title_uk,title_ru,description_uk,price_uah,price_usd
"Хлорофіл NOW Foods","Хлорофилл NOW Foods","Рідкий хлорофіл",1200.00,30.00
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<catalog>
  <product>
    <title_uk>Хлорофіл NOW Foods</title_uk>
    <title_ru>Хлорофилл NOW Foods</title_ru>
    <description_uk>Рідкий хлорофіл</description_uk>
    <price_uah>1200.00</price_uah>
    <price_usd>30.00</price_usd>
  </product>
</catalog>
```

Оба файла создаются из одного набора ExportRecord. Деньги сохраняют валюту в
Domain и preview; в Generic CSV/XML числовое значение не содержит символ валюты,
а назначение валюты определяется явной схемой и экспортным именем поля.

### **10.5. FeedSchema и FormatProfile**

```text
FeedSchema → ResolvedPublication → FormatProfile → Serializer
                                    ├── Generic CSV
                                    ├── Generic XML
                                    ├── Prom YML (после MVP)
                                    └── Rozetka XML (после MVP)
```

FeedSchema определяет пользовательские значения, FormatProfile — контракт
целевого формата: соответствие экспортных полей/имён, допустимые валюты,
обязательные поля и структуру. Общая внутренняя схема не означает, что любой
маркетплейс примет произвольные title_uk/price_usd. Профили площадок реализуются
отдельно по их официальным спецификациям, актуальным на момент реализации.

Generic CSV/XML дают свободные имена и порядок в пределах безопасной валидации.
Профиль не пересчитывает цены и не смешивает языки. Источники значения и коммерческие
правила остаются в Catalog/Pricing/FieldValueResolver. Новые профили не требуют
копировать публикации или создавать отдельную версию товара Catalog.

## **11. Асинхронная генерация и публикация файлов**

### **11.1. Процесс выполнения**

```text
RequestFeedGeneration: задание PENDING и фиксированная конфигурация
  → worker claim: RUNNING, attempt token, lease
  → фиксация единого FX snapshot перед первым расчётом
  → batch/keyset чтение ENABLED публикаций и Catalog
  → batch PriceQuote, resolve и validation
  → staging проверенных ExportRecord
  → сериализация CSV и XML из одного staging
  → сохранение неизменяемых файлов в ArtifactStorage
  → SUCCEEDED
  → условная атомарная активация обоих файлов
```

### **11.2. RequestFeedGeneration**

В короткой общей транзакции:

1. Получить Feed с блокировкой/ожидаемой версией и проверить опубликованную схему.
2. Через PricingPolicyReaderPort проверить назначение и получить активную
   неизменяемую версию; при null использовать явный NO_ADJUSTMENT.
3. Вызвать feed.request_generation: выделить следующую request_sequence,
   зафиксировать schema_version, configuration_version, policy_id/version и
   export_settings_snapshot. Прямое присваивание счётчиков из Application запрещено.
4. Создать FeedGeneration через фабрику и сохранить вместе с Feed.
5. Зафиксировать DB-задание PENDING и необходимые сообщения Outbox до commit.
6. После успешного внешнего UoW вернуть generation_id и HTTP 202.

В MVP PostgreSQL может служить очередью. Нельзя сохранять строку, затем отдельно
посылать сообщение внешнему брокеру без Outbox: так теряются задания.
Worker claim использует FOR UPDATE SKIP LOCKED, переводит PENDING в RUNNING,
устанавливает attempt_token, lease_until и фиксирует короткую транзакцию.

### **11.3. ExecuteFeedGeneration**

Worker работает с зафиксированной конфигурацией задания, не перечитывает текущие
настройки Feed в середине расчёта. Загружает точную версию схемы и политики.
При первом выполнении создаёт один FX snapshot всех нужных валют и записывает
его ID до обработки первой позиции; при retry читает тот же snapshot.
Если snapshot не был получен из-за технического сбоя, расчёт ещё не начинается.

Публикации читаются в стабильном порядке keyset-пакетами, начальный batch size=500.
Catalog получает набор локалей схемы и fallback. Pricing получает все товары
и целевые валюты пакетно. Основная наценка рассчитывается один раз на товар.
Для полей с override ненужные цены/курсы не запрашиваются.

В staging сохраняются итоговые ExportRecord и ревизии использованных источников.
При STRICT и блокирующих issues генерация завершается FAILED, сохраняются issues
и счётчики, активные файлы не переключаются. При успехе сериализаторы последовательно
читают тот же staging и пишут неизменяемые артефакты с sha256/size/content-type.

total_items — число фактически обработанных позиций, rejected_items — число
позиций с блокирующими issues. exported_items — число записей в успешно созданном
полном наборе артефактов; при FAILED равно нулю, даже если часть записей прошла
валидацию или один временный файл успел записаться. В UI они не считаются выгруженными.

Долгое чтение Catalog, PriceCalculation и запись файлов выполняются вне одной
долгой SQL-транзакции. Claim, heartbeat, фиксация snapshot, complete и activation
имеют отдельные короткие UoW, собранные внешним worker. Попытка, потерявшая lease,
не может завершить/активировать задание: все записи проверяют attempt_token.

### **11.4. Гарантии и согласованность**

- **Idempotency:** повтор задания не создаёт дублирующую активную выдачу.
- **Lease/heartbeat/fencing:** просроченное задание можно перехватить; старая
  попытка теряет право записать результат. Для каждой попытки отдельный staging.
- **Retry:** временные инфраструктурные сбои повторяются с лимитом/backoff;
  бизнес-валидация не ретраится. Отмена async-задачи не подавляется.
- **Atomic activation:** только после сохранения всех требуемых форматов
  меняется один active_generation_id; CSV и XML переключаются вместе.
- **Version safety:** схема, configuration_version и назначение/версия политики
  должны соответствовать фиксированному контексту генерации при активации.
- **Sequence safety:** генерация с request_sequence ниже уже активной не заменяет её.
- **Cleanup:** незавершённые staging/файлы и осиротевшие артефакты удаляются по
  retention policy после проверки ссылок и активных попыток.

activate_generation_if_current выполняется под блокировкой Feed и проверяет:
SUCCEEDED, наличие всех артефактов, допустимую sequence, schema_version,
configuration_version и актуальность policy_id/version. Проверка текущей версии
Pricing должна быть защищена от гонки с её публикацией: публичный порт Pricing
предоставляет согласованную проверку/блокировку версии до общего commit либо
эквивалентный транзакционный fence. FeedBuilder не читает таблицы Pricing напрямую.
Если проверка не прошла, генерация остаётся SUCCEEDED, но не активируется;
причина видна в API/истории. Сбой после complete допускает повтор активации.

Обновление курса после начала выполнения само по себе не запрещает активацию:
файл намеренно использует зафиксированный snapshot. Новый snapshot применяется
в следующей генерации; зависимые текущие проекции при этом отмечаются STALE.

MVP не гарантирует единый snapshot всего Catalog и набора публикаций на начало
генерации: при изменении Catalog/overrides/участия во время прохода используются
ревизии, фактически прочитанные для каждой позиции. Они сохраняются для трассировки.
Строгий общий source snapshot — будущее расширение. CSV и XML при этом всегда
строятся из одного staging; PricePolicy и FX внутри одной генерации не меняются.

### **11.5. Публичные ссылки**

```text
https://feeds.example.com/f/{public_id}/{token}/catalog.csv
https://feeds.example.com/f/{public_id}/{token}/catalog.xml
```

Публичный контроллер разрешает public_id через доверенный public registry,
получает tenant через Tenancy/admission, проверяет ключ через FeedAccessPort,
читает active_generation_id и метаданные артефакта. Если активной генерации нет —
404. Затем потоково выдаёт файл с ETag, Last-Modified и корректным Content-Type.

DB-проверки и UoW завершаются до длительной передачи файла; HTTP streaming не
держит tenant-транзакцию открытой. Storage stream не содержит request-scoped ORM.
Токены хранятся только в виде криптографических хешей, показываются однократно,
поддерживают отзыв/ротацию и не попадают в логи. Передача только HTTPS.
Ротация по умолчанию отзывает заменённый ключ атомарно; отдельные активные ключи
можно создавать/отзывать независимо. Кеширование не обходит проверку отзыва.

## **12. Presentation Layer — REST API**

### **12.1. Управление Feed и схемами**

| Метод   | Endpoint                                      | Use Case              |
| ------- | --------------------------------------------- | --------------------- |
| `POST`  | `/api/feed-builder/feeds`                     | `CreateFeed`          |
| `GET`   | `/api/feed-builder/feeds`                     | `ListFeeds`           |
| `GET`   | `/api/feed-builder/feeds/{id}`                | `GetFeed`             |
| `PATCH` | `/api/feed-builder/feeds/{id}`                | `UpdateFeedSettings`  |
| `GET`   | `/api/feed-builder/feeds/{id}/schema`         | `GetFeedSchema`       |
| `PUT`   | `/api/feed-builder/feeds/{id}/schema/draft`   | `SaveFeedSchemaDraft` |
| `POST`  | `/api/feed-builder/feeds/{id}/schema/publish` | `PublishFeedSchema`   |
| `GET`   | `/api/feed-builder/field-types`               | Поддерживаемые типы   |
| `GET`   | `/api/feed-builder/source-paths`              | Доступные источники   |
| `GET` | `/api/feed-builder/transforms` | Метаданные transforms |
| `PUT` | `/api/feed-builder/feeds/{id}/pricing-policy` | AssignFeedPricingPolicy |
| `POST` | `/api/feed-builder/feeds/{id}/preview` | PreviewFeed |

### **12.2. Публикации**

| Метод    | Endpoint                                  | Use Case               |
| -------- | ----------------------------------------- | ---------------------- |
| `POST`   | `/feeds/{id}/publications`                | Добавить Catalog Items |
| `GET`    | `/feeds/{id}/publications`                | Список и фильтры       |
| `GET`    | `/publications/{id}`                      | Карточка публикации    |
| `DELETE` | `/publications/{id}` | RemoveFeedPublication |
| `PUT`    | `/publications/{id}/overrides/{field_id}` | Установить override    |
| `DELETE` | `/publications/{id}/overrides/{field_id}` | Вернуть наследование   |
| `PATCH`  | `/publications/{id}/status`               | Изменить участие       |
| `POST`   | `/publications/{id}/preview`              | Вычислить предпросмотр |

Для краткости префикс `/api/feed-builder` в нижней части таблицы опущен.

### **12.3. Генерации**

| Метод    | Endpoint                           | Назначение          |
| -------- | ---------------------------------- | ------------------- |
| `POST`   | `/feeds/{id}/generations`          | Запустить генерацию |
| `GET`    | `/feeds/{id}/generations`          | История             |
| `GET`    | `/generations/{id}`                | Статус и статистика |
| `GET`    | `/generations/{id}/issues`         | Ошибки              |
| `GET`    | `/feeds/{id}/artifacts`            | Активные файлы      |
| `POST`   | `/feeds/{id}/access-keys`          | Создать ключ        |
| `DELETE` | `/feeds/{id}/access-keys/{key_id}` | Отозвать ключ       |
| `POST` | `/feeds/{id}/access-keys/{key_id}/rotate` | Ротация ключа |

### **12.4. DTO предпросмотра**

UI не должен самостоятельно разрешать SourcePath и повторять правила Domain.

Backend возвращает полностью вычисленную модель.

```
{
  "publication_id": "publication-uuid",
  "catalog_item_id": "catalog-item-uuid",
  "status": "ENABLED",
  "readiness": "INVALID",
  "schema_version": 1,
  "configuration_version": 1,
  "pricing_policy_id": "policy-uuid",
  "pricing_policy_version": 2,
  "fx_rate_snapshot_id": "fx-snapshot-uuid",
  "fields": [
    {
      "field_id": "field-title-uuid",
      "key": "title_uk",
      "system_role": "TITLE",
      "locale": "uk",
      "resolved_locale": "uk",
      "currency": null,
      "label": "Название",
      "value_type": "string",
      "source": {
        "provider": "catalog",
        "path": "item.title",
        "value": "Дуже довга початкова назва товару"
      },
      "mode": "INHERIT",
      "origin": "INHERITED",
      "override_value": null,
      "resolved_value": "Дуже довга початкова назва товару",
      "constraints": {
        "required": true,
        "max_length": 30
      },
      "validation": {
        "status": "INVALID",
        "issues": [
          {
            "code": "MAX_LENGTH_EXCEEDED",
            "message": "Название превышает 30 символов"
          }
        ]
      }
    }
  ]
}

```

Значения UUID здесь схематические для объяснения контракта.

В ответе можно также возвращать `can_override`, `can_reset`, `is_stale` и метаданные редактора.

### **12.5. Единый формат ошибок**

Общий transport error envelope содержит code, message, field_id?, details и
request_id. Он не заменяет собственные DTO результатов разных use cases.
Domain/Application ошибки преобразуются HTTP-слоем без импорта HTTPException
во внутренние слои.

Примеры:

| Code                     | Описание                     |
| ------------------------ | ---------------------------- |
| `FEED_NOT_FOUND`         | Feed отсутствует             |
| `SCHEMA_NOT_PUBLISHED`   | Нет активной схемы           |
| `INVALID_SCHEMA`         | Некорректная структура       |
| `UNKNOWN_FIELD`          | Несуществующий field_id      |
| `UNKNOWN_SOURCE_PATH`    | Неизвестный источник         |
| `SOURCE_TYPE_MISMATCH`   | Несовместимые типы           |
| `REQUIRED_VALUE_MISSING` | Отсутствует значение         |
| `MAX_LENGTH_EXCEEDED`    | Превышена длина              |
| `CURRENCY_MISMATCH`      | Валюта не совпадает с валютой поля |
| `BASE_PRICE_MISSING` | Нет исходной цены для наследуемого поля |
| `FX_RATE_MISSING` | Нет необходимого курса в snapshot |
| `TRANSLATION_MANUAL_REQUIRED` | Перевод нужно заполнить вручную |
| `PRICING_POLICY_NOT_FOUND` | Политика отсутствует или недоступна в tenant |
| `UNSUPPORTED_PRICING_RULE` | Правило не поддерживается текущим релизом |
| `VERSION_CONFLICT`       | Конкурентное изменение       |
| `SOURCE_UNAVAILABLE`     | Источник временно недоступен |

Использовать HTTP `404` для отсутствующих ресурсов, `409` для конфликтов версий и `422` для ошибок содержимого и конфигурации. Внутренние ошибки и недоступность зависимостей не следует маскировать под незаполненные поля товара.

### **12.6. API Pricing и контракт записи**

Настройки цены показываются в Feed UI, но операции принадлежат Pricing:

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| POST | /api/pricing/policies | Создание политики |
| GET | /api/pricing/policies | Список доступных политик |
| GET | /api/pricing/policies/{id} | Детали и активная версия |
| PUT | /api/pricing/policies/{id}/draft | Сохранение draft с expected_version |
| POST | /api/pricing/policies/{id}/publish | Публикация неизменяемой версии |
| POST | /api/pricing/policies/{id}/preview | Предпросмотр расчёта на snapshot входа без записи |

Приведённые маршруты — целевые контракты реализации, не заявление об уже
существующем API. Создание Feed принимает initial_locale/initial_currency для
стартовых полей и optional pricing_policy_id; общей валюты/локали вычислений нет.
PATCH различает отсутствующее поле и null через явный набор переданных полей.
PUT назначения политики с policy_id=null выбирает NO_ADJUSTMENT.

Записывающие запросы передают expected_version соответствующего агрегата/draft;
ответы возвращают новую версию. Удаление и отзыв без результата — HTTP 204 без
response body/schema; создание — 201, постановка генерации — 202.
Списки имеют серверную пагинацию и ограничения page size; preview — ограниченный limit.
Техническая недоступность зависимости возвращает отдельную 503-ошибку с безопасным
кодом, неожиданная внутренняя ошибка — 500. Не выдавать их за ошибку ввода 422.

Preview денежного поля дополнительно содержит Money source/override/resolved,
цель currency, policy_id/version, FX snapshot и price_trace с разрешёнными
составляющими расчёта. Amount остаётся строкой. can_override/can_reset/is_stale,
editor metadata и права возвращаются backend; UI не восстанавливает их догадками.

## **13. Frontend — Vue 3 + TypeScript**

Фронтенд должен строиться по согласованному интерактивному прототипу и включать создание Feed, конструктор схемы, список и редактор публикаций, экспорт и настройки ценообразования.

### **13.1. Экран создания Feed**

**Основные компоненты:**

```
FeedCreatePage
 ├── FeedGeneralForm
 │    ├── NameInput
 │    ├── CodeInput
 │    ├── InitialCurrencySelect
 │    └── InitialLocaleSelect
 ├── PricingPolicySelector
 ├── FeedFormatSelector
 │    ├── CsvOption
 │    └── XmlOption
 └── FeedCreateAction
```

Поведение:

- Пользователь вводит название и настройки.
- Backend создаёт Feed.
- Создаётся начальная draft-схема с тремя системными ролями.
- InitialLocale/InitialCurrency записываются в стартовые определения полей,
  а не становятся общими параметрами вычисления Feed.
- Политика выбирается явно; без неё отображается NO_ADJUSTMENT.
- Пользователь переходит к конструктору.
- Нельзя начать генерацию до публикации корректной схемы.

### **13.2. Конструктор схемы**

Это главный UI-компонент модуля.

Field Palette

String

Text

Money

Schema Canvas

Publication

Title

Description

Price

Inspector

Identity

Source

Constraints

Transforms

AI

Трёхпанельная структура редактора: библиотека блоков → дерево схемы → параметры выбранного поля.

Структура Vue-компонентов:

```
FeedSchemaBuilderPage
 ├── SchemaToolbar
 │    ├── DraftStatus
 │    ├── SaveDraftButton
 │    ├── PreviewButton
 │    └── PublishSchemaButton
 │
 ├── FieldPalette
 │    ├── FieldTypeCard
 │    └── FieldTypeDescription
 │
 ├── SchemaCanvas
 │    ├── RootObjectNode
 │    ├── SortableFieldList
 │    └── FieldNode
 │
 └── FieldInspector
      ├── IdentitySettings
      ├── SourceSettings
      ├── LocaleAndFallbackSettings
      ├── CurrencyAndPricingTrace
      ├── ConstraintSettings
      ├── TransformSettings
      └── AiSettings
```

**Drag-and-drop:**

- Перетаскивание типа из FieldPalette создаёт новый `FieldDefinition` с UUID.
- Перемещение поля в Canvas изменяет порядок в `FeedSchema.fields`.
- Выбор поля открывает Inspector.
- Переименование не изменяет `field_id`.
- Удаление поля без системной роли допускается; удаление системного запрещено.
- Переименование key сохраняет field_id и system_role.
- Для существующего поля locale/currency не меняются незаметно: создаётся новое
  поле или явно показывается необходимость отдельной миграции.
- Публикация схемы запускает полную проверку Backend.
- Изменения сохраняются в draft и не затрагивают активную схему.

Псевдокод состояния конструктора в отдельном draft-composable слоя model;
UI запрашивает эти действия через emits и не меняет полученные props напрямую:

```
interface FieldDefinition {
  id: string;
  key: string;
  label: string;
  value_type: "string" | "text" | "money";
  system_role: "TITLE" | "DESCRIPTION" | "PRICE" | null;
  locale: string | null;
  currency: string | null;
  fallback_policy: LocaleFallbackPolicy | null;
  source: SourceReference | null;
  default_mode: "INHERIT" | "MANUAL";
  constraints: FieldConstraints;
  transforms: TransformDefinition[];
  export: {
    enabled: boolean;
    name: string;
  };
  ai: {
    instruction: string | null;
  };
}

function onFieldDropped(
  type: FieldDefinition["value_type"],
  index: number
): void {
  const field = createDefaultFieldDefinition(type);

  schema.fields.splice(index, 0, field);
  selectedFieldId.value = field.id;
  draftDirty.value = true;
}

function onFieldMoved(
  sourceIndex: number,
  targetIndex: number
): void {
  moveArrayItem(schema.fields, sourceIndex, targetIndex);
  draftDirty.value = true;
}
```

Список доступных SourcePath и поддерживаемых transforms должен приходить с backend. Не нужно независимо поддерживать два перечня полей в Python и TypeScript.

### **13.3. Список публикаций**

Компоненты:

```
FeedPublicationsPage
 ├── PublicationStatistics
 ├── PublicationFilters
 │    ├── Search
 │    ├── ReadinessFilter
 │    └── StatusFilter
 ├── PublicationTable
 │    ├── ProductInfoCell
 │    ├── ResolvedTitleCell
 │    ├── ResolvedPriceCell
 │    ├── OverrideIndicator
 │    ├── ValidationStatusCell
 │    └── OpenPublicationAction
 └── AddCatalogItemsDialog
```

Таблица должна отображать:

| Поле      | Содержание                             |
| --------- | -------------------------------------- |
| Product   | Название Catalog, SKU                  |
| Title     | Значение поля системной роли TITLE с локалью |
| Price     | Значение роли PRICE с валютой; дополнительные поля по настройке |
| Overrides | Количество ручных значений             |
| Readiness | Готово / Заполнить / Ошибка / Устарело |
| Issues    | Краткое описание проблемы              |
| Updated   | Время расчёта проекции                 |

Нужна серверная пагинация, фильтрация и сортировка. Не загружать все публикации на frontend.

### **13.4. Редактор публикации**

```
FeedPublicationEditor
 ├── CatalogProductHeader
 ├── ReadinessSummary
 ├── DynamicPublicationForm
 │    └── DynamicFieldRenderer
 │         ├── SourceValuePreview
 │         ├── InheritanceModeSelector
 │         ├── ManualValueEditor
 │         ├── ResolvedValue
 │         └── ValidationIssues
 └── ExportPreviewPanel
      ├── CsvPreview
      └── XmlPreview
```

Основное поведение:

1. UI получает `PublicationPreviewDTO`.
2. Для каждого поля показывает исходное значение.
3. Пользователь выбирает режим наследования либо ручное значение.
4. При переключении на `MANUAL` значение подставляется в редактор как начальное, но сохраняется только после подтверждения изменения.
5. Backend сохраняет override.
6. UI повторно получает вычисленные значения.
7. Ошибки отображаются рядом с конкретным полем.
8. CSV/XML предпросмотр обновляется на основании серверного результата.

Логику вычисления цены и применения transforms нельзя дублировать во frontend. Для мгновенного UX допустима локальная предварительная проверка, но окончательный результат всегда возвращает backend.

### **13.5. Интерфейс экспорта**

```
FeedExportPage
 ├── ActiveGenerationSummary
 ├── FormatCards
 │    ├── CsvArtifactCard
 │    └── XmlArtifactCard
 ├── GenerateButton
 ├── GenerationProgress
 ├── GenerationHistory
 ├── GenerationIssues
 └── PublicAccessSettings
```

Пользователь должен видеть текущую активную генерацию, время её создания, количество выгруженных товаров, размер файлов и ошибки последнего запуска.

Если последняя генерация завершилась ошибкой, нужно явно показать, что публичная ссылка продолжает выдавать предыдущую успешную версию.

### **13.6. Ценообразование и настройки полей**

На уровне Feed — вкладка «Ценообразование»: выбранная PricePolicy и её версия,
источник базовой цены, процент наценки, Currency Provider, создание/публикация
политики через API Pricing и явное назначение Feed. Общая политика показывает,
что её изменение влияет на другие использующие её Feed/Channels.

В Inspector текстового поля: Language, Fallback, Source, Constraints, Transforms,
Export. В Inspector MONEY: Currency, Price Source, применяемая политика и trace,
Rounding, Constraints, Export. Ручная окончательная цена вводится в редакторе
конкретной публикации, а не в определении общего поля схемы.

В preview видны исходная цена, наценка, конвертация и итог, если позволяют права.
Пользователь видит actual locale при fallback и может независимо переопределить
каждый язык/валюту. AI-инструкции — только метаданные будущей функции; UI не
предлагает работающую генерацию, которой нет в MVP.

### **13.7. Структура frontend и владельцы состояния**

```text
frontends/apps/console/src/modules/feed-builder/
  api/<entity>.api.ts, <entity>.dto.ts, <entity>.mapper.ts
  model/<entity>.types.ts, <entity>.query-keys.ts
  model/queries/, mutations/, state/
  pages/
  ui/page/, results/, item/, forms/
  routes.ts, index.ts
```

Путь уточняется по соглашению именования Console при реализации. Модуль Pricing
имеет собственный публичный index.ts; FeedBuilder не импортирует его внутренние
API, query keys или stores. Переиспользуемый редактор/selector политики доступен
только через согласованный публичный контракт Pricing.

| Состояние | Владелец и поведение |
| --- | --- |
| Серверные Feed, schema, publications, generations | TanStack Vue Query; не копировать вторым кешем в Pinia |
| Доступные политики/метаданные | Queries соответствующего модуля, tenant-aware keys |
| Поиск/фильтры/сортировка/пагинация/вкладка | Page-state composable с URL/reload |
| Draft схемы и несохранённые overrides | Форма/оркестратор draft; refetch не стирает ввод |
| Диалоги и выбранное поле | Page или ближайший UI-владелец |
| Tenant/session | Существующие stores приложения |

После мутаций обновляются/инвалидируются затронутые detail/list/preview keys;
назначение политики обновляет Feed, проекции и preview, публикация схемы —
активную схему и списки публикаций, override — карточку и статистику готовности.
Сохранение draft очищает только отправленный snapshot: ввод, сделанный во время
запроса, сохраняется. Для сохранения используется expected_version, при 409
показывается конфликт с возможностью восстановить свой ввод.

Queries передают AbortSignal в общий HTTP client. При смене tenant/session
запросы отменяются, поздние ответы игнорируются, кеши и черновики старого контекста
очищаются. Polling активной генерации ограничен временем жизни страницы и
останавливается на SUCCEEDED/FAILED. Повторный submit блокируется на pending;
неоднозначный результат создания не повторяется автоматически с риском дубля.

Page собирает page state, queries/mutations, router и диалоги. UI-компоненты
получают типизированные props/emits и frontend-модели; не импортируют API/DTO,
query keys, router или session stores. Mapper чисто преобразует DTO и payload,
деньги остаются строками, any не заменяет конкретный контракт.

### **13.8. Состояния экрана и доступность**

Body выбирает loading/skeleton, empty, error/retry или results, сохраняя полезные
данные при background refetch. Форма показывает field/scenario errors и pending,
не разбирает Axios response. Результаты списков не выполняют HTTP и не управляют
навигацией: Footer связывает пагинацию с page state.

Использовать существующие semantic tokens, layouts, shadcn-vue primitives и
custom UI Console. Проверять labels, focus, keyboard navigation, disabled/error
состояния и мобильную адаптивность. Drag-and-drop имеет доступные действия
перемещения с клавиатуры. Закрытие/переход при несохранённом draft явно защищает ввод.

## **14. Безопасность и мультитенантность**

С учётом архитектуры CRM, где каждый tenant имеет собственную PostgreSQL schema, необходимо соблюдать несколько правил.

**Tenant isolation.** Таблицы `fb_*` создаются в схеме tenant. Обращение к репозиториям выполняется только через существующий механизм tenant-aware connection и Unit of Work.

**Public routing.** Публичный `public_id` резолвится через доверенный реестр, а не через произвольное имя SQL-схемы из URL.

**Authorization.** Административные запросы проверяют права на просмотр Feed, изменение схемы, редактирование публикаций, генерацию и управление ключами. Источники Catalog также должны проверять разрешённость чтения полей для данного контекста.

**Schema execution.** Пользовательский JSON не может содержать исполняемый Python, SQL, JavaScript или произвольный URL для получения данных. Все операции выполняются зарегистрированными обработчиками.

**Serialization.** CSV и XML получают только проверенные значения; XML-элементы безопасно экранируются, экспортные имена валидируются.

**Resource limits.** Необходимы ограничения на размер схемы, количество полей, глубину вложенности при будущем расширении, объём предпросмотра и число одновременных генераций.


Ценовая политика, PriceQuote, FX snapshots и batch-запросы также tenant-aware.
Нельзя назначить политику чужого tenant по UUID. Закупочные цены/trace защищаются
отдельным разрешением; UI не получает скрытые составляющие расчёта.

При отзыве public route/ключа доступ прекращается даже при наличии кешированного
артефакта. Токены исключаются из access/application logs и correlation payload.
Логи worker содержат tenant_id/feed_id/generation_id, попытку, длительность и
безопасный reason_code; Domain не логирует. Один технический сбой записывается
со stack trace на одной границе. committed — только после успешного внешнего UoW.

Наблюдаемость MVP: длительность/размер генерации, число товаров/ошибок, очередь,
lease expiry/retry, доля FAILED, возраст активного артефакта и STALE-проекций.
Ошибки валидации не считаются техническими ERROR автоматически.

## **15. Тестирование**

### **15.1. Domain Unit Tests**

| Объект                | Основные тесты                                        |
| --------------------- | ----------------------------------------------------- |
| `Feed`                | Создание, версии схемы, допустимые переходы           |
| `FeedSchema` | Уникальные ID/key, системные роли, типы, locale/currency/fallback |
| `FieldConstraints`    | Длина, обязательность, денежные диапазоны             |
| `FieldTransform`      | Trim, truncate, ceil step                             |
| `FeedPublication`     | Установка и сброс overrides                           |
| `FieldValueResolver`  | INHERIT, MANUAL, пустые и неправильные значения       |
| `PublicationResolver` | READY, NEEDS_INPUT, INVALID                           |
| `FeedGeneration`      | Переходы состояний и запрет повторной активации       |

### **15.2. Integration Tests**

Проверить работу PostgreSQL и SQLAlchemy:

- Сохранение и восстановление JSON-схемы без потери типов.
- Сохранение денежных значений без использования `float`.
- Уникальность публикации на Feed.
- Конкурентное сохранение draft.
- Конкурентное редактирование overrides.
- Атомарное переключение активной генерации.
- Корректное применение `schema_translate_map`.
- Изоляцию данных разных tenant.
- Идемпотентное создание публикаций.
- Восстановление задания после истечения lease.

### **15.3. Export Tests**

Обязательные сценарии:

| Сценарий                             | Результат                             |
| ------------------------------------ | ------------------------------------- |
| Название длиннее max_length поля (например 80) | `MAX_LENGTH_EXCEEDED` |
| Пустое обязательное описание         | `REQUIRED_VALUE_MISSING`              |
| Нет базовой цены наследуемого MONEY | `BASE_PRICE_MISSING`, INVALID |
| Цена в валюте, отличной от валюты поля | `CURRENCY_MISMATCH` |
| Цена 590.21, шаг 0.1                 | `590.30`                              |
| Строка с кавычками и запятыми        | Корректный CSV                        |
| Строка с `&` и XML-разметкой         | Корректное экранирование              |
| CSV содержит кириллицу               | Корректный UTF-8                      |
| Изменился source title               | Наследуемое значение обновляется      |
| Создан ручной override               | Catalog больше не определяет это поле |
| Удалён override                      | Значение вновь наследуется            |
| Изменён constraint                   | Публикация повторно валидируется      |
| Ошибка генерации                     | Предыдущие файлы остаются активными   |
| Старая генерация завершилась позднее | Не перезаписывает новую               |
| Публичный ключ отозван               | Доступ прекращается                   |

### **15.4. End-to-End Tests**

Сквозной тест должен проходить через API и реальную базу данных:

```
CreateFeed
    ↓
SaveFeedSchemaDraft
    ↓
PublishFeedSchema
    ↓
AddCatalogItemsToFeed
    ↓
PreviewFeedPublication
    ↓
SetPublicationOverride
    ↓
PreviewFeedPublication: повторная валидация
    ↓
RequestFeedGeneration
    ↓
ExecuteFeedGeneration
    ↓
DownloadCSV / DownloadXML
```

Отдельный E2E-тест должен проверять работу с двумя tenant, чтобы публикации, схемы и файлы одного tenant никогда не попадали в ответы другого.

### **15.5. Локализация, Pricing и согласованность**

| Сценарий | Ожидание |
| --- | --- |
| title_uk/title_ru с одним item.title | Разные значения по locale, без новых source paths |
| Нет обязательного перевода, NONE | REQUIRED_VALUE_MISSING, NEEDS_INPUT |
| Нет необязательного перевода, NONE | Допустимое отсутствие, без скрытой подстановки |
| LOCALE_CHAIN | Явный порядок, actual locale в trace |
| MANUAL_REQUIRED | Требуется ручной ввод при отсутствии целевого перевода |
| Override title_ru | title_uk продолжает наследоваться |
| Исходная цена 1000 UAH, +20%, FX=40 | 1200.00 UAH и 30.00 USD до иных transforms |
| Другой Feed +30% | 1300.00 UAH и 32.50 USD; Catalog не изменён |
| Несколько MONEY одной/разных валют | Основная наценка не дублируется, нет N+1 |
| Ручная price_usd=35.00 | Нет повторной наценки/конвертации; price_uah независима |
| Валидный override при отсутствии цены/курса | Ручное поле валидно, источник не блокирует его |
| Нет нужного курса без override | FX_RATE_MISSING, INVALID; нет устаревшей подстановки |
| Нет политики | Явный NO_ADJUSTMENT, базовая цена и нужная конвертация |
| Неизвестное или отложенное правило | Publish отклоняется, правило не игнорируется |
| FX обновился во время прохода | Все позиции используют исходный единый snapshot |
| Retry после частичного прохода | Тот же policy/FX контекст, новый staging попытки |
| Политика/настройки изменились во время генерации | Старый результат может SUCCEEDED, но не активируется |
| Более старая генерация завершилась позже новой | Active generation не откатывается назад |
| Потерян lease, старый worker продолжил | Fencing запрещает complete/activate старой попытке |
| Успешен один формат, второй упал | Оба публичных файла остаются предыдущей версии |
| Source/Pricing недоступен технически | Отдельный retryable сбой, не незаполненное поле |

Domain tests проверяют NONE/PERCENT, Decimal, положительный step,
совместимость валюты поля и системные роли без БД/HTTP. Будущие FIXED_AMOUNT,
TARGET_MARGIN и currency_rules получают отдельные тесты при реализации.
Integration tests проверяют версионирование политики, snapshot persistence,
защищённую от гонки активацию, инвалидацию проекций и общий UoW/Outbox.

### **15.6. Frontend и эксплуатационные проверки**

Проверить создание шаблона, конструктор, независимые языки/валюты, выбор/создание
политики, override/reset, preview и экспорт. В браузере пройти loading/empty/error,
retry/pending, конфликт версий, мобильный viewport, keyboard navigation,
URL/reload и сохранность ввода при refetch/сохранении. Проверить смену tenant,
отмену запросов и отсутствие поздних ответов старого контекста.

Из frontends выполнить lint:console, typecheck:console, build:console и применимые
тесты сценариев. Backend — применимые Domain/Integration/E2E и статические
проверки проекта. Нагрузочно проверить большой Catalog, batch/keyset, streaming,
ограничение памяти, lease/heartbeat, staging cleanup и повторные задания.

Полный E2E дополнительно включает PricePolicy +20%, title_uk/title_ru,
price_uah/price_usd, override одной валюты, смену политики, повторную генерацию
и сохранение прежней выдачи при ошибке. Отдельный тест с двумя tenant охватывает
также политику, quote, FX и публичную маршрутизацию.

Для изменения только документации проверяются внутренние ссылки, JSON/Python
примеры, согласованность требований и весь diff; сборка и UI-тесты не требуются.

## **16. Последовательные срезы реализации**

Реализовать восемь срезов. Каждый включает необходимые изменения во всех
затронутых слоях и проверяемый результат. Pricing добавлен отдельным срезом,
Stabilization сохранён. Сначала экспортируются универсальные CSV/XML.

### **16.1. Domain Foundation**

Feed, FeedSchema, FieldDefinition с system_role/locale/currency/fallback,
constraints/transforms, FeedPublication, FeedGeneration, PricePolicy, MoneyVO,
ошибки и события. Зафиксировать контракты override, PriceQuote, FX snapshots,
версий конфигурации и источников. Domain tests не требуют PostgreSQL/FastAPI.

Готовность: инварианты и чистая арифметика проверены; нет привязки языка/валюты
ко всему Feed; сохранена расширяемость схемы и Pricing.

### **16.2. Persistence Foundation**

Tenant-миграции Alembic, SQLAlchemy Models, create/restore mappers, write/query
repositories, UoW integration, public route registry, policy versions и draft.
Уникальные ограничения/индексы, NULLS NOT DISTINCT, optimistic locking и Outbox.

Готовность: JSON/Decimal/VO сохраняются и восстанавливаются без потерь;
транзакции и tenant isolation подтверждены интеграционно.

### **16.3. Feed CRUD + Schema Builder**

Создание Feed со стартовым шаблоном, draft/save/publish, реестры типов/источников/
transforms, проверка locale/currency через reference_data. REST-контракты,
страница создания и трёхпанельный конструктор; независимые настройки полей.

Готовность: пользователь собирает и публикует схему с несколькими языками/валютами;
несохранённый ввод и конкурентное редактирование обработаны.

### **16.4. Pricing Engine**

Создание/чтение/редактирование draft/publish PricePolicy, NONE/PERCENT, источник базовой цены, FX Provider,
PriceCalculationPort, batch quotes, единый snapshot, расчёт trace, назначение Feed,
версионирование и вкладка ценообразования. Future rules отклоняются явно.

Готовность: один товар имеет разные цены в разных Feed и валютах; наценка не
дублируется; версия политики/курсов воспроизводима. Общий контракт пригоден Channels.

### **16.5. Publication + Value Resolution**

Привязка Catalog Items, CatalogProductReader с набором локалей, source resolvers,
FieldValueResolver/PublicationResolver, overrides/reset, статусы/readiness,
материализованные проекции и инвалидация policy/FX. Список публикаций и редактор.

Готовность: preview показывает языки, происхождение, PriceQuote и ошибки;
ручная цена окончательна, остальные поля продолжают наследоваться.

### **16.6. Export Engine**

ExportRecord, Generic FormatProfiles, CSV/XML serializers, ArtifactStorage,
GenerationWorker, lease/fencing/retry, staging, snapshots, история и issues,
условная активация по схеме/конфигурации/политике/sequence.

Готовность: CSV и XML формируются из одного staging, точно сохраняют языки/валюты,
устаревшая/неуспешная генерация не портит активную выдачу.

### **16.7. Public Distribution**

Доверенный public registry, AccessKey lifecycle, отдельный публичный контроллер,
ETag/Last-Modified, streaming без открытой tenant-транзакции, ротация/отзыв,
завершение экрана экспорта и истории.

Готовность: внешняя система получает оба формата по постоянным ссылкам;
отозванный ключ не работает, данные tenant изолированы.

### **16.8. Stabilization**

Интеграционные/E2E/нагрузочные/security-проверки, конкурентные изменения,
восстановление lease, fencing, batch/query count, большие каталоги, cleanup,
ошибки storage/provider, UX loading/empty/error, доступность и мобильный экран.
Проверить весь diff по архитектурному перечню, завершить observability.

Готовность: все критерии приёмки и обязательные проверки пройдены;
известных нарушений слоёв, контрактов и tenant isolation нет.

## **17. Что заложить сейчас для дальнейшего расширения**

| Возможность после MVP | Подготовленный механизм |
| --- | --- |
| Категории Feed | reference field type и отдельный контракт категорий |
| Характеристики | Новые SourcePath и FieldType handlers |
| Вложенные объекты/массивы | kind, children, item_schema |
| Изображения | array + media и storage-порты |
| Варианты товаров | catalog_variant_id и расширение идентичности публикации |
| AI-переводы/контент | ai_instruction, field.locale, отдельный GenerateSuggestion Use Case |
| Динамический ассортимент | FeedSelectionPolicy и Selection Engine |
| Расписание генераций | Планировщик, создающий обычный Generation Request |
| Prom/Rozetka | Platform-specific FormatProfile и Serializer по актуальным контрактам |
| Bulk overrides | Отдельный Application Service с optimistic locking |
| FIXED_AMOUNT / TARGET_MARGIN | Версионируемые MarkupRule с явными валютой/себестоимостью |
| Категории/SKU/поставщики | Правила специфичности и явные приоритеты |
| Дополнительные валютные надбавки | CurrencyPriceRule, extra_markup и REPLACE_DEFAULT |
| Налоги/скидки/комиссии | Явная политика порядка расчёта Pricing |
| Строгий общий snapshot | Согласованные snapshots Catalog/публикаций/источников |
| Миграция смысла поля | Отдельная операция переноса override/системной роли с проверками |

Мультиязычные поля, валютная конвертация и базовая наценка уже входят в MVP,
поэтому не должны оставаться в перечне исключительно будущих возможностей.
FeedSchema и FeedPublication остаются разными моделями; PricePolicy не смешивается
с formatting/constraints. Это сохраняет развитие без копий Catalog и новых SQL-колонок
на каждый язык, валюту или пользовательское поле.

## **18. Критерии завершения MVP**

1. Пользователь создаёт Feed и выбирает язык/валюту стартовых полей.
2. Получает draft с обязательными ролями TITLE, DESCRIPTION, PRICE.
3. Переименовывает ключи в title_uk/description_uk/price_uah, не теряя field_id/роли.
4. Добавляет title_ru, description_ru и price_usd с независимыми настройками.
5. Меняет порядок, source paths, ограничения, transforms и экспортные имена.
6. Для текстовых полей выбирает locale и явный fallback; для MONEY — currency.
7. Создаёт/публикует PricePolicy +20%, назначает Feed; другой Feed использует +30%.
8. Публикует валидную версию схемы и добавляет простые товары Catalog без дублей.
9. Видит унаследованные переводы и рассчитанные цены в разных валютах.
10. Для длинного title получает constraint error; для отсутствующего обязательного
    перевода — NEEDS_INPUT; для отсутствующей исходной цены/курса — INVALID.
11. Переопределяет title_ru и price_usd; title_uk и price_uah продолжают наследоваться.
12. Preview показывает source/manual/resolved, локаль, валюту, разрешённый price trace,
    версию политики и snapshot курсов. Ручная цена не получает повторную наценку.
13. Reset удаляет override и возвращает наследование; права и версии проверяются backend.
14. После устранения проблем все ENABLED-публикации READY, генерация создаёт CSV/XML
    из одного staging и зафиксированного ценового контекста.
15. Оба файла атомарно становятся доступны по постоянным HTTPS URL с кеш-заголовками.
16. Изменения Catalog/PricePolicy/FX делают зависимые проекции устаревшими;
    следующий resolve применяет актуальный контекст.
17. Ошибочная генерация сохраняет предыдущую выдачу; старый worker/контекст
    не перезаписывает более новый активный результат.
18. Retry/lease/fencing восстанавливают задания без дублирующих активных артефактов.
19. Отзыв/ротация ключа прекращают доступ старого ключа; tenant и права защищают
    схемы, публикации, Pricing, snapshots и публичные файлы.
20. Проверены API, БД, UI, E2E, нагрузка и архитектурный перечень; stabilization завершён.

**Итоговый поток:**

```text
Catalog + PricePolicy + FX snapshot
  → FeedSchema + FeedPublication overrides
  → ResolvedPublication
  → FormatProfile + ExportRecord staging
  → FeedGeneration
  → CSV / XML Artifacts
  → атомарная активная выдача
```

Catalog хранит исходные данные; Pricing рассчитывает коммерческие цены;
FeedBuilder управляет схемой и публикациями; Domain защищает инварианты;
Application координирует порты; Infrastructure хранит, сериализует и доставляет;
Presentation предоставляет API и универсальный конструктор. Язык и валюта
принадлежат полю, а ценовая политика — отдельному версионируемому контексту Pricing.
