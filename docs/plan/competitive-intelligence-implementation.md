# План реализации competitive_intelligence

Дата: 2026-10-29. Статус: план, реализация не начата.
Требования продукта: [PRD «Аналитика конкурентов»](competitive-intelligence.md).
Ниже описаны будущие контракты и файлы; их наличие в плане не означает,
что соответствующие endpoint, CLI, модель или worker уже существуют.

Нормативные документы: [backend](../architecture/backend.md),
[frontend](../architecture/frontend.md). При расхождении примеров существующего
кода с правилами применяются нормативные документы.

## 1. Применимые архитектурные требования

Перечень для проверки всего diff каждого этапа:

- [ ] Код группируется как модуль → слой → Aggregate Root → ответственность.
- [ ] Source, SellerAccount, MarketPublication, CrawlRun и CatalogPublicationLink
  сохраняют самостоятельные границы; связи между ними передаются по ID.
- [ ] Aggregate/Entity используют create/restore и доменные методы; проверки
  инвариантов не переносятся в mapper. __post_init__ используется только в VO.
- [ ] Domain не импортирует HTTP, Pydantic, SQLAlchemy, браузер, inference или logger.
- [ ] Application использует Domain и абстрактные порты; не получает AsyncSession,
  ORM, session factory или конкретный адаптер площадки.
- [ ] Write repositories работают с агрегатами; query ports возвращают отдельные
  DTO сценариев без восстановления агрегата для таблиц и аналитики.
- [ ] Catalog, Tenancy и Reference Data вызываются через Application-контракты
  и адаптеры; внутренние агрегаты и ORM соседних модулей не импортируются.
- [ ] Внешняя сборка открывает UoW; repositories не делают commit/rollback.
  Репозитории одного атомарного шага используют одну сессию.
- [ ] Внешняя сеть, браузер и inference выполняются между короткими транзакциями;
  перед записью проверяются lease и актуальность исходных снимков.
- [ ] Outbox записывается вместе с изменением до commit; доставка идёт после
  commit; потребители имеют идемпотентность и Inbox там, где требуется.
- [ ] Глобальные и tenant-миграции разделены; схему tenant выбирает Tenancy
  до создания UoW, а не SQL каждого репозитория. Один UoW обслуживает один tenant.
- [ ] Каждый сценарий имеет command/query, handler.execute, конкретный DTO
  результата либо None и необходимые порты/адаптеры.
- [ ] Для каждого HTTP-метода отдельные controller/request/response по назначению;
  для 204 нет фиктивного response, для GET нет фиктивного request body.
- [ ] Все методы аннотированы, включая __init__ → None и execute; docstrings
  по-русски; backend __init__.py пустые, импорты из файлов определения.
- [ ] Структурированные логи содержат безопасные ID и reason codes; итог успеха
  фиксируется после commit, без credentials, raw HTML и inference payload.
- [ ] Console разделяет API/DTO/mapper, frontend types, queries, mutations,
  page state и UI; межмодульное использование идёт через публичный контракт.
- [ ] Query keys включают tenant и все параметры. Смена tenant отменяет запросы,
  очищает старый контекст; серверные данные не дублируются в Pinia.
- [ ] Денежные строки не превращаются в floating point на frontend.
- [ ] Для затронутого этапа выполнены необходимые проверки и отражены ограничения.

## 2. Границы и структура

~~~text
src/modules/competitive_intelligence/
  domain/
    source/
    seller_account/
    market_publication/
    crawl_run/
    catalog_publication_link/
  application/
    source/command|query|port/
    seller_account/command|query|port/
    market_publication/command|query|port/
    crawl_run/command|query|port/
    catalog_publication_link/command|query|port/
  infrastructure/
    source/definitions/prom.json
    source/definitions/rozetka.json
    source/definitions/source.schema.json
    source/configuration/
    crawl_run/fetching/
    crawl_run/extraction/
    market_publication/search/
    catalog_publication_link/adapter/
    catalog_publication_link/matching/
    <aggregate>/persistence/
    persistence/models/<one_model_per_file>.py
  presentation/
    <aggregate>/router.py
    <aggregate>/depends.py
    <aggregate>/http/controller/<scenario>.py
    <aggregate>/http/request/<scenario>.py
    <aggregate>/http/response/<scenario>.py
    <aggregate>/jobs/
    depends/
~~~

Для application запись command|query|port обозначает отдельные каталоги.
Внутри command/query каждый use case получает собственный каталог сценария.
Общие элементы остаются на соответствующем слое. Пустые заготовки дерева
заранее не создаются.

| Aggregate Root | Scope | Поведение |
| --- | --- | --- |
| Source | Instance | Активация проверенной конфигурации, пауза источника, смена активной ревизии |
| SellerAccount | Instance | Регистрация/восстановление identity и применение публичного наблюдения |
| MarketPublication | Instance | Создание по устойчивому ключу, применение свежего наблюдения, отметка исчезновения |
| CrawlRun | Instance | Старт, checkpoint, прогресс, завершение, ошибка, отмена |
| CatalogPublicationLink | Tenant | Предложение, подтверждение, skip, pause/resume, прекращение, needs_review |

Источник не содержит коллекцию всех продавцов, продавец — все публикации,
а публикация — всю историю наблюдений. Исторические/поисковые таблицы читаются
через query ports. Технические receipts URL принадлежат сценарию ingestion
и не превращаются в новый бизнес-агрегат автоматически.

## 3. Данные и миграции

Глобальная миграция после актуального global head создаёт public.ci_* из PRD.
Tenant-миграция после актуального tenant head создаёт связи, оценки, закрытую
поисковую проекцию и receipts. Номера ревизий выбираются при реализации;
исторические номера из других планов не копируются.

Основные индексы и ограничения хранения:

- Уникальный source code и неизменяемая пара source/revision для определения.
- Уникальный аккаунт продавца по source и подтверждённому внешнему ключу.
- Уникальный canonical identity key предложения в source namespace.
- Индексы publication по source, seller, canonical URL и следующему обновлению.
- Уникальный ключ применённого наблюдения для повторной доставки.
- Индексы истории по publication_id/observed_at/id для устойчивой пагинации.
- Индексы валидных идентификаторов товара для точного candidate retrieval.
- Версионированный embedding с model ID, размерностью и matching fingerprint.
- Уникальная tenant-пара catalog_item_id/publication_id; индекс status/item.
- Уникальный tenant receipt по idempotency key и fingerprint запроса.
- Индексы due jobs по маршруту, состоянию и run_at после изменения Shared Jobs.

PK, NOT NULL, уникальность и допустимые FK защищают хранение; переходы состояний
и предметные правила принадлежат Domain. Смена ревизии конфигурации не меняет
UUID уже распознанной публикации без явной миграции её identity.

Ссылка tenant → global publication хранится как стабильный UUID с проверкой
через порт. В MVP не вводится каскадное удаление из public в tenant-схемы.
Глобальные UUID сохраняются как tombstones. Доступ к Catalog не требует импорта
его ORM; согласование удаления выполняется через публичный usage-контракт.

TenantBase, naming, admission, upgrade существующих tenant и регистрацию
metadata обеспечивает Tenancy. Подключить новые модели к действующим ownership
registries, включая исторические имена для будущих удалений. Миграции не
запускаются из HTTP, scraper или matcher.

pgvector устанавливается контролируемо в БД Instance. В пилоте подтвердить
совместимость deployment-образа, нужные права и восстановление из backup.
Миграция не загружает embedding-модель из сети. Смена модели не смешивает
несовместимые векторы; предусматриваются новая версия индекса и backfill.

## 4. Внешние и межмодульные порты

| Порт | Ответственность и результат |
| --- | --- |
| SourceDefinitionPort | Прочитать и проверить определение; вернуть неизменяемый DefinitionSnapshot |
| PublicPageFetchPort | Получить ограниченный документ; вернуть FetchedPageDTO с метаданными |
| PublicationExtractionPort | Извлечь предложения; вернуть ExtractPublicationsResultDTO с issues |
| PublicationSearchPort | Найти ID и снимки кандидатов; вернуть SearchPublicationCandidatesResultDTO |
| CatalogMatchingSnapshotPort | Прочитать/повторно проверить локальный снимок и fingerprint, поддержать item-lock |
| CatalogUsagePort / контракт Catalog | Согласовать активные ссылки и удаление позиции без импорта Catalog ORM |
| EmbeddingPort | Получить версионированный вектор по ограниченному тексту |
| LlmMatchingPort | Оценить ограниченный набор кандидатов; вернуть EvaluatePublicationCandidatesResultDTO |
| TrackingDemandPort | Передать восстанавливаемый приоритет обновления публикации |
| Reference Data contracts | Проверить валюту, локаль и другие системные коды |
| Shared Jobs contracts | Планирование, маршрутизация, recovery и проверка lease |

DTO портов конкретны назначению, immutable на границах и не содержат ORM,
HTTP Request, Playwright Page или объектов клиента inference. Validation DSL
через JSON Schema/Pydantic и преобразование в snapshot остаются в адаптере;
Domain проверяет собственные инварианты.

Существующий Catalog product snapshot сначала проверяется на пригодность;
недостающий batch/matching-контракт добавляется публично в Catalog.
В текущем контракте нет обязательной бизнес-ревизии Catalog: актуальность
подтверждается content fingerprint и повторным чтением под item-lock.
Выдуманная revision не добавляется в consumer как будто она уже существует.

## 5. Матрица сценариев

Каждая строка ниже соответствует отдельному command/query, handler и DTO-файлу
при наличии результата. Сценарии не вызывают соседние handlers; общая
координация оформляется небольшими Application services.

| Владелец / сценарий | Вход | Результат |
| --- | --- | --- |
| source / validate_source_definition | JSON definition, ожидаемый dialect | ValidateSourceDefinitionResultDTO: hash, revision, issues |
| source / activate_source_definition | source ID, проверенный snapshot/hash, actor | ActivateSourceDefinitionResultDTO: source ID, активная revision |
| source / set_source_enabled | source ID, enabled, actor | None |
| crawl_run / start_crawl | source ID, область, вид discovery/refresh, dedupe key | StartCrawlResultDTO: run ID, состояние |
| crawl_run / prepare_crawl_step | run/job/token, now | PrepareCrawlStepResultDTO: закреплённая конфигурация и cursor |
| crawl_run / apply_crawl_step | run/job/token, ограниченный результат страницы | ApplyCrawlStepResultDTO: checkpoint, счётчики, продолжение |
| crawl_run / get_crawl_run | source/run ID, operator context | GetCrawlRunResultDTO: прогресс и безопасная ошибка |
| market_publication / request_publication_ingest | tenant/actor, URL, idempotency key | RequestPublicationIngestResultDTO: request ID, состояние |
| market_publication / get_publication_ingest_request | tenant, request ID | GetPublicationIngestRequestResultDTO: состояние, publication ID или reason |
| market_publication / update_publication_search_document | publication ID, matching fingerprint | None |
| market_publication / get_publication_history | publication ID, диапазон, cursor, limit | GetPublicationHistoryResultDTO |
| catalog_publication_link / match_catalog_item | tenant/item, job/token, fingerprints | MatchCatalogItemResultDTO: проверено, предложено, issues |
| catalog_publication_link / list_match_suggestions | tenant, item/filters/locale, pagination | ListMatchSuggestionsResultDTO |
| catalog_publication_link / confirm_publication_tracking | tenant/actor, link ID, expected_version | ConfirmPublicationTrackingResultDTO |
| catalog_publication_link / skip_publication_suggestion | tenant/actor, link ID, expected_version | None |
| catalog_publication_link / pause_publication_tracking | tenant/actor, link ID, expected_version | None |
| catalog_publication_link / resume_publication_tracking | tenant/actor, link ID, expected_version | None |
| catalog_publication_link / stop_publication_tracking | tenant/actor, link ID, expected_version | None |
| catalog_publication_link / list_tracked_publications | tenant, item/filters/locale, pagination | ListTrackedPublicationsResultDTO |
| catalog_publication_link / get_catalog_competitive_summary | tenant/item, locale, as_of | GetCatalogCompetitiveSummaryResultDTO |

Domain writes SellerAccount и MarketPublication координируются apply_crawl_step
через их repositories и доменные методы. Для каждой таблицы отдельный CRUD
handler/repository не создаётся. Prepared snapshots и результаты внешних портов
не являются разрешением применить данные без повторной проверки lease.

История публикации в Console доступна через проверенную tenant-связь;
внутренний query истории принимает global ID только после этой проверки.
Request receipt и его job/result нельзя читать по ID без проверки tenant.

## 6. HTTP и административный интерфейс

Предлагаемая база Console: /api/console/competitive-intelligence.
Tenant и actor поступают из доверенного Identity context. Предлагаемые права:
competitive_intelligence.read и competitive_intelligence.manage. Записывающие
методы используют существующую CSRF-защиту; tenant ID не задаётся в body.

| Метод и путь | Сценарий | Ответ |
| --- | --- | --- |
| GET /suggestions | list_match_suggestions | 200, отдельная list response |
| GET /tracked-publications | list_tracked_publications | 200, отдельная list response |
| POST /links/{link_id}/confirm | confirm_publication_tracking | 200, ConfirmPublicationTrackingResponse |
| POST /links/{link_id}/skip | skip_publication_suggestion | 204 |
| POST /links/{link_id}/pause | pause_publication_tracking | 204 |
| POST /links/{link_id}/resume | resume_publication_tracking | 204 |
| POST /links/{link_id}/stop | stop_publication_tracking | 204 |
| GET /links/{link_id}/history | get_publication_history после tenant lookup | 200, GetPublicationHistoryResponse |
| GET /catalog-items/{item_id}/summary | get_catalog_competitive_summary | 200, GetCatalogCompetitiveSummaryResponse |
| POST /publication-requests | request_publication_ingest | 202, RequestPublicationIngestResponse |
| GET /publication-requests/{request_id} | get_publication_ingest_request | 200, GetPublicationIngestRequestResponse |

Для confirm/skip/pause/resume/stop отдельные request schemas содержат
expected_version; это версия связи, а не несуществующая ревизия Catalog.
POST publication-requests принимает URL и Idempotency-Key в заголовке.
Одинаковый ключ с другим URL возвращает 409; повтор одинакового запроса
возвращает тот же receipt. Разные tenant receipts могут ссылаться на одно
дедуплицированное глобальное crawl-задание.

Пагинация списков: offset/limit с limit 1..100; история — cursor/limit 1..100.
Фильтры включают item, source, seller, relation type и freshness по назначению.
DTO/response передают деньги строками, timestamps в UTC, locale и as_of явно.

Ожидаемые статусы ошибок: 401/403 — доступ, 404 — нет ресурса в текущем tenant,
409 — устаревшее решение/недопустимый переход/idempotency conflict,
422 — неверный URL или значения запроса, 429 — лимит постановки URL.
Внешний сбой парсинга после 202 отражается в состоянии receipt; он не превращает
уже принятый запрос в задним числом неуспешный HTTP POST.

Управление definitions и запуском источников в MVP — отдельные management CLI
сценарии с системными полномочиями. Имена команд фиксируются на этапе 0.
Tenant manage не даёт права менять определения, читать raw или состояние
общих очередей. Новый API Control Plane для этого не вводится.

## 7. Jobs, процессы и транзакции

### 7.1. Изоляция ролей Shared Jobs

Предлагаемые job types:

| Роль | Типы |
| --- | --- |
| competitive-scraper | competitive.discovery, competitive.refresh |
| competitive-matcher | competitive.index_publication, competitive.match_item |
| Общий worker | Существующие типы без competitive.* |

Расширить claim-контракт и production worker allowlist маршрута/типов.
Фильтр применяется при SQL claim до limit, а не после захвата чужих заданий.
Heartbeat, recovery, retry и ограничение concurrency должны сохранять маршрут.
Инстансы одной роли могут конкурировать за свои задания; несовместимые роли
не создают друг другу ошибки handler not found. Регистрация recurring jobs
идемпотентна при нескольких replicas.

В текущем Shared Jobs tenant_id допускает null, но owns_current_lease требует
UUID tenant. Добавить согласованный глобальный вариант проверки: соответствие
job ID/token/route, running и unexpired lease с tenant_id IS NULL.
Для matcher сохраняются tenant admission и проверка tenant lease.

### 7.2. Применение страницы

1. В коротком global UoW проверить Source/CrawlRun/job, закрепить revision,
   scope и cursor; сформировать immutable snapshot.
2. Вне UoW получить документ и извлечь ограниченный batch предложений.
3. В новом global UoW повторно проверить enabled, run/revision, lease и fencing.
4. Через фабрики/методы обновить продавцов и публикации. Проверить observed_at
   и устойчивый ключ; не применить устаревший или повторный результат.
5. В одной транзакции сохранить observations, checkpoint, счётчики, необходимые
   jobs и Outbox. Commit выполняет внешняя сборка.

Если active revision изменилась, старый step не подменяет новый результат:
run отменяется или завершается как superseded, новый run начинает собственный
checkpoint. Пауза источника запрещает применение нового step после паузы.
Незавершённая страница не считается полностью пройденной.

### 7.3. Сопоставление

1. В tenant UoW под admission получить Catalog snapshot и fingerprint,
   сохранить/прочитать закрытую поисковую проекцию.
2. Прочитать ограниченные публичные snapshots кандидатов через query port.
3. Вне транзакции получить embeddings/LLM evaluation с тайм-аутом и бюджетом.
4. В новом tenant UoW повторно проверить admission/lease, существование item,
   fingerprint Catalog и смысловую версию кандидатов.
5. Сохранить оценку и новые suggested. Tracking/paused/skipped не перезаписать
   решением модели. Устаревший результат отбросить и ограниченно перепланировать.

Изменение публичной цены обновляет аналитику, но не инвалидирует смысловой
fingerprint. Public crawl job не обходит tenant-схемы. Изменения индекса
доставляются в matcher через Outbox/идемпотентные задачи, с ограниченной
диспетчеризацией по активным tenant; периодическая сверка восстанавливает
пропущенные работы. Это не полный декартов обход товаров и публикаций.

### 7.4. Решение пользователя и demand

Confirm проверяет актуальную позицию Catalog и её продаваемую роль, затем
под блокировкой связи применяет expected_version и доменный переход.
Вариативный контейнер не становится ссылкой на произвольный вариант.
Единый порядок блокировок согласуется с Catalog deletion: сначала Catalog
item-lock, затем link-lock. Skip/pause/resume/stop также защищают переход
и конкурентные решения. Повтор уже достигнутого намерения идемпотентен;
противоречащее состояние со старой версией даёт 409.

Изменение активного demand записывается вместе со связью через Outbox.
Глобальный приоритет обновления строится идемпотентным потребителем; периодическая
сверка исправляет drift, удаление tenant и прекращение последней подписки.
Расширение consumer/проекции не хранит содержимое Catalog в публичном индексе.
Ошибка общей проекции не откатывает уже подтверждённое решение пользователя;
интерфейс показывает последнее наблюдение и его реальную свежесть.

## 8. Frontend

~~~text
frontends/apps/console/src/modules/competitive-intelligence/
  api/                     HTTP functions, request/response DTO, mapper
  model/                   types, query keys, queries, mutations, page state
  pages/                   RecommendationsPage, TrackedPublicationsPage
  ui/                      comparison, recommendation, history, forms, states
  routes.ts
  index.ts                 небольшой публичный контракт
~~~

Страница собирает queries/mutations и взаимодействия. UI получает типизированные
props/emits и не импортирует API, router или query cache. Серверные данные
принадлежат TanStack Vue Query; фильтры и вкладка — page state/URL.

Ключи включают tenant, item/link, locale, фильтры, pagination и временной диапазон.
Read queries передают AbortSignal. Confirm/skip/pause/resume/stop имеют отдельные
mutations и обновляют затронутые suggestions/tracked/summary keys. Submit
блокируется на время запроса; оптимистическая запись без rollback не вводится.
При неоднозначном POST URL используется исходный Idempotency-Key.

Рекомендация показывает основания и различия, свежесть и тип соответствия.
Значения без достаточных данных обозначаются как неизвестные. Состояния:
loading, empty index, matching pending, no suggestions, error/retry,
background refetch, mutation pending и needs_review. Загруженные данные
сохраняются при фоновом обновлении.

Catalog использует публичный компонент/маршрут вкладки «Конкуренты» через
index.ts; глубокие импорты CI API/query keys в Catalog запрещены. Смена tenant
очищает выбор/черновики, отменяет запросы и игнорирует поздний ответ. Проверить
keyboard navigation, labels, existing semantic tokens и мобильный viewport.

## 9. План поставки

| Этап | Задачи | Условие завершения |
| --- | --- | --- |
| 0. Проверка выполнимости | Выборка страниц обеих площадок, identity, offers, цены/GTIN, discovery, доступность, лимиты; размеченные fixtures, DSL, budget/retention и inference benchmark | Для каждой площадки подтверждён рабочий путь обнаружения и извлечения; неподтверждённые поля названы явно |
| 1a. Контракты и jobs | Aggregate/VO, порты/DTO, маршруты очередей, global lease, схемы definitions и тесты ролей | Роли не захватывают чужие задания, global/tenant fencing подтверждён |
| 1b. Общий индекс | Global migrations, definitions Prom/Rozetka, discovery/refresh, observations, scheduler, метрики | Повторяемый ограниченный обход двух площадок без дублей; видны coverage и freshness |
| 2a. Tenant и Catalog | Tenant migration, batch/matching snapshot, fingerprints, usage/deletion, URL receipts | Связи и проекции изолированы; stale Catalog и удаление корректно обработаны |
| 2b. Matching | Text/vector retrieval, модель, rerank, evaluation, подавление skipped, reindex/backfill | Контрольная выборка достигает целевого precision; score не подменяет измерение |
| 3. API и Console | Конкретные transport schemas, рекомендации, tracking, история, summary, вкладка Catalog | Пройден сквозной пользовательский сценарий и проверки UI |
| 4. Выпуск | Images/Helm/Compose roles, ресурсы, health/readiness, retention, backup и runbook | Миграции и обновление на одноразовом окружении подтверждены, пилот имеет заданный бюджет |

Номер миграции, конкретные селекторы, модели и параметры производительности
не выбираются по историческим примерам. Результат этапа 0 дополняет эти два
документа до начала production-реализации соответствующей зависимости.

Порядок включения: применить global и tenant migrations; обновить все общие
workers с фильтрацией типов при выключенном competitive scheduler; развернуть
scraper/matcher и проверить health/readiness; затем активировать определения
и расписания пилота. Старый общий worker без фильтра не должен работать
одновременно с постановкой competitive.* заданий. При откате сначала остановить
новую постановку и обработку по согласованному drain/cancel-процессу; существующие
definitions и данные не удалять автоматически вместе с откатом приложения.

## 10. Проверки

### Domain и extraction

- Create/restore, identity и доменные переходы всех пяти агрегатов.
- Multi-seller карточка: продавец и цена из одной offer scope; AggregateOffer
  без seller price не становится предложением каждого продавца.
- Валидный/невалидный GTIN, ведущие нули, отсутствующие поля/локали, нулевая цена,
  условная акция, price from/range, разные упаковки, варианты и состояние.
- Неверный DSL/version, запрещённая операция, ограничение fallback/depth/body,
  неизвестный transform; HTML/JSON-LD fixtures каждой площадки.
- Fingerprints: перестановка JSON keys не даёт смыслового изменения;
  изменение только цены не перезапускает LLM, смена варианта запускает проверку.

### PostgreSQL и процессы

- Global и tenant migrations upgrade, повторная проверка metadata, безопасный
  downgrade в допустимых условиях; применяются к одноразовой БД.
- Два tenant с разными решениями по одной publication; отсутствие утечек через
  API, cache, jobs, receipt, embeddings и объяснения модели.
- Повтор delivery, heartbeat, истечение lease, takeover и старый worker перед
  commit; отдельная проверка global tenant_id=null.
- Смена definitions/source pause посреди fetch, отмена run, recovery cursor,
  out-of-order observations и повтор той же страницы.
- Отсутствие атомарного результата при сбое commit; Outbox не существует
  отдельно от своего изменения, consumer повторяется без дублей.
- Изменение/удаление Catalog во время inference, race confirm/delete и skip/LLM.
- Сквозной URL request, одинаковый ключ/другой URL, receipt isolation,
  retry без повторного глобального обхода и корректное завершение receipts.
- Прекращение последней подписки и удаление tenant восстанавливают demand,
  сохраняя общий индекс и другие tenant.
- Per-host quota между replicas, redirects, SSRF в HTTP и browser subrequests,
  Retry-After, CAPTCHA, timeout и потеря inference.
- EXPLAIN на representative fixtures для history, due jobs, lists и candidate
  search; bounded batch, лимиты, пагинация и отсутствие N+1.

### Качество и продукт

- Разделить tuning и контрольную выборки. Отдельно проверить Prom/Rozetka,
  варианты, аналоги, неизвестные признаки и hard negatives.
- Измерить корректность извлечения присутствующих обязательных полей (цель 95%)
  и precision показанных рекомендаций (цель 90%); также показать coverage/recall
  и количество заблокированных/неразобранных страниц.
- Проверить сравнение только свежих exact same_product предложений в одной
  валюте; нулевой знаменатель, unknown unit, условная цена и отсутствие own price.
- Отличать p95 age при доступном источнике от общей свежести; freshness failures
  не исчезают из отчёта из-за исключения source errors.

### Console и выпуск

- Проверить confirm/skip/pause/resume/stop, историю, URL request, needs_review,
  reload/URL filters, отмену запроса и смену tenant.
- Проверить loading/empty/error/retry/pending, keyboard и mobile viewport.
- Из frontends/: npm run lint:console, npm run typecheck:console,
  npm run build:console и применимые тесты сценариев.
- Для backend выполнить применимые unit/PostgreSQL/architecture tests,
  необходимые статические проверки и format-check.
- Проверить запуск/остановку отдельных workers, очереди, healthchecks,
  migration-before-startup, ресурсы браузера/inference и retention cleanup.

Операционные метрики: объём обнаруженных и разобранных публикаций, успешные
наблюдения/блокировки/issues по источнику, возраст данных, queue lag, retries,
lease loss, время и бюджет fetch/inference, semantic changes и precision
на размеченной выборке. Tenant ID не используется как неограниченная метка
метрик общего источника. Чувствительное содержимое не помещается в логи.

## 11. Проверка документации перед реализацией

- Относительные ссылки и JSON-пример валидны.
- PRD и этот план согласованы по scope, состояниям, ownership и критериям.
- Предлагаемые endpoints/CLI/модели обозначены как будущие.
- Не заявлены подтверждённые live-селекторы или качество, которых ещё нет.
- Известные зависимости Catalog, inference, Shared Jobs, deployment pgvector,
  source feasibility и retention включены в этапы.
- Перед завершением каждого этапа проверяется весь его diff по разделу 1;
  успешные функциональные тесты не заменяют архитектурную проверку.

Для изменения только этих Markdown-документов достаточно проверки ссылок,
JSON-примера, согласованности и diff. Сборка приложения и UI-тесты без изменений
приложения не требуются.
