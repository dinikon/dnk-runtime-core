# dNiko Alpha Core

Отдельное Django-приложение с глобальными аккаунтами и Nuxt/Vue-интерфейсом.
Главная страница рендерится на сервере для поисковых систем. Защищённая часть
использует серверную сессию Django, без JWT или токенов в браузерном хранилище.

| Маршрут | Ответственность |
| --- | --- |
| `/` | Публичная главная Nuxt: Hero, SEO title/description, canonical и Open Graph |
| `/app/` | Защищённый обзор текущего пользователя, исключённый из индексации |
| `/api/session/` | GET: `{authenticated, csrfToken}`, доступен гостям |
| `/api/me/` | GET: `{id, username, email, first_name, last_name}`; гостям JSON 401 |
| `/accounts/` | Django: аккаунт, способы входа, MFA и управление сессиями |
| `/admin/` | Django admin; вход проходит через allauth |

Core использует схему `core` в существующей PostgreSQL-базе. Runtime продолжает
работать отдельно со своими tenant-пользователями и консолью. Tenant registry,
Membership, OIDC, DNS и provisioning описаны как будущая работа в
[ARCHITECTURE.md](ARCHITECTURE.md).

## Локальный стенд в Docker Compose

Нужны Docker Compose 2.24+ и корневой `.env` runtime. Из корня репозитория:

```sh
cp core/.env.example core/.env
```

Заполните `CORE_SECRET_KEY` случайным постоянным значением. Для генерации после
локального `uv sync` можно использовать:

```sh
cd core
uv run --frozen python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Затем из корня репозитория:

```sh
docker compose build core core-web core-frontend
```

Если старый каркас уже мигрировал `auth.User`, сначала выполните переход из
следующего раздела. Для новой схемы этот шаг не нужен.

```sh
docker compose up --build -d core-frontend
docker compose exec core python src/manage.py createsuperuser
```

Откройте [dNiko Alpha](http://localhost:8080/).
`core-frontend` — Nginx с единым origin, `core-web` — сервер Nuxt/Nitro,
`core` — Django/Gunicorn. Существующий frontend runtime сохраняет свой порт.
`CORE_FRONTEND_PORT` в корневом окружении Compose меняет порт 8080.

Compose использует уже существующие PostgreSQL и Redis. Он передаёт Core
корневые `DB_*` и `REDIS_PASSWORD`, поэтому параметры подключения из `core/.env`
не должны задавать другую базу при запуске без Docker. Миграции и подготовка
схемы выполняются в локальной команде запуска; удаления данных при старте нет.

Письма в режиме разработки выводятся в `docker compose logs core`. Для входа
созданного администратора тоже требуется подтвердить email. Телефонный вход,
Google и GitHub появляются после настройки их ключей. Интерфейс passkeys нужно
открывать через `localhost`, а не IP-адрес: локальный HTTP origin localhost
разрешён проверкой WebAuthn без отключения безопасности.

## Переход с временного каркаса

Ранний каркас использовал `auth.User`. Просто поменять `AUTH_USER_MODEL` поверх
его истории миграций нельзя. Согласованный переход удаляет только временную
схему `core`; общая база, `public` и tenant-схемы сохраняются.

Команда ниже предназначена только для прежнего каркаса, данные которого
не требуется переносить. Она требует `CORE_DEBUG=true` и отказывается работать,
если найдёт таблицы сверх стандартного каркаса, включая новый `accounts_user`.

```sh
docker compose stop core
docker compose run --rm --no-deps core python src/prepare_database.py --reset-scaffold
docker compose up -d core-frontend
```

Обычный `prepare_database.py` только создаёт отсутствующую схему.
Новая `accounts.User(AbstractUser)` с UUID находится в начальной миграции,
а все связи allauth/admin используют `AUTH_USER_MODEL`. Django подключается
с `search_path=core` без fallback в `public`.

## Разработка без Docker

Core — отдельный uv-проект. Нужны Python 3.13.9, PostgreSQL 16 и Redis.

```sh
cd core
uv sync --frozen
uv run --frozen --env-file .env python src/prepare_database.py
uv run --frozen --env-file .env python src/manage.py migrate
uv run --frozen --env-file .env python src/manage.py runserver 127.0.0.1:8001
```

Настройки не ищут `.env` автоматически: передавайте его явно.
Заполните `CORE_DB_*` и `CORE_REDIS_*` для существующих сервисов.
Для изолированной разработки без Redis удалите `CORE_REDIS_HOST`/`CORE_REDIS_URL`:
при `CORE_DEBUG=true` используется локальный cache одного процесса.

В другом терминале из `frontends/`:

```sh
npm ci
npm run dev:core
```

Откройте `http://localhost:5174`. Nuxt проксирует Django-маршруты с сохранением
Host, поэтому формы allauth и API используют тот же origin. Общие CSS-токены
и локальные Inter-шрифты находятся в Django static `/static/core/`.

## Вход и безопасность

- Email/username с паролем, обязательное подтверждение email кодом,
  восстановление и смена пароля, вход по email-коду.
- Google/GitHub: привязка к уже авторизованному аккаунту; совпадение email
  не объединяет пользователей автоматически. OAuth начинается через POST с CSRF.
- Необязательный уникальный телефон в E.164. Telegram Gateway отправляет
  шестизначный код в **Telegram, не SMS**. Код действует 5 минут, допускает
  3 попытки; лимиты отправки и повторов обеспечивает allauth через cache.
- MFA добровольна для всех: TOTP, passkeys и резервные коды. Включённая MFA
  проверяется после остальных способов входа. Создание passkey и вход без пароля
  требуют проверки владельца (PIN/биометрия) на стороне сервера.
- Чувствительные изменения требуют свежего подтверждения. Аккаунты без локального
  пароля и MFA подтверждают действие email-кодом; срок 5 минут, 3 попытки,
  новый запрос не чаще раза в 30 секунд и не более 5 в час.
- Все новые WebAuthn-ключи Core — discoverable passkeys. Регистрации нового
  аккаунта только через passkey нет; ключ добавляется в существующем аккаунте.
- Резервные коды одноразовые и показываются один раз. Секреты MFA шифруются Fernet.
  Сохраняйте `CORE_MFA_ENCRYPTION_KEY` вместе с резервной копией базы:
  произвольная замена ключа сделает существующие MFA-секреты недоступными.
- Список устройств поддерживает выход из остальных сессий и завершение выбранной.
  Чужую сессию завершить нельзя; завершение текущей возвращает на главную.

Cookies `dnk_core_sessionid` и `dnk_core_csrftoken` имеют HttpOnly и SameSite=Lax;
в production также Secure. Cookie domain не расширяется на поддомены.
Vue получает CSRF-токен через `/api/session/` и передаёт его в `X-CSRFToken`
для изменяющих запросов. API и приватные страницы не кэшируются публично.

## Настройка провайдеров

Секреты задаются окружением, не Django admin и не frontend-конфигурацией.

| Переменные | Назначение |
| --- | --- |
| `CORE_GOOGLE_CLIENT_ID`, `CORE_GOOGLE_CLIENT_SECRET` | Google OAuth, scopes profile/email |
| `CORE_GITHUB_CLIENT_ID`, `CORE_GITHUB_CLIENT_SECRET` | GitHub OAuth, scope user:email |
| `CORE_TELEGRAM_GATEWAY_TOKEN` | Включает доставку кодов через Gateway |
| `CORE_TELEGRAM_GATEWAY_ENABLED=false` | Явно отключает телефонный вход при наличии токена |
| `CORE_TELEGRAM_GATEWAY_TIMEOUT` | Таймаут запроса, по умолчанию 5 секунд |
| `CORE_EMAIL_BACKEND` | Явно выбирает backend; без переменной — SMTP в production, console в debug |
| `CORE_EMAIL_HOST`, `CORE_EMAIL_PORT` | SMTP сервер и порт |
| `CORE_EMAIL_HOST_USER`, `CORE_EMAIL_HOST_PASSWORD` | SMTP credentials |
| `CORE_EMAIL_USE_TLS`, `CORE_EMAIL_USE_SSL` | Выберите TLS или SSL согласно SMTP-провайдеру |
| `CORE_EMAIL_VERIFY_CERTIFICATE` | Проверка сертификата в `accounts.mail.SMTPEmailBackend`; по умолчанию true |
| `CORE_DEFAULT_FROM_EMAIL` | Подтверждённый у почтового провайдера адрес отправителя |

Для реальной отправки, включая локальный стенд, задайте
`CORE_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`.
Значение `console.EmailBackend` из примера только выводит письма в логи,
даже если SMTP-хост, логин и пароль заполнены.
Для порта 465 обычно нужны `CORE_EMAIL_USE_SSL=true` и `CORE_EMAIL_USE_TLS=false`;
для STARTTLS на порту 587 — наоборот. Одновременно включать их нельзя.
Адрес `CORE_DEFAULT_FROM_EMAIL` должен совпадать с почтовым ящиком либо быть
разрешённым у провайдера адресом отправителя.
После изменения `core/.env` примените настройки:

```sh
docker compose up -d --no-deps --force-recreate core
```

Обычный `docker compose restart` не перечитывает окружение контейнера.
Если подключение возвращает `CERTIFICATE_VERIFY_FAILED`, проверьте сертификат
именно SMTP-службы: он должен включать имя из `CORE_EMAIL_HOST`, а сервер должен
передавать полную цепочку с промежуточными сертификатами (`fullchain.pem`).
Сертификат только для основного домена не покрывает его почтовый поддомен.

Для локальной совместимости с прежним SMTP-клиентом runtime доступен отдельный
backend. Он поддерживает шифрование без проверки сертификата сервера:

```dotenv
CORE_EMAIL_BACKEND=accounts.mail.SMTPEmailBackend
CORE_EMAIL_PORT=587
CORE_EMAIL_USE_TLS=true
CORE_EMAIL_USE_SSL=false
CORE_EMAIL_VERIFY_CERTIFICATE=false
```

Этот режим разрешён только при `CORE_DEBUG=true`. TLS обязателен: при отказе
STARTTLS соединение прерывается до авторизации, перехода к незашифрованной
отправке нет. Без проверки сертификата клиент не удостоверяет подлинность
сервера, поэтому в production значение false запрещено. После исправления
сертификата верните `CORE_EMAIL_VERIFY_CERTIFICATE=true`.
В runtime `USE_TLS=true` обозначает implicit TLS (обычно порт 465), что
соответствует `CORE_EMAIL_USE_SSL=true`; его `USE_STARTTLS=true` соответствует
`CORE_EMAIL_USE_TLS=true` (обычно порт 587).

Зарегистрируйте точные redirect URI для публичного origin:
`https://example.com/accounts/google/login/callback/` и
`https://example.com/accounts/github/login/callback/`.
Для локального OAuth используйте соответствующий callback на `http://localhost:8080`.

Код генерирует и проверяет allauth; Gateway занимается только доставкой.
Проверка `checkSendAbility` и SMS fallback не используются. Для неизвестных
аккаунтов не отправляются платные фиктивные коды. Ошибки провайдера логируются
без номера, кода, токена или полного ответа. Не повторяем автоматически платный
запрос после сетевого таймаута: результат доставки мог оказаться неопределённым.

Первичные справочники: [allauth](https://docs.allauth.org/en/latest/),
[Telegram Gateway](https://core.telegram.org/gateway/api),
[Nuxt deployment](https://nuxt.com/docs/4.x/getting-started/deployment).

## Production и HTTPS

`core/Dockerfile` собирает static files и запускает Gunicorn. Dockerfile frontend
имеет target `runtime` для Nuxt и `gateway` для Nginx. Django и Nuxt должны быть
доступны только через доверенный reverse proxy; наружу публикуется gateway.
Production-миграции выполняйте отдельным шагом перед запуском Gunicorn.

Минимальная конфигурация окружения:

- `CORE_DEBUG=false`, случайный `CORE_SECRET_KEY` и отдельный
  `CORE_MFA_ENCRYPTION_KEY` (`Fernet.generate_key()`).
- `CORE_PUBLIC_ORIGIN=https://example.com`, `CORE_ALLOWED_HOSTS=example.com`,
  `NUXT_PUBLIC_SITE_URL=https://example.com`.
- `CORE_TRUST_PROXY=true` только за proxy, который заменяет входящие forwarded headers.
- `CORE_TRUSTED_PROXY_COUNT=1` для одного такого gateway; при прямом доступе — 0.
- `CORE_DB_*` для общей PostgreSQL-базы и `CORE_REDIS_HOST/PORT/PASSWORD/DB`
  либо `CORE_REDIS_URL` для общего cache с префиксом `dnk:core`.
- Рабочие SMTP-настройки и адрес отправителя. Удалите development console backend.

[deploy/nginx.https.conf.template](deploy/nginx.https.conf.template) содержит
готовую маршрутизацию HTTPS и HTTP → HTTPS. В контейнере gateway смонтируйте
его как `/etc/nginx/templates/default.conf.template`, задайте `CORE_DOMAIN`,
а сертификаты смонтируйте read-only в `/etc/nginx/tls/fullchain.pem` и
`/etc/nginx/tls/privkey.pem`. Имена внутренних upstream: `core:8001` и `core-web:3000`.
На общей машине существующий runtime gateway и Core должны иметь согласованные
виртуальные хосты/адреса; локальный Compose намеренно сохраняет прежний порт runtime.

HSTS включается для origin Core без распространения на поддомены.
Не включайте `MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN`: это отключает проверку origin.
При смене публичного домена пользователям потребуется заново добавить passkeys.

## Проверки

Из `core/`:

```sh
uv sync --frozen
PYTHONPATH=src:. uv run --frozen python src/manage.py test tests --settings=tests.settings
```

Быстрые сценарии используют отдельную SQLite in-memory базу, локальную почту,
cache и тестовые ответы провайдеров. WebAuthn-проверки используют подписанные
запросы виртуального аутентификатора, включая отрицательные проверки UV,
challenge, origin, подписи и повторного использования.

PostgreSQL-тест создаёт новую временную базу и удаляет только её. Роли тестового
сервера нужно право CREATEDB:

```sh
TEST_CORE_POSTGRES_URL=postgresql://user:password@localhost:5432/postgres \
  uv run --frozen python -m unittest tests.test_database_schema -v
```

Frontend: `npm run lint:core`, `npm run typecheck:core`, `npm run build:core`.
На запущенном локальном Compose-стенде из `frontends/`:

```sh
npm --workspace @dnk/core exec -- playwright install chromium
npm run test:e2e:core
```

Браузерный тест использует Chromium с виртуальным WebAuthn-аутентификатором:
добавление passkey, вход с проверкой владельца, отказ без UV, отмена и повтор
после сетевой ошибки. Он создаёт отдельную явно помеченную тестовую учётную
запись и удаляет её вместе с её сессиями; production-окружение не допускается.

Дополнительно проверяйте HTML главной без JavaScript, SEO-метаданные, desktop/mobile,
переход на allauth с `next` и возвращение в защищённую часть. Живые OAuth и доставка
писем/Telegram требуют настоящих настроек и не подменяются результатами mock-тестов.

CI запускает runtime, Core с PostgreSQL-проверкой изоляции, сборку Nuxt и браузерный
сценарий на отдельном Compose-стенде.
