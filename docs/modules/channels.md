# Channels

Реализован backend-срез MVP: Channel с единственным Connection, проверка
подключения и первичная загрузка публикаций Prom/WooCommerce в локальную БД.
API доступен под `/api/console/channels`. Фоновые шаги выполняет существующий
shared jobs worker. Исходящая синхронизация по умолчанию выключена.

Console, связывание/снятие связи и атомарное создание Catalog Draft реализованы.
Полное чтение карточки, локализованные title/body, собственная галерея и новый
экран предпросмотра используют подготовку импорта и миграцию 0030.
Ручное обновление title/body существующих товаров Woo реализовано миграцией 0031
(текущий SDK 5/config 3); для Prom доступны сравнение и явная блокировка XML-отправки
до подтверждения update-only контракта. См. [план Channels](../plan/channels-integrations.md).
Связывание сохраняет существующий Catalog без изменений; явное создание Draft
однократно переносит подтверждённые пользователем значения в новый товар.
Прежний Channels удалён миграцией 0027; его контракты не используются новой реализацией.
Исторический срез Rozetka сохранён в [разделе 15 плана](../plan/channels-integrations.md#15-исторический-срез-rozetka-контракт-и-результаты).

## Границы и состояние

Channel — конкретный источник продаж, например отдельный магазин Prom.
Он является Aggregate Root, управляет названием, platform kind, разрешением
исходящей синхронизации, архивированием и lifecycle единственного Connection.
Connection — внутренняя Entity в `domain/channel/entity/connection.py`.
До настройки его может не быть; второй Connection запрещают Domain и SQL
`UNIQUE(channel_id)`, включая архивную строку. Самостоятельного ConnectionRepository нет.

Connection хранит endpoint, расширяемый JSONB-объект settings, защищённые credentials,
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
| `GET /publications/{publication_id}` | Типизированная проекция снимка одной публикации, без приватных metadata |

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
  "endpoint": "https://shop.example",
  "settings": {
    "locales": ["uk"],
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

SDK version 3 / config version 3 передают `settings_schema` вместо `settings_policy`.
В SQL `channel_connections.settings` хранится объект значений; JSON Schema принадлежит
manifest плагина. Endpoint остаётся отдельным полем, credentials хранятся отдельно
в зашифрованном виде. Create/update HTTP принимают `revision`, `endpoint`, `settings`
и credentials; обновление заменяет settings целиком, старый формат тела не принимается.
GetConnection возвращает `endpoint` и `settings` без отдельных locales/currency.

Схема задаёт типы, required/default/const, enum, объекты, массивы и ссылки на
справочники (`x-reference: locale/currency`). Console строит поля по схеме без
ветвлений по платформе и отклоняет неподдерживаемую структуру. Неизвестные свойства
отклоняются backend-плагином, а используемые коды проверяются через reference_data.
Новые поля плагина не требуют SQL-миграции или изменения общего Connection DTO.

Prom объявляет основной `ru`, необязательный `uk`, фиксированную `UAH`; WooCommerce —
один выбираемый язык и валюту. Основной язык находится первым в массиве locales.
Дополнительный язык сам по себе не добавляет второй поток чтения: текущий reader
использует основной язык. Prom передаёт его явно через `X-LANGUAGE`.
Defaults являются частью схемы плагина; значения tenant и автоперевод не подставляются.

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

Console поддерживает связывание, снятие связи, создание Draft и ручное обновление
текстов Woo. Сопоставление категорий/характеристик и безопасная XML-отправка Prom
остаются следующими срезами.
Техническая пауза/продолжение подключения не меняет разрешение исходящей синхронизации.

## Связи с Catalog и создание Draft

Новый локальный срез использует `ProductRepresentation` как корень Channels и
`ExternalBinding` как внутреннюю Entity. Пара `(connection_id, catalog_item_id)`
уникальна; у представления одна основная активная публикация, у публикации одна
активная связь. Снятые связи сохраняются. Переводные группы и семейства вариантов
этот срез не собирает: перенос одной публикации создаёт самостоятельный простой Draft.

Миграция `0029_channels_catalog_bindings` переносит locales/currency в settings JSONB,
удаляет publication.core_version и добавляет
`channel_product_representations`, `channel_external_bindings` и
`channel_catalog_creation_requests`. В Catalog нет внешних FK и прямых Channels
SQL joins. Публичные фасады доступны ядру Channels, не runtime платформенных плагинов.

Дополнительные пути относительно `/api/console/channels`:

| Метод и путь | Назначение |
| --- | --- |
| GET /publications/{id}/catalog-candidates | locale, search, offset/limit; товары Catalog, доступность выбора и revision представления |
| POST /publications/{id}/binding | catalog_item_id и expected_revision существующей пары; 201 с binding/representation IDs и revision |
| DELETE /publications/{id}/binding | binding_id и expected_revision; 204, товар и публикация сохраняются |
| GET /publications/{id}/catalog-draft-preview | locale и expected_observed_revision; предложение полей, origins и issues без записи товара |
| POST /publications/{id}/catalog-item | request_key, expected_observed_revision и подтверждённые values; 201 с Catalog/representation/binding IDs |

Все операции требуют Channels manage и Catalog read; preview/create дополнительно
Catalog create. Tenant/actor берутся только из Identity. Новые связи запрещены для
архивного Channel или архивного товара. is_enabled=false не запрещает явный импорт в Catalog. Пауза Connection не
запрещает локальное связывание/снятие связи и прежний минимальный create. Полная
подготовка требует активного проверенного подключения; изменение его generation
после preview требует новой подготовки. Снятие связи разрешено и у архивного канала.

Существующий товар при bind не изменяется. Создание из Console получает полную
карточку через `read_publication_details`, а не собирает товар из native extensions.
Локали берутся из проверенной конфигурации плагина; до двух title/body и вся
доступная галерея входят в явный preview. SKU, цены и наличие также берутся из
полного чтения. Никакие переводы не генерируются автоматически. Пустое описание
видно в редакторе; ошибка чтения не превращается в пустое поле.
Категории, характеристики и metadata пока не копируются. Draft/Default/virtual=false
назначает сервер. Старый минимальный HTTP preview/create остаётся совместимым
для вызовов без нового содержимого; Console использует только полный сценарий.
Передача body/gallery через create без подготовки отклоняется.

Catalog владеет валидацией SKU, переводов, валюты, цены и stock specification.
Цена имеет до 6 дробных разрядов; незначащие нули удаляются без округления. Дробное
количество не округляется, unknown не заменяется in_stock. Пользователь исправляет
количество либо выбирает ручной статус. Catalog вычисляет итоговое наличие из
количества и backorders либо использует выбранный ручной статус. Отличие от
наблюдаемого не блокирует создание; поля stock_confirmed в форме и API нет.

Create использует единственный внешний tenant UoW. Транзакционная блокировка
request_key резервирует intent; завершённый receipt читается раньше текущей
observed_revision и binding. Intent включает actor; такой же key/вход текущего
пользователя возвращает прежние IDs, другой пользователь или вход
даёт конфликт. Затем блокируются Channel SHARE и публикация FOR UPDATE,
проверяется snapshot, вызывается единый `CreateCatalogItem` Catalog, сохраняются
представление/связь/receipt. Внешний commit фиксирует всё вместе. При любой ошибке
не остаётся ни пустого товара, ни orphan Draft. Чтение внешней карточки и скачивание
изображений выполняются раньше; в финальной транзакции Files подтверждает готовность
и доступность уже подготовленных файлов.

Bind/unbind сначала захватывают публичную Catalog item-блокировку, затем source
и representation locks. Delete Catalog под той же item-блокировкой вызывает
публичный `GetCatalogUsage` Channels: активная связь, включая архивный канал,
запрещает удаление. После явного unbind товар можно удалить; история остаётся.

Локальный список публикаций одним SQL добавляет catalog_item_id, binding_id,
representation_id/revision и фильтр binding_status=bound|unbound. Console показывает
связь, выбор существующего товара, preview Draft и подтверждение снятия. Фильтр
сохраняется в URL; DTO/mapper/query/mutation/form state разделены. Для перехода
и invalidation используется небольшой публичный frontend-контракт Catalog.

Черновик формы не стирается при refetch. Новый экран сохраняет значения, выбранный
порядок/главное фото и точный незавершённый create intent в sessionStorage,
разделённом по tenant/actor/preparation. Истечение подготовки запрещает новый create,
но завершённый receipt проверяется раньше версии/срока и возвращает прежний результат.
При неопределённом ответе ввод блокируется; повтор после reload использует те же
request_key, тексты и состав галереи. Никакая операция не включает синхронизацию.

## Полная карточка и подготовка импорта: 0030

`PublicationImportPreparation` — самостоятельный Aggregate Root Channels.
Таблица `channel_publication_import_preparations` хранит publication/actor IDs,
generation Connection, observed_revision, status/revision/sequence, immutable
снимок в JSONB, результаты фотографий, принятые товаром image IDs и срок пригодности
предпросмотра (24 часа). Снимок содержит schema_version=1, время чтения,
локализованный контент, упорядоченную галерею и только переносимые коммерческие значения.
SQL-модели Catalog и Files в persistence Channels не импортируются.

Пути ниже относительны к `/api/console/channels`. Все требуют Channels manage,
Catalog read/create и текущего владельца подготовки; мутации также требуют CSRF.

| Метод | Контракт |
| --- | --- |
| POST /publications/{id}/import-preparations | preparation_id UUID как ключ повторного запуска + expected_observed_revision; 202 |
| GET /import-preparations/{id} | Локальный прогресс, read_at, значения, тексты и результаты фотографий |
| POST /import-preparations/{id}/retry | expected_revision; повтор только неготовых частей |
| POST /import-preparations/{id}/cancel | expected_revision; отмена и durable очистка временных файлов |
| GET /import-preparations/{id}/image?image_id=... | Приватный закрываемый Files stream; произвольный file_id не принимается |
| POST /publications/{id}/catalog-item | Дополнительно preparation_id/expected_preparation_revision и values.descriptions/gallery/primary_image_id |

`channels.prepare_publication_import` делает один bounded шаг: полное чтение
карточки либо перенос одной фотографии. Prepare и apply имеют короткие UoW;
внешний HTTP выполняется между ними. Apply заново проверяет source/settings/sequence
и worker lease; запись Files и результата фотографии использует общий UoW.
Физический объект, оставшийся при rollback регистрации, обрабатывает обычная
очистка orphan objects Files. Готовый файл записывается в снимок один раз.
Дубликат job не заменяет снимок и не загружает уже принятое фото.

Статусы: queued → reading → images → ready; ошибка чтения — error. Ready может
содержать явные ошибки отдельных фото: создание с ними блокируется, пока пользователь
не повторит загрузку или не исключит фото. Успешный create переводит подготовку в
consumed в одной транзакции с Catalog, binding и receipt. Отмена — cancelled;
истечение — expired. Отсутствующий/terminal worker job отображается как восстановимый
error без записи из GET; retry создаёт новую sequence, сохраняя готовые файлы.

`channels.cleanup_publication_import` освобождает временные файлы отменённых,
истёкших и использованных подготовок. Принятые товаром фото сохраняются; для остальных
через публичный Catalog query проверяется использование. Готовые файлы блокируются
публичной командой Files; прикрепление в Catalog использует ту же блокировку.
Очистка не удаляет фото, которое успели использовать в другом товаре.

Prom читает `/api/v1/products/{id}` один раз, затем извлекает настроенные ru/uk из
`name_multilang[locale]` и `description_multilang[locale]`. Заголовок `X-LANGUAGE`
задаёт локаль ответа API и не гарантирует переключение scalar `name`/`description`.
Если multilang отсутствует, scalar допускается только для основного ru; пустой
или отсутствующий перевод uk остаётся пустым, русский текст в uk не копируется.
Явные пустые/null значения multilang не заменяются scalar полем.
Для вариации Prom с пустым описанием запрашивается её `variation_base_id`:
ID и `variation_group_id` основной карточки должны совпасть с указателями вариации,
дальнейшая цепочка вариаций запрещена. Только пустое описание наследуется из того же
языка основной карточки с `description_inherited_from_parent`; собственные описания,
названия, цены, остатки и фотографии вариации сохраняются. Связь определена в
[Product API](https://public-api.docs.prom.ua/documentation/Products/schemas/Product.yaml).
Контракт: [названия](https://public-api.docs.prom.ua/documentation/common/schemas/ProductNameMultilang.yaml)
и [описания](https://public-api.docs.prom.ua/documentation/common/schemas/ProductDescriptionMultilang.yaml).
Галерея использует main_image и images, удаляет дубли URL. Для HTTPS CDN
`images.prom.ua` ссылки вида `/{id}_w200_h200_{name}` преобразуются в
`/{id}_{name}` до удаления дублей: REST отдаёт уменьшенные изображения, а CDN
без суффикса размера возвращает доступный исходный файл. Это проверенное поведение
CDN, отдельного поля оригинала в [Image API](https://public-api.docs.prom.ua/documentation/Products/schemas/Image.yaml)
нет. Чужие домены, неизвестные форматы URL и ссылки с query не переписываются.
При недоступности исходного файла возникает ошибка фотографии; уменьшенная копия
не подставляется незаметно. Уже подготовленные снимки неизменяемы: для них нужна
новая подготовка карточки. Выбор языков проверен
contract fixtures и GET подключённого магазина: scalar поля одинаковы, multilang
содержит разные ru/uk тексты. Woo читает штатный product либо variation endpoint на одной
локали; отсутствующие title/body/images вариации наследуются от родителя с явными
предупреждениями. Поддержка внешнего multilingual-плагина Woo — отдельный срез.
Сетевой downloader не передаёт API credentials/cookies, допускает публичный HTTPS,
закрепляет проверенный IP/TLS SNI, запрещает redirects, ограничивает размер 10 MiB.
`Accept: */*` не запрашивает перекодированную WebP-версию даже без суффикса размера.
CDN Prom может отдавать исходный WebP под расширением `.jpg` и MIME `image/jpeg`:
фактический MIME определяется по сигнатуре PNG/JPEG/WebP/GIF/AVIF/BMP общей
инфраструктурной функцией, а не по HTTP-заголовку или расширению,
байты при этом не меняются. Неизвестная сигнатура отклоняется до сохранения.
Эти же форматы поддерживает ручная загрузка Catalog; галерея ограничена
100 изображениями, как в Catalog. Байты изображения сохраняются и выдаются без
resize или перекодирования; размер в UI задаёт только отображение. Доступный исходник
Prom может уже отличаться от загруженного продавцом файла из-за обработки на стороне
площадки. Превышение ограничений даёт явную ошибку без усечения. Описания очищаются общей
sanitization редактора до preview и повторно проверяются владельцем Catalog.

Console открывает отдельный маршрут `channels/:channelId/publications/:publicationId/import/:preparationId`.
Локаль сохраняется в URL; rich text editor предоставлен публичным контрактом Catalog.
UI позволяет править тексты, менять порядок/главное фото, исключать фотографии,
исправлять SKU/цены/наличие. Page связывает queries/mutations и props/emits UI;
refetch и повтор загрузки фотографий не стирают введённые значения.

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

После [0032_publication_payload_meta](../../migrations/tenant/versions/0032_publication_payload_meta.py)
SQL хранит identity (`id`, `connection_id`, `resource_type`, `external_id`),
`payload`, `meta`, `source_updated_at`, `fingerprint`, `observed_revision`,
`first_seen_at`, `last_seen_at`, `last_import_run_id`. UUID и связи не меняются.

`payload` версии 1 содержит `sku`, `titles`, `display_locale`,
`pricing` (`regular`, `sale`, `currency`, `promotion`), `stock` (`quantity`, `status`),
`main_image` (`url`). Деньги и количество — Decimal-строки, без округления;
ноль и null различаются. Период имеет `starts_at`, `ends_at`, `timezone`, `precision`:
Prom сохраняет календарные даты Europe/Kyiv, Woo — GMT-моменты UTC.
Невалидный optional параметр становится null с диагностикой.

`meta` версии 1 содержит `provider_schema`, приватный `provider`, `read_issues`.
Провайдерские данные проходят схему Pydantic в плагине. Prom использует
`prom.read.v2` и `provider.import_key` для внешнего ключа XML; нативный ID по-прежнему
находится в `publication.external_id`. Woo использует `woocommerce.read.v2`;
`parent_id` сохраняется для чтения вариаций. Исторические описания, скидки и
границы акций сохраняются; произвольные ответы API и credentials не копируются.

Плагины возвращают типизированные payload/meta (SDK 5/config 3).
Временная `core`-проекция нужна для действующих сценариев details/Draft, отдельного
хранения core нет. HTTP списка/detail оставляет прежние отображаемые поля и
не выдаёт provider JSON (`extensions`/`extension_version` удалены из detail).
Список выбирает только payload и read issues, не читая большие provider-описания;
поиск/фильтры/пагинация выполняются в SQL. Индексы `(connection_id, payload.sku)`
и `(connection_id, payload.stock.status)` используют фиксированные JSON-пути.
Полный текст и галерея для Draft продолжают читаться отдельным плагинным сценарием.

### Диагностика ключей обмена

Optional manifest capability `publication_identity_diagnostics` задаёт политику
`PublicationIdentityPolicyDTO`: JSON-путь ключа и инструкцию, принадлежащие плагину.
Prom использует `meta.provider.import_key`; Woo возвращает `not_required` без сводки.
Политика не передаётся в публичный manifest: пути private JSON остаются на сервере.

`GET /connections/{id}/publications` принимает `identity_status`
(`missing / duplicate / valid / not_required`) и точный `identity_key`.
Строка list/detail содержит `identity: {state, key, conflict_count}`.
Список содержит `identity_summary`: label, total, missing, duplicate, valid,
duplicate_groups, assessment, checked_at, scope_limitations и help_* / recovery_verified.
Сводка общая для Connection, независимо от поиска, связи и страницы списка.

Оконная SQL-проекция определяет коллизии по всем известным публикациям Connection
**до** фильтров/пагинации. Null, пустой и пробельный ключ — missing; прочие строки
сравниваются точно, включая регистр и ведущие нули. `valid` не означает разрешение
экспорта. Диагностика не хранится, не меняет meta/read_issues, ревизии и Catalog.
Для этого среза не нужны миграции и уникальные ограничения на import key.

`assessment`: not_started, in_progress, current, stale, incomplete. Завершённый
обход с ограниченным API scope относится к известным публикациям; прерванное
чтение, invalid-строки и устаревшая generation не доказывают отсутствие дублей.
Console показывает общие счётчики, фильтр/URL, точный ключ с копированием,
переход к группе дублей, полноту загрузки и инструкцию исправления.
Отсутствие ключа не блокирует связывание и создание Draft.

На реальной карточке проверено назначение отсутствующего ключа через собственный
XLSX-экспорт Prom. Импорт может опубликовать скрытый товар; инструкция требует
проверить и восстановить видимость. Массовое исправление и дубли требуют отдельной
проверки одной карточки. [Протокол XLSX](../experiments/prom-xlsx/2026-10-20/README.md).

Единственная точка подключения provider factories —
`presentation/depends/plugin_registry.py`. Application SDK содержит capabilities
VerifyConnectionPlugin и ReadPublicationPagePlugin; реализации находятся в
`infrastructure/plugin/prom/` и `woocommerce/`. Общие handlers не ветвятся по kind.

WooCommerce читает административный REST products и отдельные variation-потоки.
Identity подтверждается каноническим site URL. Валюта и основная locale являются
явной конфигурацией ресурса; их нельзя считать автоматически обнаруженными.
Текущая исходящая запись Woo ограничена одной настроенной locale и ресурсом product.
Две locale требуют отдельного multilingual adapter; вариации нельзя обновлять
путём неявного изменения имени родителя.

Prom подтверждает root group авторизованным products/list, обходит страницы
списка групп и затем products/list каждой группы. Native id не подменяется
provider external_id для XML-импорта. Остаток из `quantity_in_stock` сохраняется
в core `quantity` как Decimal, включая ноль. Отсутствующее или пустое количество
остаётся null с `quantity_not_exposed`; невалидное — null с `invalid_quantity`.
Количество не вычисляется из `presence`, `in_stock` или минимального заказа.
Акционная цена Prom вычисляется из REST `price` и отдельного `discount`:
для `amount` — `price - value`, для `percent` — `price * (1 - value / 100)`.
Расчёт использует Decimal без округления; исходная цена остаётся в `price`.
`date_start` и `date_end` принимаются строго в формате `ДД.ММ.ГГГГ`, обе границы
включены. Датой наблюдения считается календарный день Europe/Kyiv; один read-шаг
использует один instant из ClockPort, в том числе при смене UTC offset.
Схема API не задаёт часовой пояс, поэтому Europe/Kyiv — явная политика коннектора
Prom.ua. Будущая, завершённая, отсутствующая или нулевая скидка даёт null.
Некорректные/отсутствующие даты, обратный период, неизвестный тип, отрицательное
значение, процент выше 100, сумма выше цены, отсутствующая базовая цена или
результат вне точности core дают null с `invalid_sale_price`. Нулевая итоговая
цена при скидке 100%/на полную сумму сохраняется как 0. Исходный `discount`
сохраняется в extension и при неактивной акции. Срок оценивается при чтении;
следующая загрузка пересчитывает и очищает истёкшую/удалённую акцию в snapshot.

REST-контракт подтверждён схемами
[Product](https://public-api.docs.prom.ua/documentation/Products/schemas/Product.yaml),
[Discount](https://public-api.docs.prom.ua/documentation/Products/schemas/Discount.yaml)
и [PostProductRequestBody](https://public-api.docs.prom.ua/documentation/Products/schemas/PostProductRequestBody.yaml)
(только чтение документации, никаких запросов редактирования).
Значение `price` до скидки дополнительно сверено 18.10.2026 на публичных карточках
Biovit: [899 − 70 = 829 UAH](https://prom.ua/p1336377549-hlorofill-myatnyj-vkus.html)
и [830 − 10% = 747 UAH](https://prom.ua/p2864192346-lipostik-fit-sht.html).
Это REST-профиль; семантика `price`/`oldprice` из XML/YML к нему не применяется.

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
`test/test_channels_architecture.py`, `test/test_channels_payload.py`,
`test/test_channels_postgres.py`, `test/test_channels_payload_postgres.py`,
`test/test_channels_identity_postgres.py`. PostgreSQL-тесты требуют TEST_POSTGRES_URL
одноразовой БД. Они проверяют реальный HTTP/CSRF/UoW, оба read plugins,
пагинацию/вариации/группы, повторы, lease, commit failure, identity collision,
ротацию ключей, recovery, Catalog isolation и миграционный roundtrip/drift.


Проверки Console: scripts `lint:console`, `typecheck:console`, `build:console`
из `frontends/`, `test:channels` из workspace `@dnk/console`. Браузерная приёмка
выполняется на изолированном API/PostgreSQL с настоящими HTTP/CSRF/UoW/jobs и
fixture-ответами внешних API: Prom/Woo, ошибки, повтор, конфликт revision,
сохранность черновика, pause/resume, URL/reload, session reset и mobile viewport.
Это не заменяет приёмку с реальными кабинетами.

Проверки связей: `test/test_channels_bindings.py`,
`test/test_channels_bindings_postgres.py`, frontend `channels-catalog-links.test.ts`.
PostgreSQL проверяет гонки create/delete/bind, replay, rollback, SKU, tenant/права,
архив, stock confirmation и сохранность Catalog при новом импорте. Браузер проверяет
в том числе обрыв ответа после commit и повтор с тем же intent.


## Ручное обновление текстов: 0031

Операция `ContentUpdateRun` независима от первичной инициализации `SyncRun` и
владеет своими `ContentUpdateItem`. Используются две tenant-таблицы:
`channel_content_update_runs` и `channel_content_update_items`. Позиции не имеют
самостоятельного write repository. Платформенные таблицы и неработающие артефакты
XML заранее не создаются.

Сценарий: выбрать 1..50 связанных публикаций одного канала → сохранить точный
снимок Catalog через существующие item-lock/publication-snapshot фасады → фоновое
чтение текущих внешних текстов → сравнение по locale → явное подтверждение
revision/hash → durable отправка → контрольное чтение результата. Подготовка
доступна при is_enabled=false; отправка требует явно включённого Channel,
verified/unpaused Connection, неизменных generation/SDK, связей и текстов Catalog.
Подготовленный снимок действителен 24 часа. Неполные/пустые тексты блокируются:
очистка описания этим срезом не поддерживается. Внешние товары и переводы не создаются.

Новые endpoint под `/api/console/channels`:

| Метод/путь | Назначение |
| --- | --- |
| `POST /{channel_id}/content-updates` | Идемпотентная подготовка по run_id и publication_ids; 202 |
| `GET /{channel_id}/content-updates` | Последние 20 операций текущего автора |
| `GET /content-updates/{run_id}` | Сравнение, состояние, результаты и наличие прерванного job |
| `POST /content-updates/{run_id}/confirm` | expected_revision/preview_hash; повтор возвращает ту же операцию; 202 |
| `POST /content-updates/{run_id}/retry` | Восстановить потерянный шаг либо повторить сверку; 202 |

Все endpoint проверяют channels.manage + catalog.read и tenant; детали/действия
доступны автору подготовки. Мутации требуют CSRF. GET читает проекцию, не обращается
к площадке и не чинит job записью. Worker `channels.update_publication_content`
использует tenant admission и проверяет текущий lease. Состояние и следующий job
сохраняются в одной транзакции; HTTP выполняется за её пределами.

Перед PUT сохраняется sending intent. Повтор доставки такого шага сначала читает
результат, не повторяет неизвестную запись. Принятый PUT получает статус verifying,
успех — только после сверки всех текстов. Перезапрос проверки не отправляет PUT.
Для новой отправки после ошибки пользователь пересобирает сравнение и подтверждает
новый снимок. Unknown удерживает резерв цели до контрольного чтения; ошибка этого
чтения не освобождает резерв. При смене generation старая неопределённая отправка
требует ручного разбора, её нельзя обойти новым preview. Успешные позиции сохраняются при partial; terminal история остаётся
доступной. Выключение Channel останавливает будущие отправки, но допускает проверку
уже принятого запроса. Атомарной транзакции с площадкой и exactly-once гарантий нет;
Woo не предоставляет здесь CAS для одновременной правки во внешнем редакторе.

SDK 5/config 3: `preview_content_update` объявляют оба плагина; `update_content`
объявляет только Woo. Реестр собирает общий ContentUpdatePlugin через фабрики,
без ветвлений ядра/Console по провайдеру. Scoped HTTP допускает PUT только с
name/description; Woo дополнительно адресует конкретный существующий product ID
и перечитывает его перед записью. Вариации показывают ограничение и не меняют родителя.

### Проверенный контракт Prom

2026-10-19 прочитан официальный
[OpenAPI JSON](https://prom.ua/cloud-cgi/static/uaprom-static/docs/swagger/documentation.json).
ImportProductURL содержит url, force_update, only_available,
mark_missing_product_as и updated_fields. `updated_fields` по схеме — **плоский
массив строк**; вложенный массив в Example Value вызван некорректным default
на уровне items. Разрешённые текстовые поля — name и description. Документированного
параметра only_update/update_only/create_missing=false нет.

[Справка Prom](https://support.prom.ua/hc/uk/articles/360004963478) описывает флаг
«Тільки оновлення» для ручного импорта в кабинете и прямо указывает, что он не
сохраняется для периодического URL-импорта. Это не доказывает наличие того же флага
в публичном API. Наличие native ID и предварительный GET не закрывают удаление
карточки между проверкой и импортом. Поэтому плагин возвращает
`content_update_update_only_unconfirmed`; прямой send также закрыт. XML не
отправляется, import ID/артефакты не создаются. `/products/edit` документирует
name/description, но не выбран в качестве скрытой замены согласованного XML.

Console показывает read-only сравнение, locale в URL, прогресс, ошибки и историю.
Данные не дублируются в Pinia; query keys включают tenant/actor. При смене контекста
запросы отменяются и поздние ответы игнорируются. HTML повторно очищается перед
рендерингом. Проверки используют реальные HTTP/CSRF/PostgreSQL/jobs, внешние API —
fixtures; реальные кабинеты этой проверкой не подтверждены.
