# Архитектура PriceBuilder на DDD + Clean Architecture

Я рекомендую реализовать PriceBuilder как самостоятельный Bounded Context, который управляет конфигурациями товарных фидов, преобразованием данных каталога и генерацией файлов для внешних платформ.

Главный принцип: Catalog определяет, что продаётся, а PriceBuilder — как эти товары должны быть представлены во внешнем файле.

При этом PriceBuilder не должен изменять товары в Catalog или отвечать за их публикацию через API маркетплейсов.

## 1. Варианты архитектуры

Рассмотрим три подхода.

| Подход                                    | Устройство                                                                | Оценка                                                            |
| ----------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1. Отдельный Builder для каждой платформы | `PromBuilder`, `RozetkaBuilder`, `CustomBuilder`, каждый со своей логикой | Просто для MVP, но много дублирования                             |
| 2. Универсальный конструктор              | Любой XML, JSON или CSV описывается динамической конфигурацией            | Максимально гибко, но сложно обеспечить платформенные ограничения |
| 3. Гибридная архитектура                  | Общее ядро генерации + платформенные профили + настраиваемый маппинг      | Рекомендую                                                        |

### Как должен работать гибридный подход

Catalog / Inventory / Pricing

Контент, характеристики, варианты, цены, наличие

## PriceBuilder Core

Единый механизм подготовки выгрузок

Feed Definition

Source Selection

Mapping Rules

Field Overrides

Validation

Build Engine

Prom Profile

XML / YML

Rozetka Profile

XML / YML

Custom Profile

XML / JSON / CSV

Feed Artifact

Сформированный файл + постоянный URL + история версий

В такой архитектуре:

- PriceBuilder Core отвечает за общую логику формирования фидов.
- Platform Profile определяет правила конкретной платформы: структуру, допустимые поля, категории, характеристики, ограничения и валидацию.
- Custom Profile позволяет пользователю создавать собственный формат выгрузки без программирования нового адаптера.
- Feed Artifact представляет готовый неизменяемый результат конкретной сборки.

Один и тот же товар может участвовать в десяти разных фидах, иметь разные цены, описания, категории и названия, но при этом оставаться единственным объектом в Catalog.

## 2. Границы ответственности модулей

| Модуль       | Ответственность                                                                       |
| ------------ | ------------------------------------------------------------------------------------- |
| Catalog      | Товары, варианты SKU, категории, характеристики, переводы, контент                    |
| Inventory    | Физические и внешние остатки, доступность товара                                      |
| Pricing      | Базовые цены, прайс-листы, денежные значения                                          |
| PriceBuilder | Отбор товаров, правила формирования полей, маппинг, валидация, генерация фидов        |
| Channels     | Подключения магазинов, внешние публикации, синхронизация через API, получение заказов |

Важно сохранить различие между `Feed` и `Publication`.

`Feed` — это конфигурация и результат экспорта набора товаров.

`Publication` — это представление конкретной товарной позиции в определённом внешнем магазине. Если в Channels уже существует такой объект, PriceBuilder не должен его дублировать.

PriceBuilder может работать совершенно самостоятельно: например, пользователь создаёт XML для поставщика или JSON-фид для своего сайта, вообще не подключая Channels.

## 3. Доменная модель PriceBuilder

Я бы выделил 5 основных Aggregate Roots и отдельный механизм стабильной идентификации экспортируемых товаров.

## FeedDefinition

Главный агрегат конфигурации фида

FeedTemplate

Структура выходного файла

FeedCategoryMapping

Категории и атрибуты

FeedItemOverride

Индивидуальные изменения

FeedBuild

Запуски и результаты сборок

Связи по идентификаторам. Каждый агрегат имеет собственный жизненный цикл и транзакционную границу.

### 3.1. FeedDefinition — основной Aggregate Root

Представляет конкретную выгрузку, созданную пользователем.

Например:

- `Prom — Магазин №1`
- `Rozetka — Основной магазин`
- `XML поставщику`
- `JSON для внешнего сайта`

Предлагаемая структура:

```
class FeedDefinition(AggregateRoot):    id: FeedId    name: str    profile: PlatformProfileRef    template: FeedTemplateVersionRef    source: FeedSourceSelection    mapping: FeedMappingConfig    pricing_policy: FeedPricingPolicy    availability_policy: FeedAvailabilityPolicy    localization_policy: LocalizationPolicy    variant_policy: VariantExportPolicy    validation_policy: FeedValidationPolicy    output: FeedOutputConfig    schedule: FeedSchedule    status: FeedStatus    revision: int
```

Основные Value Objects и Entities:

| Объект                   | Для чего нужен                                    |
| ------------------------ | ------------------------------------------------- |
| `FeedSourceSelection`    | Определяет, какие товары попадают в фид           |
| `FeedMappingConfig`      | Настройки преобразования базовых полей            |
| `FeedPricingPolicy`      | Как определяется экспортируемая цена              |
| `FeedAvailabilityPolicy` | Как рассчитываются наличие и доступное количество |
| `LocalizationPolicy`     | Языки и правила подстановки переводов             |
| `VariantExportPolicy`    | Один товар или отдельная строка на каждый SKU     |
| `FeedValidationPolicy`   | Что делать с товарами, которые не прошли проверку |
| `FeedOutputConfig`       | Формат, кодировка, URL, настройки доступа         |
| `FeedSchedule`           | Периодичность генерации                           |

Здесь важно не превращать `FeedDefinition` в огромный объект, содержащий тысячи товаров, категорий и маппингов.

Он управляет конфигурацией, а не результатами работы.

Бизнес-методы агрегата:

```
feed.rename(...)feed.set_source_selection(...)feed.configure_pricing(...)feed.configure_availability(...)feed.change_template(...)feed.update_mapping(...)feed.set_schedule(...)feed.activate()feed.pause()feed.archive()
```

Каждое значимое изменение конфигурации увеличивает `revision`. Запущенная сборка всегда привязывается к конкретной ревизии.

### 3.2. FeedTemplate — шаблон структуры

`FeedTemplate` определяет структуру данных, которую должен сформировать PriceBuilder.

Главное различие:

- `FeedDefinition` — конкретный настроенный фид.
- `FeedTemplate` — переиспользуемая схема формирования данных.

Например, пользователь создаёт пять фидов Prom для пяти магазинов. Все могут использовать один стандартный шаблон `PROM_YML`, но у каждого будут собственные товары, цены и настройки.

```
class FeedTemplate(AggregateRoot):    id: FeedTemplateId    name: str    type: TemplateType    profile_key: str | None    revisions: list[TemplateRevision]    status: TemplateStatus
```

`TemplateRevision` содержит:

| Entity / VO         | Ответственность                                      |
| ------------------- | ---------------------------------------------------- |
| `DocumentStructure` | Корневой элемент, секции, вложенность                |
| `FieldDefinition`   | Определение выходных полей                           |
| `FieldMappingRule`  | Источник значения поля                               |
| `TransformRule`     | Конвертация, форматирование, округление              |
| `ValidationRule`    | Ограничения конкретного поля                         |
| `CollectionRule`    | Как выводить массивы: фото, варианты, характеристики |

При этом я предлагаю два типа шаблонов.

System Template — стандартные версии Prom и Rozetka. Их структура контролируется платформенным адаптером и не может произвольно меняться пользователем.

Custom Template — пользователь самостоятельно определяет поля, вложенность XML, источники данных и преобразования.

Ревизии опубликованных шаблонов должны быть неизменяемыми. Изменения создают новую версию, чтобы старые сборки можно было воспроизвести.

### 3.3. FeedCategoryMapping — маппинг категорий и атрибутов

Это особенно важный агрегат для маркетплейсов.

Категория в Catalog не обязана соответствовать категории Prom или Rozetka.

Например:

Catalog

Витамины и минералы

Атрибуты: Форма выпуска, Дозировка, Количество

Prom

Внешняя категория A

Свой набор атрибутов и допустимых значений

Rozetka

Внешняя категория B

Собственные параметры, ID и справочники значений

Модель:

```
class FeedCategoryMapping(AggregateRoot):    id: FeedCategoryMappingId    feed_id: FeedId    catalog_category_id: CategoryId    external_category_id: str    attribute_mappings: list[AttributeMapping]    value_mappings: list[AttributeValueMapping]    revision: int
```

`AttributeMapping` отвечает за соответствие характеристик:

```
Catalog: dosage
      ↓
Rozetka: external_attribute_123
```

А `AttributeValueMapping` сопоставляет допустимые значения:

```
Catalog: "capsule"
      ↓
Rozetka: "Капсули" / external_value_id
```

Это позволяет отдельно работать с категориями, атрибутами и справочниками каждой платформы.

Если маппингов очень много, их лучше хранить по одной категории на агрегат, а не загружать целиком через `FeedDefinition`.

### 3.4. FeedItemOverride — переопределение отдельного товара

Этот агрегат нужен, чтобы один и тот же SKU имел разные представления в разных фидах.

Например, в Catalog:

```
Name: NOW Foods Vitamin D3 2000 IU
Price: 450 UAH
Description: Базовое описание
```

В фиде Prom:

```
Name: Вітамін D3 NOW Foods 2000 МО, 120 капсул
Price: 490 UAH
```

В фиде Rozetka:

```
Name: NOW Foods Vitamin D3 2000 IU, 120 шт
Price: 475 UAH
```

При этом Catalog не изменяется.

```
class FeedItemOverride(AggregateRoot):    id: FeedItemOverrideId    feed_id: FeedId    catalog_item_id: CatalogItemId    field_overrides: list[FieldOverride]    external_category_override: str | None
```

Здесь `FieldOverride` должен поддерживать три операции:

| Операция  | Поведение                              |
| --------- | -------------------------------------- |
| `INHERIT` | Использовать значение по правилам фида |
| `SET`     | Использовать конкретное значение       |
| `CLEAR`   | Явно очистить необязательное поле      |

Это лучше обычного `value: null`, потому что позволяет различать отсутствие настройки и намеренную очистку поля.

Порядок получения значения я бы сделал следующим:

Catalog value

Feed Mapping Rule

Category-specific Rule

Item / SKU Override

Target Validation

После применения override поле всё равно проходит проверку платформенного профиля. Пользователь не должен иметь возможности сломать обязательную XML-структуру произвольным значением.

### 3.5. FeedBuild — агрегат запуска генерации

`FeedBuild` представляет одну попытку сформировать фид.

```
class FeedBuild(AggregateRoot):    id: FeedBuildId    feed_id: FeedId    feed_revision: int    template_revision_id: TemplateRevisionId    status: FeedBuildStatus    source_snapshot: SourceSnapshotRef    statistics: FeedBuildStatistics    artifact: FeedArtifactRef | None    started_at: datetime | None    completed_at: datetime | None
```

`FeedBuildStatistics` содержит:

- количество найденных товаров;
- количество сформированных строк `Offer`;
- количество пропущенных позиций;
- ошибки и предупреждения;
- размер итогового файла;
- продолжительность выполнения.

Ошибки отдельных товаров могут храниться в отдельной append-only таблице, чтобы агрегат не загружал тысячи записей в память.

`FeedArtifact` — неизменяемый файл с метаданными:

```
artifact_id
feed_build_id
storage_key
content_type
size_bytes
checksum
created_at
```

Физически файл хранится в S3-совместимом хранилище, а в PostgreSQL находятся только метаданные.

### 3.6. FeedOfferIdentity — стабильный внешний идентификатор

Я бы также предусмотрел отдельное постоянное сопоставление:

```
FeedId
CatalogItemId / VariantId
ExternalOfferId
ExternalGroupId
```

Внешние идентификаторы не должны зависеть от текущего названия, категории или других редактируемых полей товара.

Если нужный формат позволяет использовать стабильный внутренний идентификатор, отдельную выдачу ID можно упростить. Если платформа требует другую схему идентификаторов, используется сохранённое сопоставление.

Это важно для корректного обновления уже созданных товаров. Например, документация Rozetka для XML-импорта через Pricecreator прямо требует сохранять идентификаторы товаров и категорий неизменными.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sellerhelp.rozetka.com.ua\&sz=32)

sellerhelp.rozetka.com.ua



## 4. Внутренняя модель данных для генерации

Я бы не передавал ORM-объекты Catalog прямо в генератор XML.

Вместо этого нужен отдельный канонический DTO для экспорта.

Например:

```
@dataclass(frozen=True)class ExportProduct:    product_id: UUID    variant_id: UUID | None    sku: str    title: dict[str, str]    description: dict[str, str]    category_ids: tuple[UUID, ...]    attributes: dict[str, object]    images: tuple[str, ...]    price: Money    availability: AvailabilitySnapshot
```

Это не Aggregate Root, а промежуточная read-модель.

Для неё необходимы три основных источника:

| Источник                | Что получает PriceBuilder                            |
| ----------------------- | ---------------------------------------------------- |
| `CatalogExportReader`   | Контент, структуру товаров, варианты, характеристики |
| `PricingExportReader`   | Цены, валюту, стоимость продажи                      |
| `InventoryExportReader` | Доступность, количество, наличие на складах          |

Если отдельного Pricing пока нет, источник цены может быть адаптером к Catalog. Это не должно менять интерфейс PriceBuilder.

### Product и Offer — разные сущности

`CatalogProduct` может содержать несколько вариантов. А `FeedOffer` — это отдельная продаваемая позиция в конкретной выгрузке.

```
CatalogProduct
  ├── Variant: 30 капсул
  ├── Variant: 60 капсул
  └── Variant: 120 капсул

             ↓ Export

FeedOffer: 30 капсул
FeedOffer: 60 капсул
FeedOffer: 120 капсул
```

Поэтому следует ввести промежуточный объект `FeedOffer`, который содержит уже рассчитанные и преобразованные значения, готовые к сериализации.

`FeedOffer` — DTO/проекция результата обработки, а не доменная товарная сущность, которую нужно постоянно хранить как отдельный Aggregate Root.

Это решение позволяет добавлять новые форматы, не изменяя модель Catalog.

## 5. PlatformProfile — главный механизм расширения

Для Prom, Rozetka и кастомных фидов я бы использовал паттерн Strategy + Registry.

Общий Build Engine не должен знать, какие XML-теги использует конкретный маркетплейс.

Вместо этого он обращается к интерфейсу:

```
class PlatformFeedProfile(Protocol):    def validate_configuration(        self, definition: FeedDefinition    ) -> ValidationResult: ...    def build_offers(        self, product: ExportProduct,        context: MappingContext    ) -> list[FeedOffer]: ...    def validate_offer(        self, offer: FeedOffer    ) -> list[FeedIssue]: ...    def get_renderer(self) -> FeedRenderer: ...
```

Конкретные реализации:

```
PlatformFeedProfile
    │
    ├── PromYmlProfile
    ├── RozetkaXmlProfile
    ├── CustomXmlProfile
    ├── CustomJsonProfile
    └── CustomCsvProfile
```

Каждый профиль должен предоставлять ещё и декларативный `ProfileDescriptor`: доступные поля, обязательные поля, поддерживаемые языки, правила вариантов, категории, типы значений и версию спецификации. Эти метаданные используются frontend-конструктором.

### Почему Prom и Rozetka должны иметь отдельные профили

Хотя обе платформы используют XML/YML, требования к структуре, категориям и характеристикам различаются. Prom поддерживает импорт XML и YML, а для группировки разновидностей в YML используется `group_Id`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://prom.ua\&sz=32)

№1 Платформа для продажу в Україні+1



У Rozetka собственный процесс обработки XML. Например, при импорте через Pricecreator характеристики могут содержать многоязычные значения, а сами параметры впоследствии сопоставляются с характеристиками Rozetka.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sellerhelp.rozetka.com.ua\&sz=32)

sellerhelp.rozetka.com.ua



| Возможность    | PromProfile                  | RozetkaProfile                  | CustomProfile            |
| -------------- | ---------------------------- | ------------------------------- | ------------------------ |
| Формат         | Prom YML/XML                 | Rozetka XML                     | XML/JSON/CSV             |
| Категории      | Схема Prom                   | Схема Rozetka                   | Произвольная             |
| Характеристики | Правила Prom                 | Правила и справочники Rozetka   | Пользовательский маппинг |
| Варианты       | Группировка по правилам Prom | Группировка по правилам Rozetka | Настраивается            |
| XML-структура  | Фиксированная                | Фиксированная                   | Настраиваемая            |
| Валидация      | Спецификация Prom            | Спецификация Rozetka            | Правила пользователя     |

Здесь особенно важно разделить структуру документа и источник значения поля.

Например, `PromYmlProfile` самостоятельно определяет, как сериализовать название на украинском языке. Пользователь должен выбирать, откуда взять значение, а не вручную создавать произвольный XML-тег.

Для CustomProfile пользователь получает контроль над обоими уровнями.

## 6. Как реализовать динамический маппинг полей

Предлагаю использовать декларативные `FieldMappingRule`, а не выполнять произвольный Python-код или Jinja-шаблоны от пользователя.

Например, конфигурация фида:

```

{
  "name": "Prom - Store 1",
  "profile": "PROM_YML",
  "source": {
    "categories": ["vitamins", "minerals"],
    "include_variants": true
  },
  "field_rules": [
    {
      "target": "title.uk",
      "source": "catalog.title",
      "locale": "uk"
    },
    {
      "target": "price",
      "source": "pricing.selling_price",
      "transforms": [
        {
          "type": "PERCENT_MARKUP",
          "value": "7"
        },
        {
          "type": "ROUND",
          "step": "1"
        }
      ]
    },
    {
      "target": "available",
      "source": "inventory.availability"
    }
  ]
}

```

Пример внутренней конфигурации, не буквальная спецификация XML платформы.

Нужен небольшой набор типизированных преобразований:

| Transform          | Назначение                             |
| ------------------ | -------------------------------------- |
| `COALESCE`         | Первое непустое значение               |
| `CONCAT`           | Соединение строк                       |
| `TEMPLATE`         | Создание строки из разрешённых токенов |
| `PERCENT_MARKUP`   | Наценка для конкретного фида           |
| `CURRENCY_CONVERT` | Перевод в нужную валюту                |
| `ROUND`            | Округление по правилу                  |
| `MAP_VALUE`        | Сопоставление значений атрибутов       |
| `FORMAT_DATE`      | Форматирование даты                    |
| `FORMAT_BOOLEAN`   | Преобразование в нужное представление  |

Ценовые операции должны использовать `Decimal` и объекты `Money`, а не `float`.

### Особенность CustomFeed

Пользователь может задать собственную структуру, например:

```
<products>
    <product id="1001">
        <title>Vitamin D3</title>
        <price currency="UAH">450</price>
        <stock>12</stock>
    </product>
</products>
```

Конструктор должен позволять определить:

- корневой XML-элемент;
- повторяющийся элемент товара;
- вложенные элементы и атрибуты;
- источник значения каждого элемента;
- преобразования, обязательность и значение по умолчанию.

Для JSON и CSV используется тот же механизм получения и обработки значений — меняется только сериализатор.

Это позволит поддерживать кастомные выгрузки без создания нового модуля или изменения Catalog.

## 7. Жизненный цикл Feed

Предлагаю разделить жизненный цикл конфигурации и жизненный цикл сборки файла.

### Жизненный цикл FeedDefinition

DRAFT

ACTIVE

PAUSED

ARCHIVED

`DRAFT` — конфигурация создаётся и редактируется. `ACTIVE` — генерация разрешена по расписанию или событию. `PAUSED` — автоматическая генерация выключена. `ARCHIVED` — фид выведен из использования.

### Жизненный цикл FeedBuild

1\. REQUESTED

Запрос на генерацию

2\. COLLECTING

Чтение Catalog, Pricing, Inventory

3\. PROJECTING

Формирование FeedOffer и применение Mapping

4\. VALIDATING

Проверка требований профиля

5\. RENDERING

Создание XML / JSON / CSV

6\. STAGING

Сохранение и проверка временного файла

7\. PUBLISHED

Переключение URL на готовую версию

FAILED / CANCELLED

Сборка может завершиться ошибкой или отменой. Последний успешно опубликованный файл при этом не изменяется.

### Важные технические правила

1\. Сборка всегда использует фиксированную конфигурацию. Если пользователь изменил маппинг во время генерации, выполняющаяся сборка продолжает использовать прежнюю ревизию.

2\. Не обновлять рабочий файл напрямую. Сначала создать новый Artifact, проверить его, после чего атомарно обновить указатель `current_artifact_id`.

3\. Нельзя отдавать битый фид. Если новый файл не прошёл проверку, постоянный URL продолжает возвращать предыдущую успешную версию.

4\. Нужна защита от массовой потери товаров. Например, если в новом фиде вместо 10 000 предложений осталось 20, публикацию следует остановить или отправить на подтверждение, в зависимости от настроенной политики.

5\. Не путать генерацию и импорт маркетплейсом. Статус `PUBLISHED` означает, что готовый файл доступен, но не гарантирует появление товаров на платформе. Для Rozetka, например, новые позиции после получения XML могут дополнительно проходить модерацию.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sellerhelp.rozetka.com.ua\&sz=32)

sellerhelp.rozetka.com.ua



### Как запускать новые сборки

Предусмотрите три триггера:

| Триггер      | Пример                               |
| ------------ | ------------------------------------ |
| Manual       | Пользователь нажал «Сгенерировать»   |
| Scheduled    | Каждые 30 минут                      |
| Event-driven | Изменилась цена, наличие или контент |

При этом событие изменения одного SKU не обязательно должно немедленно перегенерировать весь фид. Нужен механизм `dirty flag + debounce`, который объединяет несколько изменений в одну сборку.

Для большого количества товаров в дальнейшем можно добавить отдельную материализованную проекцию `ExportProductProjection`, обновляемую через события Catalog, Pricing и Inventory.

## 8. Структура проекта с Clean Architecture

Учитывая Python, FastAPI, SQLAlchemy и твой подход с UoW, я бы предложил следующую структуру:

```

price_builder/
│
├── domain/
│   ├── aggregates/
│   │   ├── feed_definition.py
│   │   ├── feed_template.py
│   │   ├── feed_category_mapping.py
│   │   ├── feed_item_override.py
│   │   └── feed_build.py
│   │
│   ├── entities/
│   │   ├── field_mapping_rule.py
│   │   ├── attribute_mapping.py
│   │   ├── attribute_value_mapping.py
│   │   └── template_revision.py
│   │
│   ├── value_objects/
│   │   ├── feed_source_selection.py
│   │   ├── feed_policies.py
│   │   ├── feed_output_config.py
│   │   └── field_override_value.py
│   │
│   ├── services/
│   │   ├── field_resolution_service.py
│   │   ├── price_policy_service.py
│   │   └── feed_validation_service.py
│   │
│   └── events/
│
├── application/
│   ├── commands/
│   │   ├── create_feed.py
│   │   ├── update_feed.py
│   │   ├── activate_feed.py
│   │   └── request_feed_build.py
│   │
│   ├── use_cases/
│   │   ├── preview_feed.py
│   │   ├── generate_feed.py
│   │   └── publish_feed_artifact.py
│   │
│   ├── ports/
│   │   ├── catalog_export_reader.py
│   │   ├── inventory_export_reader.py
│   │   ├── pricing_export_reader.py
│   │   ├── platform_profile_registry.py
│   │   ├── feed_renderer.py
│   │   └── artifact_storage.py
│   │
│   └── dto/
│       ├── export_product.py
│       └── feed_offer.py
│
├── infrastructure/
│   ├── persistence/
│   ├── readers/
│   ├── profiles/
│   │   ├── prom/
│   │   ├── rozetka/
│   │   └── custom/
│   ├── renderers/
│   │   ├── xml_renderer.py
│   │   ├── json_renderer.py
│   │   └── csv_renderer.py
│   ├── storage/
│   └── workers/
│
└── presentation/
    ├── console_api/
    └── public_feed_api/

```

Ключевой момент: Application Use Case координирует получение данных, применение правил и вызов сериализатора. Domain содержит бизнес-правила, но не знает про SQLAlchemy, FastAPI, S3 или XML-библиотеки.

Генерацию большого файла необходимо выполнять в worker, без долгой транзакции БД. Отдельные транзакции фиксируют создание `FeedBuild`, смену состояний и публикацию Artifact. Commit/rollback остаются обязанностью UoW.

## 9. Предлагаемая структура БД

Для твоей модели multi-tenancy с отдельной PostgreSQL-схемой на tenant достаточно заложить следующие таблицы:

| Таблица                   | Содержимое                           |
| ------------------------- | ------------------------------------ |
| `feed_definitions`        | Основные конфигурации фидов          |
| `feed_template_revisions` | Версии схем и правил шаблонов        |
| `feed_category_mappings`  | Соответствия категорий и атрибутов   |
| `feed_item_overrides`     | Переопределения товаров и SKU        |
| `feed_offer_identities`   | Стабильные экспортные идентификаторы |
| `feed_builds`             | Запуски генерации                    |
| `feed_build_issues`       | Ошибки и предупреждения              |
| `feed_artifacts`          | Метаданные готовых файлов            |

Конфигурации правил разумно хранить в `JSONB`, но идентификаторы, статусы, связи, версии и даты — в типизированных колонках.

В будущих версиях можно добавить `feed_source_projection` или `feed_offer_snapshots` для ускорения генерации, анализа изменений и инкрементальных экспортов, не меняя модель основных агрегатов.

Для файлов использовать объектное хранилище, а постоянный URL фида должен разрешаться через актуальный Artifact.

## 10. Что включить в MVP

Я бы не начинал с полноценного визуального конструктора произвольного XML. Сначала нужно создать устойчивое ядро.

| Функциональность                            | MVP | Далее |
| ------------------------------------------- | --- | ----- |
| FeedDefinition и управление статусами       |     |       |
| System Profiles: Prom, Rozetka              |     |       |
| Выбор категорий, товаров и вариантов        |     |       |
| Mapping основных полей                      |     |       |
| Маппинг категорий и характеристик           |     |       |
| Индивидуальный FieldOverride                |     |       |
| Базовый Custom XML/JSON                     |     |       |
| Preview и Validation                        |     |       |
| Генерация по расписанию                     |     |       |
| История сборок, Artifact, постоянный URL    |     |       |
| Визуальный drag-and-drop XML Builder        |     |       |
| Полноценный редактор выражений              |     |       |
| Инкрементальная генерация и diff            |     |       |
| Автоматическая загрузка таксономий платформ |     |       |
| Отправка файлов через FTP/SFTP, Webhook     |     |       |

При этом в MVP стоит заложить интерфейсы для новых Profile и Renderer, поддержку версий шаблонов, неизменяемые Artifact и стабильные Offer ID. Именно эти решения позволят расширять систему без фундаментальной переделки.

## 11. Финальное архитектурное решение

Моя рекомендация — реализовать PriceBuilder вокруг следующего разделения:

FeedDefinition — что выгружаем

Выбор товаров, фильтры, политики цен и наличия, язык, расписание, назначение.

FeedTemplate + PlatformProfile — в каком формате

Схема документа, обязательные поля, платформенная специфика, правила сериализации.

Mapping + Overrides — как преобразуем

Источники значений, категории, атрибуты, индивидуальные настройки товаров.

FeedBuild + Artifact — что получилось

Генерация, проверка, сохранение, версии, публикация по URL.

Главное проектное решение: не создавать отдельный бизнес-процесс генерации для каждого маркетплейса. Вместо этого должен существовать один pipeline:

`Source → Normalize → Map → Override → Validate → Render → Publish`

Все различия между Prom, Rozetka и произвольными форматами изолируются в профилях, правилах отображения данных и сериализаторах.

Так PriceBuilder останется независимым от Channels, не будет дублировать Catalog и сможет использоваться как универсальный сервис товарных выгрузок.&#x20;