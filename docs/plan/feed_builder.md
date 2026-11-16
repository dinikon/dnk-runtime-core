# **FeedBuilder — финальный технический план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript\
**Хранение схем:** JSONB с версионированием\
**Экспорт:** CSV, XML

## **1. Цель и границы модуля**

`FeedBuilder` — самостоятельный bounded context, отвечающий за создание пользовательских прайс-листов на основании данных Catalog.

Пользователь должен иметь возможность:

1. Создать `Feed` с названием, валютой и языком.
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
| `MONEY`    | `MoneyVO` | Цена            |

Начальная схема автоматически содержит три обязательных поля:

- `title: STRING`
- `description: TEXT`
- `price: MONEY`

В редакторе можно менять порядок полей, названия, настройки, источники, constraints и transforms. Допускается добавление необязательных полей тех же трёх типов. Таким образом, движок сразу будет работать с динамическим списком полей, а не с жёстко заданными колонками.

В рамках MVP обязательные системные ключи `title`, `description`, `price` нельзя удалить или изменить на несовместимый тип. Остальные поля можно добавлять и удалять.

В первом релизе не реализуем варианты товаров, категории, изображения, характеристики, AI-генерацию, динамический подбор ассортимента и специализированные контракты Prom/Rozetka.

При этом **структуру схемы, идентификаторы полей и границы агрегатов сразу проектируем универсальными**.

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

### **2.1. Три принципиально разных типа данных**

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

```
class Feed(AggregateRoot):    id: FeedId    name: str    code: FeedCodeVO    currency: CurrencyCodeVO    locale: LocaleCodeVO    status: FeedStatus    active_schema_version: int | None    draft_schema: FeedSchema | None    latest_generation_sequence: int    active_generation_id: UUID | None    version: int    def rename(self, name: str) -> None:        ...    def replace_draft_schema(        self,        schema: FeedSchema,    ) -> None:        ...    def publish_schema(        self,        next_version: int,    ) -> SchemaPublishedEvent:        ...    def request_generation(        self,    ) -> GenerationRequest:
```

Основные инварианты:

- У Feed не может быть двух активных версий схемы.
- Опубликованная версия схемы неизменяема.
- Активная схема обязательно содержит три основных поля.
- Все `field_id` и `key` внутри схемы уникальны.
- Нельзя генерировать файл без опубликованной схемы.
- Более старая генерация не должна перезаписывать результат более новой.
- Изменение валюты или языка после публикации схемы выполняется как контролируемое изменение конфигурации с последующей проверкой публикаций.

### **3.3. FeedSchema и FieldDefinition**

```
@dataclass(frozen=True)class FeedSchema:    fields: tuple[FieldDefinition, ...]    schema_format_version: int = 1    def get_field(self, field_id: UUID) -> FieldDefinition:        ...    def validate_structure(self) -> list[SchemaIssue]:        ...    def reorder_fields(        self,        field_ids: tuple[UUID, ...],    ) -> "FeedSchema":        ...@dataclass(frozen=True)class FieldDefinition:    id: UUID    key: str    label: str    value_type: FieldValueType    source: SourceReference | None    default_mode: ValueMode    constraints: FieldConstraints    transforms: tuple[TransformDefinition, ...]    ai_instruction: str | None = None
```

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

Для `MONEY` используется `Decimal` и существующий в проекте Money Value Object. При сериализации JSON денежная сумма представляется десятичной строкой.

В MVP валюта наследуемой или ручной цены должна совпадать с валютой Feed. При несовпадении возвращается `CURRENCY_MISMATCH`; конвертация валют добавляется отдельным transform позже.

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

Успешное завершение генерации и её активация — разные действия. Генерация может закончиться успешно, но не стать активной, например если пользователь уже изменил схему.

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
        "label": "Цена",
        "value_type": "money",
        "source": {
          "provider": "catalog",
          "path": "item.regular_price"
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
| `source`         | Ссылка на источник данных                |
| `default_mode`   | Поведение без пользовательского override |
| `constraints`    | Правила проверки итогового значения      |
| `transforms`     | Упорядоченные преобразования             |
| `export.name`    | Имя колонки CSV или элемента XML         |
| `ai.instruction` | Метаданные для будущего AI-агента        |

`field_id` нельзя изменять при простом переименовании поля.

`key` используется для внутреннего обращения к полю, а `export.name` — для итогового файла. Например, внутренний `title` может экспортироваться в `name_ua`.

### **4.3. Валидация схемы**

При сохранении черновика проверяется синтаксическая корректность. При публикации выполняется полная семантическая валидация:

- Уникальность `field_id`, `key`, экспортных имён.
- Совместимость поля с Source.
- Совместимость constraints с типом.
- Поддержка указанных transforms.
- Наличие обязательных полей и корректность их типов.
- Допустимость имён XML-элементов.
- Ограничение числа полей и размеров JSON-документа.

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

От предыдущего варианта предлагаю одно уточнение: **черновик схемы лучше хранить отдельно от опубликованных версий**. Это упрощает редактирование, блокировки и обеспечение неизменяемости опубликованной конфигурации.

### **5.2. Таблица Feed**

```

CREATE TABLE fb_feeds (
    id UUID PRIMARY KEY,

    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,

    currency_code CHAR(3) NOT NULL,
    locale_code TEXT NOT NULL,

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

Проекция считается устаревшей, если её версия схемы или публикации не совпадает с текущей. При наличии событий Catalog дополнительно сравнивается `catalog_revision`.

Не требуется массово обновлять все 100 тысяч строк сразу после публикации новой схемы. Их устаревание можно выявлять по несовпадающим версиям.

### **5.6. Генерации, ошибки, артефакты**

```

CREATE TABLE fb_generations (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    schema_version INTEGER NOT NULL,
    request_sequence BIGINT NOT NULL,

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

## **6. Application Layer — структура и Use Cases**

### **6.1. Основные Application Ports**

| Port                        | Назначение                            |
| --------------------------- | ------------------------------------- |
| `FeedRepository`            | Загрузка и сохранение Feed            |
| `FeedSchemaRepository`      | Черновики и опубликованные схемы      |
| `FeedPublicationRepository` | Публикации и overrides                |
| `FeedProjectionRepository`  | Материализованные read models         |
| `FeedGenerationRepository`  | Запуски и результаты генераций        |
| `CatalogProductReader`      | Исходные значения товаров             |
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
| `UpdateFeedSettings`           | Изменить название и допустимые настройки |
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
| `GetFeed`                | Настройки и метаданные                |
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

```
class PublishFeedSchema:    async def execute(        self,        command: PublishSchemaCommand,    ) -> PublishSchemaResult:        async with self.uow_factory() as uow:            feed = await uow.feeds.get_for_update(                command.feed_id            )            draft = await uow.schemas.get_draft(                feed.id            )            if draft.row_version != command.expected_version:                raise VersionConflict()            schema = self.schema_codec.decode(                draft.definition            )            issues = self.schema_validator.validate(                schema            )            if issues:                raise InvalidFeedSchema(issues)            next_version = (                feed.active_schema_version or 0            ) + 1            # Создаётся неизменяемая версия.            await uow.schemas.create_published(                feed_id=feed.id,
```

Use Case не вызывает `commit()` напрямую. Управление транзакцией выполняет Unit of Work.

Изменение активной версии схемы автоматически делает старые проекции устаревшими, поскольку их `schema_version` перестаёт совпадать с активной.

### **6.5. Работа с версионированием агрегатов**

`row_version` необходим у Feed, FeedSchemaDraft и FeedPublication.

Для обычных ORM-обновлений можно использовать SQLAlchemy `version_id_col`. Он проверяет версию при `flush()`, но не распространяет такую защиту автоматически на массовые `UPDATE`/`DELETE`, выполняемые отдельными SQL-операторами.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation



Поэтому операции, меняющие активную версию схемы или активный артефакт, должны дополнительно проверять ожидаемые значения непосредственно в транзакции.

## **7. Value Resolution Engine**

Это центральный Application Service модуля.

Он должен принимать определение поля, товар Catalog, overrides публикации и контекст Feed, после чего возвращать результат вычисления.

### **7.1. SourcePathRegistry**

В первом MVP доступны следующие пути:

| Source path          | Type   | Данные                  |
| -------------------- | ------ | ----------------------- |
| `item.title`         | STRING | Локализованное название |
| `item.description`   | TEXT   | Локализованное описание |
| `item.regular_price` | MONEY  | Цена и валюта           |

Каждый Source path имеет зарегистрированный контракт и обработчик.

```
@dataclass(frozen=True)class SourceDefinition:    provider: str    path: str    value_type: FieldValueTypeclass SourcePathRegistry:    def __init__(self):        self.sources: dict[str, SourceDefinition] = {}    def register(        self,        definition: SourceDefinition,    ) -> None:        self.sources[definition.path] = definition    def validate(        self,        source: SourceReference,        value_type: FieldValueType,    ) -> None:        definition = self.sources.get(source.path)        if definition is None:            raise UnknownSourcePath()        if not types_are_compatible(            definition.value_type,            value_type,        ):            raise SourceTypeMismatch()
```

Нужно избежать исполнения пользовательских выражений через `eval()`, произвольных SQL-запросов и динамического доступа к Python-атрибутам.

SourcePath — только зарегистрированный идентификатор.

### **7.2. Контракт CatalogProductReader**

```
@dataclass(frozen=True)class CatalogProductSnapshot:    id: UUID    title: str | None    description: str | None    regular_price: MoneyVO | None    revision: strclass CatalogProductReader(Protocol):    async def get_many(        self,        item_ids: tuple[UUID, ...],        locale: str,    ) -> dict[UUID, CatalogProductSnapshot]:        ...
```

Реализация находится в Infrastructure.

Она использует публичный контракт чтения Catalog, а не его доменные агрегаты.

Описание из Catalog для MVP должно возвращаться как текст. Если Catalog хранит HTML, адаптер обязан либо предоставить отдельную plain-text проекцию, либо использовать явно зарегистрированное безопасное преобразование. Не следует передавать HTML в XML без определённого контракта.

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

```
class FieldValueResolver:    def resolve(        self,        field: FieldDefinition,        publication: FeedPublication,        snapshot: CatalogProductSnapshot,        context: ResolutionContext,    ) -> ResolvedField:        issues = []        # 1. Получаем исходное значение.        source_value = self.source_resolver.resolve(            field.source,            snapshot,        )        # 2. Определяем режим.        override = publication.overrides.get(field.id)        if override is not None:            mode = override.mode        else:            mode = field.default_mode        # 3. Выбираем конечный источник.        if mode == ValueMode.MANUAL:            raw_value = (                override.value if override else None            )        else:            raw_value = source_value        # 4. Приводим к доменному типу.        try:
```

`source_resolver.resolve()` для поля без источника должен возвращать `None`. Для поля со ссылкой на источник, который временно недоступен, необходимо возвращать отдельную ошибку `SOURCE_UNAVAILABLE`, а не трактовать её как обычное отсутствие значения.

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

```
from decimal import Decimal, ROUND_CEILINGclass MoneyCeilStepTransform:    operation = "money.ceil_step"    def apply(        self,        value: MoneyVO,        parameters: dict,        context: ResolutionContext,    ) -> MoneyVO:        step = Decimal(parameters["step"])        if step <= 0:            raise InvalidTransformParameters()        if value.currency != context.feed_currency:            raise CurrencyMismatch()        units = (            value.amount / step        ).to_integral_value(rounding=ROUND_CEILING)        return MoneyVO(            amount=units * step,            currency=value.currency,        )
```

При цене `590.21` и шаге `0.1` итоговое значение будет `590.3`. На этапе сериализации цены в MVP используется фиксированная точность два знака: `590.30`.

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

```
class AddCatalogItemsToFeed:    async def execute(        self,        command: AddItemsCommand,    ) -> list[FeedPublicationId]:        products = await self.catalog.get_many(            command.catalog_item_ids,            command.locale,        )        self.validate_products(products, command.catalog_item_ids)        async with self.uow_factory() as uow:            feed = await uow.feeds.get(command.feed_id)            if feed.active_schema_version is None:                raise SchemaNotPublished()            result = []            for item_id in command.catalog_item_ids:                publication = await (                    uow.publications.get_or_create(                        feed_id=feed.id,                        catalog_item_id=item_id,                        catalog_variant_id=None,                    )                )                result.append(publication.id)            await uow.projection_tasks.enqueue_many(result)        return result
```

`get_or_create()` должен быть идемпотентным и учитывать SQL UNIQUE constraint, в том числе при конкурентных запросах.

### **8.2. SetPublicationOverride**

```
class SetPublicationOverride:    async def execute(        self,        command: SetOverrideCommand,    ) -> None:        async with self.uow_factory() as uow:            publication = await uow.publications.get(                command.publication_id            )            feed = await uow.feeds.get(                publication.feed_id            )            schema = await uow.schemas.get_published(                feed.id,                feed.active_schema_version,            )            field = schema.get_field(command.field_id)            # Проверяем базовую совместимость значения            # с типом поля, но не блокируем ввод из-за            # длины строки или ограничения диапазона.            self.types.validate_input_type(                field.value_type,                command.value,            )            publication.set_override(                field_id=field.id,                value=command.value,            )
```

Ручное значение, превышающее `max_length`, разрешено сохранить, но поле становится `INVALID`. Так пользователь не теряет ввод и может исправить значение в UI.

При изменении цены должен сохраняться объект Money с валютой. Если сумма не парсится как число, API возвращает ошибку типа, не записывая повреждённый override.

### **8.3. ResetPublicationOverride**

```
class ResetPublicationOverride:    async def execute(self, command):        async with self.uow_factory() as uow:            publication = await uow.publications.get(                command.publication_id            )            publication.reset_override(command.field_id)            await uow.publications.save(publication)            await uow.projections.invalidate(publication.id)
```

После удаления override значение вновь определяется `default_mode` из схемы. Для поля без Source это может привести к состоянию `NEEDS_INPUT`, что является корректным поведением.

### **8.4. PreviewFeedPublication**

Предпросмотр не требует сохранения промежуточной проекции.

```
class PreviewFeedPublication:    async def execute(        self,        publication_id: UUID,        schema_mode: str = "ACTIVE",    ) -> PublicationPreviewDTO:        publication = await self.publications.get(            publication_id        )        feed = await self.feeds.get(            publication.feed_id        )        schema = await self.schemas.get_for_preview(            feed.id,            mode=schema_mode,        )        product = await self.catalog.get(            publication.catalog_item_id,            locale=feed.locale,        )        resolved = self.resolver.resolve(            schema,            publication,            product,            context=ResolutionContext.for_feed(feed),        )        return self.preview_mapper.to_dto(            schema=schema,            publication=publication,
```

Поддерживаются два режима:

- `ACTIVE` — опубликованная схема, используемая при генерации.
- `DRAFT` — редактируемая схема для проверки изменений.

В режиме `DRAFT` пользователь может проверить изменения, не влияя на уже опубликованные CSV/XML.

### **8.5. RefreshPublicationProjection**

```
class RefreshPublicationProjection:    async def execute(self, publication_id: UUID):        publication = await self.publications.get(publication_id)        feed = await self.feeds.get(publication.feed_id)        schema = await self.schemas.get_active(feed.id)        product = await self.catalog.get(            publication.catalog_item_id,            feed.locale,        )        resolved = self.resolver.resolve(            schema,            publication,            product,            context=ResolutionContext.for_feed(feed),        )        await self.projections.upsert_if_current(            publication_id=publication.id,            schema_version=feed.active_schema_version,            publication_version=publication.version,            catalog_revision=product.revision,            resolved=resolved,        )
```

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

```
class RequestFeedGeneration:    async def execute(self, feed_id: UUID) -> UUID:        async with self.uow_factory() as uow:            feed = await uow.feeds.get_for_update(feed_id)            if feed.active_schema_version is None:                raise FeedSchemaNotPublished()            sequence = feed.generation_sequence + 1            generation = FeedGeneration.create(                feed_id=feed.id,                schema_version=feed.active_schema_version,                request_sequence=sequence,            )            feed.generation_sequence = sequence            await uow.feeds.save(feed)            await uow.generations.add(generation)        return generation.id
```

Задание создаётся транзакционно. Не нужно сначала сохранять строку в БД, а затем отправлять сообщение во внешний брокер без Outbox — это создаёт риск потерянного задания.

Для MVP PostgreSQL может выступать очередью заданий.

Worker забирает `PENDING` через `SELECT ... FOR UPDATE SKIP LOCKED`, помечает задание `RUNNING`, устанавливает lease и фиксирует транзакцию. PostgreSQL поддерживает такой подход именно для queue-подобных сценариев с несколькими потребителями.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

PostgreSQL



### **10.3. ExecuteFeedGeneration**

```
class ExecuteFeedGeneration:    async def execute(self, generation_id: UUID) -> None:        generation = await self.generations.claim(            generation_id        )        feed = await self.feeds.get(generation.feed_id)        schema = await self.schemas.get_published(            feed.id,            generation.schema_version,        )        staging = await self.staging.create(            generation_id        )        issues = []        total = 0        # Стабильный порядок и keyset pagination.        async for publications in self.publications.iter_batches(            feed_id=feed.id,            status=PublicationStatus.ENABLED,            batch_size=500,        ):            products = await self.catalog.get_many(                item_ids=tuple(                    p.catalog_item_id                    for p in publications                ),                locale=feed.locale,            )
```

Здесь операции `claim`, `complete`, `activate_if_current` выполняются в отдельных коротких транзакциях. Долгое чтение каталога и запись файлов не должны происходить внутри одной открытой SQL-транзакции.

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
| `POST`  | `/api/feed-builder/feeds`                     | `CreateFeed`          |
| `GET`   | `/api/feed-builder/feeds`                     | `ListFeeds`           |
| `GET`   | `/api/feed-builder/feeds/{id}`                | `GetFeed`             |
| `PATCH` | `/api/feed-builder/feeds/{id}`                | `UpdateFeedSettings`  |
| `GET`   | `/api/feed-builder/feeds/{id}/schema`         | `GetFeedSchema`       |
| `PUT`   | `/api/feed-builder/feeds/{id}/schema/draft`   | `SaveFeedSchemaDraft` |
| `POST`  | `/api/feed-builder/feeds/{id}/schema/publish` | `PublishFeedSchema`   |
| `GET`   | `/api/feed-builder/field-types`               | Поддерживаемые типы   |
| `GET`   | `/api/feed-builder/source-paths`              | Доступные источники   |

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

Для краткости префикс `/api/feed-builder` в нижней части таблицы опущен.

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

В ответе можно также возвращать `can_override`, `can_reset`, `is_stale` и метаданные редактора.

### **11.5. Единый формат ошибок**

```
class ApplicationErrorDTO(BaseModel):    code: str    message: str    field_id: UUID | None = None    details: dict = {}
```

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
| `CURRENCY_MISMATCH`      | Неверная валюта              |
| `VERSION_CONFLICT`       | Конкурентное изменение       |
| `SOURCE_UNAVAILABLE`     | Источник временно недоступен |

Использовать HTTP `404` для отсутствующих ресурсов, `409` для конфликтов версий и `422` для ошибок содержимого и конфигурации. Внутренние ошибки и недоступность зависимостей не следует маскировать под незаполненные поля товара.

## **12. Frontend — Vue 3 + TypeScript**

Фронтенд должен строиться по согласованному интерактивному прототипу и состоять из четырёх основных экранов.

### **12.1. Экран создания Feed**

**Основные компоненты:**

```
FeedCreatePage
 ├── FeedGeneralForm
 │    ├── NameInput
 │    ├── CodeInput
 │    ├── CurrencySelect
 │    └── LocaleSelect
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
| Title     | Вычисленное название                   |
| Price     | Вычисленная цена                       |
| Overrides | Количество ручных значений             |
| Readiness | Готово / Заполнить / Ошибка / Устарело |
| Issues    | Краткое описание проблемы              |
| Updated   | Время расчёта проекции                 |

Нужна серверная пагинация, фильтрация и сортировка. Не загружать все публикации на frontend.

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

### **12.5. Интерфейс экспорта**

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
| Отсутствует цена                     | `REQUIRED_VALUE_MISSING`              |
| Цена в другой валюте                 | `CURRENCY_MISMATCH`                   |
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

Рекомендую реализовать модуль семью срезами. Каждый должен включать необходимые изменения во всех соответствующих слоях, а не строиться по принципу «сначала весь Domain, затем весь Infrastructure».

## **1**

**Domain Foundation**

`Feed`, `FeedSchema`, `FieldDefinition`, Constraints, Transforms, `FeedPublication`, `FeedGeneration`, Value Objects, доменные ошибки и события.

Реализовать инварианты схемы, статусы, версионирование и правила overrides.

Готовность: все Domain Unit Tests проходят без PostgreSQL, FastAPI и SQLAlchemy.

## **2**

**Persistence Foundation**

Alembic-миграция, SQLAlchemy Models, Row Mappers, Repositories, Unit of Work.

Создать таблицы, уникальные ограничения, индексы, связь с tenant schema и поддержку `row_version`.

Готовность: агрегаты сохраняются и восстанавливаются без потери доменной типизации.

## **3**

**Feed CRUD + Schema Builder**

Use Cases создания Feed, сохранения draft, публикации схемы и получения реестра типов/источников.

Реализовать административный REST API и первые два экрана frontend — создание Feed и конструктор.

Готовность: пользователь создаёт прайс и собирает схему drag-and-drop.

## **4**

**Publication + Value Resolution**

CatalogProductReader, SourcePathRegistry, FieldTypeRegistry, TransformRegistry, FieldValueResolver, PublicationResolver и проекции.

Реализовать добавление товаров, редактирование overrides, список публикаций и карточку предпросмотра.

Готовность: товары автоматически наследуют данные Catalog, показывают ошибки и поддерживают ручные значения.

## **5**

**Export Engine**

Динамический `ExportRecord`, CSV/XML Serializers, ArtifactStorage, GenerationWorker, staging, история запусков и ошибки.

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

## **16. Что заложить сейчас для дальнейшего расширения**

Эти возможности не входят в первую реализацию, но должны учитываться в контрактах.

| Будущая возможность  | Уже подготовленный механизм                             |
| -------------------- | ------------------------------------------------------- |
| Категории Feed       | `reference` field type и отдельный Category Repository  |
| Характеристики       | Дополнительные SourcePath и типы полей                  |
| Вложенные объекты    | `FieldDefinition.kind` и `children`                     |
| Массивы изображений  | `array` + `media`                                       |
| Варианты товаров     | `catalog_variant_id`                                    |
| Переводы             | `locale` и локализованные SourcePath                    |
| AI-генерация         | `ai_instruction`, отдельный GenerateSuggestion Use Case |
| Динамическая выборка | FeedSelectionPolicy и Selection Engine                  |
| Расписание генераций | Планировщик, создающий Generation Request               |
| Prom/Rozetka         | Platform-specific FormatProfile и Serializer            |
| Валютная конвертация | `MoneyConvertTransform` через CurrencyRate Port         |
| Массовые изменения   | Bulk Override Application Service                       |

Особенно важно не объединять `FeedSchema` и `FeedPublication`. Это позволит добавлять все перечисленные возможности, не изменяя фундамент наследования и пользовательских значений.

## **17. Критерии завершения MVP**

Модуль можно считать реализованным, когда выполняется следующий сценарий:

1. Пользователь создаёт Feed с валютой UAH.
2. Конструктор автоматически предлагает поля Title, Description и Price.
3. Пользователь меняет порядок полей, source path, constraints и transforms.
4. Публикует версию схемы.
5. Добавляет несколько товаров из Catalog.
6. Получает автоматически заполненные публикации.
7. Для длинного Title видит ошибку ограничения.
8. Для отсутствующей цены видит требование заполнения.
9. Переопределяет проблемное поле.
10. Предпросмотр показывает исходное, ручное и конечное значения.
11. Все публикации переходят в `READY`.
12. Генерация создаёт CSV и XML.
13. Оба файла доступны по постоянным URL.
14. Изменение Catalog обновляет наследуемые значения при следующем разрешении.
15. Новая ошибочная генерация не уничтожает предыдущий корректный файл.

**Итоговая архитектура MVP:**

`Feed → FeedSchema → FeedPublication → ResolvedPublication → ExportRecord → FeedGeneration → Artifact`

Эта последовательность должна стать основным контрактом модуля. SQL хранит идентичность, конфигурацию и overrides; Application вычисляет значения; Domain защищает инварианты; Infrastructure сериализует и доставляет файлы; Presentation предоставляет универсальный конструктор.

Для начала реализации рекомендую зафиксировать API и доменные контракты первого среза, особенно `FieldDefinition`, `FeedSchema`, `FieldOverride` и `MoneyVO`. Именно они определяют совместимость последующих слоёв и возможность расширения FeedBuilder без переработки SQL-структуры.&#x20;