# Channels: подключения магазинов

Срез от 26.10.2026: API и Console для создания, изменения, верификации и полного
удаления подключений Prom, Rozetka и WooCommerce. Подключение проверяется фоновым
заданием. Заказы, публикации, Catalog и экспорт контента относятся к следующим срезам.

## Инварианты и типы

Один Aggregate Root `Channel` владеет одной Entity `Connection`. Изменения проходят
через методы агрегата. Domain/Application не импортируют модели платформ,
Pydantic, SQLAlchemy или HTTP-клиенты. Платформенные пакеты находятся в
`infrastructure/platforms/{prom,rozetka,woocommerce}` и связывают конкретные
типы конфигурации, credentials, manifest и verifier в самостоятельных классах
`PromPlatform`, `RozetkaPlatform`, `WooCommercePlatform`. Общий порт не зависит
от их моделей; `Generic` и `TypeVar` не используются.
JSON используется только как версия документа на внешних границах.

Domain использует `ChannelNameVO`, `ConnectionConfigVO`, `ResourceIdentityVO`,
`VerificationVO` и `VerificationStatus`. Конфигурация копирует входные настройки;
свойство `settings` возвращает независимую глубокую копию. Фабрики `create/restore`
отклоняют неположительные или несогласованные ревизии, противоречивые результаты
проверки и `verified` без identity. Сохранённые записи не исправляются автоматически.

`Channel.change_settings` атомарно меняет название и доступ: корневая `revision`
растёт один раз, даже если изменены оба; сохранение без изменений не меняет её.
Возвращаемый `connection_changed` определяет необходимость фонового задания.
`Connection` управляет конфигурацией и проверкой, `Channel` — ревизией и аудитом.
Проверка закреплённой identity принадлежит Domain, проверка уникальности —
Application через единственный `ChannelRepositoryProtocol`.

Предметные ошибки Domain не содержат полей формы или HTTP-кодов. Presentation
отображает их в прежние публичные коды; техническая валидация пакетов возвращает
`ChannelInputError` из Application. Read DTO явно перечисляют публичные поля.
Тип capability принадлежит Application, декларации остаются в manifest платформ.

`verified` означает успешную аутентификацию и установленную identity магазина.
Права на товары, заказы и запись не выводятся из этого результата. Единственный
capability этого среза — `verify_connection`: декларация хранится в manifest пакета,
а публичная доступность вычисляется при чтении. Таблицы capabilities нет.

После первой успешной проверки identity закреплена. Другой магазин требует нового
Channel. Один магазин может принадлежать только одному Channel в пределах tenant.
Удаление освобождает identity. Названия каналов могут повторяться.

Изменения настроек/credentials сразу заменяют действующее подключение, увеличивают
`config_revision` и создают новое поколение проверки. Старые credentials не остаются
резервной копией. Переименование меняет только `revision`, не инвалидируя проверку.
Пропущенное поле credentials сохраняет секрет; переданное заменяет весь комплект.
`null`, пустые обязательные значения и неизвестные поля отклоняются.

## Хранение и транзакции

Миграция `0006_channels_verification` продолжает текущую цепочку tenant-миграций.
Создаются только `channels` и `channel_connections`. В Connection находятся
публичная конфигурация, ciphertext, `config_revision`, индексируемая identity и
версионированный документ текущего результата проверки. Истории проверок нет.

Channel и задание `channels.verify_connection` записываются в одном UoW через
существующий Shared Jobs. Payload задания содержит ID tenant, Channel, Connection,
задания и ревизию конфигурации. Credentials и ответы API в payload не попадают.

Worker получает снимок в короткой транзакции, вызывает API без SQL-транзакции,
затем в новом UoW проверяет config revision, текущее задание и неистёкшую lease.
Порядок блокировок: Channel → задание → advisory lock identity. Уникальное
ограничение identity остаётся последней защитой БД. Изменённое/удалённое подключение,
потерянная lease и повторная доставка не применяют устаревшие результаты.

Временные ошибки используют повторы Shared Jobs, окончательные ошибки сохраняются
сразу. Исчерпание попыток сохраняет последнюю безопасную ошибку. Аварийно завершённое
или отсутствующее задание при `pending` отображается как `recovery_required` и
допускает ручной запуск новой проверки. Общий предел API-проверки — 30 секунд.

Удаление требует актуальную revision, отменяет активные задания и удаляет обе
таблицы агрегата в одной транзакции. Внешний API при удалении не вызывается.
Метаданные завершённых/отменённых заданий Shared Jobs остаются без секретов.

## Платформы

| Платформа | Конфигурация | Credentials | Identity |
|---|---|---|---|
| Prom | endpoint `https://my.prom.ua`, settings `{}` | `token` | ID единственной группы с положительным ID и `parent_group_id=null` |
| Rozetka | endpoint `https://api-seller.rozetka.com.ua`, settings `{username}` | `password` | `content.market.id` ответа `/sites` |
| WooCommerce | HTTPS base URL магазина, settings `{}` | `consumer_key`, `consumer_secret` | canonical `environment.site_url` защищённого `system_status` |

Prom обходит `groups/list` страницами по 100, максимум 50 страниц. Повторяющиеся
страницы, отсутствие/неоднозначность корневой группы и незавершённый обход дают
`resource_identity_unavailable`. **Стабильность этого кандидата identity на реальных
магазинах пока не подтверждена.**

У Rozetka `content.id` — пользователь, а не магазин. Временный access token не
сохраняется. Ответ HTTP 200 с `success=false` не является успешной проверкой.
WooCommerce требует доступ к metadata endpoint; недостаток прав даёт
`permission_missing`. Подпуть WordPress сохраняется. Public API index сам по себе
не подтверждает аутентификацию.

Все запросы используют HTTPS, проверенные публичные IP с закреплением адреса,
исходные Host/TLS SNI, ограничение тела 2 MiB и запрет автоматических redirect.
Секреты не передаются в URL. Ответы API полностью не сохраняются.

## API и Console

Базовый URL: `/api/console/channels`. Маршруты аутентифицированы, изменения требуют
CSRF. Действия `channels.read`/`channels.manage` проходят существующий authorization
service; стандартная политика допускает всех участников tenant.

| Метод | URL | Результат |
|---|---|---|
| GET | `/platforms` | Manifest, supported capabilities и JSON Schema платформ |
| GET | `` | Страница: `search`, `platform_kind`, `status`, `offset`, `limit` |
| POST | `` | Атомарное создание `{name,platform_kind,config,credentials}`, 201 |
| GET | `/{id}` | Публичная конфигурация, identity, verification, capabilities |
| PATCH | `/{id}` | `{expected_revision,name?,config?,credentials?}` |
| POST | `/{id}/connection/verify` | 202, существующее активное либо новое задание |
| DELETE | `/{id}?expected_revision=…` | Полное удаление, 204 |

Ошибки: 404 — отсутствующий Channel; 409 — конфликт revision; 422 — некорректный
ввод; 503 — нет операционного ключа. Платформенные отказы проверки асинхронны и
отображаются в `verification.error_code`. Ошибки валидации не возвращают input/ctx.

Console: `/channels`, `/channels/new`, `/channels/:id`. Форма строится по schemas,
секреты остаются в локальном черновике и не попадают в Query/Pinia/localStorage.
Polling выполняется каждые две секунды только для активной проверки. Refetch
сохраняет черновик. Конфликт предлагает загрузить актуальные настройки либо явно
применить черновик к новой revision. Смена tenant/session отменяет запросы и
очищает черновики. Создание автоматически не повторяется при неоднозначном ответе.

## Запуск и проверка

Перед запуском передать одинаковый постоянный Fernet-ключ API и worker через
общий `ENCRYPTION__KEY` либо `ENCRYPTION__KEY_PATH`. Channels и Control Plane
используют [Cipher из Shared](shared-encryption.md). Прежние имена настроек
поддерживаются как совместимые входы единого конфига. Ключ не генерируется при старте; его потеря
делает сохранённые credentials нечитаемыми. Отсутствие ключа не блокирует соседние
модули; операции Channels, которым нужен ключ, недоступны. Невалидный заданный
ключ отклоняется конфигурацией.

Применить tenant-миграции существующим способом и запустить `jobs worker`.
Рабочая база автоматически при разработке этого среза не мигрируется.

Автоматические проверки:

```sh
python -m unittest test.test_channels test.test_module_registration
TEST_POSTGRES_URL=postgresql+asyncpg://… python -m unittest test.test_channels_postgres
cd frontends
npm run lint:console
npm run typecheck:console
npm run build:console
```

PostgreSQL-тесты требуют отдельную disposable БД. Fixtures синтетические, по
официальным формам ответов; см. `test/fixtures/channels/README.md`. Проверка реальных
магазинов не входит в приёмку этого среза и остаётся отдельным live smoke этапом.
