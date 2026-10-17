# Catalog

Catalog MVP v1 хранит только простые самостоятельные товары, их контент и
заявленные коммерческие значения. Полная спецификация вариативности сохранена
в [плане следующего этапа](../plan/catalog.md); обязательны
[архитектурные требования](../architecture/AGENTS.md).

## Модель и границы

CatalogItem — Aggregate Root одной продаваемой позиции. У него нет родителя,
детей, осей, selections или смены kind. AttributeDefinition, Category и Tag
имеют самостоятельные корни; options принадлежат определению атрибута.
ProductType Default — фиксированная read-only схема migration seed.

Сохранение проходит через create_simple/restore и доменные методы. Команды
принимают expected_revision; после shared guard справочных ссылок берётся
блокировка одного item. Изменения справочников берут exclusive guard.
Write repository проверяет optimistic revision и сохраняет только изменённые
группы связей. UoW владеет транзакцией. Query repositories не восстанавливают
агрегат; batch-чтение связей не зависит по числу запросов от размера страницы.

## Поля товара

У товара собственные status (draft/active/archived), virtual, SKU, цена,
наличие, измерения, тексты, галереи, характеристики, metadata и классификация.
Наследование и own/effective/origins отсутствуют. SKU — trim-код, уникальный
в tenant с сохранением регистра; nullable SKU не мешает созданию черновика.

Цена хранится как price_specification: regular/sale, currency и UTC-интервал
[from,to). Текущая price вычисляется на as_of; 0 допустим, отсутствие цены
блокирует продажу. Decimal точный, до шести дробных разрядов, без float.
Валюта проверяется публичным контрактом Reference Data.

Вес — nullable пара value/unit g/kg, размеры независимо nullable в cm/m.
Ноль является значением. Точность проверяется в канонических g/mm, до шести
дробных разрядов без округления; хранятся только исходные пары. Virtual не
очищает измерения и не меняет наличие. Inventory, резервы и движения отсутствуют.

Новые товары получают manage_stock=false, stock_quantity=null,
stock_status=in_stock, backorders=no. Boolean строгий. При true обязательно
целое количество, включая отрицательное; stock_status вычисляется по порогу 0
и политике no/notify/yes. При false количества нет, backorders=no, действует
ручной in_stock/out_of_stock/on_backorder. Общего запаса и stock source нет.

available_for_sale требует active, собственную цену и наличие
in_stock/on_backorder. available_for_publication проверяет active.
backorders_allowed/backordered — вычисляемые поля. Domain policy не читает часы.

## Контент, справочники и медиа

Default version 1 содержит name (обязательный непустой текст при сохранении
перевода), desc и short_desc (optional rich_text). CRUD типов/блоков отсутствует.
PUT values передаёт полный dict[str,str] выбранной locale; отсутствие optional
блока удаляет его, пустая строка сохраняется. DELETE удаляет перевод.
HTML очищается NH3 через порт и DOMPurify перед показом в Console.

Locale передаётся явно; запись разрешена для активной locale Reference Data.
Сохранённый перевод неактивной locale читается. Межъязыкового fallback нет.
Default labels en/ru/uk читаются по выбранной locale, без угадывания языка.

Глобальные атрибуты — enum с устойчивыми ID definitions/options и переводами.
Назначение содержит несколько option IDs, position и visible; вариантов это
не создаёт. Options должны принадлежать определению. Категории образуют дерево
с защитой циклов. Непустое назначение требует ровно одну primary; назначаются
только явные узлы. Используемые справочники/options не удаляются.

Metadata — полный упорядоченный набор keys с типами text/decimal/boolean,
без режимов override. Зарезервированные канонические ключи запрещены. Удаление
характеристики или metadata выполняется исключением из полного набора.

Галерея принадлежит item+locale: Files links, порядок, alt/caption и одно главное
изображение в непустом наборе. Replace заменяет полный набор, empty очищает,
DELETE удаляет локализованную галерею. До 100 изображений; upload PNG/JPEG/WebP
до 10 MiB с проверкой MIME/сигнатуры. Files adapter использует публичные handlers
на общем UoW, без Files ORM/FK. HTTP отдаёт закрываемый поток только для
изображения галереи этого товара и tenant. Снятие связи не удаляет Files объект.
Хранилище подготавливается сценариями Files до загрузки.

## API и Console

Префикс /api/console/catalog: /items, /items/simple, /items/{id},
/product-type/default, /attributes, /categories, /tags.
Разделы записи: status, sku, virtual, price, stock, measurements,
content/{locale}, attributes, categories, tags, metadata, gallery/{locale},
gallery/{locale}/primary; upload /items/{id}/images/{locale}/upload.
Create variable, variants, structure и kind endpoints отсутствуют.

Мутации получают expected_revision и возвращают id/revision; upload также
image_id/file_id. Delete -> None/204, image content -> управляемый stream.
Каждому сценарию принадлежат отдельные Command/Query, Handler, DTO и HTTP-контракты.

List — компактные строки, locale/search/status/category/tag и offset/limit (до 100).
Detail сохраняет item/as_of с прямыми полями; price_specification отличается от
вычисляемой price, stock — от stock_status. Нет kind, root/parent, own/effective,
origins, осей или диапазона цен. Чтение использует REPEATABLE READ на общей session
до SQL Identity. Unsupported SQL kinds не читаются и не меняются через MVP.

Console /catalog/items: список, создание черновика, обзор и отдельный редактор.
Есть сохранение разделов, локали, галерея, классификация, цены/наличие/измерения.
Выбора вида, вариантов, структуры и наследования нет. Query keys включают tenant,
сценарий, item ID, locale и filters/pagination. 409 сохраняет ввод; перезагрузка
актуального состояния выполняется явно с подтверждением потери изменений.

## SQL и Channels

SQL-модели и регистрация полностью сохранены: catalog_item поддерживает
simple/variable/variant, parent role FK, оси и таблицы selections/defaults.
MVP mapper записывает simple, parent_id=NULL, is_variation=false и mode=set;
старый clear простого товара читается как отсутствие. Активные adapters не
загружают детей и не читают/записывают selections/defaults. Новых миграций нет.
Сохраняются baseline 0023_catalog_item и следующая 0024_currency_exchange_rates.
Для сокращения уже развёрнутого Catalog пересоздание БД не требуется.

GetCatalogItemsPublicationSnapshot — публичный batch Application-контракт простых
товаров: locale/as_of, expected_revisions по item ID, fixed schema и собственные
значения с вычислениями. Он имеет собственные вложенные DTO. Потребитель открывает
краткий согласованный read UoW. Usage port проверяет внешние зависимости удаления;
пока Catalog bindings отсутствуют, адаптер возвращает пустой набор. При появлении
bindings обязательны проверка Channels и Outbox в общей транзакции.

Существующие observed/read коннекторы и внешние варианты Channels сохраняются.
Bindings, representations, mappings/overrides и исходящая доставка остаются
в плане; завершение Catalog MVP их не реализует.
