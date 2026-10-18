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

Сохранение проходит через create/restore и один CatalogItem.update. Обработчик
берёт shared guard справочных ссылок, затем блокировку одного товара и загружает
актуальное состояние. Изменения справочников берут exclusive guard. Ревизий
в активных Domain, Application, HTTP и Console контрактах Catalog нет.
При конкурентной правке одного поля или набора побеждает последняя успешная запись;
PATCH разных полей применяется к актуальному состоянию без потери остальных полей.
Write repository сохраняет только изменённые группы связей. Транзакцией владеет
внешний UoW. Query repositories читают согласованные batch-проекции без N+1.

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
PATCH content.values передаёт полный dict[str,str] выбранной locale; отсутствие optional
блока удаляет его, пустая строка сохраняется. content=null удаляет перевод.
HTML очищается NH3 через порт и DOMPurify перед показом в Console.

Locale передаётся явно; запись разрешена для активной locale Reference Data.
Сохранённый перевод неактивной locale читается. Межъязыкового fallback нет.
Default labels en/ru/uk читаются по выбранной locale, без угадывания языка.

Глобальные атрибуты — enum с устойчивыми ID definitions/options и переводами.
Коды отсутствуют в Domain, Application, HTTP, Console и текущем SQL. Название
атрибута и значение option — независимый label для каждой locale; переименование
и сортировка не меняют ID. Совпадающие labels не объединяют разные ID.
POST /attributes принимает locale/label и необязательные options(label).
PUT /attributes/{id}/options/{locale} заменяет упорядоченный набор: option_id
сохраняется для существующей опции, для новой UUID создаёт сервер. У существующей
опции пропущенный/null label сохраняет переводы и допускает сортировку при
отсутствующем переводе; у новой label обязателен. Пустой label отклоняется.
Чтение возвращает null без перевода, Console показывает «Нет перевода».
Поиск характеристик выполняется по label выбранной locale и UUID.
Назначение содержит несколько option IDs, position и visible; вариантов это
не создаёт. Options должны принадлежать определению. Категории образуют дерево
с защитой циклов. Непустое назначение требует ровно одну primary; назначаются
только явные узлы. Используемые справочники/options не удаляются.

Metadata — полный упорядоченный набор keys с типами text/decimal/boolean,
без режимов override. Зарезервированные канонические ключи запрещены. Удаление
характеристики или metadata выполняется исключением из полного набора.

Галерея принадлежит item+locale: Files links, порядок, alt/caption и одно главное
изображение в непустом наборе. Replace заменяет полный набор, empty очищает,
gallery=null удаляет локализованную галерею. До 100 изображений; upload PNG/JPEG/WebP
до 10 MiB с проверкой MIME/сигнатуры. Files adapter использует публичные handlers
на общем UoW, без Files ORM/FK. HTTP отдаёт закрываемый поток только для
изображения галереи этого товара и tenant. Снятие связи не удаляет Files объект.
Хранилище подготавливается сценариями Files до загрузки.

## API и Console

Префикс /api/console/catalog: POST/GET /items, GET/PATCH/DELETE /items/{id},
/product-type/default, /attributes, /categories, /tags. Создание возвращает id,
PATCH возвращает id, delete -> None/204. Сценарии имеют собственные Command/Query,
Handler, DTO и HTTP-контракты. Старый /items/simple и endpoints изменения отдельных
полей удалены без aliases. Upload /items/{id}/images/{locale}/upload возвращает
id/image_id/file_id; получение содержимого изображения отдаёт закрываемый поток.

PATCH принимает status, sku, virtual, price_specification, stock, weight, dimensions,
content, gallery, attributes, metadata, category_ids, primary_category_id, tag_ids.
Отсутствие поля сохраняет значение, null очищает только nullable-значения. Явный
null запрещён для status, virtual, stock и наборов attributes/metadata/category_ids/tag_ids.
Вложенные спецификации и наборы заменяются полностью. Пустой PATCH и неизвестные
поля отклоняются с 422. Изменение content/gallery требует query locale; content
принимает expected_schema_version и values. Версия фиксированной схемы сохраняется.
Все изменения одного запроса атомарны; ошибки разделов содержат field/message.
409 обозначает бизнес-конфликт, например занятый SKU или используемую связь.

List — компактные строки, locale/search/status/category/tag и offset/limit (до 100).
Detail сохраняет item/as_of с прямыми полями; price_specification отличается от
вычисляемой price, stock — от stock_status. Нет kind, root/parent, own/effective,
origins, осей или диапазона цен. Чтение использует REPEATABLE READ на общей session
до SQL Identity. Unsupported SQL kinds не читаются и не меняются через MVP.

Console /catalog/items: список, явное создание черновика, обзор и редактор.
Все разделы товара автоматически сохраняются через 800 мс после последней правки.
Одна очередь отправляет только корректные изменённые разделы; во время запроса
ввод доступен, более новые значения сохраняются следующим PATCH. Ошибочный раздел
остаётся в черновике, остальные продолжают сохраняться. Сеть/5xx приостанавливают
очередь с общей кнопкой «Повторить». Статус доступен через aria-live. Upload следует
после сохранения галереи в той же очереди; его неоднозначный результат не повторяется.
Уход со страницы и смена locale сначала сохраняют изменения; при оставшемся вводе
требуется подтверждение отказа. Смена tenant/session отменяет отложенные записи.
Редакторы характеристик, категорий и тегов сохраняют текущие кнопки без ревизий.

## SQL и публичные контракты

SQL товара и регистрация сохраняются: catalog_item поддерживает
simple/variable/variant, parent role FK, оси и таблицы selections/defaults.
MVP mapper записывает simple, parent_id=NULL, is_variation=false и mode=set;
старый clear простого товара читается как отсутствие. Активные adapters не
загружают детей и не читают/записывают selections/defaults.
История миграций, включая baseline 0023_catalog_item, сохраняется. Новая tenant-
миграция 0026_catalog_attribute_ids удаляет code и UNIQUE по коду только у
catalog_attributes/catalog_attribute_options. UUID, переводы, позиции и FK
назначений/осей не изменяются. Downgrade заполняет коды из UUID с префиксами a_/o_;
исходные коды можно вернуть только из резервной копии. Backend, Console и миграция
выпускаются согласованно: старый backend несовместим с удалёнными колонками.
Для сокращения уже развёрнутого Catalog пересоздание БД не требуется.
SQL-колонки revision пассивны: при INSERT adapter записывает 1, UPDATE сохраняет
прежнее значение. Domain и проекции их не используют; проверок сравнения нет.

GetCatalogItemsPublicationSnapshot — публичный batch Application-контракт простых
товаров: locale/as_of, fixed schema и собственные
значения с вычислениями. Он имеет собственные вложенные DTO. Потребитель открывает
краткий согласованный read UoW. Usage port проверяет внешние зависимости удаления;
пока внешние связи отсутствуют, адаптер возвращает пустой набор. При появлении
внешнего потребителя адаптер проверяет его зависимости через публичный контракт.
Связанные сообщения Outbox записываются в общей транзакции.
