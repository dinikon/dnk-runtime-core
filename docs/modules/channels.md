# Channels

Реализован backend-срез MVP: Channel с единственным Connection, проверка
подключения и первичная загрузка публикаций Prom/WooCommerce в локальную БД.
API доступен под `/api/console/channels`. Фоновые шаги выполняет существующий
shared jobs worker. Исходящая синхронизация по умолчанию выключена.

Console для настройки и read-сценариев реализована. Связывание с Catalog,
создание Draft и исходящие изменения — следующие срезы [плана Channels](../plan/channels-integrations.md). Catalog этот срез не меняет.
Прежний Channels удалён миграцией 0027; его контракты не используются новой реализацией.
Исторический срез Rozetka сохранён в [разделе 15 плана](../plan/channels-integrations.md#15-исторический-срез-rozetka-контракт-и-результаты).

## Границы и состояние

Channel — конкретный источник продаж, например отдельный магазин Prom.
Он является Aggregate Root, управляет названием, platform kind, разрешением
исходящей синхронизации, архивированием и lifecycle единственного Connection.
Connection — внутренняя Entity в `domain/channel/entity/connection.py`.
До настройки его может не быть; второй Connection запрещают Domain и SQL
`UNIQUE(channel_id)`, включая архивную строку. Самостоятельного ConnectionRepository нет.

Connection хранит endpoint, выбранные языки, валюту, защищённые credentials,
подтверждённую resource identity, техническую паузу и verification status:
`unverified / queued / verified / error`. Изменения проходят через Channel;
HTTP-команды существующего источника требуют revision Channel.

`is_enabled=false` запрещает исходящую синхронизацию. Verify и первичная загрузка
при этом разрешены и никогда не включают Channel автоматически. В этом срезе
нет исходящих capabilities или заданий, даже если разрешение явно включить.
Пауза Connection или архивирование Channel запрещают новые сетевые шаги.

Ротация credentials сначала сохраняет зашифрованного кандидата. Рабочие ключи
заменяются после проверки того же ресурса. Смена подтверждённого магазина/site
требует нового Channel; старые публикации и история сохраняются.

ExternalPublication и SyncRun — самостоятельные корни. Первый хранит observed
состояние карточки, второй — прогресс обхода. Ссылки между корнями передаются
по ID. Доменные IDs — EntityIdVO; DTO и SQL используют UUID на своих границах.
Правила реализации заданы [архитектурой backend](../architecture/backend.md).

## API

Пути в таблице относительны к `/api/console/channels`. Tenant/actor поступают
из Identity, в body их передавать нельзя. Чтение требует `channels.read`,
изменения — `channels.manage` и CSRF. Query-чтение не обращается к внешнему API.

| Метод и путь | Результат |
| --- | --- |
| `GET /platforms` | Manifest зарегистрированных Prom/WooCommerce, SDK/config versions, реализованные capabilities и secret schema |
| `GET /platforms/{kind}/config` | Конфигурационный контракт одной платформы |
| `POST /` | Новый Channel, revision, is_enabled=false; 201 |
| `GET /`, `GET /{channel_id}` | Локальный список и карточка Channel |
| `PATCH /{channel_id}` | revision и изменённые name/is_enabled |
| `POST /{channel_id}/archive` | Архивирование источника целиком; 204 |
| `POST /{channel_id}/connection` | Создание единственного подключения и постановка проверки; 201 |
| `GET /{channel_id}/connection` | Настройки, статус и признаки наличия credentials без ciphertext/секретов |
| `PATCH /{channel_id}/connection` | revision, полная замена settings и optional новые credentials; неприостановленное подключение получает новую проверку |
| `POST /{channel_id}/connection/verify` | revision → job_id, revision; 202 |
| `POST /{channel_id}/connection/pause` | revision → техническая пауза; 204 |
| `POST /{channel_id}/connection/resume` | revision → продолжение/проверка, без включения записи; 204 |
| `POST /connections/{connection_id}/initialization` | request_key UUID → run_id/status/job_id; 202 |
| `GET /connections/{connection_id}/initialization` | Последний прогресс либо not_started, read_complete и recovery_required |
| `GET /connections/{connection_id}/publications` | Core-строки, total, search/stock_status, offset/limit до 100 |
| `GET /publications/{publication_id}` | Core и schema-versioned extensions одной публикации |

В OpenAPI пути коллекции указаны без завершающего `/`.
Каждый сценарий имеет отдельные Command/Query, Handler, DTO и HTTP-контракты;
операции 204 возвращают None без пустых DTO/Response. Валидационные ответы
Channels исключают исходные input и exception ctx, содержащие credentials.

Пример создания Channel:

```json
{"name": "Основной WooCommerce", "platform_kind": "woocommerce"}
```

Следующий запрос `POST /{channel_id}/connection`:

```json
{
  "revision": 1,
  "settings": {
    "endpoint": "https://shop.example",
    "locales": ["uk", "ru"],
    "currency": "UAH"
  },
  "credentials": {
    "consumer_key": "<consumer key>",
    "consumer_secret": "<consumer secret>"
  }
}
```

Prom использует endpoint `https://my.prom.ua` и credentials с полем `token`.
Если `/products/list` возвращает `group_id=0`, проверка получает до 100 групп
через `/groups/list` и закрепляет ID единственной группы с явным
`parent_group_id=null`. Ноль не используется как общая identity магазинов.
Отсутствующий или неоднозначный корень в этой странице приводит к
`resource_identity_unavailable`; ID товаров остаются строго положительными.
WooCommerce читает публичный `/wp-json/` без credentials для проверки адреса
сайта. Ключи передаются через Basic header только в `/wp-json/wc/v3/*`;
доступность публичного корня не заменяет проверку прав на чтение товаров.
Коды locale/currency проверяются через публичные контракты reference_data. Settings
задаются явно: нет подстановки валюты/языка из tenant или автоперевода.
У paused Connection настройки можно исправить локально; проверка кандидата
произойдёт после resume. Секреты не возвращаются API и не попадают в job payload.

## Console

Раздел `/channels` показывает каналы с пагинацией и состоянием единственного
подключения. Создание состоит из двух шагов: название/платформа, затем настройки
Connection. Если второй шаг прерван, канал остаётся доступен для настройки.
Страница `/channels/:channelId` содержит вкладки «Публикации» и «Подключение».

Manifest обоих read-сценариев (`platforms` и `platforms/{kind}/config`) содержит
`endpoint_schema`: JSON Schema для string/uri с title, description, maxLength и
optional default/const. Prom объявляет фиксированный `https://my.prom.ua`, Woo —
ввод HTTPS-адреса магазина. Credentials schema поддерживает string-поля,
required, minLength/maxLength и writeOnly. Console не ветвится по platform kind;
неподдержанная версия/структура формы показывается недоступной. Семантическая
валидация и ограничения безопасности остаются на backend.

Сохранение Connection запускает проверку автоматически, затем backend запускает
инициализацию. UI показывает processed/invalid, время обновления, ограничения
охвата и recovery_required. Процент не вычисляется без total источника. Завершённый
partial/read_complete и прерванный partial имеют разные сообщения. На активной
странице проверка/прогресс опрашиваются раз в 2 секунды, публикации — раз в 3;
опрос прекращается после завершения, паузы, ошибки чтения или ухода со страницы.

Список публикаций читает локальную БД, поддерживает поиск, stock_status и
пагинацию; вкладка/фильтры/страница находятся в URL. Уже загруженные строки
сохраняются при refetch/error. Decimal остаётся строкой, отображение раскрывает
экспоненту и убирает незначащие нули без floating point. Неизвестные поля не
заменяются нулями. Ключи и пароли не возвращаются в форму и не сохраняются в
web storage; замена явная, после успеха секретный ввод очищается.

Frontend-модуль — `frontends/apps/console/src/modules/channels`: отдельные DTO,
mapper, API, query keys, queries, mutations, URL state, страницы-оркестраторы и
UI через props/emits. Query keys включают tenant/session. Смена контекста очищает
формы, отменяет запросы и не допускает применения позднего результата. Черновик
не перезаписывается фоновыми запросами; конфликт revision сохраняет ввод.
Права проверяет backend, 403 отображается явно. В текущем Identity нет публичного
каталога capabilities пользователя: роль admin не используется как выдуманный
заменитель channels.manage.

Новые Console-сценарии не включают outbound, не меняют Catalog и не предлагают
связывание/Create Draft до реализации этих use cases. Техническая пауза/продолжение
подключения не меняет разрешение исходящей синхронизации.

## Проверка и фоновая загрузка

1. CreateConnection сохраняет агрегат и `channels.verify_connection` в общей транзакции.
2. Worker проверяет tenant admission и lease, читает immutable вход и закрывает UoW.
3. Плагин выполняет GET через scoped credentials/HTTP фасады без SQL session.
4. Новый UoW повторно проверяет generation. Verified-состояние, initialization run
   и первое `channels.initialize_publications` задание сохраняются атомарно.
5. Каждая порция проходит prepare → HTTP → apply. Публикации, checkpoint,
   счётчики и следующее задание фиксируются вместе. При завершении Domain
   проверяет read_complete перед терминальным переходом.
6. Перед commit worker повторно проверяет действующую lease под блокировкой.
   Ошибка commit или потеря lease откатывает весь apply, включая продолжение.

Во время HTTP удерживается tenant admission, но нет открытой SQL-транзакции.
Плагин не управляет jobs, агрегатами, Catalog, ORM, commit или rollback.
Все новые публичные HTTPS адреса проверяются по DNS и закреплённому IP;
локальные/служебные адреса и redirects запрещены. GET ограничен временем и размером.

Run statuses: `queued / running / succeeded / partial / failed / cancelled`.
`read_complete=true` означает завершение обхода согласованного API scope.
`partial + read_complete=true` сообщает о постоянном ограничении охвата/неполных
строках; `partial + read_complete=false` — о прерванном обходе с сохранёнными данными.
Total источника не выдумывается; processed считает уникальные публикации данного run.

Повтор страницы не увеличивает счётчики. Сетевые transient ошибки имеют ограниченный
retry. После сбоя новый request_key продолжает checkpoint той же generation.
После полного обхода или смены generation создаётся новый run с чтением с начала;
внутренние publication IDs сохраняются. Исчезновение из неполного обхода не удаляет
карточку и не обнуляет её остаток. Повтор прежнего request_key не ставит новое задание.

Если shared job исчерпал собственные попытки/удалён, read-side показывает
recovery_required. Явный initialization с новым request_key восстанавливает процесс,
а не оставляет его навсегда queued/running.

## Core и плагины

Хранение: `channels`, `channel_connections`, `channel_sync_runs`,
`channel_external_publications`. Новая forward-миграция —
[0028_channels_core](../../migrations/tenant/versions/0028_channels_core.py), после 0027.
У публикации UNIQUE(connection_id, resource_type, external_id); внешний SKU не уникален.

Core SQL-поля: external_id/SKU, price/sale_price/currency, quantity/stock_status,
title/title_locale, main_image_url, source_updated_at, first_seen_at/last_seen_at,
last_import_run_id, observed_revision, core_version и warnings. Цена/количество
передаются Decimal-строками без округления. 0 и null различаются. Невалидное
optional поле превращается в null с предупреждением; невалидный native ID
учитывается в неполноте run. Дополнительные поля проходят версионные Pydantic
read-схемы провайдера и сохраняются в extensions; произвольные meta_data не копируются.

Единственная точка подключения provider factories —
`presentation/depends/plugin_registry.py`. Application SDK содержит capabilities
VerifyConnectionPlugin и ReadPublicationPagePlugin; реализации находятся в
`infrastructure/plugin/prom/` и `woocommerce/`. Общие handlers не ветвятся по kind.

WooCommerce читает административный REST products и отдельные variation-потоки.
Identity подтверждается каноническим site URL. Валюта и основная locale являются
явной конфигурацией ресурса; их нельзя считать автоматически обнаруженными.
Требование multilingual adapter относится к будущему outbound-срезу.

Prom подтверждает root group авторизованным products/list, обходит страницы
списка групп и затем products/list каждой группы. Native id не подменяется
provider external_id для XML-импорта. Остаток из `quantity_in_stock` сохраняется
в core `quantity` как Decimal, включая ноль. Отсутствующее или пустое количество
остаётся null с `quantity_not_exposed`; невалидное — null с `invalid_quantity`.
Количество не вычисляется из `presence`, `in_stock` или минимального заказа.
Sale price не вычисляется по неоднозначным discount/date полям;
discount сохраняется отдельно с предупреждением.

Оба плагина явно объявляют ограничение `api_visible_statuses_only`: официальный
read-контракт не доказывает охват недоступных/удалённых статусов. Завершённый
обход поэтому сохраняет partial/read_complete=true с указанным scope, не обещая
полную копию всех состояний кабинета. Проверка на реальном кабинете остаётся
отдельной приёмкой; fixtures не заменяют её.

Источники wire-контрактов: [WooCommerce REST API](https://developer.woocommerce.com/docs/apis/rest-api/v3/products),
[Prom Swagger](https://prom.ua/cloud-cgi/static/uaprom-static/docs/swagger/index.html).

## Запуск и проверки

Deployment должен предоставить Fernet key через
`CHANNELS__CREDENTIALS_ENCRYPTION_KEY` либо mounted file
`CHANNELS__CREDENTIALS_ENCRYPTION_KEY_PATH`. Ключ сохраняется между перезапусками;
отсутствие настройки даёт явный отказ сохранения credentials, а не plaintext fallback.
HTTP-пределы: `CHANNELS__HTTP_TIMEOUT_SECONDS`, `CHANNELS__MAX_RESPONSE_BYTES`.

Перед использованием API tenant-схемы обновляются обычным
`dnk-manage tenant-migrations upgrade`; production фоновые шаги исполняет
`dnk-manage jobs worker`. Рабочая БД не изменяется при импорте модуля.

Тесты: `test/test_channels.py`, `test/test_channels_manifest.py`,
`test/test_channels_architecture.py`,
`test/test_channels_postgres.py`. PostgreSQL-тесты требуют TEST_POSTGRES_URL
одноразовой БД. Они проверяют реальный HTTP/CSRF/UoW, оба read plugins,
пагинацию/вариации/группы, повторы, lease, commit failure, identity collision,
ротацию ключей, recovery, Catalog isolation и миграционный roundtrip/drift.


Проверки Console: scripts `lint:console`, `typecheck:console`, `build:console`
из `frontends/`, `test:channels` из workspace `@dnk/console`. Браузерная приёмка
выполняется на изолированном API/PostgreSQL с настоящими HTTP/CSRF/UoW/jobs и
fixture-ответами внешних API: Prom/Woo, ошибки, повтор, конфликт revision,
сохранность черновика, pause/resume, URL/reload, session reset и mobile viewport.
Это не заменяет приёмку с реальными кабинетами.
