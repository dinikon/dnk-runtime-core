# Catalog: enum-атрибуты и VARIABLE

Срез реализует enum-определения, VARIABLE, явные переходы вида и наследование
системного Title. Inventory/SKU, файлы/downloadable, общие характеристики,
классификация и Channels остаются следующими срезами общего плана.

## Архитектура и требования

Корни: Product, AttributeDefinition, существующие ProductType и
ContentBlockDefinition. Variant принадлежит Product; AttributeOption принадлежит
AttributeDefinition. У внутренних Entity нет write repositories. Product хранит
типизированную структуру SIMPLE/VARIABLE и устойчивые ссылки на attribute/option.
Domain получает immutable снимки определений, не чужие агрегаты.

Применяются все правила docs/architecture/AGENTS.md: модуль → слой → корень →
назначение; Domain без I/O; Application только с портами; create/restore и
доменные методы; инварианты в агрегатах; __post_init__ только в VO; аннотации
всех параметров/результатов и русские docstrings; отдельные DTO каждого сценария;
write/query repositories раздельны; mapper без бизнес-исправлений; HTTP
controller/request/response раздельны; именованные Depends; общий tenant UoW,
Identity и CSRF; отсутствие commit/rollback в repositories; SQL-модель на файл,
пустые __init__.py, прямые импорты. Контент, секреты и payload не логируются.
Интеграционные сообщения в этом срезе не создаются.

## Решения

- AttributeDefinition пока имеет только enum; options имеют неизменяемые ID/коды,
  порядок и независимые переводы. Подписи не определяют идентичность.
- Замена options сохраняет переводы других locale и проверяет использование
  удаляемых options, включая разрешённые значения осей, не только selection.
- SIMPLE имеет одну позицию с пустым selection и без VARIANT-переводов.
  VARIABLE имеет непустые оси и минимум две позиции с полными уникальными
  комбинациями. Default selection отсутствует или совпадает с существующей позицией.
- Смешанные virtual разрешены в Catalog. Downloadable по-прежнему недоступен.
- Изменение структуры сохраняет ID и контент оставленных позиций. Удаление
  позиции с переводами и переход в SIMPLE с VARIANT-переводами отклоняются:
  пользователь сначала явно удаляет переводы отдельными сценариями.
- Наследуется только системный блок title, включённый в оба scope схемы.
  Отсутствующий ключ означает наследование, пустая строка является собственным
  значением. Снятие override — PUT полного VARIANT-перевода без ключа title.
  Другие блоки не наследуются. Required проверяется по собственным значениям
  перевода; VARIANT title в Default необязателен; custom required требует собственное значение. Наследование не записывается в SQL.
- Read DTO разделяют content, effective_title и title_source
  (PRODUCT/VARIANT/null); другой язык не используется. Наличие собственного
  VARIANT-перевода независимо от возможности наследовать Title.
- Контракты чтения Product используют axes, default_selection и variants;
  старые одиночные variant-поля удаляются. CreateSimpleProductResultDTO сохраняет
  variant_id как результат создания одной позиции.
- Схема Default версии 1 не меняется. Новая миграция расширяет 0017, сохраняет
  SIMPLE, их Variant ID, контент и ревизии. JSON/JSONB и legacy не вводятся.

## Новые сценарии

Все команды имеют доверенный tenant/actor; изменения — expected_revision.
Чтение и запись подписей требуют явную locale. Структурные команды принимают
оси (attribute_id, option_ids, position), default_selection и позиции
(variant_id либо null для новой, selection, virtual).

| Корень / сценарий | Вход | execute | HTTP после /api/console/catalog |
| --- | --- | --- | --- |
| attribute/create_attribute | code, locale, label, options(code,label) | CreateAttributeResultDTO | POST /attributes |
| attribute/put_attribute_translation | ID, locale, label, revision | PutAttributeTranslationResultDTO | PUT /attributes/{id}/translations/{locale} |
| attribute/replace_attribute_options | ID, locale, options(ID/code/label), revision | ReplaceAttributeOptionsResultDTO | PUT /attributes/{id}/options/{locale} |
| attribute/delete_attribute | ID, revision | None | DELETE /attributes/{id} |
| attribute/get_attribute | ID, locale | GetAttributeDetailsDTO | GET /attributes/{id} |
| attribute/list_attributes | locale, search, page/page_size | ListAttributesPageDTO | GET /attributes |
| product/create_variable_product | type ID, полная структура | CreateVariableProductResultDTO | POST /products/variable |
| product/replace_variants | product ID, revision, полная VARIABLE-структура | ReplaceVariantsResultDTO | PUT /products/{id}/structure |
| product/change_product_kind | product ID, revision, kind, полная целевая структура | ChangeProductKindResultDTO | PUT /products/{id}/kind |

Существующие put/delete_variant_content и set_variant_properties адресуют позицию
через product ID + variant ID; get_product/get_variant/list_products получают
собственные расширенные DTO. list_products добавляет kind и считает товары,
а не строки JOIN позиций. Смена типа/схемы проверяет весь контент всех позиций.

## Обязательные файлы и зависимости

Для каждой строки таблицы: application/<root>/command|query/<scenario>/
command|query.py, handler.py, dto.py (кроме None); presentation/<root>/http/
controller/<scenario>.py, request/<scenario>.py при теле,
response/<scenario>.py при результате; router.py и depends.py.

Для attribute: domain/attribute/{aggregate,error,repository}.py, entity/option.py,
value_object/identifier.py и option_id.py; infrastructure/attribute/persistence/
{mapper,repository,query_mapper,query_repository}.py; Application query repository
port. Product получает AttributeDefinitionsPort и immutable снимки через SQL
adapter. Его structure компоненты находятся в domain/product/entity/, axis и
selection — в value_object/. Команды структуры используют общий небольшой
Application service подготовки снимков и новых ID, не вызывают другие handlers.

SQL-модели: attribute, attribute_translation, attribute_option,
attribute_option_translation, product_axis, product_axis_option,
variant_selection, product_default_selection; регистрация в tenant_persistence.
FK защищают ownership option→attribute и selection→разрешённый option оси.
Tenant Catalog transaction lock сохраняет сериализацию изменений определений,
структуры и контента; query shared lock обеспечивает согласованное чтение.

Console: справочник и редактор enum-атрибутов; создание SIMPLE/VARIABLE;
редактор полной структуры и отдельная карточка варианта; Title override и
возврат к наследованию; подтверждение перехода с перечнем затронутых позиций.
Формы работают через props/emits, страницы координируют API, DTO преобразуются
в frontend-модели. Сохранение по разделам, dirty/pending guards, 409 сохраняет ввод.

## Приёмка

Domain: create/restore, структуры обоих видов, неполные/недопустимые/повторные
комбинации, default selection, переходы без потери контента, локали и Title.
HTTP/PostgreSQL: ссылки и tenant isolation, revision/schema conflicts, очистка
HTML, использование options, rollback, список без дублей, сохранение SIMPLE
при upgrade, безопасный downgrade, autogenerate без расхождений.
Архитектурный diff и наличие обязательных файлов проверяются отдельно.
Console: lint, typecheck, production build; браузерные сценарии справочника,
создания VARIABLE, структуры, контента, переходов и мобильного отображения.

## Выполнено (2026-10-10)

Все девять новых сценариев и расширения существующих реализованы вместе с SQL,
HTTP и Console. 0018 сохраняет текущие SIMPLE; Default/schema_version 1 не меняется.
Результаты архитектурного аудита, 90 выбранных unittest, статических проверок и
Chromium desktop/mobile QA зафиксированы в
[документации Catalog](../modules/catalog.md#проверка-второго-среза-2026-10-10).
Следующий срез: общие типизированные значения характеристик и классификация;
Inventory/SKU, файлы и Channels требуют собственных последующих контрактов.
