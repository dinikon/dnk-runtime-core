# Catalog: первый срез

Состав: SIMPLE, один Variant, ProductType, ContentBlockDefinition, text/rich_text,
явные локали, tenant persistence, API и Console. VARIABLE, SKU, downloadable,
категории, атрибуты, медиа и Channels добавляются следующими срезами.

Корни: Product, ProductType, ContentBlockDefinition. Variant — Entity Product.
Порядок: модуль → слой → корень → назначение. Domain не выполняет I/O;
create/restore и domain methods защищают инварианты, __post_init__ только в VO.
Все методы аннотированы и имеют русские docstrings. DTO принадлежат use case.
Write repositories восстанавливают агрегаты; Query repositories читают проекции.
Mapper не исправляет данные. HTTP controller/request/response раздельны;
router регистрирует маршруты, Depends собирает порты на общем tenant UoW.
Контекст Identity и CSRF обязательны. Репозитории не делают commit/rollback.
__init__.py пустые, SQL-модели по одной в файле. Логи не содержат контент/секреты.

## Сценарии и результаты

У команд доверенный tenant/actor; изменения получают expected_revision.
Запись контента и схемы дополнительно требует expected_schema_version.
У GET locale обязательна; отсутствие перевода — null, fallback отсутствует.

### Выравнивание SIMPLE (2026-10-10)

Product владеет всем редактируемым контентом SIMPLE. Его единственный Variant
сохраняет продаваемые свойства, но не имеет активных переводов. PRODUCT-схема
Default содержит title, description, short_description; VARIANT-схема содержит
необязательные title и description для следующего среза VARIABLE.
Наследование Title реализуется вместе с VARIABLE; сейчас его нет.

Применяются все архитектурные требования выше: инвариант SIMPLE проверяется
в Product.restore и domain methods, а не в mapper. Корни и границы слоёв не меняются.
Методы аннотированы, имеют русские docstrings; __post_init__ остаётся только в VO;
пакетные __init__.py
пустые. Миграция не коммитит и не импортирует текущие ORM-модели.

Затронутые сценарии и обязательные файлы:

| Сценарий | Вход и результат execute | Изменение и файлы |
| --- | --- | --- |
| put_variant_content | Прежний PutVariantContentCommand → PutVariantContentResultDTO | Product.put_content отклоняет SIMPLE с 422; command.py, handler.py, dto.py, HTTP request/controller/response и Depends сохранены |
| delete_variant_content | Прежний DeleteVariantContentCommand → None | Product.delete_content отклоняет SIMPLE с 422; command.py, handler.py, HTTP controller и Depends сохранены; пустой DTO/Response не создаётся |
| get_product | Product ID, tenant, locale → GetProductDetailsDTO | Собственные dto.py и HTTP response/get_product.py, query_repository port, SQL query_repository/query_mapper и Depends сохраняют контракт |
| change_product_type / replace_product_type_schema | Прежние команды → свои ChangeProductTypeResultDTO / ReplaceProductTypeSchemaResultDTO | Проверяется сохранённый контент Product; у SIMPLE нет переводов позиции |
| update_content_block / delete_content_block | Прежние команды → UpdateContentBlockResultDTO / None | is_used проверяет ссылки схем; исправляются ветвления Console |

Модуль не выходил в production. Единственная новая tenant-миграция
0017_catalog_simple сразу создаёт исправленную схему: 11 таблиц, Default с
schema_version=1/revision=1, три PRODUCT-связи и две VARIANT-связи без
short_description. Отдельной миграции выравнивания и поддержки прежних данных нет.
Тестовые базы со старой редакцией Catalog пересоздаются перед использованием.

Console показывает только PRODUCT-форму контента SIMPLE.
Старые VARIANT URL направляются на контент товара; URL позиции показывает свойства.
AppLayout инициализирует tenant даже при закрытом мобильном sidebar: загрузка
Catalog не зависит от монтирования WorkspaceTenantInfo внутри меню.

Проверки: доменные отказы без изменения состояния; HTTP 422/404/409;
локали, пустые переводы и значения; upgrade/downgrade, tenant isolation,
rollback, FK и autogenerate; смена типа/схемы; архитектурный checklist; Console
lint/typecheck/build и браузерные SIMPLE, изменение/удаление блока.

| Корень | Сценарий | Вход command/query | Результат execute | HTTP после /api/console/catalog |
| --- | --- | --- | --- | --- |
| product | create_simple_product | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_type_id: ProductTypeIdVO \| None = None; virtual: bool = False | CreateSimpleProductResultDTO | POST /products/simple |
| product | change_product_type | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; product_type_id: ProductTypeIdVO | ChangeProductTypeResultDTO | PUT /products/{product_id}/type |
| product | set_variant_properties | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; variant_id: VariantIdVO; virtual: bool; downloadable: bool | SetVariantPropertiesResultDTO | PUT /products/{product_id}/variants/{variant_id}/properties |
| product | put_product_content | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; locale: str; expected_schema_version: int; values: dict[str,str] | PutProductContentResultDTO | PUT /products/{product_id}/content/{locale} |
| product | delete_product_content | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; locale: str | None | DELETE /products/{product_id}/content/{locale} |
| product | put_variant_content | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; variant_id: VariantIdVO; locale: str; expected_schema_version: int; values: dict[str,str] | PutVariantContentResultDTO | PUT /products/{product_id}/variants/{variant_id}/content/{locale} |
| product | delete_variant_content | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int; variant_id: VariantIdVO; locale: str | None | DELETE /products/{product_id}/variants/{variant_id}/content/{locale} |
| product | delete_product | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_id: ProductIdVO; expected_revision: int | None | DELETE /products/{product_id} |
| product_type | create_product_type | tenant_id: EntityIdVO; actor_id: EntityIdVO; code: str; locale: str; label: str; blocks: tuple[ProductTypeContentBlock,...] | CreateProductTypeResultDTO | POST /product-types |
| product_type | delete_product_type | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_type_id: ProductTypeIdVO; expected_revision: int | None | DELETE /product-types/{product_type_id} |
| product_type | put_product_type_translation | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_type_id: ProductTypeIdVO; expected_revision: int; locale: str; label: str | PutProductTypeTranslationResultDTO | PUT /product-types/{product_type_id}/translations/{locale} |
| product_type | replace_product_type_schema | tenant_id: EntityIdVO; actor_id: EntityIdVO; product_type_id: ProductTypeIdVO; expected_revision: int; expected_schema_version: int; blocks: tuple[ProductTypeContentBlock,...] | ReplaceProductTypeSchemaResultDTO | PUT /product-types/{product_type_id}/schema |
| content_block | create_content_block | tenant_id: EntityIdVO; actor_id: EntityIdVO; code: str; locale: str; label: str; value_type: ContentValueType | CreateContentBlockResultDTO | POST /content-blocks |
| content_block | delete_content_block | tenant_id: EntityIdVO; actor_id: EntityIdVO; content_block_id: ContentBlockIdVO; expected_revision: int | None | DELETE /content-blocks/{content_block_id} |
| content_block | update_content_block | tenant_id: EntityIdVO; actor_id: EntityIdVO; content_block_id: ContentBlockIdVO; expected_revision: int; locale: str; label: str; value_type: ContentValueType | UpdateContentBlockResultDTO | PUT /content-blocks/{content_block_id} |
| product | get_product | tenant_id: EntityIdVO; product_id: ProductIdVO; locale: str | GetProductDetailsDTO | GET /products/{product_id} |
| product | list_products | tenant_id: EntityIdVO; locale: str; search: str = ""; page: int = 1; page_size: int = 20; product_type_id: ProductTypeIdVO \| None = None | ListProductsPageDTO | GET /products |
| product_type | get_product_type | tenant_id: EntityIdVO; product_type_id: ProductTypeIdVO; locale: str | GetProductTypeDetailsDTO | GET /product-types/{product_type_id} |
| product_type | list_product_types | tenant_id: EntityIdVO; locale: str; search: str = ""; page: int = 1; page_size: int = 20 | ListProductTypesPageDTO | GET /product-types |
| content_block | get_content_block | tenant_id: EntityIdVO; content_block_id: ContentBlockIdVO; locale: str | GetContentBlockDetailsDTO | GET /content-blocks/{content_block_id} |
| content_block | list_content_blocks | tenant_id: EntityIdVO; locale: str; search: str = ""; page: int = 1; page_size: int = 20 | ListContentBlocksPageDTO | GET /content-blocks |
| product | get_variant | tenant_id: EntityIdVO; product_id: ProductIdVO; variant_id: VariantIdVO; locale: str | GetVariantDetailsDTO | GET /products/{product_id}/variants/{variant_id} |

## Обязательные файлы и зависимости

Для каждой строки: application/<root>/command|query/<scenario>/command|query.py,
handler.py, dto.py (кроме None); presentation/<root>/http/controller/<scenario>.py,
request/<scenario>.py при теле, response/<scenario>.py при результате;
presentation/<root>/router.py и depends.py с именованной зависимостью handler.

Для каждого корня: domain/<root>/aggregate.py, error.py, repository.py, value_object/;
infrastructure/<root>/persistence/{repository,mapper,query_repository,query_mapper}.py.
SQL-модели: infrastructure/persistence/models/{product,variant,product_type,
content_block,product_type_block,content_block_translation,product_type_translation,
product_translation,variant_translation,product_content_value,variant_content_value}.py.
Tenant-миграция: 0017_catalog_simple.

Порты: locales (reference_data), rich_text sanitizer, mutation_lock,
product/schema snapshot, query repositories. Schema service координирует
репозитории типов/блоков и создаёт immutable snapshot. Обработчики не вызывают
друг друга. NH3 sanitizer находится в Infrastructure. Locale adapter обращается
к Application-порту reference_data, не к его моделям.

## Защита конкурентных изменений

Все команды сначала получают PostgreSQL transaction advisory lock для tenant
и Catalog. Он удерживается общим внешним UoW до commit/rollback. Поэтому проверка
версии, проверка использования, смена схемы, создание и сохранение контента
не пересекаются с другой записью Catalog в этом tenant. Query-сценарии используют shared lock: читатели выполняются параллельно,
запись ожидает завершения чтения; многотабличная проекция остаётся согласованной.
Это намеренная грубая блокировка первого среза; будущая оптимизация обязана
сохранить защиту гонок и единый порядок блокировок.

Изменение пользовательской схемы проверяет все активные переводы Product.
У SIMPLE нет активных переводов Variant.
Несовместимость отклоняется, миграция контента не выполняется автоматически.
Системные определения меняются только миграцией. Код стабилен; используемый
value_type нельзя изменить. Физическая позиция без SKU допустима как карточка,
но не получает обещания готовности к продаже. Downloadable отвергается до файлового
контракта. Цена, размеры, остатки и публикационный статус не принадлежат Product.

Решения для следующего среза: смешанные физические/виртуальные варианты предлагается разрешить
в Catalog с проверкой capabilities канала; повтор SKU внутри одного Product
предлагается запретить. Эти решения утверждаются до VARIABLE/Inventory.
Сейчас SKU-связи и VARIABLE не реализованы.

## Приёмка

Domain create/restore и переходы; пользовательский тип без title; независимые
локали PRODUCT и запрет VARIANT у SIMPLE;
очистка HTML; used/system protection; tenant isolation; rollback,
ошибка commit; конкурирующая схема/контент и устаревшие ревизии. Проверка всего
архитектурного diff и обязательных файлов. Console: lint, typecheck, build и
браузерные создание/редактирование, отсутствие fallback, конфликты и dirty guards.

## Табличное хранение переводов

JSON/JSONB в Catalog отсутствуют. Подписи определений: content_block_translations
и product_type_translations с PK (owner_id, locale) и label. PRODUCT и VARIANT:
product_translations/variant_translations отмечают существование перевода;
product_content_values/variant_content_values хранят (owner_id, locale, block_id,
value TEXT). Отдельная строка перевода сохраняет различие между отсутствием
перевода и существующим переводом без необязательных значений. Значения имеют
составной FK к переводу и FK к определению блока. Locale хранится явно, без
каскадной зависимости от активности глобального справочника.

VARIANT-таблицы сохранены для следующего среза VARIABLE; команды записи и удаления
VARIANT-перевода у SIMPLE возвращают 422.
