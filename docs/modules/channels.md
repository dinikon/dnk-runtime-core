# Channels: каналы, подключения и проверка доступа

Модуль управляет каналами Prom, Rozetka и WooCommerce. Единственная реализованная
возможность платформ — `verify_connection`. Публикации, сопоставления, цены,
остатки, представления, галереи, исходящие доставки и XML-фиды удалены.

## Границы и структура

Один Aggregate Root `Channel` владеет Entity `Connection`. У агрегата один
`ChannelRepositoryProtocol`. Корень отвечает за ревизию и аудит; подключение —
за настройки доступа, зашифрованные credentials, identity магазина и проверку.

```text
channels/
├── domain/                 # Channel, Connection, VO и ошибки
├── application/            # CRUD, prepare/apply verification, чтение
├── application/port/platform.py     # Порт пакета, manifest и registry
├── infrastructure/         # Persistence и Shared Jobs
├── infrastructure/platforms/       # Конкретные модели и verifier трёх площадок
└── presentation/           # HTTP, Depends и worker проверки
```

Domain использует обычные dataclass, Enum и `EntityIdVO`. Восстановление происходит
через фабрики `create/restore`. Mapper не исправляет противоречивые состояния.
Настройки копируются на входе и выходе; наружу не выдаётся изменяемый словарь агрегата.

## Подключения платформ

| Платформа | Endpoint | Credentials | Identity |
| --- | --- | --- | --- |
| Prom | `https://my.prom.ua` | API `token` | Единственная корневая группа `groups/list` |
| Rozetka | `https://api-seller.rozetka.com.ua` | API `token` | `content.market.id` ответа `sites/get-auth-data` |
| WooCommerce | HTTPS base URL, включая подпуть WordPress | `consumer_key`, `consumer_secret` | Canonical `environment.site_url` защищённого `system_status` |

У конфигурации есть `version`, `endpoint` и пустой `settings: {}`. Политика
`stock_sync`, валюты и локали больше не принимаются и не показываются в Console.
Каждый пакет явно связывает свои config, credentials, manifest и verifier.
В общем порте нет моделей платформ, `Generic` или `TypeVar`.

Credentials сериализуются явно по полям через `get_secret_value()`. Шифрование
использует [общий Shared Cipher](shared-encryption.md) и единый конфиг проекта.
Секреты, шифротекст и содержимое ответа площадки не возвращаются в HTTP и логи.
Ранее сохранённый шифротекст не перекодируется миграцией.

## HTTP

Базовый путь Console: `/api/console/channels`.

| Метод | Путь | Действие |
| --- | --- | --- |
| GET | `/platforms` | Manifest и JSON Schema форм подключения |
| GET | `/` | Список с фильтрами и пагинацией |
| POST | `/` | Создать Channel и запланировать проверку |
| GET | `/{id}` | Публичная карточка и состояние проверки |
| PATCH | `/{id}` | Изменить название, конфигурацию или credentials |
| POST | `/{id}/connection/verify` | Повторно проверить сохранённое подключение |
| DELETE | `/{id}` | Удалить локальный Channel и отменить его проверки |

Точные параметры методов задаются request/response соответствующего сценария.
Чтение требует `channels.read`; изменения используют существующие права Channels
и CSRF. Каждый запрос ограничен текущим tenant. Чужой ID не раскрывается.
Удалённых маршрутов публикаций, XML и публичных изображений больше нет.

## Ревизии и проверка

Создание записывает агрегат и `channels.verify_connection` в одном внешнем UoW.
Новый Channel имеет ревизию 1, подключение — `config_revision=1`, проверка —
`pending`, identity отсутствует. Сеть в HTTP-команде не вызывается.

Переименование меняет ревизию Channel один раз и не отменяет текущую проверку.
Замена конфигурации или полного комплекта credentials увеличивает ревизию
подключения, отменяет прежнее задание и планирует проверку новой ревизии.
Пропущенные credentials сохраняют прежний секрет. Сохранение без изменений
не меняет ревизию. Изменение имени и доступа атомарно.

Worker выполняет следующие этапы:

1. В короткой транзакции проверяет tenant, Channel, подключение, config revision,
   job ID и владение lease; восстанавливает конфигурацию и расшифровывает credentials.
2. Вызывает verifier выбранного пакета вне SQL-транзакции.
3. В новой транзакции повторяет проверки актуальности и lease, проверяет
   допустимость identity в Domain и уникальность магазина через repository.
4. Сохраняет `verified` или безопасную ошибку. Устаревший результат игнорируется.

Успех верификации не запускает других заданий. После первой успешной проверки
магазин закреплён: другой магазин требует нового Channel. Identity сохраняется
при ошибке повторной проверки. Уникальность действует внутри tenant; удаление
канала освобождает магазин. Названия каналов могут повторяться.

Для отсутствующего или завершённого задания при `pending` чтение возвращает
`recovery_required`; Console прекращает polling и предлагает повторную проверку.
Manifest и `available_capabilities` содержат только `verify_connection`.

## Хранение и миграция очистки

В tenant остаются только таблицы `channels` и `channel_connections` этого модуля.
Соседние таблицы Catalog, Files и остальных модулей сохраняются.

Новая tenant-ревизия `0016_channels_connections_only` после
`0015_channels_feed_import` удаляет данные и таблицы:

- `channel_content_deliveries`;
- `channel_content_feeds`;
- `channel_content_media`;
- `channel_product_representations`;
- `channel_stock_sync_states`;
- `channel_catalog_binding_items`;
- `channel_catalog_binding_groups`;
- `channel_external_publications`;
- `channel_sync_runs`.

Она удаляет из `channel_connections.settings` только ключи `stock_sync`,
`currency`, `locales`, `locale`, сохраняя UUID, endpoint, credentials, identity,
проверки, ревизии и аудит. Исторические ревизии и исторические имена таблиц
не переписываются.

Global-ревизия `0002_channels_jobs_cleanup` удаляет из `public.scheduled_jobs`
только типы `channels.sync_publications`, `channels.sync_stock`,
`channels.deliver_content`, `channels.apply_content_feed` и внутренние задания
`catalog.stock_changed` удалённого consumer. Проверки подключений, другие задания
и интеграционный outbox сохраняются. Catalog продолжает сохранять собственные
интеграционные события в outbox, но больше не ставит задания для Channels.
Files проверяет оставшиеся ссылки Catalog; физические файлы не удаляются очисткой.

Обе ревизии необратимы по данным; `downgrade` завершается явной ошибкой.
Откат требует резервной копии. SQL не удаляет товары или изображения на площадке.

### Порядок выпуска

1. Остановить старые API/worker, создающие и исполняющие удаляемые задания.
2. Проверить уже принятые внешние импорты: удаление локального состояния не
   отменяет обработку на площадке. Сохранить нужную диагностику до очистки.
3. Сделать резервную копию БД и развернуть согласованный код удаления.
4. Штатной командой `dnk-manage database upgrade` применить global- и tenant-
   ревизии. Команда выполняет их во внешней транзакции с существующими блокировками.
5. Запустить API/worker/Console новой версии и проверить CRUD/verify.

Применять миграцию к работающему старому коду нельзя. Реализация среза сама
не применяет миграции к рабочей БД и не перезапускает сервисы.

## Console и проверки

Остаются `/channels`, `/channels/new`, `/channels/:id`: список, настройки,
проверка и удаление подключения. Редактор сохраняет несохранённый ввод при refetch,
ошибке и конфликте; смена tenant/session очищает его контекст. После сохранения
секрет не попадает в поля формы. Удалены вкладки публикаций/XML и действия Channels
из редактора Catalog.

Основные проверки: `test_channels`, `test_channels_domain`,
`test_channels_connection_settings`, `test_channels_postgres`,
`test_channels_cleanup_postgres`, архитектурные тесты, тесты Catalog/Files и
`channels-contracts.test.ts`, `channels-navigation.test.ts`.
PostgreSQL проверяет заполненную историческую схему, сохранность подключения
и соседнего tenant, точную очистку очереди, CRUD и fencing verifier.
