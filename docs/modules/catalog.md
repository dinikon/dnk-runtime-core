# Catalog

Catalog хранит канонические карточки, их контент и заявленные коммерческие
значения. Реализация соответствует [плану](../plan/catalog.md) и
[архитектурным требованиям](../architecture/AGENTS.md).

## Модель и границы

Единственная товарная модель — `CatalogItem`, SQL `CatalogItemModel`, таблица
`catalog_item`. SIMPLE и VARIABLE являются Aggregate Roots. VARIABLE владеет
VARIANT как внутренними узлами того же класса; у них `parent_id` корня. SIMPLE
не имеет детей. Вложенность ровно один уровень, у VARIABLE минимум два варианта,
непустые enum оси, полные уникальные комбинации и допустимый default. Репозитория
варианта нет. ProductType Default — фиксированная read схема migration seed.
Системные подписи читаются по явной locale (en/ru/uk, остальные без fallback).
AttributeDefinition, Category и Tag имеют собственные корни.

Сохранение проходит через create/restore и доменные методы. Команды принимают
expected_root_revision; блокировка семьи берётся после shared guard ссылок.
Изменение определения/дерева берёт exclusive guard. Разные семьи изменяются
параллельно. Write repo восстанавливает семью, проверяет optimistic revision
при UPDATE и сохраняет только изменённые группы связей. UoW владеет транзакцией.

## Контент и effective значения

Default schema version 1: `name` (text, обязательное имя собственного перевода
корня), `desc` и `short_desc` (optional rich_text). CRUD типов и блоков отсутствует.
Контент хранится по item/locale/block. У VARIANT отсутствие ключа наследует блок
той же locale; set переопределяет, clear убирает optional блок. Переводы разных
языков не смешиваются. Запись проверяет активную locale Reference Data; сохранённый
перевод неактивной locale можно читать. HTML очищается NH3 через порт.

Цена и virtual принадлежат SIMPLE/VARIANT и не наследуются. VARIABLE всегда
невиртуальный, без собственной спецификации цены: он возвращает диапазон цен
активных детей и признак неполноты. Цена 0 допустима; отсутствие цены блокирует
продажу. Скидки используют точный Decimal и интервал `[from,to)` в UTC;
семья использует одну валюту Reference Data.

Вес хранится парой `value/unit` (`g`/`kg`), каждый размер — собственной парой
(`cm`/`m`). Длина, ширина и высота независимо необязательны. VARIANT наследует
отсутствующее измерение вместе с единицей; 0 остаётся собственным значением.
Domain точно переводит массу в граммы, размеры в миллиметры без float и
округления. Проверяется до шести дробных разрядов канонической единицы с учётом
незначащих нулей. Хранятся только исходные пары, без дублирования канонических чисел.
Виртуальность не отменяет сохранённые измерения и не меняет наличие.

SKU — собственный trim код SIMPLE/VARIANT, уникальный в tenant и чувствительный
к регистру; у VARIABLE SKU отсутствует. Остальные правила контента, атрибутов,
галерей и metadata сохраняют существующее наследование.

`manage_stock` — строгий boolean. Новые узлы получают false, ручной `in_stock`,
без количества и `backorders=no`. При true количество обязательно, целое и
может быть отрицательным; статус вычисляется по порогу 0 и политике no/notify/yes.
При false количество отсутствует, backorders=no; ручной on_backorder допустим.
VARIANT с false использует общий запас родителя с true. Собственный true
перекрывает общий запас. `stock_source_id` обозначает источник без копирования
или суммирования общего количества по детям. VARIABLE показывает собственный
общий запас отдельно от сводного статуса активных детей
(in_stock > on_backorder > out_of_stock; без активных детей out_of_stock).

`available_for_sale` вычисляется из active карточки/родителя, собственной цены
и эффективного наличия (in_stock/on_backorder). У VARIABLE это наличие хотя бы
одного продаваемого ребёнка. `available_for_publication` остаётся проверкой
жизненного цикла. Inventory, его порты, fallback, движения и резервы не реализуются.

Metadata — нормализованные text/decimal/boolean keys с порядком и set/clear,
канонические ключи запрещены. Override сохраняет место parent key, новые ключи
добавляются в собственном порядке. Own/effective/origins разрешает одна Domain
policy для команд и query projections, без сохранения effective копий в SQL.

## Справочники и медиа

Глобальные атрибуты только enum. Definitions/options имеют устойчивые ID и
переводы. Назначение содержит список options, position, visible и роль оси;
visible независимо от is_variation. Axis options проверяются с владельцем,
каждый variant выбирает по одному option каждой оси. Используемые options нельзя
удалять. Categories — дерево с защитой циклов, назначаются только SIMPLE:
много явных узлов, ровно одна primary при непустом наборе. Tags также только SIMPLE.

Галерея принадлежит item+locale: упорядоченные Files ссылки, alt/caption и одно
главное изображение в непустом наборе. У ребёнка отсутствующий набор наследует
parent locale, empty явно скрывает его; replace заменяет весь набор, delete
возвращает наследование. В MVP до 100 изображений, upload PNG/JPEG/WebP до 10 MiB
с проверкой MIME/сигнатуры. Files adapter использует публичные handlers на общем
UoW, не импортирует Files ORM и не создаёт межмодульный FK. HTTP отдаёт закрываемый
поток только для изображения effective галереи. Detach не удаляет Files объект.
Файловое хранилище подготавливается сценариями Files до загрузки.

## API и Console

Префикс `/api/console/catalog`: `/items`, `/items/simple`, `/items/variable`,
`/items/{id}`, `/items/{root_id}/variants`, `/product-type/default`,
`/attributes`, `/categories`, `/tags`. Каждый use case имеет отдельные
command/query, handler, DTO и HTTP контракты; delete -> None/204, image content
-> закрываемый stream. Разделы записи: status, sku, virtual, price, stock,
measurements, content/{locale}, attributes, categories, tags, metadata,
structure, kind, gallery/{locale}; upload `/items/{id}/images/{locale}/upload`.

List — компактная проекция с title, SKU, ценой/диапазоном, статусом и главным
изображением; filters locale/search/kind/status/category/tag/parent, offset/limit
(до 100). Detail — own/effective/origins. Чтение использует REPEATABLE READ на одной
session, настроенной router Depends до SQL Identity, и batch links: число SELECT не зависит от количества строк страницы.
Get VARIANT не загружает соседей. Query repos не восстанавливают Aggregate.

Console использует `/catalog/items` и одну карточку для всех kinds, отдельные
сохранения разделов, locale/query keys и root revision. Ввод сохраняется при 409;
актуальное состояние загружается явно. Есть галерея, структура с явными удалениями
и переходы kind. SIMPLE -> VARIABLE требует снять классификацию и явно выбрать
ребёнка для переноса SKU, цены, virtual и наличия; измерения корня остаются defaults.
VARIABLE -> SIMPLE материализует выбранного ребёнка,
сохраняет root ID и требует подтверждения всех удаляемых child IDs.

## Channels и миграции

GetCatalogItemsPublicationSnapshot — публичный batch Application контракт с
locale/as_of, root revisions, fixed schema и effective данными. Сборка потребителя
обеспечивает краткий согласованный read UoW. Топология внешнего канала остаётся
независимой: несколько SIMPLE могут образовать synthetic внешнего parent,
VARIANT могут публиковаться отдельными simple. Bindings/mappings/overrides/delivery
принадлежат Channels; новые этапы исходящей доставки остаются в плане. Текущий
usage adapter возвращает пустой набор: observed Channels пока не содержит Catalog
source bindings. При появлении bindings требуется подключить проверку Channels
и события Outbox; нельзя оставлять пустой adapter с реальными зависимостями.

Fresh baseline `0023_catalog_item` следует за `0022_tenant_currency_settings`.
Удалены 0012/0015/0017/0018/0019 Catalog, обновлены только связи 0013/0016/0020.
Baseline пересобрана с boolean manage_stock и отдельными value/unit парами;
зависимость 0024_currency_exchange_rates сохранена. Нужна пустая база;
data migration, compatibility endpoints и автоматический
DB drop отсутствуют. Downgrade baseline удаляет только Catalog, сохраняет Files
и другие модули. Подробности — [tenant migrations](../data/tenant-migrations.md).
