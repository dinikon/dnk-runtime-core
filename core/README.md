# DNK Core

Самостоятельный Django-каркас будущего сервиса управления тенантами.
У приложения свои зависимости и виртуальное окружение. PostgreSQL и база общие
с runtime; таблицы Django находятся в отдельной схеме `core`.

Сейчас доступны стандартные Django-приложения и `/admin/`. Библиотеки
`django-allauth[socialaccount]` и Django OAuth Toolkit установлены как зависимости,
но не подключены к приложениям, middleware или маршрутам. Google login, глобальные
учетные записи клиентов, Tenant, Membership, OIDC, DNS и отправка писем пока
не реализованы. Их устройство и порядок реализации описаны в
[ARCHITECTURE.md](ARCHITECTURE.md).

## Структура

```text
core/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
├── Dockerfile
├── .dockerignore
├── README.md
├── ARCHITECTURE.md
├── tests/
│   └── test_database_schema.py
└── src/
    ├── manage.py
    ├── prepare_database.py
    └── dnk_core/
        ├── __init__.py
        ├── settings.py
        ├── urls.py
        ├── asgi.py
        └── wsgi.py
```

## Локальный стенд в Docker Compose

В корневом [docker-compose.yml](../docker-compose.yml) сервис `core` подключается
к существующему сервису `postgres`. Django входит в общий локальный запуск
`docker compose up`; отдельный профиль не требуется.
Для него нужен Docker Compose версии 2.24 или новее.

Команды этого раздела выполняются из корня репозитория. Корневой Compose также
использует файл `.env` для runtime: если его еще нет, выполните
`cp temaplate.env .env`. Запущенные сервисы runtime для Core не требуются.
Если `core/.env` еще нет, создайте его из примера, затем соберите образ:

```sh
cp core/.env.example core/.env
docker compose build core
```

Сгенерировать ключ можно непосредственно в образе, без локальной установки Python:

```sh
docker compose run --rm --no-deps core \
  python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Запишите результат в `CORE_SECRET_KEY` в `core/.env`. Остальные параметры базы
из этого файла для Compose менять не нужно: Compose направляет Django на
`postgres:5432` и берет имя базы, пользователя и пароль из корневых
`DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, как и runtime. По умолчанию это база
`dniko` и пользователь `postgres`. Для Django задается `search_path=core`
без `public`, включая таблицу истории миграций `core.django_migrations`.

Запустить весь локальный стенд одной командой, затем создать администратора:

```sh
docker compose up --build -d
docker compose exec core python src/manage.py createsuperuser
```

При запуске Compose дожидается PostgreSQL, выполняет `prepare_database.py`
(`CREATE SCHEMA IF NOT EXISTS core`), применяет стандартные миграции и запускает
Django. Это работает и на существующем PostgreSQL volume: подготовка схемы
не зависит от init-скриптов первого запуска пустой базы.
Админка доступна на [127.0.0.1:8001/admin/](http://127.0.0.1:8001/admin/).
Порт публикуется только на loopback; `CORE_PORT` в окружении Compose или корневом
`.env` позволяет выбрать другой порт. Используются общие сеть Compose и volume
`postgres_data`; отдельные PostgreSQL, volume и сеть для Core не создаются.

Чтобы запустить только Django и его зависимость `postgres`, используйте
`docker compose up --build -d --wait core`.
Настройка runtime описана в [основном README](../README.md#development).
Файл `core/.env` необязателен при разборе конфигурации Compose;
сам Django без `CORE_SECRET_KEY` завершится с понятной ошибкой.

Проверить и остановить только Django:

```sh
docker compose exec core python src/manage.py check
docker compose logs -f core
docker compose stop core
```

Общий PostgreSQL продолжает работать для runtime. Локальный стенд использует Django `runserver`
с локальным HTTP и `CORE_DEBUG=true`. Код копируется в образ, поэтому после его
изменения повторите команду запуска с `--build`. Образ работает от пользователя
`core`, зависимости устанавливаются из lock-файла; `.env`, локальное окружение
и файлы runtime не входят в контекст сборки Core.

При прямом использовании [Dockerfile](Dockerfile) подготовку схемы и миграции
нужно выполнить отдельно: автоматические шаги находятся в команде Compose. Продакшен-запуск и
публичный staging требуют отдельной конфигурации сервера, HTTPS и static files.

## Установка без Docker

Нужны `uv`, Python `3.13.9` и PostgreSQL `16`. Команды следующих разделов выполняются
из каталога `core/`; это отдельный uv-проект, не участник общего uv workspace.
Окружение создается в `core/.venv`.

```sh
cd core
uv sync --frozen
cp .env.example .env
uv run --frozen python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Запишите выведенный ключ в `CORE_SECRET_KEY` в `.env`. Этот ключ нужен только Core.
Секреты не коммитятся. Настройки не ищут `.env` самостоятельно: файл передается
явно через `uv run --env-file .env`. Общий `.env` runtime не используется.

## Общая база и схема core

Для запуска без Docker заполните `CORE_DB_*` в `core/.env` значениями существующей
базы runtime: `CORE_DB_NAME` соответствует `DB_DATABASE`, `CORE_DB_USER` —
`DB_USERNAME`, пароль — `DB_PASSWORD`. Укажите адрес и опубликованный порт
PostgreSQL, доступные с хоста. Создавать еще одну базу не нужно.

Перед первыми миграциями выполните `prepare_database.py`, как в командах ниже.
Роль подключения должна иметь право создать схему в этой базе либо уже иметь
доступ к заранее подготовленной схеме `core`. Повтор подготовки сохраняет ее
таблицы и данные. `search_path` задается только соединениям Django; настройки
базы, роли PostgreSQL и соединений runtime не меняются.

Все Django-таблицы, индексы, sequences и история миграций относятся к `core`.
Если схема еще не создана, миграции завершаются ошибкой, а не создают таблицы
в `public`. Общая роль локального стенда обеспечивает разделение имен таблиц;
раздельные права сервисов при необходимости настраиваются отдельными ролями.

| Переменная | Назначение / значение по умолчанию |
| --- | --- |
| `CORE_SECRET_KEY` | Обязательный ключ Django; запуск без него завершается ошибкой |
| `CORE_DEBUG` | По умолчанию `false`; `true`, `1`, `yes` включают debug |
| `CORE_ALLOWED_HOSTS` | Разделенные запятыми хосты; `localhost,127.0.0.1,[::1]` |
| `CORE_DB_NAME` | Существующая общая база; `dniko` |
| `CORE_DB_USER` | Пользователь общей базы; `postgres` |
| `CORE_DB_PASSWORD` | Пароль роли; по умолчанию пустой, заполнить для подключения |
| `CORE_DB_HOST` | `127.0.0.1` |
| `CORE_DB_PORT` | `5432` |

## Проверка и запуск

```sh
uv run --frozen --env-file .env python src/manage.py check
uv run --frozen --env-file .env python src/prepare_database.py
uv run --frozen --env-file .env python src/manage.py migrate
uv run --frozen --env-file .env python src/manage.py createsuperuser
uv run --frozen --env-file .env python src/manage.py runserver 127.0.0.1:8001
```

Откройте [Django admin](http://127.0.0.1:8001/admin/).
Пустой корневой маршрут `/` не является API или страницей продукта.
Стандартный пользователь Django admin служит для проверки каркаса; это еще
не глобальная учетная запись клиента.

Миграции этого каркаса предназначены для схемы `core` на стенде разработки. До появления
постоянных клиентских данных нужно определить собственную модель пользователя
и `AUTH_USER_MODEL`, как описано в [плане реализации](ARCHITECTURE.md#порядок-реализации).
На том этапе пересоздание временных данных каркаса ограничивается схемой `core`;
общая база и схемы runtime сохраняются. Перенос постоянных пользователей
с `auth.User` в каркас не закладывается.

Для локального HTTP в `.env.example` включен `CORE_DEBUG=true`. При выключенном
debug cookies требуют HTTPS. Имена cookies Core отличаются от стандартных,
чтобы локальные приложения на одном хосте и разных портах не перезаписывали их.
Настройки не доверяют заголовкам reverse proxy автоматически.

ASGI/WSGI entrypoints: `dnk_core.asgi:application` и `dnk_core.wsgi:application`.
При внешнем запуске добавьте `core/src` в путь импорта Python, например работайте
из этого каталога, и передайте переменные окружения отдельно. Продакшен-сервер,
TLS, reverse proxy и настройка отдачи `staticfiles/` в каркас не включены.

## Проверки каркаса

- `uv sync --frozen` устанавливает зависимости только из собственного lock-файла.
- `check` проверяет конфигурацию, `migrate --check` — отсутствие непримененных миграций.
- На одноразовой PostgreSQL-базе миграции проверяются при уже существующих
  таблицах в `public` и tenant-схеме: таблицы Django создаются только в `core`.
- Повтор подготовки схемы/миграций сохраняет данные и настройки других соединений.
- `/admin/` перенаправляет на стандартный login, `/admin/login/` открывается.
- ASGI/WSGI загружаются из `src`, импортов FastAPI runtime нет.
- `/accounts/` и tenant OIDC маршруты не зарегистрированы.

Проверка разделения схем запускается на PostgreSQL с правом `CREATEDB`:

```sh
TEST_CORE_POSTGRES_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres \
  uv run --frozen python -m unittest discover -s tests -v
```

Укажите параметры своего тестового сервера. Тест создает отдельную базу со
случайным именем и удаляет только ее после проверки. Проверяются отсутствие
fallback в `public`, сохранение существующих одноименных таблиц и истории
миграций, повторный запуск подготовки и неизменность чужого `search_path`.
Без `TEST_CORE_POSTGRES_URL` интеграционный тест пропускается.

Существующий runtime остается отдельным приложением:
[корневой README](../README.md).
