> Архивный план. После очистки от 31.10.2026 в Channels остаются только каналы,
> подключения и проверка доступа. Товарные сценарии ниже не описывают текущую реализацию.
> Актуальная граница: [Channels](../modules/channels.md).

# Channels: представления публикаций, overrides и доставка контента

Статус: композиция, overrides, media, ручная API-доставка WooCommerce и постоянный
XML-фид Prom, ручная отправка ссылки в API Prom и наблюдение в Console реализованы.
Автоматическая API-доставка остаётся планом.
Сохранён 30.10.2026 по обсуждению в чате.

Реализованы базовое формирование представления/preview и `ProductRepresentation`
с редактором общих/индивидуальных overrides, ревизиями и отдельным разрешением
экспорта. Добавлена только `channel_product_representations`; её запись создаётся
лениво первым сохранением. При изменении состава сопоставлений неизменные пары
и их overrides сохраняются, разрешение выключается.
Текущее поведение описано в [документации Channels](../modules/channels.md#представление-публикаций-и-preview).
Дополнительно реализована `channel_content_media`: ограниченные URL, проверка Files,
соответствия внешним ID, защита удаления и конкретный Woo gallery adapter. Автоматическая
API-доставка контента остаётся планом следующих срезов; XML Prom реализован отдельно. SQL media ниже —
исходный эскиз; актуальная модель с отдельными статусом, ID операции, ревизией и
metadata fingerprint описана в документации Channels.
Реализован первый полный ручной путь WooCommerce с `channel_content_deliveries`,
зашифрованным подготовленным запросом, поколениями/lease, сверкой unknown и
результатами по целям в Console. SQL deliveries ниже — первоначальный эскиз;
актуальные поля и ограничения описаны в
[ручной доставке](../modules/channels.md#ручная-доставка-контента-woocommerce).
Автоматические события Catalog и расширенные галереи вариаций в него не входят.
Реализован backend-срез `ContentFeed`: `channel_content_feeds`, serializer Prom YML,
управление источником/токеном, preview и постоянный публичный endpoint.
SQL feeds ниже — первоначальный эскиз; актуальные поля без delivery_state и
границы среза описаны в [XML-фиде Prom](../modules/channels.md#постоянный-xml-фид-prom).
Добавлена ручная доставка ссылки через Shared Jobs, восстановление неоднозначного
принятия, отчёт и независимая проверка полей в Console. Миграция
`0015_channels_feed_import` расширяет существующую таблицу ContentFeed; новых
таблиц нет. Точные состояния и ограничения описаны в
[применении XML через API Prom](../modules/channels.md#применение-xml-через-api-prom).
Для реализованной части действуют уточнения текущей документации:
версия документа `representation_overrides.v1`, три expected-revision токена,
нулевая ревизия только в read-state до сохранения и экспорт по умолчанию выключен.

Документ фиксирует следующий срез после получения публикаций и сопоставления с Catalog. Он описывает целевое поведение, а не готовность текущего runtime. Перед реализацией необходимо сверить существующие контракты и переиспользовать уже готовые механизмы.

Связанные документы: [текущий Channels](../modules/channels.md), [Catalog](../modules/catalog.md), [Shared encryption](../modules/shared-encryption.md), [архитектура backend](../architecture/backend.md), [архитектура frontend](../architecture/frontend.md).

Исторический [общий план Channels](channels-integrations.md) не заменяет границы и решения этого среза.

Следующий срез предлагаю строить вокруг **`ProductRepresentation` — желаемого представления существующей публикации на основе Catalog и локальных overrides**.

Это отдельный объект от `ExternalPublication`: импорт продолжает хранить фактические данные площадки, а representation определяет, какие данные мы хотим ей передать.

Исходные решения для этого плана: **названия, описания и галерея; preview; API WooCommerce; XML Prom/Rozetka**. XML сохраняет полный исходный ассортимент и накладывает изменения сопоставленных позиций. Эти допущения определяют объём описанных ниже моделей и этапов.

## 1. Границы среза

Пользователь сможет:

1. Открыть существующую группу сопоставлений.
2. Увидеть представление, сформированное из актуального Catalog.
3. Переопределить контент для этой группы или отдельной сопоставленной позиции.
4. Сравнить источник, переопределения и итог.
5. Проверить готовность представления для выбранной платформы.
6. Явно разрешить экспорт.
7. Получать обновления через API либо постоянный XML endpoint.

В этот срез не входят:

- создание новых публикаций и изменение структуры внешних вариантов;
- переопределение SKU, внешних идентификаторов, цен и остатков;
- редактор внешних категорий, характеристик и правил их сопоставления;
- автоматический перевод.

Для XML обязательные категории, характеристики и прочие неизменяемые поля сохраняются из исходного фида. Они не становятся новыми справочниками Channels.

**Создание связи само по себе не включает экспорт.** У нового representation экспорт выключен.

## 2. Объекты и правила формирования

Основной поток:

```text
Catalog: актуальная семья и эффективные значения
                         +
CatalogBindingGroup: режим и сопоставленные позиции
                         +
ProductRepresentation: overrides и разрешение экспорта
                         +
ExternalPublication: внешние цели и платформенные ключи
                         ↓
              PreparedRepresentation
                         ↓
           Проверки пакета платформы
                         ↓
              Preview / API / XML
```

### Сохраняемые и вычисляемые объекты

| Объект | Ответственность | Хранение |
|---|---|---|
| `CatalogBindingGroup` | Какие позиции сопоставлены | Существующее |
| `ExternalPublication` | Последний наблюдаемый снимок площадки | Существующее |
| `ProductRepresentation` | Overrides и разрешение экспорта одной группы | Новое |
| `PreparedRepresentation` | Итоговый контент, цели, происхождение значений и ошибки | Вычисляется |
| `ContentDelivery` | Текущее состояние доставки в API для конкретной цели | Новое |
| `ContentFeed` | Постоянный XML endpoint и настройки источника | Новое |
| `ContentMedia` | Доступ площадки к изображениям и соответствия внешних media ID | Новое при поддержке галереи |

**Готовый representation не сохраняем вторым полным снимком Catalog.** Preview и экспорт собирают его одним и тем же сервисом из актуальных данных.

Для API сохраняется только подготовленный запрос на время исполнения: worker должен понимать, какой именно контент он отправил.

### Привязка representation

Один `ProductRepresentation` принадлежит одной `CatalogBindingGroup`.

Это учитывает существующее поведение: один товар Catalog может иметь несколько независимых групп даже внутри одного подключения. У каждой группы будут собственные overrides.

Внутри representation:

- общие overrides группы;
- overrides отдельных пар по стабильному `CatalogBindingItem.id`;
- разрешение экспорта;
- ревизия и аудит.

Отдельные таблицы для overrides каждого поля или языка не нужны.

### Приоритет значений

```text
Эффективное значение Catalog
    → общий override группы
    → override конкретной сопоставленной позиции
```

Общий override явно означает «применить ко всем целям группы». Интерфейс должен показывать этот охват.

Правила:

- отсутствующий override означает использование предыдущего уровня;
- удаление override возвращает наследование;
- `body=""` означает явную очистку описания;
- пустое название недопустимо;
- пустая галерея означает явное удаление изображений, если платформа поддерживает такую операцию;
- галерея заменяется целиком, включая порядок и главное изображение;
- между языками нет неявного fallback.

Overrides не изменяют Catalog и не используют наблюдаемое описание площадки как запасной источник.

### Вариативные товары

| Режим связи | Формирование целей |
|---|---|
| `SIMPLE_TO_SIMPLE` | Одна продаваемая цель |
| `VARIABLE_TO_SIMPLE` | Каждая сопоставленная позиция становится независимой целью |
| `VARIABLE_TO_VARIABLE` Prom | Основная позиция и её разновидности сохраняют существующие внешние роли |
| `VARIABLE_TO_VARIABLE` WooCommerce | Отдельно формируется контент контейнера и сопоставленных вариаций |

Для частичного сопоставления preview доступен всегда. Экспорт независимых целей возможен по готовым парам. Изменение общего контейнера вариативной карточки разрешается только при полном согласованном сопоставлении семьи, поскольку оно может затронуть несопоставленных детей.

`conflict`, устаревшая конфигурация и несовместимая структура блокируют экспорт.

### Изменение связей

Реализовано сохранение неизменных строк пар без удаления и повторной вставки.

При изменении состава группы:

- overrides неизменных пар сохраняются;
- overrides удалённых пар удаляются атомарно;
- новая пара не наследует overrides прежней;
- экспорт representation выключается до повторной проверки и включения;
- ожидающие отправки отменяются.

Снятие группы удаляет принадлежащий ей representation, но не меняет Catalog или внешнюю площадку.

## 3. SQL-модели

Предлагаю **четыре новые таблицы для полного среза с галереей**. Нового универсального `SyncRun`, таблиц операций на каждое поле и истории всех вычисленных представлений не требуется.

Общие правила: tenant-схема, проектный `StringUUID`, даты с timezone, Domain Enum сохраняются строками. SQL обеспечивает ссылки, уникальность и индексы; бизнес-проверки остаются в Domain.

### `channel_product_representations`

Хранит только пользовательское намерение.

```text
id                      UUID PK
binding_group_id        UUID NOT NULL UNIQUE
                        FK → channel_catalog_binding_groups
                        ON DELETE CASCADE

revision                integer NOT NULL
export_enabled          boolean NOT NULL DEFAULT false

overrides_schema        text NOT NULL
overrides_data          jsonb NOT NULL

created_at              timestamptz NOT NULL
updated_at              timestamptz NOT NULL
created_by              UUID NOT NULL
updated_by              UUID NOT NULL
```

Пример `overrides_data`:

```json
{
  "common": {
    "uk": {
      "title": "Назва для цього каналу"
    }
  },
  "items": {
    "<binding_item_id>": {
      "uk": {
        "body": "<p>Опис конкретного варіанта</p>",
        "gallery": [
          {
            "file_id": "<files_uuid>",
            "alt": "Вигляд спереду"
          }
        ]
      }
    }
  }
}
```

Первое изображение — главное. Порядок элементов значим.

В Python это конкретные типы overrides, локализованного контента и изображения. JSONB — формат хранения, а не замена типизации через `Any`.

Идентификаторы Catalog, подключения и публикаций берём через существующую группу. В этой таблице их не дублируем.

### `channel_content_feeds`

Один фид соответствует одному источнику XML-обмена, а не обязательно всему подключению. Это важно для нескольких источников Rozetka.

```text
id                      UUID PK
connection_id           UUID NOT NULL
                        FK → channel_connections ON DELETE CASCADE

scope_key               text NOT NULL
revision                integer NOT NULL
enabled                 boolean NOT NULL DEFAULT false

source_schema           text NOT NULL
source_settings         jsonb NOT NULL
source_url_encrypted    bytea NOT NULL

access_token_hash       bytea NOT NULL
delivery_state          jsonb NOT NULL

created_at              timestamptz NOT NULL
updated_at              timestamptz NOT NULL

UNIQUE(connection_id, scope_key)
```

`source_settings` содержит типизированные настройки пакета: источник Rozetka, режим формирования и параметры XML. URL исходного фида может содержать секрет, поэтому хранится через существующий Shared Cipher.

`delivery_state` нужен для передачи ссылки Prom: состояние запроса, внешний ID импорта и безопасная ошибка. У pull-фида он остаётся пустым версионированным документом.

Индекс уникальности одновременно обслуживает поиск фидов подключения. Общий GIN-индекс на JSONB не нужен.

### `channel_content_deliveries`

Текущее состояние API-доставки, **одна строка на внешнюю цель representation**.

```text
representation_id       UUID NOT NULL
                        FK → channel_product_representations
                        ON DELETE CASCADE

publication_id          UUID NOT NULL
                        FK → channel_external_publications

requested_generation    bigint NOT NULL
sending_generation      bigint NULL
status                  text NOT NULL
current_job_id          UUID NULL

prepared_schema         text NULL
prepared_payload        jsonb NULL
prepared_context        jsonb NULL
prepared_hash           text NULL

last_applied_hash       text NULL
platform_state          jsonb NOT NULL
error_code              text NULL
updated_at              timestamptz NOT NULL

PRIMARY KEY(representation_id, publication_id)
```

В `prepared_context` находятся ревизии подключения, связи и representation, hash контента Catalog и идентификаторы использованных media.

Это состояние исполнения, а не бессрочная история запросов. Технические попытки остаются в Shared Jobs.

Для выборки ожидающих доставок — небольшой частичный индекс по статусам `queued` и `unknown`. Индекс по `publication_id` нужен отдельно: составной PK начинается с другого поля.

### `channel_content_media`

Нужна для внешнего доступа к Files и повторного использования уже переданных изображений.

```text
id                      UUID PK
connection_id           UUID NOT NULL
                        FK → channel_connections ON DELETE CASCADE

file_id                 UUID NOT NULL
source_fingerprint      text NOT NULL

access_token_hash       bytea NOT NULL
access_token_encrypted  bytea NOT NULL

platform_schema         text NOT NULL
platform_data           jsonb NOT NULL

created_at              timestamptz NOT NULL
updated_at              timestamptz NOT NULL

UNIQUE(connection_id, file_id, source_fingerprint)
```

Для WooCommerce `platform_data` хранит подтверждённый attachment ID. Повторное обновление использует его, вместо повторного скачивания того же изображения.

SQL FK на Files не добавляется. Доступность файла и его использование проверяются публичными контрактами владельца.

## 4. Структура модуля и контракты

```text
channels/
├── domain/
│   ├── product_representation/
│   │   ├── aggregate.py
│   │   ├── entity/content_delivery.py
│   │   ├── value_object/
│   │   ├── policy/
│   │   ├── error.py
│   │   └── repository.py
│   └── content_feed/
│       ├── aggregate.py
│       ├── value_object/
│       ├── error.py
│       └── repository.py
│
├── application/
│   ├── product_representation/
│   │   ├── command/
│   │   │   ├── save_representation/
│   │   │   ├── enable_representation_export/
│   │   │   ├── disable_representation_export/
│   │   │   └── request_content_delivery/
│   │   ├── query/
│   │   │   ├── get_representation/
│   │   │   └── preview_representation/
│   │   ├── service/
│   │   └── port/
│   ├── content_delivery/
│   │   ├── command/
│   │   │   ├── prepare_content_delivery/
│   │   │   └── apply_content_delivery_result/
│   │   └── port/
│   └── content_feed/
│       ├── command/
│       ├── query/
│       └── port/
│
├── infrastructure/
│   ├── product_representation/persistence/
│   ├── content_feed/persistence/
│   ├── content_media/
│   └── platforms/
│       ├── prom/content/
│       ├── rozetka/content/
│       └── woocommerce/content/
│
└── presentation/
    ├── product_representation/
    ├── content_feed/
    ├── content_media/
    └── content_delivery/jobs/
```

Для каждого сценария — собственные command/query, handler и DTO. Отдельного repository на каждую SQL-таблицу не требуется: deliveries принадлежат representation.

Основные новые типы:

- `RepresentationOverridesVO` — сохраняемые изменения.
- `PreparedRepresentation` — общая итоговая модель.
- `PreparedPublicationContent` — контент конкретной внешней цели.
- `FieldOrigin` — источник значения для preview.
- `RepresentationIssue` — код, поле, locale и целевая позиция.
- `PreparedApiUpdate` — проверенный запрос конкретного пакета.
- `ContentDeliveryResult` — результат внешнего вызова.

Платформенные модели остаются внутри пакетов. Общий слой не импортирует `WooProduct` или XML-модели Prom/Rozetka. Используем конкретные порты подготовки контента, сериализации XML и API-доставки, без generic-класса платформы.

### Catalog и Files

Существующий контракт Catalog уже возвращает эффективный контент и галереи. Для сборки нескольких локалей нужно добавить публичное batch-чтение на одном согласованном снимке и с общим `as_of`.

Channels использует собственный adapter, без чтения ORM Catalog.

Для изменений Catalog сейчас нет готового потока событий. Нужно добавить событие изменения контента/структуры семьи через Shared Outbox в том же UoW. Оно должно охватывать обычное редактирование, варианты и импорт Catalog.

Изображения площадка получает через отдельный ограниченный media endpoint. Авторизованные Console URL изображений для этого не подходят.

## 5. Выполнение API и XML

### API WooCommerce

После включения экспорта:

```text
Изменение Catalog / overrides
    → durable событие или Job в том же UoW
    → отметить новую requested_generation
    → worker собирает актуальное представление
    → сохраняет подготовленный запрос
    → вызывает API вне транзакции
    → сохраняет результат
```

Правила исполнения:

- одна цель не отправляется параллельно двумя заданиями;
- частые изменения объединяются;
- неизменившийся hash не создаёт повторную запись;
- изменение во время запроса оставляет следующую генерацию ожидающей;
- проверяются ревизии, целевая identity и действующая lease;
- таймаут переводит доставку в `unknown`: сначала сверка, затем решение о повторе;
- повтор с изображениями использует подтверждённые media ID; неоднозначная загрузка не повторяется вслепую;
- наблюдаемый `ExternalPublication` обновляется обычным чтением площадки.

Запросы меняют только выбранные поля контента существующих товаров и вариаций. [Контракт WooCommerce Products API](https://woocommerce.github.io/woocommerce-rest-api-docs/#products).

### Постоянный XML endpoint

```text
GET постоянного URL
    → получить исходный XML вне SQL-транзакции
    → прочитать согласованный снимок Catalog и overrides
    → наложить изменения сопоставленных позиций
    → проверить полный результат
    → вернуть XML
```

Файл на каждый запуск не сохраняется. Итог сначала формируется и проверяется полностью; ошибка не должна приводить к выдаче оборванного или неожиданно пустого фида.

Исходный XML сохраняет:

- несопоставленные позиции;
- исходные offer ID и категории;
- цены, остатки и прочие поля вне этого среза;
- неизвестные расширения формата.

Для Rozetka особенно важно сохранить исходные ID и состав источника: пропуск позиции в подключённом XML может изменить наличие. Поэтому новый endpoint заменяет URL того же источника после проверки состава. Обновление названий, описаний и фотографий также может потребовать модерации. [Правила редактирования Rozetka](https://sellerhelp.rozetka.com.ua/p202-edit-items.html), [правила наличия](https://sellerhelp.rozetka.com.ua/p342-avaliable-and-stock.html).

Для Prom нужно выделить подтверждённый import key в `platform_data`. Подмена его нативным ID публикации недопустима. Отсутствующий или конфликтующий ключ блокирует рабочий экспорт.

Передача постоянной ссылки Prom — отдельное Job-действие. В запросе явно задаются обновляемые поля и `mark_missing_product_as=none`. Параметр `only_update=true` нельзя использовать как защиту обновления контента: опубликованный контракт ограничивает его ценой и наличием. [Схема импорта Prom](https://public-api.docs.prom.ua/documentation/Products/schemas/PostProductsImportUrlRequestBody.yaml).

Выдача XML и принятие ссылки площадкой не означают, что контент уже применён.

## 6. HTTP, Console и порядок реализации

Новые сценарии HTTP:

| Метод | Назначение |
|---|---|
| `GET/PUT …/catalog-bindings/{group_id}/representation` | Читать и сохранять overrides |
| `POST …/representation/preview` | Проверить сохранённый или несохранённый вариант |
| `POST …/representation/enable` | Проверить и разрешить экспорт |
| `POST …/representation/disable` | Запретить новые отправки |
| `POST …/representation/deliver` | Явно запросить API-обновление |
| `GET …/representation/delivery` | Получить состояние целей |
| `GET/POST/PUT …/content-feeds` | Управлять фидами |
| Отдельные GET XML/media | Доступ площадки по ограниченному токену |

В Console нужен редактор представления рядом с существующей группой:

- выбор языка и позиции;
- «Catalog / Override / Итог»;
- сброс поля к наследованию;
- preview API/XML и ошибки по конкретным полям;
- отдельное разрешение экспорта;
- различимые состояния подготовки, отправки, выдачи XML и подтверждённого применения.

Query cache, черновики и URL-состояние остаются разделёнными по правилам frontend. Refetch не стирает ввод.

Порядок реализации:

1. **Композиция и overrides:** Domain, одна таблица representation, preview и тесты всех режимов сопоставления.
2. **Редактор Console:** сохранение с ревизией, наследование и диагностика.
3. **XML:** полный исходный фид, платформенные serializers, постоянный endpoint и сохранение ключей.
4. **Медиа:** доступ через Files, ограниченные URL и соответствия внешних изображений.
5. **API:** durable доставка WooCommerce, события Catalog, объединение изменений и сверка ошибок.
6. **Rollout:** экспорт выключен по умолчанию; включение после проверки реального магазина и XML-источника.

Обязательная приёмка:

- приоритет overrides, очистка и возврат к Catalog;
- независимость языков, групп и вариантов;
- сохранность overrides при изменении неизменных пар;
- блокировка конфликтной структуры и отмена устаревших заданий;
- отсутствие изменений цен, остатков, SKU и внешних ключей;
- сохранность несопоставленного XML-ассортимента;
- идемпотентность доставки и отсутствие повторной загрузки изображений при обычном повторе;
- tenant isolation и ограничения доступа к XML/media;
- PostgreSQL, архитектурные проверки, frontend-тесты и браузерная проверка основных состояний.

