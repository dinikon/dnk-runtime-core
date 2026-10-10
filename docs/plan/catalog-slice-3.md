# Catalog: срез 3 — общие enum-значения и классификация

Дата: 2026-10-10. Статус: реализован и проверен. Граница согласована запросом
реализации следующего среза.

## Архитектура и требования

Нормативный источник: `docs/architecture/AGENTS.md`, прочитан полностью.
Корни: Product, ProductType, ContentBlock, AttributeDefinition, Category, Tag.
Product владеет общими enum-значениями и назначениями; отдельные write repositories
для таблиц назначений не создаются. Category владеет своим parent ID и переводами,
Tag — переводами. Идентичность справочников — UUID, подписи не являются ключами.

Domain чистый; create/restore проверяют состояние, изменения проходят через методы.
__post_init__ только в VO. Все методы аннотированы и документированы по-русски.
Каждый сценарий имеет собственные Command/Query, Handler и DTO; delete -> None.
Write repository восстанавливает агрегат, Query repository создаёт проекции без
восстановления. Mapper не принимает бизнес-решений. Depends собирает порты на одной
tenant-сессии внешнего UoW, repositories не выбирают schema и не выполняют commit.
Общий transaction lock Catalog защищает назначения, удаления и перемещения.
HTTP Request/Response разделены, мутации требуют CSRF и доверенного Identity context.
Пакетные __init__.py пусты. Существующий контент и структура сохраняются.

## Контракты до реализации

Общее значение: attribute_id, option_id, visible, position; один enum option на
определение, уникальны definition и position. Visible не меняет оси или selection.
Category: ID, parent_id nullable, локализованная label, revision, audit. Циклы
проверяются Domain по immutable ancestor snapshot Application-порта.
Tag: ID, локализованная label, revision, audit; произвольного изменяемого кода нет.
Категории Product: явно назначенные IDs и primary_category_id; непустой набор имеет
ровно одну основную. Предки не назначаются автоматически. Tags уникальны.
Пустой полный набор очищает назначения. Все ссылки проверяются в текущем tenant.
Удаление используемых category/tag/attribute/option запрещено; category с детьми
удалить нельзя. Смена kind/type сохраняет назначения.

| Сценарий | Вход | Результат | Порты и HTTP |
| --- | --- | --- | --- |
| create_category | parent_id, locale, label | CreateCategoryResultDTO(id, revision) | CategoryRepository, Tree, locales, lock, clock, uuid; POST /catalog/categories |
| put_category_content | ID, locale, label, expected_revision | PutCategoryContentResultDTO | Repository, locales, lock, clock; PUT /categories/{id}/translations/{locale} |
| move_category | ID, parent_id, expected_revision | MoveCategoryResultDTO | Repository, Tree, lock, clock; PUT /categories/{id}/parent |
| delete_category | ID, expected_revision | None | Repository, lock; DELETE /categories/{id} |
| get_category | ID, locale | GetCategoryDetailsDTO | Query repository, read lock; GET /categories/{id} |
| list_categories | locale, search, parent_id?, roots_only, page, page_size | ListCategoriesPageDTO | Query repository, read lock; GET /categories |
| create_tag | locale, label | CreateTagResultDTO | TagRepository, locales, lock, clock, uuid; POST /catalog/tags |
| put_tag_translation | ID, locale, label, expected_revision | PutTagTranslationResultDTO | Repository, locales, lock, clock; PUT /tags/{id}/translations/{locale} |
| delete_tag | ID, expected_revision | None | Repository, lock; DELETE /tags/{id} |
| get_tag | ID, locale | GetTagDetailsDTO | Query repository, read lock; GET /tags/{id} |
| list_tags | locale, search, page, page_size | ListTagsPageDTO | Query repository, read lock; GET /tags |
| set_product_attributes | ID, expected_revision, values | SetProductAttributesResultDTO | ProductRepository, definitions snapshots, lock, clock; PUT /products/{id}/attributes |
| set_product_categories | ID, expected_revision, IDs, primary ID | SetProductCategoriesResultDTO | ProductRepository, references, lock, clock; PUT /products/{id}/categories |
| set_product_tags | ID, expected_revision, IDs | SetProductTagsResultDTO | ProductRepository, references, lock, clock; PUT /products/{id}/tags |

Для каждой строки: application/<root>/{command|query}/<scenario>/{command|query}.py,
handler.py и dto.py (кроме delete); presentation/<root>/http/controller/<scenario>.py,
request для тела мутации, response для результата; именованный Depends и route.
Domain repository.py и application/<root>/port/query_repository.py; infrastructure
/<root>/persistence/{repository,mapper,query_repository,query_mapper}.py.
Минимальные Tree/References/Definitions порты не возвращают чужие агрегаты Product.
get_product расширяется отдельными вложенными DTO значений и ссылками классификации.

## Хранение и Console

Нормализованные category/tag и переводы, product_attribute_values,
product_categories (is_primary), product_tags; FK запрещают удаление используемых
справочников. Partial unique index запрещает две primary; Product требует одну
primary у непустого набора, Category проверяет циклы по снимку предков под общим
transaction lock Catalog. Миграции не создают пользовательские функции и триггеры.
Новая tenant migration после текущего head; старые ревизии и контент не изменяются.
Console: дерево по ветвям, отдельные редакторы category/tag; три секции Product.
Каждая секция сохраняет один сценарий и сохраняет черновик при 409. Tenant/locale,
dirty guards, pending и stale session проверяются как в предыдущем срезе.

## Проверки и последующие шаги

Domain: membership, uniqueness, primary, cycle, delete protection, сохранение
структуры/контента. HTTP/Postgres: tenant, CSRF, 404/409/422, rollback, SQL FK и
primary, миграция с сохранением SIMPLE/VARIABLE, autogenerate без drift.
Статика: архитектурный AST audit, Black, ESLint, vue-tsc, build; браузерная проверка.
Следующий срез: text/number/boolean/multi_enum с отдельными контрактами локализации
и единиц; затем SKU/Inventory, медиа/Files, цены/упаковки и Channels с потребителем.


## Результат проверки

Добавлены 14 сценариев; Catalog теперь имеет 45 use cases / HTTP-методов и
26 нормализованных таблиц. Обязательные файлы проверены для всех 45 сценариев.
Delete возвращает None; для остальных 37 сценариев есть собственные DTO/Responses.
Проверены фабрики, методы изменения, аннотации, русские docstrings, пустые init,
отсутствие SQL/HTTP/logging в Domain/Application, направление импортов и общий UoW.
Mapper передаёт все primary IDs в restore: он не выбирает правильную primary
из некорректных SQL-строк вместо проверки агрегатом.

75 выбранных unittest прошли: Catalog Domain/architecture, SIMPLE/VARIABLE и новый
срез HTTP/Postgres, tenant migrations/management, module registration/ownership.
Проверены доменные циклы и primary, SQL FK и уникальность primary, защищённые
удаления general-only options, membership, ревизии, конкуренция, CSRF и tenant.
Upgrade 0018 -> 0019 сохраняет все прежние таблицы, включая ID, PRODUCT/VARIANT
переводы, selections и ревизии. Autogenerate на текущем head пустой.
Параллельно добавленный 0020_files продолжает 0019; общая CLI-проверка также прошла.
Black, diff whitespace, Console ESLint, vue-tsc и production build успешны.

Chromium/Playwright: 127.0.0.1:4173, 1440×1000 и 390×844. Browser plugin отсутствует.
API/CSRF/UoW/PostgreSQL реальные, Identity context и locale selector тестовые.
Дерево -> создание дочерней категории -> перемещение -> создание/перевод метки ->
три раздела Product -> подтверждённое чтение. Девять действий сохраняют по одной
команде; общие значения сохраняют axes/default/variants/content. Primary выбирается
явно, предки не назначаются. Нет неожиданных console/runtime ошибок, overlay или
горизонтального переполнения; desktop/mobile screenshots просмотрены.
Отдельно проверены dirty-navigation cancel, 409 для Product и Tag с сохранением
черновика, запрет записи до явного reload и восстановление подтверждённых значений.
Production SSO, другие браузеры и Catalog↔Files/SKU/Channels этим срезом не проверены.
Временные сервисы и тестовые tenant-схемы убраны; рабочие данные не изменялись.
