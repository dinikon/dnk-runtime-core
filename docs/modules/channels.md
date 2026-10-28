# Channels: подключения и чтение публикаций

Срез от 28.10.2026: Backend → Shared Worker → Console для подключений Prom,
Rozetka и WooCommerce, проверки доступа и постраничного импорта публикаций.
Чтение Console работает с локальными снимками. Catalog, заказы, запись на
площадки, XML и периодическая бизнес-синхронизация остаются следующими срезами.

## Границы

Три независимых Aggregate Root: `Channel` (владеет Entity `Connection`), `SyncRun`
и `ExternalPublication`. Каждый имеет собственный Domain Repository. Каталоги
слоёв разделены по агрегатам `channel`, `sync_run`, `external_publication`.
Общие адаптеры остаются в `infrastructure/platforms/{prom,rozetka,woocommerce}`.

Domain использует dataclass, Enum и существующий `EntityIdVO`. В нём нет Pydantic,
SQLAlchemy и моделей платформ. Фабрики `create/restore` проверяют ревизии,
сочетания статусов и времени, роли и идентичность. JSON копируются на входе и
выходе. Чистая `PublicationStructurePolicy` проверяет затронутое дерево: один
уровень, то же подключение, допустимый родитель, отсутствие самоссылки. Mapper
не исправляет противоречивое состояние.

Каждый пакет явно связывает конкретные config, credentials, manifest, verifier
и reader. Общий порт не использует `Generic`/`TypeVar` и модели платформ.
Manifest декларирует `verify_connection` и `publications`. Последнее означает
обязательную реализацию чтения источника, не право записи. Публичная доступность
`publications` требует проверенного подключения текущей ревизии. Таблицы
capabilities нет.

## Подключение, валюта и языки

| Платформа | Endpoint | Credentials | Settings |
|---|---|---|---|
| Prom | `https://my.prom.ua` | `token` | `currency: UAH`, `locales: [uk, ru]`, фиксированы |
| Rozetka | `https://api-seller.rozetka.com.ua` | `token` | `currency: UAH`, `locales: [uk, ru]`, фиксированы |
| WooCommerce | HTTPS base URL, включая подпуть WordPress | `consumer_key`, `consumer_secret` | `currency: UAH/USD/EUR`, `locale: uk/ru/en`; defaults `UAH`, `uk` |

Наборы Prom/Rozetka обязательны: другой код, неполный набор, дубли и дополнительные
языки отклоняются. Порядок нормализуется в `uk, ru`. Woo принимает одну валюту и
одну локаль. Коды дополнительно проверяются через публичные Application-контракты
справочников без доступа к их SQL-моделям.

Настройки остаются в JSON `ConnectionConfig`. Пустые прежние настройки читаются
с defaults без записи в БД. Сравнение выполняется после нормализации:
переименование и сохранение тех же настроек не меняют `config_revision`.
Операция `Channel.change_settings` повышает ревизию Channel один раз, даже при
одновременной замене названия и подключения.

Замена настроек или credentials повышает `config_revision`, отменяет активный
SyncRun и прежние задания, запускает проверку. Пропущенные credentials сохраняют
секрет; переданные заменяют комплект целиком. Секреты шифруются через
[Shared Cipher](shared-encryption.md), сериализуются явно с `get_secret_value()`
и не возвращаются в HTTP. После первой успешной проверки identity закреплена.
Другой магазин требует нового Channel; один магазин принадлежит одному Channel
в tenant. Удаление освобождает identity. Названия каналов могут повторяться.

- Prom: identity — единственная корневая группа `groups/list` с положительным ID
  и `parent_group_id=null`; страницы по 100, максимум 50. Стабильность кандидата
  identity на живых магазинах ещё требует проверки.
- Rozetka: Bearer API token, `GET /sites/get-auth-data` → `content.market.id`.
  Логина, пароля и парольного fallback нет. `success=false` при HTTP 200 — отказ.
  `content.id` не является идентификатором магазина.
- WooCommerce: защищённый `system_status` → canonical `environment.site_url`.
  Публичный индекс WordPress не подтверждает доступ.

## Снимки публикаций

| Платформа | Импорт и структура |
|---|---|
| Prom | Основной товар — продаваемый `simple`; разновидности — `variant` с `parent_id` на него |
| WooCommerce | `simple`, `variable` и дочерние `variant`; контейнер не является продаваемой позицией |
| Rozetka | Все позиции как самостоятельные `simple`; группировки остаются в `platform_data` |

WooCommerce `grouped`, `external` и неизвестные типы пропускаются со счётчиком.
Флаги `virtual`/`downloadable` поддерживаемые типы не исключают.

Публикация хранит стабильный UUID, ключ источника, роль, родителя и ревизию;
полный `raw_data`, `normalized_schema=publication.v1`, `normalized_data`,
`platform_schema`, `platform_data`; первое/последнее наблюдение и наблюдавший
SyncRun. Изменившийся снимок повышает ревизию; тот же обновляет только наблюдение.
JSONB-порядок ключей переводов не считается изменением.

Нормализуются названия по локалям, артикул, доступные ссылка/изображение, цены,
количество, режим остатка, наличие и состояние. Деньги — `Decimal`, JSON и HTTP
передают их строками. Неизвестное — `null`, ноль остаётся нулём. Цена не
пересчитывается: нормализованная валюта берётся из канала. Несовпадение с
источником не блокирует импорт и не создаёт предупреждения. Исходные значения
остаются в `raw_data`, валюта контекста — в `platform_data.source_currency`.

Prom/Rozetka сохраняют обе полученные языковые версии; нативный `ua` становится
`uk`. Отсутствующий перевод не копируется из `name` или другой локали. Woo
сохраняет текст под настроенной локалью, без перевода и поддержки WPML.
После изменения настроек снимок сохраняет прежние валюту и переводы до нового
получения. Console обозначает его `stale_configuration`.

Prom использует `variation_base_id`; отсутствующий родитель дозагружается перед
сохранением. При смене основного товара известные затронутые участники
перечитываются, итоговое дерево проверяется и сохраняется атомарно. Характеристики
не угадываются по названию/SKU.

Woo обходит товары, затем вариации каждого полученного `variable`. Следующий
родитель выбирается из БД: растущего списка в checkpoint нет.
`manage_stock=parent` разрешается в representation с явным источником общего
остатка. Название контейнера наследуется только при отдельном нормализованном
признаке, без смешивания локалей.

Rozetka обходит `/goods/all` и `/goods/archive` с `available=0,1,2`.
Ключ — `source_offer` + `sync_source_id:price_offer_id`; `item_id` и `rz_item_id`
хранятся отдельно, последний может отсутствовать. Повтор в архиве обновляет тот же
UUID. Пропущенные и неполученные позиции автоматически не удаляются.

## Хранение и выполнение

Tenant-миграция `0007_channels_publications` следует за
`0006_channels_verification`. Новые таблицы: `channel_sync_runs` и
`channel_external_publications`. PK/FK/NOT NULL, уникальность
`(connection_id, resource_type, external_id)` и индексы подключения/родителя/запуска
защищают хранение. Новых бизнес-CHECK, SQL Enum и `parent_kind` нет.
Удаление Channel каскадно удаляет локальные подключения, запуски и публикации.
Отдельное удаление истории SyncRun не удаляет публикации.

`SyncRun`: `queued → running → completed/failed/cancelled`, собственная и
конфигурационная ревизии, current job, версионированный checkpoint, счётчики,
безопасная ошибка, время и признак автоматического запуска. Checkpoint содержит
фазу и курсор, без credentials и ответов товаров.

Успешная проверка создаёт автоматический запуск один раз для ревизии подключения.
Ручной старт под блокировкой Channel возвращает действующий запуск либо создаёт
новый полный обход после завершения. Автоматические повторы продолжают текущий
checkpoint через существующий Shared Jobs.

Шаг задания `channels.sync_publications`:

1. Короткий UoW блокирует Channel, проверяет run/config/job/lease, возвращает
   неизменный снимок доступа и курсора.
2. Расшифровка и запрос страницы/родителей выполняются вне SQL-транзакции.
3. Новый UoW повторно проверяет ревизии, владельца задания и lease.
4. Снимки, checkpoint, прогресс и следующее задание сохраняются атомарно.

Потерянная lease, повторная доставка и изменённое подключение не применяют
устаревшую страницу. Полученные страницы остаются после ошибки. Потерянное или
терминальное задание активного запуска даёт `recovery_required`; ручной старт
завершает прерванный запуск и начинает новый. При удалении Channel задания
отменяются, внешний API не вызывается.

Transport сохраняет HTTPS, запрет redirects, проверку публичного IP с закреплением
адреса и ограничение тела 2 MiB. Credentials не передаются в URL. Общая очередь,
TenantGate, lease и повторы принадлежат Shared Jobs.

## HTTP и Console

База: `/api/console/channels`. Аутентификация, `channels.read`/`channels.manage`
и CSRF сохранены. Прежние CRUD, manifests и `POST /{id}/connection/verify`
сохраняют контракты.

| Метод | Новый путь | Результат |
|---|---|---|
| POST | `/{id}/sync-runs` | 202, новый либо действующий запуск |
| GET | `/{id}/sync-runs/latest` | `{sync_run: …}` или `{sync_run: null}` |
| GET | `/{id}/sync-runs/{run_id}` | Состояние и `recovery_required` |
| GET | `/{id}/publications` | Карточки, `search`, `offset`, `limit`, `locale` |
| GET | `/{id}/publications/{publication_id}` | Карточка с выбранной позицией |

HTTP DTO явно перечисляют публичные поля, без raw/platform документов, checkpoint
и секретов. Чтение не восстанавливает агрегаты. Пагинация — по корням, дети
загружаются пакетно; поиск по ребёнку возвращает его карточку. Prom показывает
основной товар среди вариантов; Woo — вариации; Rozetka — одну позицию.
Диапазон цен считается только в одной сохранённой валюте.

Карточка передаёт `root_external_id`, `root_sku` и `root_main_image_url` из
корневой публикации. В списке WooCommerce название, артикул и фото относятся
к родительскому товару; состав `items` по-прежнему содержит только вариации.
Отсутствующее фото родителя отображается заглушкой, отсутствие артикула — его
внешним ID; данные вариаций их не подменяют.

Console: `/channels/:id/publications` и
`/channels/:id/publications/:publicationId`. Добавлены переходы из настроек,
запуск, счётчики/ошибки/повтор, карточки и разновидности. Форма поддерживает enum,
const и фиксированный массив языков без преобразования массивов в строки.
Поиск, язык, позиция и пагинация сохраняются в URL и tenant/session query keys.
Смена контекста отменяет запросы и очищает кеш. Polling выполняется только для
активного запуска; обновление не стирает черновик настроек. Без достоверного
общего числа процент выполнения не выводится.

## Запуск и проверки

API и worker должны получать один постоянный `ENCRYPTION__KEY` либо
`ENCRYPTION__KEY_PATH`; см. [Shared encryption](shared-encryption.md).
Применить tenant-миграции существующим способом и запустить `jobs worker`.
Рабочая БД при разработке этого среза не мигрируется.

```sh
python -m unittest test.test_channels test.test_channels_domain test.test_channels_publications test.test_module_registration test.test_architecture_boundaries
TEST_POSTGRES_URL=postgresql+asyncpg://… python -m unittest test.test_channels_postgres test.test_channels_publications_postgres test.test_scheduled_jobs test.test_jobs_management_command
cd frontends
npm run lint:console
npm run typecheck:console
npm run build:console
```

PostgreSQL-тесты требуют отдельную disposable БД. Контрактные fixtures
синтетические, см. [описание](../../test/fixtures/channels/README.md).
Рабочих credentials нет: live smoke всех платформ, включая постоянный API-токен
Rozetka для `/sites/get-auth-data`, необходимо выполнить перед rollout.
Автотесты проверяют обработку контрактов, но не доступ конкретного магазина.
