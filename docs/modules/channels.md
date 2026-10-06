# Channels

Первый срез управляет настройками подключений через Console и HTTP API.
Проверка доступа, синхронизация и связь с Catalog пока не выполняются.

## Модель

`ChannelKind` — конечная платформа (`prom`, `woocommerce`, `shopify`, …).
`ChannelType` — категория платформы: `marketplace`, `cms`, `shop`; она выводится
из реестра по kind и не дублируется в tenant-таблице. Отдельного ConnectionType нет.

Channel — единственный Aggregate Root модуля. Слои размещены непосредственно
в `channels/domain`, `application`, `infrastructure`, `presentation`.
Агрегат неизменяем: его методы возвращают новое проверенное состояние.
Он хранит название, kind, версию конфигурации, настройки, активность, статус и audit.
Domain получает только запечатанные credentials; открытые ключи существуют
в Application при проверке и объединении настроек. Секреты не входят в repr.

- `is_active` управляется пользователем, по умолчанию `true`.
- `status`: `unverified`, `connected`, `error`; новый канал — `unverified`.
- Изменение настроек сбрасывает проверку. Идентичная запись, переименование
  и переключение активности её не меняют.
- Kind нельзя менять: для другой платформы создаётся новый канал.
- Выключенный канал можно редактировать и удалить.

## Реестр и форма

Реестр находится в `infrastructure/definitions/registry.py`, выдаёт копии определений
и включает 21 платформу из плана, кроме Facebook Leads и TikTok Leads.
Сохранение доступно для Prom и WooCommerce. Остальные записи имеют причину
недоступности и `config.connection: null`.

Определение содержит kind, type, label, can_configure, unavailable_reason,
config_version и config. В `config.connection` находятся JSON Schema Draft 2020-12
и ui_schema (упорядоченные property/widget/help_text). `config.capabilities` пока
пустой; отсутствующая возможность недоступна. Схемы не редактируются через API.

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

Tenant-миграция `0013_channels` следует за `0012_catalog`. Таблица channels
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
- `/channels/:channelId` — настройки, замена ключей, активность и удаление.

Сохранённые секреты представлены текстом «Ключ задан». Действие «Заменить»
включает ввод нового значения; без этого секрет не отправляется. Изменение платформы
сбрасывает параметры. Неизвестная структура схемы блокирует сохранение.

Credentials не сохраняются в web storage или query/mutation cache; запросы записи
не используют mutation cache, ошибки Axios очищаются от тела запроса. Query keys
изолированы по tenant, смена tenant очищает форму и отменяет текущий запрос.
При 409 пользователь явно обновляет схему; автоматической повторной отправки нет.
Проверка доступа и запуск синхронизации пока не отображаются как действия.

## Проверки

```sh
.venv/bin/python -m unittest test.test_channels test.test_channels_http -q
TEST_POSTGRES_URL='<disposable PostgreSQL URL>' .venv/bin/python -m unittest test.test_channels_postgres -q
npm --prefix frontends run typecheck:console
npm --prefix frontends run lint:console
npm --prefix frontends run build:console
```

PostgreSQL-тесты создают отдельные временные tenant-схемы, проверяют миграцию,
шифрование, изоляцию, rollback, конкурентное объединение PATCH и удаление.
