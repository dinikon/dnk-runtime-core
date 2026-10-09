# Catalog

Первый срез реализует SIMPLE-товары, пользовательские типы и блоки контента,
явные локали, HTTP API и Console. Полный целевой план находится в
[docs/plan/catalog.md](../plan/catalog.md), матрица сценариев и архитектурный
checklist — в [catalog-slice-1.md](../plan/catalog-slice-1.md).

## Модель и правила

Самостоятельные корни: Product, ProductType и ContentBlockDefinition. Product
владеет ровно одним Variant и независимым контентом PRODUCT/VARIANT. Variant
не имеет своего write repository. Создание товара не создаёт SKU и допускается
без переводов. ProductKind содержит simple/variable, однако создание VARIABLE
и переходы вида ещё не реализованы.

Системный Default / «Чистый», код `default`, создаётся tenant-миграцией. Блоки
`title` (text), `description` и `short_description` (rich_text) доступны в обоих
scope. Title обязателен только при записи PRODUCT-перевода Default. Пользовательский
тип может не иметь title. Обязательность и порядок принадлежат связи блока с
типом; одно определение допускает разные настройки PRODUCT и VARIANT.

Все изменения проходят через доменные методы; create/restore проверяют создание
и восстановление. Схема передаётся Product как immutable snapshot. Смена типа и
схемы проверяет весь сохранённый контент, включая Variant и все локали. Несовместимое
изменение отклоняется, данные не удаляются автоматически. Системные определения
изменяются только миграцией. Коды стабильны, используемый value_type изменить
нельзя, используемые определения нельзя удалить.

Локали проверяются через Application-контракт reference_data. GET требует locale;
отсутствующий перевод возвращается как null. Нет fallback между языками и
наследования VARIANT от PRODUCT. Запись разрешена только для активной locale;
существующий перевод деактивированной locale остаётся читаемым. Catalog не задаёт
язык tenant. HTML очищается NH3-адаптером за Application-портом до проверки Domain.

## Таблицы

JSON и JSONB для хранения Catalog не используются.

| Таблица | Назначение / ключ |
| --- | --- |
| catalog_products | Product, kind, product_type_id, revision, audit |
| catalog_variants | Позиция Product, virtual/downloadable; уникальный product_id для SIMPLE |
| catalog_product_types | Определение типа, code, schema_version, revision, audit |
| catalog_content_block_definitions | Определение блока, code, value_type, revision, audit |
| catalog_product_type_content_blocks | (product_type_id, block_id, scope), required, position |
| catalog_product_type_translations | (product_type_id, locale), label |
| catalog_content_block_translations | (content_block_id, locale), label |
| catalog_product_translations | (product_id, locale), наличие перевода PRODUCT |
| catalog_variant_translations | (variant_id, locale), наличие перевода VARIANT |
| catalog_product_content_values | (product_id, locale, block_id), value TEXT |
| catalog_variant_content_values | (variant_id, locale, block_id), value TEXT |

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
в документе первого среза. GET коллекций принимает locale, search, page и
page_size (1–100); список товаров также принимает product_type_id. Порядок
стабилен: created_at DESC, id. Поиск товаров ищет значения выбранного перевода
и ID; справочников — подпись, код и ID. Поиск не выбирает другую locale.

- `/products/simple`: POST создания; результат id, revision, variant_id.
- `/products`: GET списка; `/products/{product_id}`: GET и DELETE.
- `/products/{product_id}/type`: PUT смены типа.
- `/products/{product_id}/content/{locale}`: PUT/DELETE PRODUCT-перевода.
- `/products/{product_id}/variants/{variant_id}`: GET позиции через оба ID.
- `/products/{product_id}/variants/{variant_id}/content/{locale}`: PUT/DELETE VARIANT-перевода.
- `/products/{product_id}/variants/{variant_id}/properties`: PUT свойств позиции.
- `/product-types`: GET/POST; `/product-types/{product_type_id}`: GET/DELETE.
- `/product-types/{product_type_id}/translations/{locale}`: PUT подписи.
- `/product-types/{product_type_id}/schema`: PUT связей блоков.
- `/content-blocks`: GET/POST; `/content-blocks/{content_block_id}`: GET/PUT/DELETE.

PUT контента заменяет один полный перевод; values — HTTP-словарь block ID → строка,
который сохраняется в отдельных строках SQL, а не JSON-колонке. DELETE использует
expected_revision в query и возвращает 204 без пустого DTO/Response.

## Console

Раздел «Каталог» содержит товары, типы и блоки. Маршруты находятся в существующем
защищённом workspace layout. Список сохраняет locale, поиск, тип и страницу в URL.
Карточка товара сохраняет активный раздел в URL. Формы PRODUCT, VARIANT, свойств,
типа, подписей и схемы сохраняются отдельно. Создание типа сначала создаёт пустую
схему; связи добавляются в его редакторе отдельной явной операцией.

Данные HTTP и frontend-модели разделены. Pages координируют API, queries и navigation;
остальные UI получают props/emits. Query keys включают tenant/session, use case,
ID, locale и параметры списка. Поздний ответ старой сессии не изменяет формы
и не запускает навигацию. При смене tenant/session запросы отменяются,
старый cache и формы очищаются. Несохранённый ввод защищён при навигации и смене
locale; запись блокирует повторную отправку. Сетевой/версионный конфликт сохраняет
ввод и требует явного обновления. После сохранения форма показывает очищенный
сервером HTML. Неактивная locale доступна для чтения, не для записи контента.

## Проверки

- `python -m unittest test.test_catalog`: Domain и архитектура, аннотации,
  обязательные файлы, границы импортов, пустые __init__.py, отсутствие JSON-хранения.
- `TEST_POSTGRES_URL=... python -m unittest test.test_catalog_postgres`: реальные
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

Нет VARIABLE, осей и атрибутов, категорий/меток, медиа, SKU, цифровых файлов,
цен, упаковки, импорта и доставки Channels. Virtual поддержан; downloadable=true
отклоняется до файлового контракта. Физическая карточка без SKU не объявляется
готовой к продаже. Нет публикационного статуса магазина или складских остатков
в Product. GetProductPublicationSnapshot появится вместе с потребителем Channels.

Существующие tenant нужно явно обновить до `0017_catalog_simple`; миграция не
запускается автоматически при открытии Console. Downgrade удаляет новый Catalog
и данные, поэтому применяется только как отдельная согласованная операция.

## Результат проверки первого среза

Проверено локально на отдельной PostgreSQL 16: общий набор unittest — 626 проверок,
успешно, 133 пропущены без соответствующего окружения; дополнительные 5 Catalog
интеграционных тестов и 17 tenant migration тестов выполнены с TEST_POSTGRES_URL.
После финального аудита DTO и Depends повторены Domain/architecture и реальные
Catalog HTTP-тесты. Проверены black и diff whitespace; Console lint/typecheck/build
успешны.

Chromium через установленный Playwright (Browser plugin отсутствует): создание
SIMPLE, очищенный HTML после сохранения, независимые PRODUCT/VARIANT переводы,
смена языка и вкладки с несохранённым вводом, пользовательские блок/тип/схема без
обязательного title, конфликт двух редакторов с сохранением ввода и явным
обновлением, неизвестная позиция. Desktop 1440×1000 и mobile 390×844: нет
горизонтального переполнения, runtime ошибок или framework overlay. HTTP 409/404
в отрицательных сценариях ожидаемы. Браузерный вход использовал тестовую
auth-сессию; production SSO и другие браузеры в этой проверке не покрыты.
