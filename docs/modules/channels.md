# Channels

Реализованы настройки подключений и чтение публикаций Prom/WooCommerce через
Console и HTTP API. Карточки сохраняются локально; импорт выполняет shared jobs
worker. Проверка подключения как отдельный сценарий, запись на платформы и связь
с Catalog остаются следующими этапами.

## Модель

`ChannelKind` — конечная платформа (`prom`, `woocommerce`, `shopify`, …).
`ChannelType` — категория платформы: `marketplace`, `cms`, `shop`; она выводится
из реестра по kind и не дублируется в tenant-таблице. Отдельного ConnectionType нет.

Корни модуля: `Channel`, `ExternalPublication`, `PublicationImportRun`. В каждом
слое они размещены в `channel/`, `external_publication/`,
`publication_import_run/`; SQL-модели находятся в общей
`infrastructure/persistence/models/`.
Агрегат неизменяем: его методы возвращают новое проверенное состояние.
Он хранит название, kind, версию конфигурации, настройки, активность, статус и audit.
Domain получает только запечатанные credentials; открытые ключи используются
в Application при объединении настроек и в HTTP-адаптерах при чтении источника.
Секреты не входят в repr.

- `is_active` управляется пользователем, по умолчанию `true`.
- `status`: `unverified`, `connected`, `error`; новый канал — `unverified`.
- Изменение настроек сбрасывает проверку. Идентичная запись, переименование
  и переключение активности её не меняют.
- Kind нельзя менять: для другой платформы создаётся новый канал.
- Выключенный канал можно редактировать и удалить.

## Архитектура и контракты сценариев

Правила: [архитектура проекта](../architecture/AGENTS.md) и корневой `AGENTS.md`.
Сценарии разделены по Aggregate Root внутри соответствующего слоя.

| Сценарий Application | Вход | Результат | HTTP response |
| --- | --- | --- | --- |
| `create_channel` | `CreateChannelCommand` | `CreateChannelResultDTO` | `CreateChannelResponse` |
| `update_channel` | `UpdateChannelCommand` | `UpdateChannelResultDTO` | `UpdateChannelResponse` |
| `delete_channel` | `DeleteChannelCommand` | `None` | 204 без тела |
| `get_channel` | `GetChannelQuery` | `ChannelDetailsDTO` | `GetChannelResponse` |
| `list_channels` | `ListChannelsQuery` | `tuple[ChannelListItemDTO, ...]` | список `ListChannelItemResponse` |
| `list_kinds` | `ListKindsQuery` | `tuple[ChannelKindListItemDTO, ...]` | список `ListChannelKindItemResponse` |
| `get_kind_config` | `GetKindConfigQuery` | `ChannelKindConfigDTO` | `GetKindConfigResponse` |

Каждый сценарий находится в `application/<aggregate_root>/command|query/<scenario>/` с отдельными
`command.py` или `query.py`, `handler.py` и `dto.py` при наличии результата.
Удалению пустой DTO не нужен. Все методы имеют явные аннотации и docstrings.
Каждый HTTP-метод имеет собственные controller/response файлы; request нужен
только созданию и PATCH. Общих DTO и response для разных методов нет.

`Channel.create` и `Channel.restore` проверяют состояние явно; `__post_init__`
используется только в VO настроек. Переименование, изменение настроек и активности
проверяют значения и обновляют audit через методы агрегата. Сохранение одинаковых
значений сохраняет статус и audit. Фабрики не позволяют восстановить некорректные
типы ID, статус, версию, название или audit без часового пояса.

`ChannelMapper` преобразует агрегат в значения вставки/обновления и восстанавливает
его через `Channel.restore`. `ChannelQueryMapper` отдельно собирает карточку и
строку списка из явной публичной SQL-проекции без загрузки агрегата и credentials.

Handlers получают только порты. Depends собирает SQL-адаптеры на общей сессии
внешнего UoW; handlers, repositories и mappers не выполняют commit/rollback.
Команды возвращают собственный безопасный DTO из изменённого агрегата; контроллер
не вызывает дополнительный query handler для формирования ответа. Успех HTTP
отправляется только после завершения UoW; ошибка commit не становится успехом.

Ошибки проверки схемы, конфликта версии и хранилища credentials принадлежат
Application. Ошибки полей имеют независимые от транспорта path/message/code.
Контроллер каждого метода явно преобразует DTO в свой response и ожидаемые ошибки
в HTTP-статусы; префикс `body` добавляется только здесь. `ChannelRoute` очищает
ошибки валидации FastAPI от входных значений. Domain не содержит HTTP-контрактов.

## Реестр и форма

Реестр находится в `infrastructure/channel/definitions/registry.py`, выдаёт копии определений
и включает 21 платформу из плана, кроме Facebook Leads и TikTok Leads.
Сохранение доступно для Prom и WooCommerce. Остальные записи имеют причину
недоступности и `config.connection: null`.

Определение содержит kind, type, label, can_configure, unavailable_reason,
config_version и config. В `config.connection` находятся JSON Schema Draft 2020-12
и ui_schema (упорядоченные property/widget/help_text).
`config.capabilities.read_publications` доступна для Prom и WooCommerce. Схемы не редактируются через API.

Prom требует секретный `api_key`. WooCommerce требует `url` и секретные
`consumer_key`, `consumer_secret`. URL — HTTPS без userinfo, query и fragment,
с поддержкой магазина в подкаталоге. Формат `https-store-url` проверяется
серверным FormatChecker и renderer Console. Сервер валидирует ту же схему,
которую отдаёт UI. Дополнительные поля запрещены.

## API

База: `/api/console/channels`. Все запросы аутентифицированы и требуют tenant;
запись использует существующий CSRF. Tenant и actor из тела не принимаются.

| Метод | Путь относительно базы | Назначение |
| --- | --- | --- |
| GET | `/kinds` | Каталог платформ |
| GET | `/kinds/{kind}/config` | Определение со схемой |
| GET / POST | пустой | Список / создание |
| GET / PATCH / DELETE | `/{channel_id}` | Карточка / изменение / удаление |

Пример создания (значение ключа демонстрационное):

```json
{
  "name": "Основной Prom",
  "kind": "prom",
  "config_version": 1,
  "connection_settings": {"api_key": "example-only"},
  "is_active": true
}
```

PATCH поддерживает name, is_active, connection_settings и config_version.
Настройки и версия передаются вместе. Пропущенные настройки сохраняются;
null и пустые обязательные значения отклоняются. Kind и status недоступны для записи.
При несовпадении версии возвращается 409; валидация — 422; отсутствие — 404;
невозможность использовать хранилище credentials — 503.

Ответ содержит безопасные connection_settings и configured_secret_fields,
но никогда не содержит ключи доступа или их маски. Ошибки валидации содержат
loc/msg/type без input. Ошибка проходит через исключение HTTP и приводит к rollback UoW.

## Хранение и запуск

Tenant-миграция `0013_channels` следует за `0012_catalog`;
`0014_channel_publications` добавляет локальные карточки, запуски и ревизию подключения. Таблица channels
хранит публичные параметры в JSONB, секретные — одним Fernet ciphertext.
Query-проекции не выбирают ciphertext. PATCH блокирует строку на время UoW;
HTTP-вызовов внешних платформ внутри транзакции нет.

Для записи credentials требуется отдельный ключ Channels:

```sh
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Передать его через `CHANNELS__SECRET_ENCRYPTION_KEY` или файл, указанный в
`CHANNELS__ENCRYPTION_KEY_PATH`. Одновременно использовать оба параметра нельзя.
Ключ должен сохраняться между перезапусками; его замена без перешифровки сделает
существующие credentials недоступными. Не использовать ключи других модулей.

Без ключа работают каталог, безопасное чтение, переименование, переключение
активности и удаление. Создание и изменение настроек требуют доступного ключа.
Миграция применяется штатным механизмом tenant-миграций; код не меняет рабочую БД
автоматически при открытии Console.

## Console

Раздел «Интеграции → Каналы»:

- `/channels` — список, активность и технический статус отдельно.
- `/channels/new` — выбор платформы и динамическая форма из API.
- `/channels/:channelId` — переход к вкладке «Публикации».
- `/channels/:channelId/publications` — список локальных карточек и обновление.
- `/channels/:channelId/publications/:publicationId` — поля карточки и вариации.
- `/channels/:channelId/settings` — существующая форма подключения.

На странице канала общие вкладки «Публикации» и «Настройки подключения».
Карточка сохраняет активность вкладки публикаций. Переход из изменённой формы
защищён существующим подтверждением несохранённых изменений.

Сохранённые секреты представлены текстом «Ключ задан». Действие «Заменить»
включает ввод нового значения; без этого секрет не отправляется. Изменение платформы
сбрасывает параметры. Неизвестная структура схемы блокирует сохранение.

Credentials не сохраняются в web storage или query/mutation cache; запросы записи
не используют mutation cache, ошибки Axios очищаются от тела запроса. Query keys
изолированы по tenant, смена tenant очищает форму и отменяет текущий запрос.
При 409 пользователь явно обновляет схему; автоматической повторной отправки нет.
В публикациях доступна кнопка загрузки/обновления и прогресс активного импорта.
Страницы читают локальное хранилище; GET страницы Console не вызывает платформу.

## Проверки

```sh
.venv/bin/python -m unittest test.test_channels test.test_channels_http test.test_channel_publications test.test_channels_architecture -q
TEST_POSTGRES_URL='<disposable PostgreSQL URL>' .venv/bin/python -m unittest test.test_channels_postgres test.test_channel_publications_postgres.ChannelPublicationsPostgresTests -q
npm --prefix frontends run typecheck:console
npm --prefix frontends run lint:console
npm --prefix frontends run build:console
```

PostgreSQL-тесты создают отдельные временные tenant-схемы, проверяют миграцию,
шифрование, изоляцию, rollback, конкурентное объединение PATCH и удаление.

`test_channels_architecture.py` проверяет структуру сценариев всех трёх корней, отдельные DTO
и HTTP-схемы, аннотации, русские docstrings, запрет `__post_init__` вне VO,
направление импортов, границы транзакций, mapper-ы и пустые `__init__.py`.
Он включается стандартным `unittest discover`, используемым `scripts.cicd.checks`,
и также запускается отдельно без PostgreSQL. Семантику фабрик, audit, безопасных
результатов команд, ошибок полей и сбоя commit проверяют регрессионные тесты.

## Read публикации и импорт

`ExternalPublication` сохраняет идентичность `(channel_id, connection_revision,
resource_type, external_id)`, внешний ID родителя, native `raw_payload` в JSONB,
типизированный `document` с `schema_version=1`, ревизию снимка и время наблюдения.
Native данные сохраняют неизвестные поля, но не выдаются Read API. Документ
содержит название, SKU, ссылки, очищенные описания, изображения, категории,
характеристики, цены, валюту, остаток, наличие, внешний статус и тип товара.
`None` означает отсутствие данных; нулевые цена/остаток остаются нулём.
Изменение снимка увеличивает ревизию; повторный одинаковый импорт сохраняет ID
и ревизию. Этот документ описывает наблюдаемое состояние и не является payload
будущего создания/обновления на платформе.

`PublicationImportRun` хранит queued/running/succeeded/partial/failed, число
сохранённых страниц и ресурсов, курсор, текущий job_id и безопасный код ошибки.
Создание активного канала автоматически ставит первоначальный импорт в очередь.
Существующие каналы загружаются кнопкой. Повторный запуск возвращает активный run.
Пустой успешный источник завершается succeeded с нулём ресурсов.

| Сценарий | Вход | Результат |
| --- | --- | --- |
| start_publication_import | StartPublicationImportCommand | StartPublicationImportResultDTO |
| prepare_publication_import | PreparePublicationImportCommand | PreparePublicationImportResultDTO или None для устаревшего job |
| import_publication_page | ImportPublicationPageCommand | ImportPublicationPageResultDTO |
| complete_publication_import | CompletePublicationImportCommand | None |
| list_publications | ListPublicationsQuery | PublicationPageDTO |
| get_publication | GetPublicationQuery | PublicationDetailsDTO |
| get_publication_import_run | GetPublicationImportRunQuery | PublicationImportRunDetailsDTO или None |

HTTP относительно `/api/console/channels/{channel_id}`:

- POST `/publication-imports` — 202 и run_id, обязательный CSRF, без фиктивного body.
- GET `/publication-imports/latest` — последний run текущего подключения или null.
- GET `/publication-imports/{run_id}` — прогресс конкретного run или 404.
- GET `/publications?offset=0&limit=25` — пагинированные локальные публикации.
- GET `/publications/{publication_id}` — поля карточки и связанные позиции.

Prom использует GET `/products/list` без фильтра группы/статуса. Курсор `last_id`
уменьшается согласно верхней границе ID. Ответ списка уже содержит поля модели
Product; отдельное чтение карточки пока не требуется. Вариации Prom остаются
отдельными публикациями; связи строятся только по явному `variation_base_id`.
Совпадение названий и SKU ничего не группирует. Локализованные native поля
сохраняются; этот срез отображает основной контент ответа без выбора fallback.

Для Prom `regular_price` берётся из native `price`, а `sale_price` вычисляется
из `discount`: процент (`percent`) или фиксированная сумма (`amount`). Например,
480 UAH со скидкой 20% даёт 384 UAH. `price` сохраняет цену ответа платформы;
`sale_price` отражает заданную скидку без определения её активности по датам.
Период скидки остаётся в native JSON. Некорректная скидка даёт предупреждение
`invalid_discount` и пустую `sale_price`, не прерывая импорт карточки.

Woo использует REST v3 GET products со status=any и страницы GET
products/{id}/variations. В списке находятся верхние ресурсы, в деталях —
дочерние позиции текущего run. Если получение вариаций не завершено, карточка
показывает неполноту. Валюта читается через general/woocommerce_currency;
если права магазина не позволяют прочитать настройку, значение остаётся пустым
с предупреждением. Доступные статусы определяет API и права ключа: данные вне
его области видимости не считаются загруженными.

Worker зарегистрирован как `channels.publication_import` в `jobs worker`.
Каждое задание обрабатывает ограниченную страницу. Подготовка коммитится до GET;
после GET открывается новый короткий UoW. Запись карточек, прогресса и задания
продолжения атомарна. Lease проверяется с блокировкой перед записью; повтор старой
страницы не продвигает прогресс. Shared jobs повторяют временные ошибки.
Окончательная ошибка сохраняет уже полученные карточки и статус partial/failed;
исчерпанное или потерянное job видно в проекции и допускает новый ручной запуск.

`connection_revision` увеличивается только при действительном изменении настроек.
Старый worker не сохраняет данные после смены подключения или выключения канала.
Чтение выбирает только текущую ревизию; старые снимки остаются в БД до удаления
канала. Ротация ключей также создаёт новую область снимков и требует загрузки.
Отсутствие карточки в следующем обходе пока не удаляет ранее полученный снимок:
автоматическая сверка удалений и периодический импорт отложены. Исчезнувшие
вариации не смешиваются с текущим набором родителя.

HTTP адаптеры разрешают HTTPS с публичным IP, закрепляют DNS адрес и TLS host,
отключают proxy/redirect, ограничивают распакованный JSON до 16 MiB на запрос.
Внешние ошибки не содержат URL, credentials и тела ответа. Описания очищает nh3
за Application-портом; ссылки изображений и карточек ограничены HTTP(S) без
userinfo. Запись на Prom/Woo, YML, локальные правки и привязка Catalog не входят
в текущий срез.

Проверки импорта покрывают страницы Prom, более 100 вариаций Woo, отсутствие
валюты, нулевые значения, очистку HTML, сохранение native полей, повторные запуски,
lease/ревизию подключения, частичный сбой, пустой источник и HTTP tenant isolation.
Проверяются остановка при повторяющейся странице источника и полный rollback
карточек, курсора и задания продолжения с успешным повтором после сбоя.
