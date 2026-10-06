# Catalog: товары, варианты, категории и схема контента

Catalog хранит данные в tenant-схеме. `Product` — корень агрегата с видом
`simple` (один Variant) или `variable` (минимум два Variant). Каждый Variant
ссылается на Inventory.SKU того же tenant. Один SKU может участвовать в разных
товарах, но не повторяется среди вариантов одного товара. `Category` — отдельный
корень с деревом и переводами названий. Цена, остатки, медиа и атрибуты пока не
имеют контрактов Catalog.

## Схема контента

`ContentBlockDefinition` задаёт устойчивые `id` и `code`, тип значения
`text | rich_text`, системный признак и локализованные подписи. Определение не
задаёт область применения. `ProductType` ссылается на определения через
`ProductTypeContentBlock(block_id, scope, required, position)`. Пары `PRODUCT`
и `VARIANT` независимы: одно определение допускается в обеих областях с разной
обязательностью и позицией. Код определения неизменяем после создания.

Новая tenant-схема получает системный тип `clean` («Чистый») и системные блоки
`title` (`text`), `description` и `short_description` (`rich_text`). Все три
блока включены и в PRODUCT, и в VARIANT. Обязателен только PRODUCT `title` при
сохранении перевода. Пользовательские типы могут не содержать `title`; товар
без переводов создать можно. По умолчанию новому товару назначается `clean`.

Значения хранятся отдельно от определений по ключу «владелец, locale, block ID».
Фиксированных текстовых колонок у Product и Variant нет. Тип текстового блока
хранится обычной строкой. `rich_text` принимается как HTML и очищается
инфраструктурным адаптером `nh3` до сохранения. Пустое обязательное значение
отклоняется. Locale проверяется по активному глобальному справочнику
`reference_data` при записи; ранее сохранённый перевод продолжает читаться,
если locale стала неактивной. Backend не выбирает основной язык и не делает
fallback: GET всегда требует `locale`, а отсутствующий перевод равен `null`.

Состав типа заменяется целиком с `expected_schema_version`. Изменение структуры
увеличивает версию. Старая версия редактора, удаление блока с существующими
значениями и добавление обязательного блока при недостающем контенте дают `409`.
Запись контента и изменение типа сериализуются блокировкой строки ProductType.
Смена типа уже созданного товара проверяет контент Product и всех Variant.
Системные определения и тип нельзя удалить; пользовательские записи удаляются
только если не используются.

## Console API

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET/POST | `/api/console/catalog/content-blocks` | Список и создание определения |
| GET/PUT/DELETE | `/api/console/catalog/content-blocks/{block_id}` | Карточка, обновление типа и подписей, удаление |
| GET/POST | `/api/console/catalog/product-types` | Список и создание типа |
| GET/PUT/DELETE | `/api/console/catalog/product-types/{type_id}` | Карточка, замена состава и переводов, удаление |
| GET/POST | `/api/console/catalog/products` | Список и создание SIMPLE |
| POST | `/api/console/catalog/products/variable` | Создание VARIABLE |
| GET/DELETE | `/api/console/catalog/products/{product_id}` | Карточка и удаление |
| PUT | `/api/console/catalog/products/{product_id}/product-type` | Смена типа с проверкой контента |
| PUT | `/api/console/catalog/products/{product_id}/variant-structure` | Замена вида и состава вариантов |
| POST | `/api/console/catalog/products/{product_id}/variants` | Добавление варианта |
| GET/PUT/DELETE | `/api/console/catalog/products/{product_id}/variants/{variant_id}` | Карточка, SKU и удаление варианта |
| PUT/DELETE | `/api/console/catalog/products/{product_id}/contents/{locale}` | Замена или удаление перевода Product |
| PUT/DELETE | `/api/console/catalog/products/{product_id}/variants/{variant_id}/contents/{locale}` | Замена или удаление перевода Variant |
| PUT | `/api/console/catalog/products/{product_id}/categories` | Замена категорий и основной категории |
| GET/POST | `/api/console/catalog/categories` | Список и создание категории |
| GET/DELETE | `/api/console/catalog/categories/{id}` | Карточка и удаление категории |
| PUT | `/api/console/catalog/categories/{id}/contents/{locale}` | Перевод названия |
| PUT | `/api/console/catalog/categories/{id}/parent` | Перенос в дереве |

PUT контента принимает `{schema_version, blocks: {code: value}}`. Код блока
разрешается через тип товара и область владельца; чужой блок отклоняется. Карточка
возвращает тип, версию схемы, контент Product и каждого Variant только для явно
запрошенной locale. Список показывает PRODUCT `title` этой locale, если он есть;
иначе интерфейс показывает SKU либо ID. Создание принимает необязательный
`product_type_id`; без него назначается `clean`. Аутентификация обязательна,
изменяющие запросы проходят CSRF. Дополнительных уровней доступа в Catalog нет.

## Хранение и развёртывание

После `0011_inventory_skus` одна начальная миграция `0012_catalog` создаёт
таблицы Product, Variant, категорий, определений, типов и значений контента,
а также системный seed для каждого tenant. Прежние одноразовые ревизии Catalog
заменены; локальную тестовую БД с ними нужно пересоздать. Новых настроек языков
tenant нет. Репозитории используют общую tenant-сессию UoW, не выбирают схему в
запросах и не управляют транзакцией.

```sh
dnk-manage tenant-migrations upgrade --all
```

В Console добавлены редакторы определений и типов, а формы товара строятся по
полученной схеме. Выбор языка карточки начинается с языка интерфейса пользователя
и затем меняется пользователем. Для `rich_text` применяется Tiptap. Атрибуты и
свойства ProductType — следующий срез; передача атрибутов во внешние системы не
входит в MVP.
