# Catalog

> Этот документ описывает текущий код Product/Variant. Целевая замена с 2026-10-11 —
> [CatalogItem](../plan/catalog.md): одна товарная модель, fresh database
> и переписанные Catalog-миграции. План новой модели не означает, что код ниже
> уже переработан; отчёты проверок относятся к прежней реализации.

Catalog реализует SIMPLE/VARIABLE, enum-характеристики, пользовательские типы
и блоки контента, общие enum-значения, Category/Tag, явные локали, HTTP API и Console. Полный целевой план находится в
[docs/plan/catalog.md](../plan/catalog.md), исторические матрицы сценариев и
checklist текущего кода — в [catalog-slice-1.md](../plan/catalog-slice-1.md) и
[catalog-slice-2.md](../plan/catalog-slice-2.md) и
[catalog-slice-3.md](../plan/catalog-slice-3.md).

## Модель и правила

Самостоятельные корни: Product, ProductType, ContentBlockDefinition и
AttributeDefinition, Category и Tag. Product владеет типизированным компонентом структуры:
SIMPLE содержит ровно один Variant с пустым selection и без VARIANT-переводов;
VARIABLE содержит непустые оси и минимум два Variant. Позиции принадлежат Product,
options — AttributeDefinition; у них нет собственных write repositories.
Создание допускается без переводов и не создаёт SKU.

Оси используют enum attribute/option ID, разрешённые options и порядок. Каждая
комбинация полная, допустимая и уникальная; default_selection отсутствует либо
совпадает с существующей позицией. ID и коды определений/options стабильны,
подписи локализуются независимо. Используемые значения нельзя удалить, включая
options, разрешённые осью, но ещё не выбранные в позиции.

replace_variants и change_product_kind передают полную целевую структуру.
Существующие Variant ID и переводы сохраняются. Удаление позиции с переводами
отклоняется (409); переход в SIMPLE с переводами оставляемой позиции — 422.
Переводы сначала явно удаляются отдельными командами. Переход в тот же kind
отклоняется. Mixed virtual допускается; downloadable остаётся недоступен.

Системный Default / «Чистый», код `default`, создаётся tenant-миграцией. Блоки
`title` (text), `description` и `short_description` (rich_text) доступны в PRODUCT.
VARIANT содержит только необязательные title и description для VARIABLE;
у SIMPLE эти связи не создают форму или разрешение записи. Версия схемы Default
в `0017_catalog_simple` — 1. Title обязателен при записи PRODUCT-перевода
Default. Пользовательский тип может не иметь title. Обязательность и порядок
принадлежат связи блока с типом; одно определение допускает разные настройки
PRODUCT и VARIANT.

Все изменения проходят через доменные методы; create/restore проверяют создание
и восстановление. Схема передаётся Product как immutable snapshot. Смена типа и
схемы проверяет весь активный контент Product во всех локалях. Несовместимое
изменение отклоняется, данные не удаляются автоматически. Системные определения
изменяются только миграцией. Коды стабильны, используемый value_type изменить
нельзя, используемые определения нельзя удалить.

Локали проверяются через Application-контракт reference_data. GET требует locale;
отсутствующий перевод возвращается как null. Нет fallback между языками.
VARIABLE наследует только системный Title той же locale, если блок включён в оба scope. Отсутствующий ключ означает наследование,
пустая строка — собственный override. PUT полного VARIANT-перевода без ключа
title возвращает наследование. effective_title/title_source в read DTO вычисляются
без копирования значений в SQL; описание позиции всегда собственное. Запись разрешена только для активной
locale; существующий перевод деактивированной locale остаётся читаемым. Catalog не задаёт
язык tenant. HTML очищается NH3-адаптером за Application-портом до проверки Domain.

## Таблицы

JSON и JSONB для хранения Catalog не используются.

| Таблица | Назначение / ключ |
| --- | --- |
| catalog_products | Product, kind, product_type_id, revision, audit |
| catalog_variants | Позиции Product, virtual/downloadable; составной ключ ownership product_id/id |
| catalog_product_types | Определение типа, code, schema_version, revision, audit |
| catalog_content_block_definitions | Определение блока, code, value_type, revision, audit |
| catalog_product_type_content_blocks | (product_type_id, block_id, scope), required, position |
| catalog_product_type_translations | (product_type_id, locale), label |
| catalog_content_block_translations | (content_block_id, locale), label |
| catalog_product_translations | (product_id, locale), наличие перевода PRODUCT |
| catalog_variant_translations | (variant_id, locale), собственные переводы VARIANT |
| catalog_product_content_values | (product_id, locale, block_id), value TEXT |
| catalog_variant_content_values | (variant_id, locale, block_id), value TEXT |

В `0018_catalog_variable` добавлены восемь таблиц:

| Таблица | Назначение / ключ |
| --- | --- |
| catalog_attributes | enum-определение, code/revision/audit |
| catalog_attribute_options | option ID, attribute owner, code, position |
| catalog_attribute_translations | (attribute_id, locale), label |
| catalog_attribute_option_translations | (option_id, locale), label |
| catalog_product_axes | (product_id, attribute_id), position |
| catalog_product_axis_options | разрешённые options оси с составным FK к владельцу |
| catalog_variant_selections | option каждой оси позиции, составные FK ownership/allowed |
| catalog_product_default_selections | явная комбинация по умолчанию |

Product проверяет количество позиций, полные уникальные комбинации, default
и запрет VARIANT-переводов SIMPLE. SQL сохраняет FK, CHECK и уникальные ограничения;
миграции Catalog не создают пользовательские функции и триггеры. Изменения
выполняются через Application под общей transaction-блокировкой Catalog tenant.

Строка перевода существует отдельно от значений: {} означает существующий перевод
без значений, null — отсутствие перевода. Значения имеют составной FK к переводу
и FK к определению блока. Внутренние части удаляются с владельцем; ссылки на
самостоятельные определения используют RESTRICT. Locale не имеет каскадной связи
с глобальным справочником, чтобы деактивация не уничтожала данные.

У каждого root есть write и query repositories с отдельными mapper/query_mapper.
Табличные части восстанавливаются только write side; read side собирает DTO из
SQL-строк без создания Domain. Все репозитории используют выбранную Tenancy
схему и сессию общего UoW. Commit выполняется до отправки успешного ответа.

## Конкурентность

Каждая команда получает PostgreSQL transaction advisory lock по tenant + Catalog.
Проверка ревизии, ссылок и контента выполняется внутри него. Query-сценарии берут
shared lock на время чтения нескольких таблиц: параллельные читатели совместимы,
запись не может изменить части проекции между SELECT. Locks освобождает внешний
UoW при commit/rollback. Это намеренная граница производительности первого среза.

Команды изменения существующих агрегатов требуют expected_revision. Запись
контента и изменение схемы дополнительно требуют expected_schema_version.
Устаревшая версия даёт 409, доменное нарушение — 422, отсутствие объекта — 404.
Дубли кодов и защищённые ссылки дают 409. Authentication и CSRF используют Identity;
tenant/actor не принимаются из тела пользовательского запроса.

## API

Префикс: `/api/console/catalog`. Каждый метод имеет собственный controller,
Request (при теле) и Response (при результате). Полная матрица с DTO находится
в документах обоих срезов. GET коллекций принимает locale, search, page и
page_size (1–100); список товаров также принимает product_type_id и kind. Порядок
стабилен: created_at DESC, id. Поиск товаров ищет значения выбранного перевода
и ID; справочников — подпись, код и ID. Поиск не выбирает другую locale.

- `/products/simple`: POST создания; результат id, revision, variant_id.
- `/products/variable`: POST полной структуры; результат id, revision.
- `/products/{product_id}/structure`: PUT структуры VARIABLE.
- `/products/{product_id}/kind`: PUT явного перехода вида.
- `/attributes`: GET/POST; `/attributes/{id}`: GET/DELETE.
- `/attributes/{id}/translations/{locale}`: PUT подписи.
- `/attributes/{id}/options/{locale}`: PUT полного списка options с порядком и подписями.
- `/products`: GET списка; `/products/{product_id}`: GET и DELETE.
- `/products/{product_id}/type`: PUT смены типа.
- `/products/{product_id}/content/{locale}`: PUT/DELETE PRODUCT-перевода.
- `/products/{product_id}/variants/{variant_id}`: GET позиции через оба ID.
- `/products/{product_id}/variants/{variant_id}/content/{locale}`: сохранённый контракт VARIANT; PUT/DELETE у SIMPLE возвращает 422.
- `/products/{product_id}/variants/{variant_id}/properties`: PUT свойств позиции.
- `/product-types`: GET/POST; `/product-types/{product_type_id}`: GET/DELETE.
- `/product-types/{product_type_id}/translations/{locale}`: PUT подписи.
- `/product-types/{product_type_id}/schema`: PUT связей блоков.
- `/content-blocks`: GET/POST; `/content-blocks/{content_block_id}`: GET/PUT/DELETE.

PUT контента заменяет один полный перевод; values — HTTP-словарь block ID → строка,
который сохраняется в отдельных строках SQL, а не JSON-колонке. DELETE использует
expected_revision в query и возвращает 204 без пустого DTO/Response.

## Console

Раздел «Каталог» содержит товары, enum-характеристики, типы и блоки. Маршруты находятся в существующем
защищённом workspace layout. Список сохраняет locale, поиск, kind, тип и страницу в URL.
Карточка товара сохраняет активный раздел в URL. Формы PRODUCT, свойств,
типа, подписей и схемы сохраняются отдельно. Создание типа сначала создаёт пустую
схему; связи добавляются в его редакторе отдельной явной операцией.
Отдельной формы VARIANT-контента SIMPLE нет. У SIMPLE URL с section=VARIANT показывает
контент товара; маршрут позиции открывает её свойства. У VARIABLE маршрут
позиции открывает собственный контент и управление Title; отдельный раздел
сохраняет полную структуру осей, комбинаций и default selection. Enum-редактор
сохраняет подпись определения отдельно от списка options, их порядка и подписей.
Редактор блока сохраняет и удаляет только блок, без дополнительных команд ProductType.
AppLayout запускает определение tenant независимо от открытого мобильного меню;
прямое открытие карточки не остаётся в загрузке из-за скрытого sidebar.

Данные HTTP и frontend-модели разделены. Pages координируют API, queries и navigation;
остальные UI получают props/emits. Query keys включают tenant/session, use case,
ID, locale и параметры списка. Поздний ответ старой сессии не изменяет формы
и не запускает навигацию. При смене tenant/session запросы отменяются,
старый cache и формы очищаются. Несохранённый ввод защищён при навигации и смене
locale; запись блокирует повторную отправку. Сетевой/версионный конфликт сохраняет
ввод и требует явного обновления. После сохранения форма показывает очищенный
сервером HTML. Неактивная locale доступна для чтения, не для записи контента.

## Проверки

- `python -m unittest test.test_catalog test.test_catalog_variable`: Domain и архитектура, аннотации,
  обязательные файлы, границы импортов, пустые __init__.py, отсутствие JSON-хранения.
- `TEST_POSTGRES_URL=... python -m unittest test.test_catalog_postgres test.test_catalog_variable_postgres`: реальные
  HTTP/CSRF, tenant isolation, версии, HTML, FK, empty/null, системные определения,
  rollback, ошибка commit, гонка schema/content и downgrade/upgrade.
- `TEST_POSTGRES_URL=... python -m unittest test.test_tenant_migrations_postgres`:
  onboarding, migration isolation, round-trip, autogenerate без расхождений metadata.
- Из frontends: `npm run lint:console`, `npm run typecheck:console`,
  `npm run build:console`.
- Браузерная проверка выполняется на отдельном тестовом tenant с искусственной
  auth-сессией и реальными Catalog API/SQL. Рабочие данные пользователя не затрагиваются.

Локальные общие Identity HTTPS-тесты требуют AUTH__ALLOW_INSECURE_HTTP=false,
если окружение разработки разрешает HTTP. Это настройка запуска тестов, не изменение
политики рабочего сервиса.

## Границы среза

Нет text/number/boolean/multi_enum, медиа, SKU, цифровых файлов,
цен, упаковки, импорта и доставки Channels. Virtual поддержан; downloadable=true
отклоняется до файлового контракта. Физическая карточка без SKU не объявляется
готовой к продаже. Нет публикационного статуса магазина или складских остатков
в Product. GetProductPublicationSnapshot появится вместе с потребителем Channels.

Catalog не выходил в production. Исправленная `0017_catalog_simple` остаётся
baseline; тестовые базы с ранней редакцией пересоздаются. Новая 0018 расширяет
текущую 0017 без преобразования или удаления контента. Остальные tenant
обновляются явно до head перед API; миграции не запускаются при открытии Console.
Downgrade 0018 запрещён при наличии VARIABLE, иначе сохраняет SIMPLE и удаляет
enum-справочники. Downgrade до 0016 удаляет Catalog и его данные.

## Проверка выравнивания SIMPLE (2026-10-10)

Domain/architecture проверяют инвариант SIMPLE, обязательные файлы сценариев,
аннотации и направление импортов. PostgreSQL-тесты покрывают PRODUCT-переводы,
запрет VARIANT, версии, очистку HTML, tenant isolation, FK, null/пустой перевод,
rollback, ошибки commit, гонку схемы и контента, downgrade/upgrade. Tenant migration
тесты проверяют onboarding и транзакционность; autogenerate на head должен быть пустым.
Обязательны Black, diff whitespace, Console lint/typecheck/build и браузерная проверка.

В браузере проверяются три PRODUCT-поля без отдельной VARIANT-формы,
сохранение перевода, выбор locale, section=VARIANT и маршрут позиции.
Редактор блока должен отправлять один PUT или DELETE блока без команды ProductType,
а редактор ProductType — сохранять собственную ветку. Desktop и mobile включают
прямую загрузку с закрытым sidebar, проверку Console, framework overlay и переполнения.
Используется отдельная тестовая PostgreSQL с искусственной auth-сессией;
production SSO и другие браузеры проверяются отдельно.

После сборки единственной 0017 выполнены 65 unittest: 43 Domain/architecture/
ownership/registration/management и 22 PostgreSQL (5 Catalog, 17 tenant migrations).
Все успешны, autogenerate на head пустой. Black, diff whitespace и Console
lint/typecheck/build прошли. Chromium/Playwright на 127.0.0.1:4173, desktop
1440×1000 и mobile 390×844: сохранение PRODUCT, отсутствие fallback, маршрут
позиции, прямое открытие с закрытым меню, сохранение/удаление блоков и типов.
API и форма товара содержат только текущий контракт. Console/runtime ошибок,
framework overlay и горизонтального переполнения нет. Browser plugin отсутствует;
использован установленный Playwright и реальный тестовый Catalog API/SQL.

## Проверка второго среза (2026-10-10)

Выполнены 90 выбранных unittest: 59 Domain/architecture/ownership/registration/
management и 31 PostgreSQL (5 SIMPLE Catalog, 9 VARIABLE Catalog, 17 tenant
migrations). Все успешны; autogenerate на head пустой.
Проверены upgrade с сохранением SIMPLE, ID, переводов и revision, защищённый
downgrade, SQL ownership и доменные проверки комбинаций и структуры.
Весь diff проверен по требованиям архитектуры; для 31 сценария проверены
обязательные файлы, отдельные результаты, аннотации, docstrings и границы слоёв.
Black, diff whitespace, Console lint, vue-tsc и Vite production build прошли;
CLI запущены bundled Node, поскольку npm в окружении отсутствует.

Chromium/Playwright, 127.0.0.1:4173, desktop 1440×1000 и mobile 390×844:
создание enum и VARIABLE, порядок options, редактор осей/позиций/default,
сохранение ID и контента, Title override/возврат/смена названия Product,
отсутствие fallback, переход VARIABLE→SIMPLE, сохранность SIMPLE.
Каждое сохранение отправляет одну соответствующую команду. Отдельно проверены
отмена навигации с dirty-вводом, 409 с сохранением ввода и блокировкой повторной
записи до явного reload. Нет неожиданных runtime/Console ошибок, framework overlay или
горизонтального переполнения. Browser plugin отсутствует, использован установленный
Playwright. API/CSRF/UoW/SQL реальные, auth и selector locale тестовые.
Production SSO и другие браузеры этим прогоном не проверены.


## Срез 3: общие enum-значения и классификация

Product хранит отдельные attribute_values (attribute_id, option_id, visible,
position), category_ids/primary_category_id и tag_ids. Enum membership проверяется
по immutable снимкам определений; позиции и attribute IDs уникальны. Общие значения
и оси VARIABLE независимы. Видимость не ограничивает чтение и не меняет selection.
Непустой набор категорий требует одну основную из назначенных IDs; пустой очищает
набор и primary. Предки не назначаются автоматически. Kind/type/content команды
сохраняют все назначения. Ссылки проверяются в текущем tenant под общим lock.

Category — отдельный агрегат с parent ID и локализованными подписями. Перемещение
проверяет цепочку предков нового родителя; нельзя переместить в себя или под потомка.
Tag — отдельный агрегат со стабильным UUID и переводами, без ключа по тексту подписи.
Существующие переводы других locale сохраняются; locale fallback отсутствует.
Используемые category/tag/attribute/option нельзя удалить; category с детьми также
защищена. Проверки общих значений дополняют защиту options, разрешённых осями.

`0019_catalog_classification` добавляет семь таблиц:

| Таблица | Назначение |
| --- | --- |
| catalog_categories | ID, parent_id, revision, audit |
| catalog_category_translations | (category_id, locale), label |
| catalog_tags | ID, revision, audit |
| catalog_tag_translations | (tag_id, locale), label |
| catalog_product_attribute_values | (product_id, attribute_id), option_id, visible, position |
| catalog_product_categories | (product_id, category_id), is_primary |
| catalog_product_tags | (product_id, tag_id) |

Всего у Catalog 26 таблиц. FK справочников используют RESTRICT, внутренних частей
CASCADE. Partial unique index запрещает две primary. Product требует одну primary
у непустого набора, Category запрещает циклы по снимку предков. Эти доменные
проверки выполняются под transaction-блокировкой Catalog. Прямой SQL вне сценариев
не гарантирует соблюдение всех инвариантов агрегатов. Миграция не меняет
существующие строки и не вводит compatibility path.
Downgrade 0019 удаляет справочники и назначения этого среза, оставляя старый Catalog.

API под `/api/console/catalog`: POST/GET `/categories`, GET/DELETE `/categories/{id}`,
PUT `/categories/{id}/translations/{locale}` и `/categories/{id}/parent`;
POST/GET `/tags`, GET/DELETE `/tags/{id}`, PUT `/tags/{id}/translations/{locale}`.
Чтение категорий поддерживает parent_id либо roots_only=true, поиск и пагинацию;
без фильтра возвращает плоскую страницу для selector. Каждая строка имеет child_count.
GET требует locale. Все команды существующих объектов требуют expected_revision.
PUT `/products/{id}/attributes`, `/categories`, `/tags` заменяют один полный набор.
GET Product содержит собственные DTO новых полей. Контракты и файлы всех 14 новых
сценариев перечислены в плане среза 3; у delete результат None и HTTP 204.

Console добавляет дерево по ветвям и редакторы Category/Tag, три раздела Product.
Каждое сохранение отправляет одну команду, затем читает подтверждённое состояние.
409 сохраняет черновик и блокирует повторную запись до явного reload. Dirty-ввод
защищён при смене section/locale/route; tenant и session входят в query keys.


## Проверка третьего среза (2026-10-10)

75 выбранных unittest прошли, включая Domain/architecture, HTTP/Postgres,
регистрацию/ownership и tenant migrations/management. Проверены все 45 сценариев
по обязательным файлам и требованиям архитектуры. Autogenerate на текущем head
пустой; upgrade сохраняет SIMPLE/VARIABLE, контент и идентичности. Black, whitespace,
ESLint, vue-tsc и production build успешны. Подробности — в плане среза 3.

Playwright/Chromium на 127.0.0.1:4173, 1440×1000 и 390×844: дерево, создание и
перемещение категории, создание/перевод метки, три секции Product, явная primary,
независимость общих enum-значений от осей. По одной команде на каждое сохранение.
409 в Product и Tag сохраняет ввод и блокирует запись до reload; dirty-навигация
защищена. Нет неожиданных console/runtime ошибок, overlay или переполнения.
Browser plugin отсутствует; auth/locale selector тестовые, остальной путь реальный.
Production SSO и другие браузеры остаются вне этой проверки.
