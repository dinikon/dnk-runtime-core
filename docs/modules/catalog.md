# Catalog

Catalog MVP хранит простые самостоятельные товары, локализованный контент,
галереи и коммерческие значения. Атрибуты, категории, метки и metadata удалены
из Domain, Application, HTTP, Console и текущей SQL-схемы. Архитектура описана в
[backend](../architecture/backend.md) и [frontend](../architecture/frontend.md).

## Модель и транзакции

CatalogItem и ProductType — отдельные Aggregate Roots. Блоки контента и их
переводы принадлежат ProductType, отдельного write repository для блока нет.
Фабрики create/restore и доменные методы проверяют состояние. Mapper выполняет
только преобразования; чтение коллекций использует batch-проекции без N+1.

Товар изменяется одним атомарным PATCH под блокировкой конкретного item.
Разные поля применяются к актуальному состоянию; для одного поля побеждает
последняя успешная запись. Репозиторий сохраняет изменённые группы связей.
Reference guards удалены вместе с изменяемыми справочниками.
Внешний UoW владеет транзакцией; ревизий в активных контрактах нет.

## ProductType и создание Tenant

CatalogProvisioningFacade.initialize_defaults(tenant_id, actor_id) — публичный
Application-контракт установки Default. Tenancy обращается к нему через свой порт
и Infrastructure-адаптер после создания схемы и администратора, до commit общего
UoW. CLI и Control Plane используют тот же процесс. Ошибка откатывает onboarding.

Фасад создаёт системный тип code=default, schema_version=1 и два блока:

| Код | Тип | Обязательность |
| --- | --- | --- |
| title | text | Непустой текст до 255 символов при сохранении перевода |
| body | rich_text | Необязательный текст до 1000000 символов |

ProductType и каждый блок получают собственный UUIDv7. UUID разных Tenant
независимы; audit содержит UUID созданного администратора. Подписи en/ru/uk
создаются вместе со схемой, без межъязыкового fallback. Повторная инициализация
полной схемы сохраняет UUID; неполная или изменённая системная схема — ошибка.
Чтение и создание товара не инициализируют отсутствующий Default.

Объект product команды CreateCatalogItemCommand содержит product_type_code="default". Application
разрешает код в существующий UUID текущего tenant и передаёт его фабрике товара.
HTTP принимает все поддержанные разделы создания; Console по-прежнему создаёт
пустой Draft и открывает редактор. Выбора и изменения типа в Console нет.
Схема сохранённого товара читается по его product_type_id. GET /product-type/default
находит схему по коду. Фиксированных UUID и таблиц соответствия UUID в коде нет.

## Поля товара

Сохраняются status draft/active/archived, virtual, nullable SKU, цена, наличие,
измерения, переводы и галереи. SKU уникален в tenant после trim с сохранением
регистра. Товар создаётся черновиком без контента, цены и SKU.

Price specification хранит regular/sale, currency и UTC-интервал [from,to).
Текущая price вычисляется на as_of. Decimal точный, до шести дробных разрядов;
0 допустим, отсутствие цены блокирует продажу. Валюта проверяется Reference Data.

Вес — nullable value/unit g/kg; размеры независимо nullable cm/m. Точность
проверяется в g/mm до шести знаков без округления, хранятся исходные пары.
Virtual не очищает измерения и не меняет наличие. Inventory и резервы отсутствуют.

Новый товар: manage_stock=false, stock_quantity=null, stock_status=in_stock,
backorders=no. При учёте количества требуется целое число, включая отрицательное;
наличие вычисляется по количеству и политике backorders. При выключенном учёте
действует ручной stock_status. Boolean строгий. Продажа требует active, цену
и наличие in_stock/on_backorder; публикация проверяет active.

## Контент и медиа

Контент передаётся по кодам title/body. PATCH content.values заменяет полный
набор выбранной locale; пропуск body удаляет его, пустая строка сохраняется.
content=null удаляет перевод. Состав, обязательность, типы и expected_schema_version
проверяются по снимку схемы товара. Rich text очищается NH3 до доменной проверки
и DOMPurify перед показом. Запись разрешена для активной locale Reference Data,
сохранённый перевод неактивной locale читается. Межъязыкового fallback нет.

Галерея принадлежит item+locale: Files links, порядок, alt/caption и одно главное
изображение в непустом наборе. Полный набор заменяется атомарно; gallery=null
удаляет галерею. До 100 изображений. Upload PNG/JPEG/WebP/GIF/AVIF/BMP до 10 MiB
определяет MIME по сигнатуре файла общей инфраструктурной функцией, а не по расширению
или объявлению клиента. В Files передаются те же байты без конвертации, resize и сжатия.
Files handlers работают на общем UoW без Files ORM/FK в Catalog.
Image stream закрывается после ответа; снятие связи не удаляет Files объект.

## HTTP и Console

Префикс /api/console/catalog: POST/GET /items, GET/PATCH/DELETE /items/{id},
GET /product-type/default, upload и image content. Удалённые справочники отсутствуют
в OpenAPI. PATCH принимает status, sku, virtual, price_specification, stock, weight,
dimensions, content, gallery. Неизвестные поля и пустой PATCH дают 422.
Пропуск поля сохраняет значение; null очищает только nullable-поля. Изменение
content/gallery требует query locale. Ошибки разделов содержат field/message.
List поддерживает locale/search/status и offset/limit до 100; поиск идёт по SKU/title.

Console показывает список, создание товара/услуги, обзор и редактор. Поля title
и body сохраняются общей очередью autosave через 800 мс. Подтверждение запроса
не стирает более новый ввод. Ошибочный раздел остаётся в черновике, сеть/5xx
приостанавливают очередь до явного повтора. Upload не повторяется автоматически.
Уход и смена locale сначала сохраняют ввод; смена tenant/session отменяет очередь.

Публичный GetCatalogItemsPublicationSnapshot сохраняет собственные DTO,
locale/as_of, схему и значения товаров с вычислениями. Удалённых полей в нём нет.

## SQL и выпуск

Baseline 0023_catalog_item создаёт структуру без seed Catalog. Данные Default
создаются только через onboarding. Таблицы справочников, назначений, metadata,
variant selections и default selections удалены. Сохраняются SQL kind,
parent_id и ограничения ролей simple/variable/variant. Активный MVP работает
только с simple без parent; сценарии вариативности остаются будущим этапом.

Ревизия 0026_catalog_attribute_ids удалена; 0027_remove_channels следует за
0025_user_display_currency. Глобальные миграции и другие модули сохраняются.
Исторические имена таблиц остаются в ownership registry для autogenerate.
Переход требует пересозданных tenant-схем и повторного onboarding; переноса данных
нет. Backend и Console выпускаются согласованно.


## Публичный контракт Draft и внешние связи

`CreateCatalogItem` принимает типизированный объект `CreateCatalogItemValues`:
тип, статус, virtual, SKU, price specification с периодом акции, stock, вес,
габариты, контент нескольких локалей и локализованные галереи. Пустой объект
по-прежнему создаёт Draft типа Default. Старые HTTP-входы `{}` и `{virtual: ...}`
сохраняются; POST `/catalog/items` принимает дополнительные разделы без изменения
ответа `{id}`. Переводы передаются как `translations[locale]` с `values` и
`expected_schema_version`, галереи — как `galleries[locale]` по прежнему контракту Files.

`CatalogItemCreationService` проверяет справочники, SKU, схемы, доступность файлов,
очищает rich text и применяет Domain create/update до единственного сохранения.
`ValidateCatalogDraft` использует ту же подготовку без записи. Отдельный сценарий
CreateDraftCatalogItem удалён. `LockCatalogItemForBinding` предоставляет потребителю
собственную item-блокировку и безопасную проекцию. Consumer query/lock не требуют
дополнительных HTTP endpoints. Channels задаёт Draft/Default/virtual=false явно.

Channels вызывает контракт через свой adapter. В Catalog не передаются platform
kind, publication ID или native JSON. Ограничение двух языков интерфейса Channels
не ограничивает количество переводов самого Catalog. Цены и количество не
округляются, SKU проверяется также SQL uniqueness. Сервис не вызывает HTTP или
соседние create/update handlers друг из друга и не выполняет commit.

Delete подключён к CatalogItemUsagePort через публичный GetCatalogUsage Channels
на той же сессии. Проверка под item-lock запрещает удаление при активных ссылках,
включая архивные каналы. Явное снятие ссылки сохраняет товар. Последующая загрузка
публикаций не меняет canonical значения Catalog.
