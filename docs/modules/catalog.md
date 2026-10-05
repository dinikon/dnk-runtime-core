# Catalog: SIMPLE и VARIABLE

Catalog хранит карточку товара в tenant-схеме. `Product` — корень агрегата: у
`SIMPLE` ровно один Variant, у `VARIABLE` не менее двух. Каждый Variant ссылается
через `sku_id` на Inventory.SKU; один SKU можно использовать повторно. Цена,
остатки, категории и Channels пока не входят в Catalog.

## Атрибуты и варианты

Отдельный агрегат `Attribute` задаёт стабильный код и варианты выбора `Option`.
Сейчас поддержан тип `SELECT`: например `capsules` со значениями `100`, `200`,
`500`. Коды нормализуются в нижний регистр и уникальны в tenant. Названия
атрибута и вариантов переводятся по явным кодам локалей; отсутствие перевода
возвращает `name: null`, без подстановки другого языка.

Каждый Variant вариативного товара выбирает по одному option каждого используемого
атрибута. Набор атрибутов у всех вариантов товара одинаков, комбинации значений
не повторяются. Тип товара после создания пока не меняется. Создание Variant или
Attribute отдельно после создания товара пока не предусмотрено.

## Переводы

У Catalog нет выбранного или основного языка. Товар можно создать без контента.
Каждый сохранённый перевод содержит код локали BCP 47, обязательное `name` длиной
1–255 символов и необязательное `description`. Состав и применение, если они нужны,
входят в текст описания, а не в отдельные поля. При записи
код проверяется по активному глобальному справочнику `reference_data` через
Application-контракт; старые переводы остаются читаемыми, если код позднее
станет неактивным. Два перевода одного товара с одинаковым кодом не допускаются.

GET всегда требует явный `locale`. Если перевод отсутствует, `content` равен
`null`; другой язык не подставляется. Frontend сможет взять первоначальный выбор
языка из `interface_language` профиля пользователя, но backend не выбирает его сам.

## Console API

| Метод | Путь | Результат |
| --- | --- | --- |
| POST | `/api/console/catalog/products` | Создание SIMPLE, `201` |
| POST | `/api/console/catalog/products/variable` | Создание VARIABLE, `201` |
| GET | `/api/console/catalog/products/{product_id}?locale=uk` | Карточка, `200` |
| PUT | `/api/console/catalog/products/{product_id}/contents/{locale}` | Записать или заменить перевод, `200` |
| POST | `/api/console/catalog/attributes` | Создание атрибута с options, `201` |
| GET | `/api/console/catalog/attributes?locale=uk` | Список атрибутов и options, `200` |
| GET | `/api/console/catalog/attributes/{attribute_id}?locale=uk` | Атрибут и options, `200` |

POST принимает `sku_id` и необязательный массив `contents`; сервер создаёт Product
ID и Variant ID. Ответ содержит оба ID, `sku_id`, актуальный `sku_code`, коды
сохранённых переводов и аудит. GET добавляет `requested_locale` и `content`,
который может быть `null`. PUT принимает `name` и `description` и заменяет перевод
целиком.

Создание VARIABLE принимает `variants` (минимум два): у каждого `sku_id` и
`selections` с парами `attribute_id`/`option_id`. Общие переводы передаются тем же
массивом `contents`, что и для SIMPLE. Ответ содержит каждый Variant, его SKU,
код SKU и выбранные IDs. GET VARIABLE возвращает массив вариантов с кодами и
названиями атрибутов и options на запрошенной локали. JSON-ответ SIMPLE остался
прежним.

Например, после создания атрибута `capsules` с options `100`, `200`, `500` и
трёх SKU запрос на создание товара содержит:

```json
{
  "variants": [
    {"sku_id": "<sku-100-id>", "selections": [{"attribute_id": "<capsules-id>", "option_id": "<option-100-id>"}]},
    {"sku_id": "<sku-200-id>", "selections": [{"attribute_id": "<capsules-id>", "option_id": "<option-200-id>"}]},
    {"sku_id": "<sku-500-id>", "selections": [{"attribute_id": "<capsules-id>", "option_id": "<option-500-id>"}]}
  ],
  "contents": [{"locale": "uk", "name": "Омега 3"}]
}
```

Все методы требуют authentication и tenant-контекста; команды POST и PUT используют
существующую CSRF-проверку. AuthorizationService получает resource_type
`catalog.product` либо `catalog.attribute` и action `create`, `read` или `update`.
Неизвестные поля, неверный option и повтор комбинации дают `422`; отсутствующий
товар или SKU — `404`, занятый код атрибута — `409`.

## Хранение и развёртывание

Миграция tenant `0012_catalog_simple` создаёт исходные таблицы простого товара;
`0013_catalog_variable` расширяет их и создаёт таблицы атрибутов, options,
переводов и выбранных значений. Ссылки на SKU и глобальные
локали проверяются через Application-порты; чужие ORM-модели не становятся
контрактом Catalog. Репозитории используют общую сессию UoW с уже выбранной
tenant-схемой и не управляют транзакцией.

Перед открытием API обновить существующие tenant-схемы:

```sh
dnk-manage tenant-migrations upgrade --all
```
