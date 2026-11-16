# **FeedBuilder — финальный технический план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript\
**Хранение схем:** JSONB с версионированием\
**Экспорт:** CSV, XML

## **1. Цель и границы модуля**

`FeedBuilder` — самостоятельный bounded context, отвечающий за создание пользовательских прайс-листов на основании данных Catalog.

Пользователь должен иметь возможность:

1. Создать `Feed` с названием, схемой и собственной ценовой политикой. Языки и валюты задаются независимо для каждого поля.
2. Через визуальный drag-and-drop конструктор определить структуру публикации.
3. Добавить типизированные поля, указать для них источники, ограничения и преобразования.
4. Привязать товары Catalog к Feed.
5. Автоматически наследовать значения из Catalog либо задавать индивидуальные значения через override.
6. Просматривать готовность публикаций, ошибки и предупреждения.
7. Получать предварительный просмотр отдельной публикации.
8. Генерировать CSV и XML с постоянными ссылками для внешних систем.

### **1.1. Функциональные границы MVP**

В первом релизе поддерживаются три базовых типа полей.

| Field Type | Python    | Применение      |
| ---------- | --------- | --------------- |
| `STRING`   | `str`     | Название товара |
| `TEXT`     | `str`     | Описание        |
| `MONEY`    | `ExportMoneyVO` | Точная сумма с валютой |

Начальная схема автоматически содержит три обязательных поля:

- `title: STRING`
- `description: TEXT`
- `price: MONEY`

В редакторе можно менять порядок полей, названия, настройки, источники, constraints и transforms. Допускается добавление полей тех же трёх типов с собственной обязательностью, в том числе нескольких переводов и цен в разных валютах. Таким образом, движок сразу будет работать с динамическим списком полей, а не с жёстко заданными колонками.

В рамках MVP обязательные системные ключи `title`, `description`, `price` нельзя удалить или изменить на несовместимый тип. Остальные поля можно добавлять и удалять.

В первом релизе не реализуем варианты товаров, категории, изображения, характеристики, AI-генерацию, динамический подбор ассортимента и специализированные контракты Prom/Rozetka.

В MVP входят независимые locale/currency полей, версионируемая `PricePolicy`, наценка `PERCENT`, выбор базовой цены Catalog, конвертация через публичный Currency Port, overrides каждой валюты и перевода, snapshot политики и курсов. `NO_ADJUSTMENT` — явный режим без наценки. Отсутствие PricePolicy не запрещает конвертацию.

Источники остатков подключаются отдельным интеграционным срезом после появления доступных Application-контрактов Inventory/3PL/Supplier Sourcing. Уже в модели Feed предусмотрены именованные availability bindings и ссылки на версии политик. До регистрации соответствующего адаптера UI не предлагает такие поля; отсутствие источника нельзя подменять нулём или фиктивным складом.

Структура схемы, идентификаторы полей и границы агрегатов проектируются универсальными.

### **1.2. Bounded Context**

**CATALOG**

Product · Content · Price · Source revisions

## **FEED BUILDER**

**Feed**

Settings, Schema, Versions

**Publication**

Catalog reference, Overrides

**Projection**

Resolved values, Validation

**Generation**

Export, Artifacts, Issues

**CSV**

**XML**

Channels остаётся независимым модулем. FeedBuilder не создаёт внешние товары через API и не получает заказы.

**Принцип границ:** Catalog является источником исходных значений, FeedBuilder создаёт проекции и артефакты. Ни один Use Case FeedBuilder не изменяет Catalog.

Связь с Catalog реализуется через Application Port, а не через прямое использование его SQLAlchemy ORM-моделей.

| Контекст | Ответственность |
| --- | --- |
| Catalog | Локализованные title/body, базовые цены, идентичность товара |
| Pricing | PricePolicy, выбор базы, коммерческая наценка и PriceQuote |
| Currency | Версионируемые курсы, FxRateSnapshot и конвертация |
| Inventory | Физические остатки, резервы и доступное количество по складам/владельцу |
| Внешние источники / Supplier Sourcing | Доступность 3PL и поставщиков с датой наблюдения и точностью |
| Availability | Политика выбора/объединения источников и AvailabilityQuote через публичный порт |
| FeedBuilder | Схема, языки/валюты полей, ссылки на политики, overrides, проверка и файлы |

`Availability` обозначает публичный контракт расчёта доступности; его размещение согласуется с владельцами источников. FeedBuilder не становится складским учётом. Channels при последующей API-синхронизации использует ту же PricePolicy и согласованную политику доступности.

## **2. Основные архитектурные решения**

До реализации необходимо зафиксировать следующие решения.

| Вопрос                               | Принятое решение                           |
| ------------------------------------ | ------------------------------------------ |
| Кому принадлежит публикация?         | Конкретному Feed                           |
| Как хранится схема?                  | Типизированный JSON-документ в JSONB       |
| Где хранятся значения?               | В Catalog либо в overrides публикации      |
| Как идентифицируется поле?           | Стабильный UUID `field_id`                 |
| Что является конечным значением?     | Результат FieldValueResolver               |
| Где хранится результат вычисления?   | В materialized read model                  |
| CSV/XML имеют разные схемы?          | Нет, одна схема и разные сериализаторы     |
| Как изменяется схема?                | Draft → Validate → Publish                 |
| Как формируются файлы?               | Асинхронная генерация через worker         |
| Что происходит при ошибке генерации? | Предыдущие файлы остаются активными        |
| Где хранятся файлы?                  | В ArtifactStorage, в SQL только метаданные |

### **2.1. Языки, валюты и политики**

- `Feed` не имеет обязательного единственного языка или валюты.
- `FieldDefinition.locale` задаёт язык локализованного текста; нелокализованный текст может иметь locale=null.
- `FieldDefinition.currency` обязательно для MONEY; для остальных типов currency=null.
- `default_locale`/`default_currency` у Feed — необязательные подсказки создания полей. После создания поле хранит явное значение; смена defaults не меняет расчёт существующих полей.
- Один Feed содержит, например, title_uk/title_ru и price_uah/price_usd/price_eur. Каждое поле имеет собственные ID, constraints, transforms и override.
- `pricing_policy_id` — логическая ссылка на Pricing. Наценка не копируется в каждое поле.
- `availability_bindings` связывает ключи default/kyiv/supplier с политиками доступности; поле выбирает binding явно.
- Выбранные языки и валюты проверяются через Reference Data. Списки не зашиваются в enum UAH/USD/EUR или uk/ru.

### **2.2. Три принципиально разных типа данных**

**Definition**

Описание поля: тип, источник, constraints, transforms и экспортный ключ. Одинаково для всех публикаций внутри версии FeedSchema.

**Override**

Индивидуальное значение поля конкретной FeedPublication. Не копирует остальные данные Catalog.

**Resolved Value**

Вычисленный результат после наследования, преобразования и валидации. Используется для предпросмотра и экспорта.

Это разделение должно сохраняться на всех уровнях — Domain, Application, Infrastructure и Presentation.

## **3. Domain Layer**

### **3.1. Агрегаты**

В MVP предлагаю три Aggregate Root.

| Aggregate Root    | Управляет                               | Инварианты                                               |
| ----------------- | --------------------------------------- | -------------------------------------------------------- |
| `Feed`            | Настройки, редактируемая схема, версия  | Уникальность полей, валидная структура                   |
| `FeedPublication` | Связь с товаром, overrides, участие     | Один товар на Feed, корректные режимы override           |
| `FeedGeneration`  | Выполнение генерации, статус, артефакты | Допустимые переходы состояний, неизменяемость результата |

`FeedSchema`, `FieldDefinition`, `FieldConstraint`, `FieldTransform` — Value Objects либо дочерние объекты агрегата `Feed`.

`FeedPublicationProjection` — read model, а не Aggregate Root.

`FeedArtifact` и `GenerationIssue` — объекты результата генерации.

### **3.2. Aggregate Feed**

```python
class Feed:
    id: FeedId
    name: str
    code: FeedCodeVO
    default_locale: LocaleCodeVO | None
    default_currency: CurrencyCodeVO | None
    pricing_policy_id: UUID | None
    availability_bindings: tuple[AvailabilityBinding, ...]
    status: FeedStatus
    active_schema_version: int | None
    draft_schema: FeedSchema | None
    latest_generation_sequence: int
    active_generation_id: UUID | None
    input_revision: int
    version: int

    # create/restore, replace_draft_schema, publish_schema,
    # change_pricing_policy, replace_availability_bindings,
    # request_generation, activate_generation — доменные методы.
```

`AvailabilityBinding` — immutable VO: key, policy_id и policy_version. Это ссылка на внешний контракт, а не коллекция складских остатков внутри Feed. Агрегаты других контекстов в Feed не передаются.

Основные инварианты:

- У Feed не может быть двух активных версий схемы.
- Опубликованная версия схемы неизменяема.
- Активная схема обязательно содержит три основных поля.
- Все `field_id` и `key` внутри схемы уникальны.
- Нельзя генерировать файл без опубликованной схемы.
- Более старая генерация не должна перезаписывать результат более новой.
- Изменение locale/currency существующего поля требует новой версии схемы и перепроверки overrides; ручная сумма не получает другой код валюты автоматически.
- Изменение schema, привязки PricePolicy, availability bindings, состава/статусов публикаций или overrides увеличивает input_revision. Изменение имени или UI-defaults само по себе не меняет входы экспорта.
- Чужая/устаревшая generation не активируется: проверяются schema_version, input_revision, policy versions, request_sequence и lifecycle Feed.
- Смена активной версии внешней политики помечает projections устаревшими; worker фиксирует версии в execution manifest и проверяет их актуальность перед активацией.

### **3.3. FeedSchema и FieldDefinition**

```python
@dataclass(frozen=True, slots=True)
class FieldDefinition:
    id: UUID
    key: str
    label: str
    value_type: FieldValueType
    locale: LocaleCodeVO | None
    currency: CurrencyCodeVO | None
    fallback_policy: LocaleFallbackPolicy
    source: SourceReference | None
    default_mode: ValueMode
    constraints: FieldConstraints
    transforms: tuple[TransformDefinition, ...]
    export: FieldExportSettings
    ai_instruction: str | None

@dataclass(frozen=True, slots=True)
class SourceReference:
    provider: str
    path: str
    binding: str | None = None
```

`FeedSchema` содержит immutable упорядоченный tuple полей, schema_format_version, get_field(), used_locales(), used_currencies() и проверку структуры. Локаль не кодируется внутри source path: item.title + locale=uk и тот же путь + locale=ru.

Для локализованного источника locale обязателен. По умолчанию fallback=NONE: отсутствие перевода не включает другой язык. Явная LOCALE_CHAIN проверяет перечисленные локали по порядку, без циклов и дублей; MANUAL_REQUIRED требует ручного значения при отсутствии перевода. Происхождение содержит requested_locale и resolved_locale. Необязательное поле без перевода остаётся пустым; required получает REQUIRED_VALUE_MISSING.

Модель использует типизированные VO; __post_init__ разрешён только для VO. Для Aggregate/Entity обязательны create/restore и domain-методы.

Для будущей поддержки вложенных объектов можно расширить модель свойствами `kind`, `children` и `item_schema`. В MVP все редактируемые поля являются scalar-полями внутри одного корневого объекта `publication`.

Не рекомендую сразу вводить универсальные Python-классы для каждого возможного вложенного объекта. Лучше начать с типизированного дерева определений.

### **3.4. Constraints**

```
@dataclass(frozen=True)class FieldConstraints:    required: bool = False    min_length: int | None = None    max_length: int | None = None    min_amount: Decimal | None = None    max_amount: Decimal | None = None
```

Ограничения по типам:

| Constraint   | STRING | TEXT | MONEY |
| ------------ | ------ | ---- | ----- |
| `required`   | Да     | Да   | Да    |
| `min_length` | Да     | Да   | Нет   |
| `max_length` | Да     | Да   | Нет   |
| `min_amount` | Нет    | Нет  | Да    |
| `max_amount` | Нет    | Нет  | Да    |

Constraints проверяют результат, но не изменяют его.

### **3.5. Transforms**

```
@dataclass(frozen=True)class TransformDefinition:    operation: str    parameters: dict[str, JsonValue]
```

Первоначальный реестр:

| Operation         | Назначение                    |
| ----------------- | ----------------------------- |
| `string.trim`     | Удалить крайние пробелы       |
| `string.truncate` | Ограничить длину              |
| `money.ceil_step` | Округлить сумму вверх с шагом |

Порядок операций определяется порядком элементов массива `transforms`.

Для MONEY используется точный `ExportMoneyVO(amount: Decimal, currency)`, до шести дробных знаков, без неявного округления. Общий MoneyVO проекта округляет до четырёх знаков и не подходит для промежуточных расчётов экспорта. Изменять его глобальную семантику ради FeedBuilder не требуется. JSON передаёт суммы строками; арифметика не зависит от внешнего Decimal context.

Наценка и конвертация выполняются Pricing/Currency до field transforms. `money.ceil_step` только округляет сумму в валюте конкретного поля; target_currency берётся из FieldDefinition.currency. Несовпадение валюты готового quote или ручного override с валютой поля — CURRENCY_MISMATCH. Ручная цена не конвертируется и не получает наценку автоматически.

### **3.6. Aggregate FeedPublication**

```
class FeedPublication(AggregateRoot):    id: FeedPublicationId    feed_id: FeedId    catalog_item_id: UUID    catalog_variant_id: UUID | None    status: PublicationStatus    overrides: dict[UUID, FieldOverride]    version: int    def set_override(        self,        field_id: UUID,        value: JsonValue,    ) -> None:        self.overrides[field_id] = FieldOverride(            mode=ValueMode.MANUAL,            value=value,        )    def reset_override(        self,        field_id: UUID,    ) -> None:        self.overrides.pop(field_id, None)    def enable(self) -> None:        ...    def pause(self) -> None:        ...
```

Модель связывает Feed с Catalog Item. Для простого товара `catalog_variant_id = None`.

В MVP применяется следующее правило: если у поля есть Source, его значение по умолчанию наследуется. Ручное значение создаёт override. Если Source отсутствует, поле требует ручного заполнения при `required=true`.

Отсутствующий override не означает, что в публикации хранится копия исходного значения.

### **3.7. Состояния публикаций**

Нужно разделить пользовательское состояние и вычисленную готовность.

**PublicationStatus:**

```
DRAFT
ENABLED
PAUSED
ARCHIVED
```

**PublicationReadiness:**

```
READY
NEEDS_INPUT
INVALID
STALE
```

Например, публикация может иметь `status=ENABLED` и `readiness=INVALID`. Это означает, что пользователь включил её в состав фида, но генерация выявила ошибки.

В первом MVP включённые публикации с ошибками блокируют успешную генерацию всего файла. Умышленно исключать их без уведомления нельзя.

### **3.8. Aggregate FeedGeneration**

```
class FeedGeneration(AggregateRoot):    id: FeedGenerationId    feed_id: FeedId    schema_version: int    request_sequence: int    status: GenerationStatus    total_items: int    exported_items: int    rejected_items: int    artifacts: tuple[FeedArtifact, ...]    def start(self) -> None:        ...    def complete(        self,        artifacts: tuple[FeedArtifact, ...],        counts: GenerationCounts,    ) -> None:        ...    def fail(self, reason: GenerationFailure) -> None:        ...
```

Жизненный цикл:

PENDING

RUNNING

SUCCEEDED

FAILED

Generation фиксирует feed input_revision, schema_version, PricePolicy ID/version или явный NO_ADJUSTMENT, FxRateSnapshot, availability binding/policy versions, source fingerprints и as_of. Большие source snapshots и ExportRecord хранятся в staging; в агрегате остаётся manifest/reference.

Успешное завершение генерации и её активация — разные действия. Генерация может закончиться успешно, но не стать активной, например если пользователь уже изменил схему.

### **3.9. PricePolicy и расчёт цены**

PricePolicy — самостоятельный версионируемый Aggregate Root контекста Pricing. Feed хранит только policy_id. В минимальном Pricing реализуются source базовой цены, правило NONE/PERCENT, immutable версии и PriceCalculator; не создавать временный второй движок наценок внутри FeedBuilder.

| Параметр | Правило |
| --- | --- |
| base_price_source | Catalog regular/current price; выбран явно |
| default_rule | NO_ADJUSTMENT либо PERCENT; percent передаётся десятичной строкой, 20 означает 20% |
| currency_rules | Явные дополнительные корректировки после конвертации; не замена default_rule |
| version | Неизменяемая опубликованная версия, общая политика может обслуживать несколько Feed |

Начальная реализация: P = B × (1 + percent / 100), percent >= 0. Дополнительная процентная корректировка поддерживает ту же семантику и может отсутствовать. Для разных Feed выбираются разные политики: +20%, +30%, +5%. Без политики действует явный NO_ADJUSTMENT. Настройки меняются через Application Pricing; FeedBuilder не импортирует и не изменяет его агрегат.

Последовательность расчёта:

1. Получить B и его currency из выбранного источника.
2. Применить основную наценку один раз на товар и версию политики.
3. Преобразовать результат во все валюты, требуемые наследуемыми MONEY-полями.
4. Применить явно заданную дополнительную корректировку соответствующей валюты.
5. Для MANUAL заменить quote окончательным значением override без новой наценки/FX.
6. Применить transforms конкретного поля, затем constraints и сериализацию.

Для условного курса 40 UAH за USD база 1000 UAH с +20% даёт 1200 UAH/30 USD, с +30% — 1300 UAH/32.50 USD. Это пример арифметики, не текущий валютный курс. Несколько полей USD получают один quote и независимо округляют его; базовая наценка повторно не применяется.

PriceQuote содержит amount/currency, base price snapshot, policy ID/version, FX snapshot и trace валютной корректировки. FxRateSnapshot фиксирует направление from/to, множитель (target amount = source amount × rate), источник, effective_at, obtained_at и срок допустимости. Совпадающие валюты используют identity conversion без внешнего курса. Отсутствующий/просроченный курс — FX_RATE_MISSING; отсутствующая база — BASE_PRICE_MISSING, без условных значений и скрытого fallback.

FIXED_AMOUNT (B+A с явной currency A), TARGET_MARGIN (C/(1-m), 0<=m<1 и обязательная себестоимость C), комиссии, налоги и category/SKU приоритеты — следующие срезы. Наценка и целевая валовая маржа имеют разные типы; их нельзя заменять одной формулой.

### **3.10. Источники остатков и AvailabilityPolicy**

У каждого Feed собственные именованные bindings, например default, kyiv и supplier. Поле с source.provider=availability, path=status или quantity указывает binding. Binding ссылается на конкретную версию AvailabilityPolicy; изменение источников не требует замены всех полей.

AvailabilityPolicy определяет разрешённые собственные склады, 3PL или SupplierSource, приоритеты, freshness/TTL, учёт резервов/буфера и strategy. Физический warehouse, внешний 3PL и dropshipping не превращаются в один SQL StockBalance. Поставщик со статусом наличия не является фиктивным Warehouse.

| Strategy | Семантика |
| --- | --- |
| PRIORITY | Выбрать первый допустимый свежий источник; возвращаем количество только выбранного источника |
| SUM_EXACT | Суммировать только точные, совместимые и независимые остатки; STATUS_ONLY не включается и отмечается в trace |
| ANY_AVAILABLE | Рассчитать возможность продажи; агрегированное количество не обещается |

AvailabilityQuote содержит status=IN_STOCK/OUT_OF_STOCK/UNKNOWN, quantity nullable, quantity_mode=EXACT/STATUS_ONLY/UNKNOWN, unit, source refs, policy version, observed_at, valid_until и fingerprint. quantity=null не равно 0; статус IN_STOCK без количества не превращается в 1/9999. Просроченный/недоступный источник не равен OUT_OF_STOCK.

При SUM_EXACT количество полного выбранного набора остаётся null, если в наборе есть непросуммированный STATUS_ONLY или unknown источник; при необходимости отдельный диагностический known_exact_total показывает известную часть. Требующее точного количества поле получает EXACT_QUANTITY_UNAVAILABLE. Политика может заранее ограничить набор только EXACT-источниками.

Inventory/внешний адаптер отвечает за доступный для продажи остаток с резервами и буфером. FeedBuilder не вычитает их повторно. Перед суммированием проверяются единицы, права владельца, physical_stock_identity и отсутствие зеркал одного склада через 3PL. Бэкордеры и неизвестная свежесть требуют явной политики; произвольное количество не создаётся.

Эта конфигурация описывает доступность для экспорта, не резервирует товар и не выбирает фактический источник исполнения заказа. Ценовая и availability policies независимы: automatic выбор самой дешёвой цены и самого большого остатка разных поставщиков не создаёт согласованное предложение. Для такого сценария нужен общий offer/source binding и отдельный контракт Sourcing/Fulfillment.

## **4. Формат типизированной схемы**

Схема должна быть декларативной. В БД хранятся определения и параметры, а исполнение обеспечивается зарегистрированными обработчиками Python.

### **4.1. Пример JSON-документа**

```

{
  "schema_format_version": 1,
  "root": {
    "key": "publication",
    "kind": "object",
    "fields": [
      {
        "id": "11111111-1111-4111-8111-111111111111",
        "key": "title",
        "locale": "uk",
        "currency": null,
        "fallback_policy": {"mode": "NONE"},
        "label": "Название",
        "value_type": "string",
        "source": {
          "provider": "catalog",
          "path": "item.title"
        },
        "default_mode": "INHERIT",
        "constraints": {
          "required": true,
          "max_length": 80
        },
        "transforms": [
          {
            "op": "string.trim",
            "params": {}
          }
        ],
        "export": {
          "enabled": true,
          "name": "title"
        },
        "ai": {
          "instruction": null
        }
      },
      {
        "id": "22222222-2222-4222-8222-222222222222",
        "key": "description",
        "locale": "uk",
        "currency": null,
        "fallback_policy": {"mode": "NONE"},
        "label": "Описание",
        "value_type": "text",
        "source": {
          "provider": "catalog",
          "path": "item.description"
        },
        "default_mode": "INHERIT",
        "constraints": {
          "required": true,
          "max_length": 5000
        },
        "transforms": [],
        "export": {
          "enabled": true,
          "name": "description"
        },
        "ai": {
          "instruction": null
        }
      },
      {
        "id": "33333333-3333-4333-8333-333333333333",
        "key": "price",
        "locale": null,
        "currency": "UAH",
        "label": "Цена",
        "value_type": "money",
        "source": {
          "provider": "pricing",
          "path": "final_price"
        },
        "default_mode": "INHERIT",
        "constraints": {
          "required": true,
          "min_amount": "0.01"
        },
        "transforms": [
          {
            "op": "money.ceil_step",
            "params": {
              "step": "0.1"
            }
          }
        ],
        "export": {
          "enabled": true,
          "name": "price"
        },
        "ai": {
          "instruction": null
        }
      }
    ]
  }
}

```

### **4.2. Семантика свойств**

| Свойство         | Описание                                 |
| ---------------- | ---------------------------------------- |
| `id`             | Стабильный UUID поля                     |
| `key`            | Внутренний системный ключ                |
| `label`          | Отображаемое пользователю название       |
| `value_type`     | Зарегистрированный тип                   |
| `locale` | Язык конкретного текстового поля |
| `currency` | Целевая валюта конкретного MONEY-поля |
| `fallback_policy` | Явное поведение при отсутствии перевода |
| `source.binding` | Ключ именованной политики доступности |
| `source`         | Ссылка на источник данных                |
| `default_mode`   | Поведение без пользовательского override |
| `constraints`    | Правила проверки итогового значения      |
| `transforms`     | Упорядоченные преобразования             |
| `export.name`    | Имя колонки CSV или элемента XML         |
| `export.scale` | Явная точность сериализации MONEY (стартовое значение 2), без скрытого округления |
| `ai.instruction` | Метаданные для будущего AI-агента        |

`field_id` нельзя изменять при простом переименовании поля.

`key` используется для внутреннего обращения к полю, а `export.name` — для итогового файла. Например, внутренний `title` может экспортироваться в `name_ua`.

### **4.3. Валидация схемы**

При сохранении черновика проверяется синтаксическая корректность. При публикации выполняется полная семантическая валидация:

- Уникальность `field_id`, `key`, экспортных имён.
- Совместимость поля с Source, наличием locale/currency и объявленной capability источника.
- MONEY требует currency и не принимает locale; текст не принимает currency.
- Локализованный Source требует locale, fallback-цепочки явно валидируются.
- Source availability требует существующий binding. При недоступном адаптере поле нельзя опубликовать.
- Совместимость constraints с типом.
- Поддержка указанных transforms.
- Наличие обязательных полей и корректность их типов.
- Допустимость имён XML-элементов.
- Ограничение числа полей и размеров JSON-документа; стартовые лимиты — 50 полей, 1 MiB schema, batch до 100 товаров, 10000 включённых публикаций на Feed; лимиты конфигурируются.

Для XML в MVP допустим безопасный набор имён вроде `title`, `regular_price`, `description_ua`, без пользовательских namespace и произвольных XPath-выражений.

```
class FeedSchemaValidator:    def validate(self, schema: FeedSchema) -> list[SchemaIssue]:        issues = []        issues += self.check_required_fields(schema)        issues += self.check_unique_ids(schema)        issues += self.check_unique_keys(schema)        issues += self.check_export_names(schema)        for field in schema.fields:            issues += self.type_registry.validate(field)            issues += self.source_registry.validate(field)            issues += self.transform_registry.validate(field)        return issues
```

Изменение типа существующего поля с сохранением `field_id`, если оно делает старые overrides несовместимыми, запрещается. Для такой операции нужно создавать новое поле либо использовать отдельный механизм миграции.

## **5. Infrastructure Layer — PostgreSQL**

### **5.1. Состав SQL-моделей**

Рекомендую следующую окончательную структуру для MVP.

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

Черновик схемы хранится отдельно от неизменяемых опубликованных версий.

### **5.2. Таблица Feed**

```

CREATE TABLE fb_feeds (
    id UUID PRIMARY KEY,

    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,

    default_currency CHAR(3) NULL,
    default_locale TEXT NULL,
    pricing_policy_id UUID NULL,
    availability_bindings JSONB NOT NULL DEFAULT '[]',
    input_revision BIGINT NOT NULL DEFAULT 1 CHECK (input_revision > 0),

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
5. Фиксируем событие `FeedSchemaPublished`.

Когда пользователь снова открывает редактирование, новая draft-схема создаётся копированием активной версии.

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

Это определение рассчитано на PostgreSQL 15+. `NULLS NOT DISTINCT` предотвращает создание нескольких публикаций одного простого товара, для которого `catalog_variant_id IS NULL`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

PostgreSQL



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
    feed_input_revision BIGINT NOT NULL,
    pricing_policy_id UUID NULL,
    pricing_policy_version INTEGER NULL,
    fx_snapshot_id UUID NULL,
    availability_fingerprint TEXT NULL,
    dependency_manifest JSONB NOT NULL DEFAULT '{}',
    valid_until TIMESTAMPTZ NULL,

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

Проекция считается устаревшей, если её версия схемы или публикации не совпадает с текущей. Дополнительно сравниваются input_revision, fingerprints всех локалей Catalog, PricePolicy version, Fx snapshot/срок действия, availability binding/policy/source versions и valid_until. Изменение любого влияющего входа даёт STALE. Отсутствие событий не означает вечную актуальность: перед экспортом источники перечитываются.

Не требуется массово обновлять все 100 тысяч строк сразу после публикации новой схемы. Их устаревание можно выявлять по несовпадающим версиям.

### **5.6. Генерации, ошибки, артефакты**

```

CREATE TABLE fb_generations (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    schema_version INTEGER NOT NULL,
    request_sequence BIGINT NOT NULL,
    feed_input_revision BIGINT NOT NULL,
    pricing_policy_id UUID NULL,
    pricing_policy_version INTEGER NULL,
    fx_rate_snapshot_id UUID NULL,
    availability_policy_snapshot JSONB NOT NULL DEFAULT '[]',
    execution_manifest JSONB NOT NULL DEFAULT '{}',
    source_capture_started_at TIMESTAMPTZ NULL,
    source_capture_completed_at TIMESTAMPTZ NULL,

    status TEXT NOT NULL
        CHECK (status IN (
            'PENDING', 'RUNNING',
            'SUCCEEDED', 'FAILED'
        )),

    attempt_count INTEGER NOT NULL DEFAULT 0,
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

    file_id UUID NOT NULL UNIQUE,
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

### **5.8. Хранение политик и snapshots**

Pricing владеет tenant-таблицами pricing_policies и pricing_policy_versions: ID/name, active_version и immutable definition источника/наценки/валютных корректировок. Это модели Pricing, а не дополнительные агрегаты FeedBuilder. AvailabilityPolicy и её версии принадлежат владельцу Availability; bindings хранят только логические UUID/version references без межконтекстных FK.

Execution manifest generation содержит policy versions, список from/to FX rates (либо ссылку на immutable Currency snapshot с гарантией хранения), availability policy/source snapshots, все required locales и currencies, as_of и источник каждого поля. Значения amount/rate в JSON — decimal strings.

Source snapshots каждой записи и зафиксированные membership/status/overrides сохраняются в staging generation. Их нельзя подменять чтением текущей fb_publication_projections. Сериализаторы используют только sealed staging. Повтор после sealing не перечитывает текущие курсы/политики/источники.

## **6. Application Layer — структура и Use Cases**

### **6.1. Основные Application Ports**

| Port                        | Назначение                            |
| --------------------------- | ------------------------------------- |
| `FeedRepository`            | Загрузка и сохранение Feed            |
| `FeedSchemaVersionStore` | Application-порт append-only истории; изменение схемы только через Feed |
| `FeedPublicationRepository` | Публикации и overrides                |
| `FeedProjectionRepository`  | Материализованные read models         |
| `FeedGenerationRepository`  | Запуски и результаты генераций        |
| `CatalogProductReader`      | Batch локализованного контента и базовых цен |
| `PriceCalculationPort` | PriceQuote для набора валют, фиксированная PricePolicy |
| `CurrencySnapshotPort` | Согласованный набор курсов через публичный Currency-контракт |
| `AvailabilityReaderPort` | Batch AvailabilityQuote по именованным bindings |
| `PricingPolicyManagementPort` | Создание/изменение политики через владельца Pricing |
| `SourcePathRegistry`        | Контракты разрешённых источников      |
| `FieldTypeRegistry`         | Типизация и валидация значений        |
| `TransformRegistry`         | Выполнение разрешённых операций       |
| `FeedSerializerRegistry`    | Сериализаторы форматов                |
| `ArtifactStorage`           | Чтение и запись файлов                |
| `UnitOfWork`                | Транзакции и согласованное сохранение |

### **6.2. Команды**

| Use Case                       | Назначение                               |
| ------------------------------ | ---------------------------------------- |
| `CreateFeed`                   | Создать Feed и стартовую схему           |
| `UpdateFeedSettings`           | Изменить название и UI-defaults |
| `AssignFeedPricingPolicy` | Привязать существующую PricePolicy либо выбрать NO_ADJUSTMENT |
| `ReplaceFeedAvailabilityBindings` | Сохранить именованные ссылки на версии политик доступности |
| `SaveFeedSchemaDraft`          | Сохранить черновик конструктора          |
| `PublishFeedSchema`            | Валидировать и опубликовать версию       |
| `AddCatalogItemsToFeed`        | Привязать товары из Catalog              |
| `RemoveFeedPublication`        | Удалить привязку из Feed                 |
| `SetPublicationOverride`       | Установить ручное значение               |
| `ResetPublicationOverride`     | Вернуть наследование                     |
| `ChangePublicationStatus`      | Включить или приостановить публикацию    |
| `RefreshPublicationProjection` | Пересчитать значения и ошибки            |
| `RequestFeedGeneration`        | Создать задание на генерацию             |
| `ExecuteFeedGeneration`        | Выполнить генерацию                      |
| `RotateFeedAccessKey`          | Заменить ключ публичного URL             |

### **6.3. Queries**

| Query                    | Возвращает                            |
| ------------------------ | ------------------------------------- |
| `ListFeeds`              | Список прайс-листов                   |
| `GetFeed`                | Настройки, policy refs, availability bindings и метаданные |
| `PreviewFeedPriceCalculation` | База, основная наценка, курс, корректировка и итог для валют |
| `ListAvailabilitySources` | Доступные источники и поддержанные capabilities |
| `GetFeedSchema`          | Активная версия или draft             |
| `ListFeedPublications`   | Публикации со статусами и ошибками    |
| `GetFeedPublication`     | Полная карточка с вычисленными полями |
| `PreviewFeedPublication` | Экспортную проекцию одного товара     |
| `PreviewFeed`            | Первые N строк будущей выгрузки       |
| `GetGeneration`          | Статус и статистику                   |
| `ListGenerationIssues`   | Ошибки генерации с фильтрами          |
| `GetActiveFeedArtifact`  | Метаданные актуального CSV/XML        |

### **6.4. Разделение Use Case и Domain**

Важное правило: Use Case управляет последовательностью действий, но не содержит алгоритмы проверки типов и transforms.

Например, `PublishFeedSchema`:

Обработчик получает репозитории и порты уже открытого внешним Depends UoW. Он загружает Feed под блокировкой, проверяет expected_version, передаёт typed schema в domain-метод публикации, сохраняет агрегат/immutable revision и Outbox в той же сессии. Domain проверяет структуру; Application через порты проверяет справочники и существование внешних policy references.

Use Case не открывает вложенный UoW, не получает AsyncSession и не вызывает commit. Завершение транзакции выполняет внешняя сборка.

Изменение активной версии схемы автоматически делает старые проекции устаревшими, поскольку их `schema_version` перестаёт совпадать с активной.

### **6.5. Работа с версионированием агрегатов**

`row_version` необходим у Feed, FeedSchemaDraft и FeedPublication.

Для обычных ORM-обновлений можно использовать SQLAlchemy `version_id_col`. Он проверяет версию при `flush()`, но не распространяет такую защиту автоматически на массовые `UPDATE`/`DELETE`, выполняемые отдельными SQL-операторами.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation



Поэтому операции, меняющие активную версию схемы или активный артефакт, должны дополнительно проверять ожидаемые значения непосредственно в транзакции.

### **6.6. Файлы сценариев и сборка зависимостей**

Backend: `src/modules/feed_builder/<layer>/<aggregate_root>/`; root names — feed, feed_publication, feed_generation. В Domain у каждого корня aggregate.py/repository.py/error.py и необходимые VO. FeedSchema и FieldDefinition размещаются внутри domain/feed. Pricing создаётся в `src/modules/pricing/` с собственными слоями; Source/FX/Availability adapters находятся в Infrastructure FeedBuilder.

Каждый command/query имеет отдельные command.py или query.py, handler.py и собственный dto.py при результате. Например AssignFeedPricingPolicyCommand → AssignFeedPricingPolicyHandler.execute → AssignFeedPricingPolicyResultDTO; ReplaceFeedAvailabilityBindings возвращает свой ResultDTO с bindings/input_revision. Для операции без результата используется None, пустой DTO не создаётся.

HTTP каждого метода разделён на controller/request/response/<scenario>.py; router только регистрирует контракты, Depends собирает порты на общем внешнем UoW. Query repositories/проекции принадлежат Application, write repositories — Domain и работают с корнями. FeedSchemaVersionStore сохраняет immutable версии в рамках сохранения Feed, а не даёт независимый CRUD для дочернего объекта.

Все методы имеют типы входов/результатов, русские docstrings; __init__ возвращает None, __init__.py пустые, импорты прямые. Ссылки на чужие policies — IDs/snapshots, не Domain aggregates/ORM соседей. Domain не проверяет существование справочника через I/O.

## **7. Value Resolution Engine**

Это pipeline подготовки значений: Application координирует порты, Domain выполняет чистые правила выбора, преобразования и проверки.

Он должен принимать определение поля, товар Catalog, overrides публикации и контекст Feed, после чего возвращать результат вычисления.

### **7.1. SourcePathRegistry**

Реестр объявляет следующие источники; availability paths доступны только после реализации соответствующего интеграционного среза:

| Source path          | Type   | Данные                  |
| -------------------- | ------ | ----------------------- |
| `item.title`         | STRING | Локализованное название |
| `item.description`   | TEXT   | Локализованное описание |
| `item.regular_price` | MONEY | Базовая цена Catalog; явный обход коммерческой наценки, с FX в валюту поля |
| `pricing.final_price` | MONEY | Итог PricePolicy в field.currency; provider=pricing, path=final_price |
| `availability.status` | STRING | Статус именованного binding |
| `availability.quantity` | INTEGER | Точное количество либо null; только после регистрации типа/адаптера |

Каждый Source path имеет зарегистрированный контракт и обработчик.

```
@dataclass(frozen=True)class SourceDefinition:    provider: str    path: str    value_type: FieldValueTypeclass SourcePathRegistry:    def __init__(self):        self.sources: dict[str, SourceDefinition] = {}    def register(        self,        definition: SourceDefinition,    ) -> None:        self.sources[definition.path] = definition    def validate(        self,        source: SourceReference,        value_type: FieldValueType,    ) -> None:        definition = self.sources.get(source.path)        if definition is None:            raise UnknownSourcePath()        if not types_are_compatible(            definition.value_type,            value_type,        ):            raise SourceTypeMismatch()
```

Нужно избежать исполнения пользовательских выражений через `eval()`, произвольных SQL-запросов и динамического доступа к Python-атрибутам.

SourcePath — только зарегистрированный идентификатор.

### **7.2. Контракты чтения и ResolutionContext**

```python
class CatalogProductReader(Protocol):
    async def get_many(
        self,
        item_ids: tuple[UUID, ...],
        locales: frozenset[str],
        as_of: datetime,
    ) -> tuple[CatalogProductSnapshot, ...]: ...
```

Snapshot содержит own typed localized_content[locale], исходную цену с валютой, отсутствие перевода/позиции, eligibility и dependency fingerprints. Locale set включает все локали полей и явных fallback-цепочек. Один batch получает весь нужный контент, без I/O на каждое поле. Catalog title/body адаптируются к item.title/item.description; HTML description преобразуется безопасным парсером в текст до чистого resolver.

`ResolutionContext` содержит as_of, schema/input revision, snapshots PricePolicy/FX/availability и подготовленные PriceQuote/AvailabilityQuote. В нём нет feed_locale/feed_currency. Application загружает данные через порты; чистая Domain-логика выбирает значения, выполняет transforms и constraints без I/O. API DTO чужих модулей преобразуются adapter в свои snapshots.

PriceCalculationPort рассчитывает базовую наценку один раз на товар+policy version, затем даёт quotes по всем необходимым валютам. Прямой MONEY source Catalog явно обходит наценку, но использует тот же FX snapshot для приведения в currency поля. UI поясняет этот выбор. Отсутствие policy у pricing.final_price означает NO_ADJUSTMENT с конвертацией, а не обход проверки курса. AvailabilityReaderPort читает источники по binding пакетами. MANUAL-поля не требуют доступности источника, если override полностью заменяет результат; недоступный исходник отмечается в provenance, но не блокирует корректное ручное поле.

Каждое отсутствующее значение и ошибка зависимости представлены раздельно. Отсутствие перевода — missing, неисправный adapter — SOURCE_UNAVAILABLE; их нельзя подменять пустой строкой/нулём.

### **7.3. FieldTypeRegistry**

Каждый тип получает собственный обработчик.

```
class FieldTypeHandler(Protocol):    def parse(        self,        raw_value: JsonValue | DomainValue,    ) -> DomainValue:        ...    def validate(        self,        value: DomainValue | None,        constraints: FieldConstraints,        context: ResolutionContext,    ) -> list[ValidationIssue]:        ...class FieldTypeRegistry:    handlers = {        FieldValueType.STRING: StringFieldHandler(),        FieldValueType.TEXT: TextFieldHandler(),        FieldValueType.MONEY: MoneyFieldHandler(),    }
```

`StringFieldHandler` и `TextFieldHandler` могут использовать общую базовую реализацию, но различаться поддерживаемыми constraints и UI-метаданными.

### **7.4. TransformRegistry**

```
class TransformHandler(Protocol):    operation: str    def apply(        self,        value: DomainValue,        parameters: dict,        context: ResolutionContext,    ) -> DomainValue:        ...class TransformRegistry:    handlers = {        "string.trim": TrimTransform(),        "string.truncate": TruncateTransform(),        "money.ceil_step": MoneyCeilStepTransform(),    }    def apply_all(        self,        value: DomainValue,        transforms: tuple[TransformDefinition, ...],        context: ResolutionContext,    ) -> DomainValue:        result = value        for transform in transforms:            handler = self.handlers[transform.operation]            result = handler.apply(                result,                transform.parameters,                context,            )
```

Регистрация новых transforms не должна требовать изменения `FeedPublication` или SQL-схемы.

### **7.5. Полный алгоритм FieldValueResolver**

```python
def resolve_field(field, publication_snapshot, prepared_context):
    override = publication_snapshot.overrides.get(field.id)
    source_value, source_issue = prepared_context.source_for(field)
    if override is not None:
        raw_value = override.value
        origin = "MANUAL"
    else:
        raw_value = source_value
        origin = "INHERITED"
    value = parse_typed_value(raw_value, field.value_type)
    value = apply_field_transforms(value, field.transforms)
    issues = validate_constraints(value, field.constraints, field.currency)
    if override is None and source_issue is not None:
        issues.append(source_issue)
    return resolved_field(value, origin, issues, requested_locale=field.locale)
```

Это иллюстрация порядка, а не готовый интерфейс реализации: реальные классы и все методы типизированы. Pricing quotes уже содержат коммерческую наценку и конвертацию; повторное применение этих операций в FieldValueResolver запрещено. Для ручного значения проверяется field.currency, а преобразование перевода не выполняется.

### **7.6. Правила вычисления**

Для каждого поля применяется одинаковая последовательность:

Source

Получить исходное значение

Override

Выбрать унаследованное или ручное

Parse

Привести к типу поля

Transform

Выполнить упорядоченные преобразования

Constraints

Проверить итоговое значение

Resolved Field

Вернуть value, origin и issues

### **7.7. Money Transform**

Используем `Decimal`, а не `float`.

`MoneyCeilStepTransform` принимает типизированный ExportMoneyVO, положительный step и currency конкретного поля. Он проверяет валюту, рассчитывает ceil(amount / step) * step в изолированном Decimal context и возвращает новое значение. Операция не получает наценку, policy ID или текущий курс.

590.21 при step=0.1 становится 590.3. Форматирование на экспорт задаётся явным параметром scale конкретного поля: стартовое значение 2 даёт 590.30. Если исходная точность выше scale, схема должна содержать явное округление; serializer не теряет знаки молча.

### **7.8. PublicationResolver**

Этот сервис вычисляет все поля публикации.

```
class PublicationResolver:    def resolve(        self,        schema: FeedSchema,        publication: FeedPublication,        product: CatalogProductSnapshot,        context: ResolutionContext,    ) -> ResolvedPublication:        fields = []        for definition in schema.fields:            fields.append(                self.field_resolver.resolve(                    definition,                    publication,                    product,                    context,                )            )        issues = [            issue            for field in fields            for issue in field.issues        ]        readiness = calculate_readiness(issues)        return ResolvedPublication(            publication_id=publication.id,            schema_version=context.schema_version,            fields=tuple(fields),            readiness=readiness,            issues=tuple(issues),
```

`calculate_readiness()` возвращает:

- `INVALID`, если имеется хотя бы одна ошибка типа, преобразования или constraints.
- `NEEDS_INPUT`, если отсутствуют обязательные значения, но нет ошибок более высокого приоритета.
- `READY`, если обязательные значения корректны.

`STALE` не является результатом текущего вычисления — это состояние сохранённой проекции, которую ещё не пересчитали.

## **8. Use Cases управления публикациями**

### **8.1. AddCatalogItemsToFeed**

Алгоритм:

1. Получить Feed.
2. Проверить наличие опубликованной схемы.
3. Проверить Catalog Items через `CatalogProductReader`.
4. Проверить, что типы товаров поддерживаются MVP.
5. Создать FeedPublication для новых товаров.
6. Если товар уже привязан — вернуть существующую публикацию.
7. Сохранить всё в одной транзакции.
8. Запланировать построение проекций.

Application получает товары batch-контрактом по schema.used_locales() и fallback-локалям, проверяет допустимые типы и через domain-фабрику создаёт отсутствующие FeedPublication. Запись membership, увеличение feed.input_revision и durable projection jobs выполняются одной внешней транзакцией. Handler не открывает UoW и не меняет поля агрегата напрямую.

`get_or_create()` должен быть идемпотентным и учитывать SQL UNIQUE constraint, в том числе при конкурентных запросах.

### **8.2. SetPublicationOverride**

Handler получает опубликованную схему и текущую публикацию в общем внешнем UoW, проверяет expected versions, передаёт field definition и typed override в domain-метод, сохраняет публикацию, feed.input_revision и invalidation job. MANUAL money требует явную currency, совпадающую с FieldDefinition.currency; наценка и FX к нему не применяются.

Ручное значение, превышающее `max_length`, разрешено сохранить, но поле становится `INVALID`. Так пользователь не теряет ввод и может исправить значение в UI.

При изменении цены должен сохраняться объект Money с валютой. Если сумма не парсится как число, API возвращает ошибку типа, не записывая повреждённый override.

### **8.3. ResetPublicationOverride**

Handler вызывает publication.reset_override(field_id), сохраняет агрегат и изменение feed.input_revision, затем атомарно планирует обновление проекции в уже открытом UoW. Повторный reset отсутствующего override — no-op.

После удаления override значение вновь определяется `default_mode` из схемы. Для поля без Source это может привести к состоянию `NEEDS_INPUT`, что является корректным поведением.

### **8.4. PreviewFeedPublication**

Предпросмотр не требует сохранения промежуточной проекции.

Query читает выбранную схему/публикацию, batch контент всех требуемых локалей, policy/FX snapshots и quotes; применяет общий resolver без сохранения и возвращает собственный PreviewFeedPublicationResultDTO. Currency/locale берутся из каждого поля. Ошибки и trace расчёта передаются по field_id.

Поддерживаются два режима:

- `ACTIVE` — опубликованная схема, используемая при генерации.
- `DRAFT` — редактируемая схема для проверки изменений.

В режиме `DRAFT` пользователь может проверить изменения, не влияя на уже опубликованные CSV/XML.

### **8.5. RefreshPublicationProjection**

Command фиксирует dependency manifest, batch читает контент/quotes и рассчитывает публикацию тем же resolver. Запись upsert_if_current сравнивает schema/publication/feed input versions, policy versions, source fingerprints и freshness до замены проекции. Результат имеет собственный RefreshPublicationProjectionResultDTO.

`upsert_if_current()` не должен перезаписывать более новую проекцию результатом устаревшего worker.

Для списка товаров используется сохранённая проекция, а для экспорта выполняется новое разрешение значений. Это гарантирует, что устаревший кэш не будет единственным источником содержимого фида.

## **9. Генерация CSV/XML**

### **9.1. Внутренняя экспортная модель**

Не следует жёстко привязывать сериализатор к классу с тремя атрибутами. Это усложнит добавление новых полей.

Лучше использовать динамический список типизированных значений.

```
@dataclass(frozen=True)class ExportCell:    field_id: UUID    export_name: str    value_type: FieldValueType    value: DomainValue@dataclass(frozen=True)class ExportRecord:    publication_id: UUID    cells: tuple[ExportCell, ...]
```

Порядок `cells` совпадает с порядком полей FeedSchema.

Это позволит добавлять новые поля без изменения сериализаторов CSV/XML.

### **9.2. CSV Serializer**

Контракт:

```
class FeedSerializer(Protocol):    format_code: str    content_type: str    async def serialize(        self,        records: AsyncIterator[ExportRecord],        schema: FeedSchema,    ) -> AsyncIterator[bytes]:        ...
```

Псевдокод CSV:

```
class CsvFeedSerializer:    format_code = "csv"    async def serialize(self, records, schema):        writer = StreamingCsvWriter(            delimiter=",",            encoding="utf-8",        )        yield writer.header([            field.export.name            for field in schema.exported_fields        ])        async for record in records:            yield writer.row([                self.format_value(cell)                for cell in record.cells            ])
```

Правила:

- UTF-8.
- Разделитель `,` по умолчанию.
- Колонки формируются в порядке схемы.
- Строковые значения корректно экранируются при наличии запятых, кавычек и переносов.
- Цена сериализуется в десятичном формате без валютного символа.
- Для значений, которые могут восприниматься электронными таблицами как формулы, предусмотрена отдельная политика безопасности CSV, не искажающая машинный импорт молча.

### **9.3. XML Serializer**

```
class XmlFeedSerializer:    format_code = "xml"    async def serialize(self, records, schema):        yield b'<?xml version="1.0" encoding="UTF-8"?>\n'        yield b'<catalog>\n'        async for record in records:            yield b'  <product>\n'            for cell in record.cells:                yield self.write_element(                    name=cell.export_name,                    value=self.format_value(cell),                )            yield b'  </product>\n'        yield b'</catalog>'
```

`write_element()` должен экранировать спецсимволы XML и отклонять недопустимые символы XML 1.0. Имена тегов валидируются при публикации схемы.

### **9.4. Пример результата**

CSV:

```
title,description,price
"Хлорофіл NOW Foods 473 мл","Рідкий хлорофіл",590.30
"Омега-3 NOW Foods","Риб'ячий жир",890.00
```

XML:

```
<?xml version="1.0" encoding="UTF-8"?>
<catalog>
  <product>
    <title>Хлорофіл NOW Foods 473 мл</title>
    <description>Рідкий хлорофіл</description>
    <price>590.30</price>
  </product>
  <product>
    <title>Омега-3 NOW Foods</title>
    <description>Риб'ячий жир</description>
    <price>890.00</price>
  </product>
</catalog>
```

Оба файла формируются из одного набора `ExportRecord`.

Пример другой пользовательской схемы в том же формате:

```csv
title_uk,title_ru,price_uah,price_usd
"Хлорофіл NOW Foods","Хлорофилл NOW Foods",1200.00,30.00
```

```xml
<catalog>
  <product>
    <title_uk>Хлорофіл NOW Foods</title_uk>
    <title_ru>Хлорофилл NOW Foods</title_ru>
    <price_uah>1200.00</price_uah>
    <price_usd>30.00</price_usd>
  </product>
</catalog>
```

Валюта определяется metadata поля; в универсальном CSV/XML она не выводится автоматически дополнительным тегом. Пользователь явно задаёт экспортные имена, позволяющие различить валюты. Generic CSV/XML не гарантирует соответствие Prom/Rozetka: будущий FormatProfile задаёт свои допустимые локали/валюты, обязательные поля и mapping. Требования платформ проверяются отдельно по актуальной официальной документации при реализации профиля.

## **10. Асинхронная генерация и публикация файлов**

### **10.1. Процесс выполнения**

RequestFeedGeneration

Создать задание PENDING

GenerationWorker

Захватить задание и зафиксировать версию схемы

Load Publications

Постранично загрузить включённые товары

Resolve & Validate

Получить значения, выполнить transforms, собрать ошибки

Staging

Сохранить проверенный набор ExportRecord

Serialize

Сформировать CSV и XML

ArtifactStorage

Записать неизменяемые файлы

Activate

Атомарно заменить указатель активной генерации

### **10.2. RequestFeedGeneration**

Внешний Depends открывает общий UoW. Handler загружает Feed под lock, через domain-метод проверяет active schema и регистрирует request_sequence. В одной транзакции фиксируются schema/input revision, назначенная PricePolicy и её версия, availability binding versions, membership/status/overrides snapshot, FeedGeneration и durable shared job. Idempotency-Key с hash payload защищает повтор HTTP-запроса.

Перед чтением первого товара worker получает единый as_of и FxRateSnapshot для всех требуемых валют и базовых валют, найденных в источниках. Пара фиксируется один раз и больше не обновляется внутри generation. При невозможности подготовить полный допустимый набор курсов inherited поля получают FX_RATE_MISSING; готовый ручной override независим от этого курса.

Используются штатные shared jobs/heartbeat/recovery, без второй очереди внутри fb_generations. Если доставку инициирует Outbox, запись job/Outbox атомарна с generation. Worker/CLI открывает собственные короткие UoW; HTTP session не передаётся в фон.

### **10.3. ExecuteFeedGeneration**

Worker читает зафиксированный request manifest и источники batch-пакетами по стабильному порядку. Application запрашивает контент всех нужных локалей, Pricing quotes для валют полей и Availability quotes по bindings. Domain resolver получает immutable typed snapshots; нет locale=feed.locale, feed_currency или нового курса на каждую позицию.

Для каждой записи сохраняются исходные зависимости, policy/FX/source versions и resolved ExportRecord. После проверки всего набора staging запечатывается. CSV и XML строятся исключительно из него.

Files reserve → загрузка байтов вне SQL → Files confirm и регистрация artifacts выполняются по существующему двухфазному Application-контракту Files. В FeedBuilder хранятся file_id, hash, размер и format, а не второй реестр объектов хранилища. Методы claim/complete/activate используют короткие внешние транзакции; сеть не удерживает SQL UoW.

Финальный domain-метод активации получает snapshot результата и проверяет request_sequence, schema/input revision, актуальность PricePolicy/availability versions и lifecycle. Если пользователь сменил политику/схему/источники, старый успешный результат остаётся в истории. CAS и lease fencing предотвращают перезапись более новым или потерявшим lease worker.

### **10.4. Гарантии выполнения**

В реализации worker необходимо обеспечить:

- **Idempotency:** повторный запуск одного задания не создаёт дублирующиеся активные результаты.
- **Lease и heartbeat:** зависшее задание можно повторно забрать.
- **Retry:** временные инфраструктурные ошибки допускают повторную попытку; ошибки бизнес-валидации — нет.
- **Atomic activation:** активная ссылка переключается только после успешного сохранения всех требуемых форматов.
- **Version safety:** генерация старой схемы не заменяет файл новой версии.
- **Cleanup:** незавершённые временные файлы удаляются по политике хранения.

Промежуточные `ExportRecord` сохраняются в staging, чтобы CSV и XML строились из одного и того же набора данных.

При изменении Catalog во время длительной генерации в MVP сохраняются версии источников, использованные для каждой записи. Строгий единый snapshot нескольких независимых модулей не гарантируется до появления механизма согласованных source snapshots.

### **10.5. Публичные ссылки**

Пример:

```
https://feeds.example.com/f/{public_id}/{token}/catalog.csv

https://feeds.example.com/f/{public_id}/{token}/catalog.xml
```

Публичный контроллер:

```
class DownloadPublicFeed:    async def execute(        self,        public_id: UUID,        token: str,        format_code: str,    ) -> ArtifactResponse:        route = await self.routes.resolve(public_id)        tenant = await self.tenants.resolve(route.tenant_id)        async with tenant.context():            await self.access.verify(                feed_id=route.feed_id,                token=token,            )            feed = await self.feeds.get(route.feed_id)            if feed.active_generation_id is None:                raise FeedArtifactNotFound()            artifact = await self.artifacts.get_active(                feed.id,                format_code,            )            return await self.storage.stream(artifact)
```

При выдаче поддержать `ETag`, `Last-Modified`, потоковую передачу и корректный `Content-Type`.

Токены хранятся только в виде криптографических хешей, поддерживают ротацию и не должны попадать в application logs. Ссылки передаются по HTTPS.

## **11. Presentation Layer — REST API**

### **11.1. Управление Feed и схемами**

| Метод   | Endpoint                                      | Use Case              |
| ------- | --------------------------------------------- | --------------------- |
| `POST`  | `/api/console/feed-builder/feeds`                     | `CreateFeed`          |
| `GET`   | `/api/console/feed-builder/feeds`                     | `ListFeeds`           |
| `GET`   | `/api/console/feed-builder/feeds/{id}`                | `GetFeed`             |
| `PATCH` | `/api/console/feed-builder/feeds/{id}`                | `UpdateFeedSettings`  |
| `GET`   | `/api/console/feed-builder/feeds/{id}/schema`         | `GetFeedSchema`       |
| `PUT`   | `/api/console/feed-builder/feeds/{id}/schema/draft`   | `SaveFeedSchemaDraft` |
| `POST`  | `/api/console/feed-builder/feeds/{id}/schema/publish` | `PublishFeedSchema`   |
| `GET`   | `/api/console/feed-builder/field-types`               | Поддерживаемые типы   |
| `GET`   | `/api/console/feed-builder/source-paths`              | Доступные источники   |
| `PUT` | `/api/console/feed-builder/feeds/{id}/pricing-policy` | AssignFeedPricingPolicy |
| `POST` | `/api/console/feed-builder/feeds/{id}/pricing-preview` | PreviewFeedPriceCalculation |
| `PUT` | `/api/console/feed-builder/feeds/{id}/availability-bindings` | ReplaceFeedAvailabilityBindings |
| `GET` | `/api/console/feed-builder/availability-sources` | ListAvailabilitySources |

### **11.2. Публикации**

| Метод    | Endpoint                                  | Use Case               |
| -------- | ----------------------------------------- | ---------------------- |
| `POST`   | `/feeds/{id}/publications`                | Добавить Catalog Items |
| `GET`    | `/feeds/{id}/publications`                | Список и фильтры       |
| `GET`    | `/publications/{id}`                      | Карточка публикации    |
| `PUT`    | `/publications/{id}/overrides/{field_id}` | Установить override    |
| `DELETE` | `/publications/{id}/overrides/{field_id}` | Вернуть наследование   |
| `PATCH`  | `/publications/{id}/status`               | Изменить участие       |
| `POST`   | `/publications/{id}/preview`              | Вычислить предпросмотр |

Для краткости префикс `/api/console/feed-builder` в нижней части таблицы опущен.

### **11.3. Генерации**

| Метод    | Endpoint                           | Назначение          |
| -------- | ---------------------------------- | ------------------- |
| `POST`   | `/feeds/{id}/generations`          | Запустить генерацию |
| `GET`    | `/feeds/{id}/generations`          | История             |
| `GET`    | `/generations/{id}`                | Статус и статистика |
| `GET`    | `/generations/{id}/issues`         | Ошибки              |
| `GET`    | `/feeds/{id}/artifacts`            | Активные файлы      |
| `POST`   | `/feeds/{id}/access-keys`          | Создать ключ        |
| `DELETE` | `/feeds/{id}/access-keys/{key_id}` | Отозвать ключ       |

### **11.4. DTO предпросмотра**

UI не должен самостоятельно разрешать SourcePath и повторять правила Domain.

Backend возвращает полностью вычисленную модель.

```

{
  "publication_id": "publication-uuid",
  "catalog_item_id": "catalog-item-uuid",
  "status": "ENABLED",
  "readiness": "INVALID",
  "schema_version": 1,
  "fields": [
    {
      "field_id": "field-title-uuid",
      "key": "title",
      "label": "Название",
      "value_type": "string",
      "source": {
        "path": "item.title",
        "value": "Очень длинное исходное название товара"
      },
      "mode": "INHERIT",
      "override_value": null,
      "resolved_value": "Очень длинное исходное название товара",
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

В каждом поле ответа обязательны locale/currency (nullable по типу), requested_locale/resolved_locale, source binding, quote ID и применённые policy/FX versions. Для MONEY trace показывает base, markup, conversion, extra adjustment, override и rounding; для availability — выбранные источники, observed_at/valid_until и точность количества. Ответ не раскрывает credentials поставщика/3PL. Можно возвращать can_override/can_reset/is_stale и метаданные редактора.

### **11.5. Единый формат ошибок**

Application возвращает конкретные dataclass DTO сценариев; HTTP Request/Response — отдельные Pydantic-схемы Presentation. Транспортная ошибка содержит code/message, nullable field_id и безопасные details. Pydantic BaseModel в Application не используется.

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
| `CURRENCY_MISMATCH` | Готовый quote/override имеет другую валюту, чем поле |
| `FX_RATE_MISSING` | Нет допустимого курса конвертации |
| `BASE_PRICE_MISSING` | Нет базовой цены для расчёта |
| `PRICING_POLICY_UNAVAILABLE` | Не найдена доступная версия PricePolicy |
| `AVAILABILITY_SOURCE_STALE` | Источник остатка просрочен |
| `EXACT_QUANTITY_UNAVAILABLE` | У binding нет точного количества |
| `VERSION_CONFLICT`       | Конкурентное изменение       |
| `SOURCE_UNAVAILABLE`     | Источник временно недоступен |

Использовать HTTP `404` для отсутствующих ресурсов, `409` для конфликтов версий и `422` для ошибок содержимого и конфигурации. Внутренние ошибки и недоступность зависимостей не следует маскировать под незаполненные поля товара.

## **12. Frontend — Vue 3 + TypeScript**

Frontend предоставляет создание Feed, конструктор, публикации и экспорт, а также настройки ценообразования и источников остатков.

### **12.1. Экран создания Feed**

**Основные компоненты:**

```
FeedCreatePage
 ├── FeedGeneralForm
 │    ├── NameInput
 │    ├── CodeInput
 │    ├── DefaultCurrencySelect (подсказка новых полей)
 │    └── DefaultLocaleSelect (подсказка новых полей)
 ├── FeedFormatSelector
 │    ├── CsvOption
 │    └── XmlOption
 └── FeedCreateAction
```

Поведение:

- Пользователь вводит название и настройки.
- Backend создаёт Feed.
- Создаётся начальная draft-схема.
- Пользователь переходит к конструктору.
- Нельзя начать генерацию до публикации корректной схемы.

### **12.2. Конструктор схемы**

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
      ├── FieldCurrencySettings
      ├── AvailabilityBindingSelect
      ├── ConstraintSettings
      ├── TransformSettings
      └── AiSettings
```

**Drag-and-drop:**

- Перетаскивание типа из FieldPalette создаёт новый `FieldDefinition` с UUID.
- Перемещение поля в Canvas изменяет порядок в `FeedSchema.fields`.
- Выбор поля открывает Inspector.
- Переименование не изменяет `field_id`.
- Удаление необязательного поля допускается.
- Публикация схемы запускает полную проверку Backend.
- Изменения сохраняются в draft и не затрагивают активную схему.

Псевдокод состояния конструктора:

```
interface FieldDefinition {
  id: string;
  key: string;
  label: string;
  value_type: "string" | "text" | "money";
  locale: string | null;
  currency: string | null;
  fallback_policy: LocaleFallbackPolicy;
  source: SourceReference | null;
  default_mode: "INHERIT" | "MANUAL";
  constraints: Record<string, unknown>;
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
) {
  const field = createDefaultFieldDefinition(type);

  schema.fields.splice(index, 0, field);
  selectedFieldId.value = field.id;
  draftDirty.value = true;
}

function onFieldMoved(
  sourceIndex: number,
  targetIndex: number
) {
  moveArrayItem(schema.fields, sourceIndex, targetIndex);
  draftDirty.value = true;
}
```

Список доступных SourcePath и поддерживаемых transforms должен приходить с backend. Не нужно независимо поддерживать два перечня полей в Python и TypeScript.

### **12.3. Список публикаций**

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
| Title     | Выбранные локализованные поля схемы с указанием языка |
| Price     | Выбранные MONEY-поля с валютой каждого столбца |
| Overrides | Количество ручных значений             |
| Readiness | Готово / Заполнить / Ошибка / Устарело |
| Issues    | Краткое описание проблемы              |
| Updated   | Время расчёта проекции                 |

Нужна серверная пагинация, фильтрация и сортировка. Не загружать все публикации на frontend. Язык и валюта столбца выбираются по field_id схемы, а не по единственным feed.locale/feed.currency.

### **12.4. Редактор публикации**

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

### **12.5. Ценообразование и источники остатков**

Feed имеет раздел «Ценообразование»: выбор существующей PricePolicy/создание через API Pricing, источник базы, процент наценки, дополнительные валютные корректировки и просмотр применённой версии. Наценка +20% хранится один раз в политике, не копируется в price_uah/price_usd. Для NO_ADJUSTMENT показывается явное отсутствие наценки.

Inspector текста показывает locale/fallback, Inspector MONEY — currency/rounding и ссылку на PricePolicy; default_locale/default_currency формы создания только заполняют значения новых полей. Перед публикацией пользователь видит итоговый список языков и валют. Предпросмотр объясняет вычисление цены и показывает override как окончательную цену до field transforms.

Раздел «Источники остатков» показывает bindings и доступные capabilities: собственный склад, 3PL или SupplierSource, policy/version, strategy, freshness и точность. Он появляется после подключения адаптеров. Поле quantity нельзя назначить STATUS_ONLY-источнику без видимой ошибки. Выбор связки не изменяет Inventory и не создаёт резерв.

Frontend разделяется по архитектуре Console: api DTO/mapper, чистые frontend types, queries/mutations, page state, Page-оркестраторы и UI с props/emits. Используется общий HTTP provider, Vue Query с tenant-aware keys; суммы остаются строками. Изменение schema/policy/bindings инвалидирует зависимые preview/projections. Refetch/409 не стирают несохранённый ввод, смена tenant отменяет запросы и очищает drafts. Вычисления наценки/FX/availability выполняет backend.

### **12.6. Интерфейс экспорта**

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

## **13. Безопасность и мультитенантность**

С учётом архитектуры CRM, где каждый tenant имеет собственную PostgreSQL schema, необходимо соблюдать несколько правил.

**Tenant isolation.** Таблицы `fb_*` создаются в схеме tenant. Обращение к репозиториям выполняется только через существующий механизм tenant-aware connection и Unit of Work.

**Public routing.** Публичный `public_id` резолвится через доверенный реестр, а не через произвольное имя SQL-схемы из URL.

**Authorization.** Административные запросы проверяют права на просмотр Feed, изменение схемы, редактирование публикаций, генерацию и управление ключами. Источники Catalog также должны проверять разрешённость чтения полей для данного контекста.

**Schema execution.** Пользовательский JSON не может содержать исполняемый Python, SQL, JavaScript или произвольный URL для получения данных. Все операции выполняются зарегистрированными обработчиками.

**Serialization.** CSV и XML получают только проверенные значения; XML-элементы безопасно экранируются, экспортные имена валидируются.

**Resource limits.** Необходимы ограничения на размер схемы, количество полей, глубину вложенности при будущем расширении, объём предпросмотра и число одновременных генераций.

## **14. Тестирование**

### **14.1. Domain Unit Tests**

| Объект                | Основные тесты                                        |
| --------------------- | ----------------------------------------------------- |
| `Feed`                | Создание, версии схемы, допустимые переходы           |
| `FeedSchema`          | Уникальные ID, обязательные поля, совместимость типов |
| `FieldConstraints`    | Длина, обязательность, денежные диапазоны             |
| `FieldTransform`      | Trim, truncate, ceil step                             |
| `FeedPublication`     | Установка и сброс overrides                           |
| `FieldValueResolver`  | INHERIT, MANUAL, пустые и неправильные значения       |
| `PublicationResolver` | READY, NEEDS_INPUT, INVALID                           |
| `FeedGeneration`      | Переходы состояний и запрет повторной активации       |

### **14.2. Integration Tests**

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

### **14.3. Export Tests**

Обязательные сценарии:

| Сценарий                             | Результат                             |
| ------------------------------------ | ------------------------------------- |
| Название длиннее 80 символов         | `MAX_LENGTH_EXCEEDED`                 |
| Пустое обязательное описание         | `REQUIRED_VALUE_MISSING`              |
| Пустой обязательный MANUAL price без источника | REQUIRED_VALUE_MISSING |
| Исходная цена UAH, поле USD, курс доступен | Конвертация по фиксированному snapshot |
| Ручной USD override в UAH-поле | CURRENCY_MISMATCH |
| Нет допустимого курса | FX_RATE_MISSING; нет тихого fallback |
| Нет базовой цены Pricing | BASE_PRICE_MISSING, поле INVALID |
| title_uk и title_ru в одном Feed | Независимые переводы и overrides |
| MANUAL price_usd | Нет повторной наценки и конвертации |
| Цена 1000 UAH, +20%, 40 UAH/USD | 1200 UAH и 30 USD |
| Цена 1000 UAH, +30%, тот же курс | Другой Feed: 1300 UAH и 32.50 USD |
| Повторное MONEY-поле одной валюты | Не применяет базовую наценку второй раз |
| STATUS_ONLY у поставщика | quantity=null, точное количество не выдумывается |
| Тот же остаток через склад и его 3PL зеркало | Не суммируется повторно |
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

### **14.4. End-to-End Tests**

Сквозной тест должен проходить через API и реальную базу данных:

```
CreateFeed
    ↓
SaveSchemaDraft
    ↓
PublishFeedSchema
    ↓
AddCatalogItems
    ↓
GetPublicationPreview
    ↓
SetOverride
    ↓
ValidatePublication
    ↓
RequestGeneration
    ↓
WorkerProcessing
    ↓
DownloadCSV / DownloadXML
```

Отдельный E2E-тест должен проверять работу с двумя tenant, чтобы публикации, схемы и файлы одного tenant никогда не попадали в ответы другого.

## **15. Последовательные срезы реализации**

Первый срез реализует Domain и unit-тесты. Последующие срезы последовательно подключают persistence, Application, HTTP и Console; коммерческая арифметика Pricing остаётся в собственном контексте. Availability contracts закладываются сразу, реальные adapters подключаются при готовности владельцев источников.

## **1**

**Domain Foundation**

`Feed`, `FeedSchema`, `FieldDefinition`, Constraints, Transforms, `FeedPublication`, `FeedGeneration`, Value Objects, доменные ошибки и события.

Реализовать инварианты схемы, статусы, версионирование и overrides. FieldDefinition содержит locale/currency/fallback_policy, Feed — pricing_policy_id и availability bindings; ExportMoneyVO сохраняет точность. Три корня FeedBuilder: Feed, FeedPublication, FeedGeneration; FeedSchema остаётся частью Feed. PricePolicy — отдельный агрегат Pricing, не четвёртый корень FeedBuilder.

Готовность: все Domain Unit Tests проходят без PostgreSQL, FastAPI и SQLAlchemy.

## **2**

**Persistence Foundation**

Alembic-миграция, SQLAlchemy Models, Row Mappers, Repositories, Unit of Work.

Создать таблицы, ограничения, индексы, tenant schema и row_version; обязательные feed.locale_code/currency_code отсутствуют. Locale/currency живут в JSON схемы, policy refs и input_revision — отдельные колонки; snapshots — в generation/projections. Межконтекстных FK нет.

Готовность: агрегаты сохраняются и восстанавливаются без потери доменной типизации.

## **3**

**Feed CRUD + Schema Builder**

Use Cases создания Feed, draft/publish, реестров типов/источников, назначения PricePolicy и availability bindings; UI выбирает язык/fallback и валюту каждого поля.

Реализовать административный REST API и первые два экрана frontend — создание Feed и конструктор.

Готовность: пользователь создаёт прайс и собирает схему drag-and-drop.

## **4**

**Publication + Value Resolution**

Минимальный Pricing-контекст: PricePolicy, версии, PERCENT/NO_ADJUSTMENT, PriceCalculator, base-price adapter и CurrencySnapshotPort. Затем CatalogProductReader, registries, resolver и projections с multi-locale/multi-currency quotes. Наценка считается один раз; ручные цены её обходят.

Реализовать добавление товаров, редактирование overrides, список публикаций и карточку предпросмотра.

Готовность: товары автоматически наследуют данные Catalog, показывают ошибки и поддерживают ручные значения.

## **5**

**Export Engine**

Динамический ExportRecord, CSV/XML serializers, GenerationWorker, staging, история/ошибки и Files adapter. Generation фиксирует schema/input/policy versions, FX и availability snapshots; оба формата читают один sealed набор.

Готовность: пользователь получает корректные CSV/XML из одного набора публикаций.

## **6**

**Public Distribution**

Public route registry, AccessKey, публичный контроллер, ротация токенов, HTTP-кеширование, атомарная активация артефактов.

Завершить экран экспорта и истории генераций.

Готовность: внешняя система скачивает CSV/XML по постоянным ссылкам.

## **7**

**Stabilization**

Интеграционные, E2E, нагрузочные и security-тесты. Проверить повторные задания, tenant isolation, работу с большим каталогом, восстановление после ошибок.

Готовность: выполнение всех критериев приёмки MVP.

### **15.8. Интеграция источников остатков**

При готовности Inventory/внешних адаптеров реализовать AvailabilityPolicy/quotes и INTEGER/BOOLEAN типы для quantity/available, capability descriptors, batch-read и UI bindings. Проверить стратегии PRIORITY/SUM_EXACT/ANY_AVAILABLE, TTL, права владельца, единицы измерения и дедупликацию. До этого среза binding contracts хранятся, но неподдержанные availability fields не публикуются. Не блокировать многоязычные/мультивалютные CSV/XML наличием полного WMS.

## **16. Что заложить сейчас для дальнейшего расширения**

Эти возможности не входят в первую реализацию, но должны учитываться в контрактах.

| Будущая возможность  | Уже подготовленный механизм                             |
| -------------------- | ------------------------------------------------------- |
| Категории Feed       | `reference` field type и отдельный Category Repository  |
| Характеристики       | Дополнительные SourcePath и типы полей                  |
| Вложенные объекты    | `FieldDefinition.kind` и `children`                     |
| Массивы изображений  | `array` + `media`                                       |
| Варианты товаров     | `catalog_variant_id`                                    |
| Дополнительные локали | Locale/fallback поля уже работают; источник не кодирует язык в path |
| AI-генерация         | `ai_instruction`, отдельный GenerateSuggestion Use Case |
| Динамическая выборка | FeedSelectionPolicy и Selection Engine                  |
| Расписание генераций | Планировщик, создающий Generation Request               |
| Prom/Rozetka         | Platform-specific FormatProfile и Serializer            |
| Сложные ценовые правила | FIXED_AMOUNT, TARGET_MARGIN, category/SKU правила в Pricing |
| Новые источники остатков | Версионируемые availability bindings и adapter capabilities |
| Массовые изменения   | Bulk Override Application Service                       |

Особенно важно не объединять `FeedSchema` и `FeedPublication`. Это позволит добавлять все перечисленные возможности, не изменяя фундамент наследования и пользовательских значений.

## **17. Критерии завершения MVP**

Модуль можно считать реализованным, когда выполняется следующий сценарий:

1. Пользователь создаёт Feed с собственной PricePolicy; добавляет title_uk/title_ru и price_uah/price_usd с явными locale/currency.
2. Конструктор автоматически предлагает поля Title, Description и Price.
3. Пользователь меняет порядок полей, source path, constraints и transforms.
4. Публикует версию схемы.
5. Добавляет несколько товаров из Catalog.
6. Получает автоматически заполненные публикации.
7. Для длинного Title видит ошибку ограничения.
8. Для отсутствующей цены видит требование заполнения.
9. Переопределяет проблемное поле.
10. Предпросмотр показывает исходное, ручное и конечное значения.
11. Все включённые публикации переходят в READY; override одного перевода/валюты не меняет соседние поля.
12. Разные Feed применяют разные PricePolicy (+20% / +30%) к той же базе, не меняя Catalog; FX snapshot одинаков для всех строк поколения. Ручная цена не получает наценку повторно.
13. Генерация создаёт CSV и XML с одинаковыми переводами и валютными колонками из одного staging.
14. Оба файла доступны по постоянным URL.
15. Изменение Catalog/PricePolicy/FX делает зависимую проекцию STALE; новый расчёт читает новые входы.
16. Новая ошибочная генерация не уничтожает предыдущий корректный файл.
17. При подключённых availability adapters два Feed могут выбирать разные bindings; STATUS_ONLY сохраняет quantity=null, устаревший источник виден как ошибка/UNKNOWN по политике.

**Итоговая архитектура MVP:**

`Feed + FeedSchema + FeedPublication + Catalog/Pricing/Currency/Availability snapshots → ResolvedPublication → ExportRecord → FeedGeneration → Artifact`

Эта последовательность должна стать основным контрактом модуля. SQL хранит идентичность, конфигурацию и overrides; Application вычисляет значения; Domain защищает инварианты; Infrastructure сериализует и доставляет файлы; Presentation предоставляет универсальный конструктор.

Контракты первого среза включают FieldDefinition, FeedSchema, FieldOverride, ExportMoneyVO, policy references и immutable resolution snapshots. Код, миграции и UI реализуются отдельными задачами согласно срезам.
