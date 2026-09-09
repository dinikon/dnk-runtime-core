# dNiko Alpha Core

Отдельное Django-приложение с глобальными аккаунтами и Nuxt/Vue-интерфейсом.
Главная страница рендерится на сервере для поисковых систем. Защищённая часть
использует серверную сессию Django, без JWT или токенов в браузерном хранилище.

| Маршрут | Ответственность |
| --- | --- |
| `/` | Публичная главная Nuxt: Hero, SEO title/description, canonical и Open Graph |
| `/app/` | Защищённый обзор текущего пользователя, исключённый из индексации |
| `/api/session/` | GET: `{authenticated, csrfToken, showAdminLink}`, доступен гостям |
| `/api/capabilities/` | GET: доступные способы входа и регистрации, без секретов |
| `/api/me/` | GET: `{id, username, email, first_name, last_name, middle_name, display_name, initials}`; гостям JSON 401 |
| `/accounts/` | Django: аккаунт, способы входа, MFA и управление сессиями |
| `/accounts/profile/` | Просмотр и изменение собственного ФИО через форму Django |
| `/admin/` | Django admin; вход проходит через allauth |

Core использует схему `core` в существующей PostgreSQL-базе. Runtime продолжает
работать отдельно со своими tenant-пользователями и консолью. Tenant registry,
Membership, OIDC, DNS и provisioning описаны как будущая работа в
[ARCHITECTURE.md](ARCHITECTURE.md).

Для Kubernetes используйте [Helm-пакет Core](../deploy/helm/README.md): Django,
Nuxt и gateway с независимым выбором встроенных или внешних PostgreSQL/Redis.
Инструкция включает подготовку Secrets, миграции, установку и обновление.

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

С почтовым backend из примера письма выводятся в `docker compose logs core`. Для входа
созданного администратора тоже требуется подтвердить email. Телефонный вход,
Google, GitHub и Telegram Login появляются после настройки их ключей. Интерфейс passkeys нужно
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
uv run --frozen python src/prepare_database.py
uv run --frozen python src/manage.py migrate
uv run --frozen python src/manage.py runserver 127.0.0.1:8001
```

Настройки автоматически читают `core/.env` по абсолютному пути, независимо от
текущей директории. `CORE_ENV_FILE` позволяет выбрать другой файл; пустое
значение отключает чтение файла, например в тестах.
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

## Конфигурация и режимы авторизации

Единая точка загрузки — `src/dnk_core/config.py`, класс `CoreSettings` на
Pydantic Settings. Группы небольших настроек находятся в `configuration/`.
Конфигурация проверяется до подключения к PostgreSQL, Redis и провайдерам.
Ошибки называют настройку и причину, не выводя её значение. Секреты представлены
`SecretStr`; прикладные сервисы используют проекцию `django.conf.settings`.

Приоритет источников, от высшего к низшему:

1. Аргументы `load_config(...)` / `CoreSettings(...)`, предназначенные для тестов.
2. Переменные процесса.
3. Файл `core/.env` либо путь из переменной процесса `CORE_ENV_FILE`.
4. Defaults полей.

`CORE_ENV_FILE=` отключает dotenv. Посторонние переменные, включая `NUXT_*`,
игнорируются. Неизвестные boolean/enum и несовместимые сочетания вызывают ошибку
запуска. Все поддерживаемые переменные с русскими пояснениями собраны в
[.env.example](.env.example). Обязательное подтверждение email, CSRF, безопасные
cookies, HTTPS в production, проверка UV/origin/JWT и запрет автоматического
объединения аккаунтов не являются отключаемыми функциями.

| `CORE_AUTH_PASSWORD_MODE` | Обычная регистрация | Первичный вход | Управление паролем / reauth |
| --- | --- | --- | --- |
| `passwordless` (default) | Без полей пароля | Email-код, passkey, провайдеры | Доступно |
| `optional` | Пароль можно пропустить | Пароль или разрешённый альтернативный способ | Доступно |
| `required` | Пароль обязателен | Пароль или разрешённый альтернативный способ | Доступно |

Для переключения достаточно изменить, например:

```dotenv
CORE_AUTH_PASSWORD_MODE=passwordless
CORE_AUTH_EMAIL_CODE_ENABLED=true
CORE_AUTH_SIGNUP_ENABLED=true
```

`optional` и `passwordless` требуют включённого email-кода. В `passwordless`
основная форма запускает email OTP; отправка непустого пароля на неё возвращает
ошибку без проверки пароля и отправки кода. Существующие хеши не меняются.
Установка, смена, сброс и повторное подтверждение паролем сохраняются;
после сброса пароля автоматический вход отключён.

`CORE_AUTH_SIGNUP_ENABLED=false` закрывает создание новых обычных, социальных
и passkey-аккаунтов. Существующие пользователи продолжают входить, а уже
созданный аккаунт может завершить подтверждение email. Отдельные переключатели
email-кода, passkey-входа, passkey-регистрации, Google/GitHub/Telegram применяются
к интерфейсу и прямым запросам, включая незавершённые сценарии. Для провайдеров
`auto` включает вход при наличии обоих credentials, `false` скрывает и запрещает,
`true` требует корректно заполненных credentials. Telegram Gateway независим.

`CORE_MFA_TOTP_ENROLLMENT_ENABLED=false` и
`CORE_MFA_PASSKEY_ENROLLMENT_ENABLED=false` запрещают добавление новых факторов,
сохраняя проверку и управление ранее подключёнными. Для passkey signup требуется
разрешённое создание ключей; резервные коды остаются частью безопасного сценария.
Удаление способа входа проверяет оставшиеся **разрешённые первичные способы**.
Пароль, доступный только для reauth, не считается запасным первичным входом.

Настройки глобальны для CORE и применяются при старте процесса. Без Docker
перезапустите Django. Compose читает `core/.env` в окружение контейнера и поверх
него задаёт в `environment` параметры сети, БД, Redis, локального origin/Host и
DEBUG. Эти параметры имеют приоритет над `core/.env`. Корневой `.env` служит
Compose/runtime и не загружается `CoreSettings`. После правок файла выполните:

```sh
docker compose up -d --no-deps --force-recreate core
```

При обновлении Python-кода сначала пересоберите образ. Горячей перезагрузки
конфигурации нет; `docker compose restart` не обновляет окружение контейнера.

Nuxt получает безопасный список возможностей через `/api/capabilities/` и
адаптирует действия главной. До ответа остаётся переход на вход; при ошибке
доступен повтор. Сбой этого запроса не завершает сессию. Основной текст главной
продолжает рендериться на сервере.

Ответ capabilities содержит `registrationEnabled`, `passwordLoginEnabled`,
`emailCodeLoginEnabled`, `phoneCodeLoginEnabled`, `phoneLoginMode`, `passkeyLoginEnabled`,
`passkeySignupEnabled` и массив `providers` (`google`, `github`, `telegram` при
доступности). Endpoint доступен гостям, принимает только GET и не кэшируется.

## Вход и безопасность

- По умолчанию вход и обычная регистрация без пароля: email-код, passkey или
  настроенный провайдер. Email подтверждается обязательно. Парольные сценарии
  включаются режимом `CORE_AUTH_PASSWORD_MODE`; управление паролем доступно во всех режимах.
- Google/GitHub: привязка к уже авторизованному аккаунту; совпадение email
  не объединяет пользователей автоматически. OAuth начинается через POST с CSRF.
- Несколько необязательных телефонов в E.164, один подтверждённый основной. Telegram Gateway отправляет
  шестизначный код в **Telegram, не SMS**. По умолчанию код действует 5 минут, допускает
  3 попытки; срок и число попыток задаются через `CORE_AUTH_CODE_*`, лимиты отправки и повторов обеспечивает allauth через cache.
- MFA добровольна для всех: TOTP, passkeys и резервные коды. Включённая MFA
  проверяется после остальных способов входа. Создание passkey и вход без пароля
  требуют проверки владельца (PIN/биометрия) на стороне сервера.
- Чувствительные изменения требуют свежего подтверждения. Аккаунты без локального
  пароля и MFA подтверждают действие email-кодом; срок 5 минут, 3 попытки,
  новый запрос не чаще раза в 30 секунд и не более 5 в час.
- Все новые WebAuthn-ключи Core — discoverable passkeys. Доступна регистрация
  без пароля: ФИО/email → подтверждение email → passkey → резервные коды.
- Резервные коды одноразовые и показываются один раз. Секреты MFA шифруются Fernet.
  Сохраняйте `CORE_MFA_ENCRYPTION_KEY` вместе с резервной копией базы:
  произвольная замена ключа сделает существующие MFA-секреты недоступными.
- Список устройств поддерживает выход из остальных сессий и завершение выбранной.
  Чужую сессию завершить нельзя; завершение текущей возвращает на главную.
- Связанные аккаунты показывают ник, email либо стабильный ID внешнего профиля;
  подписи доступны и для временно выключенных провайдеров.
- Страница резервных кодов без созданных кодов предлагает настройку MFA или
  явное создание кодов для подключённого фактора. Открытие страницы не создаёт коды.
- Сотрудникам (`is_staff`) и суперпользователям (`is_superuser`) в шапке Nuxt
  и Django показывается кнопка Django admin. Признак `showAdminLink` в ответе
  сессии управляет навигацией; доступ к админке проверяет сам Django.

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
| `CORE_TELEGRAM_LOGIN_CLIENT_ID`, `CORE_TELEGRAM_LOGIN_CLIENT_SECRET` | Telegram OIDC, scopes openid/profile; оба значения обязательны |
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

`core/Dockerfile` собирается из корня репозитория: Node собирает Vue-компоненты
для Django, затем Python выполняет collectstatic и запускает Gunicorn. Dockerfile frontend
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

Тестовые настройки отключают чтение `.env` и задают `required` для прежних
сценариев; отдельная матрица проверяет все три режима и переключатели.
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
Перед браузерными тестами включите изолированную почту из корня репозитория:
`docker compose -f docker-compose.yml -f core/deploy/compose.e2e.yml up -d --build --wait core-frontend`.
Затем из `frontends/`:

```sh
npm --workspace @dnk/core exec -- playwright install chromium
npm run test:e2e:core
```

Этот полный прогон использует `required`. Матрица остальных режимов применяет
реальные серверные настройки, а не подмену ответа capabilities. Для каждого
значения `optional` и `passwordless` из корня репозитория:

```sh
export CORE_E2E_AUTH_PASSWORD_MODE=passwordless
docker compose -f docker-compose.yml -f core/deploy/compose.e2e.yml up -d --wait --no-build --no-deps --force-recreate core
cd frontends
npm --workspace @dnk/core exec -- playwright test e2e/auth-modes.spec.ts
```

Тесты проверяют обычный и выключенный JavaScript, email OTP/пароль, обязательность
полей регистрации и сохранение `next`. После матрицы удалите тестовую переменную
из окружения (`unset CORE_E2E_AUTH_PASSWORD_MODE`) и восстановите обычный Compose.

Браузерный тест использует Chromium с виртуальным WebAuthn-аутентификатором:
добавление passkey, вход с проверкой владельца, отказ без UV, отмена и повтор
после сетевой ошибки. Он создаёт отдельную явно помеченную тестовую учётную
запись и отдельного пользователя регистрации с passkey, затем удаляет их вместе с сессиями.
Production и реальная SMTP-доставка в браузерных тестах запрещены. После тестов
восстановите обычную конфигурацию: `docker compose up -d --no-build --no-deps --force-recreate core`.

Дополнительно проверяйте HTML главной без JavaScript, SEO-метаданные, desktop/mobile,
переход на allauth с `next` и возвращение в защищённую часть. Живые OAuth и доставка
писем/Telegram требуют настоящих настроек и не подменяются результатами mock-тестов.

CI запускает runtime, Core с PostgreSQL-проверкой изоляции, сборку Nuxt и браузерный
сценарий на отдельном Compose-стенде.


## Telegram Login и регистрация с passkey

Telegram Login — отдельное действие от «Код в Telegram». В BotFather задайте
публичный origin и точный callback `/accounts/oidc/telegram/login/callback/`,
скопируйте Client ID/Secret в окружение и оставьте RS256. Настройки описаны в
[официальной документации Telegram](https://core.telegram.org/bots/telegram-login).
Приложение использует POST + CSRF, Authorization Code, PKCE S256 и одноразовый
state текущей сессии. Оно не запрашивает номер телефона, доступ боту к переписке
или UserInfo. ID token всегда проверяется по JWKS: подпись RS256, issuer,
audience, срок действия и обязательный subject. Токены не сохраняются в БД.

Новый Telegram-пользователь проверяет ФИО и подтверждает email. Совпавший
email не объединяет аккаунты: сначала войдите в существующий аккаунт и
подключите Telegram через настройки. Отключение требует недавнего подтверждения
личности и оставшегося рабочего способа входа. Сохранённая связь видна и после
выключения провайдера. Подключённая MFA остаётся обязательной.

Регистрация `/accounts/signup/passkey/` создаёт аккаунт без рабочего пароля.
После подтверждения email `/accounts/2fa/webauthn/signup/` требует resident key
и UV; криптографическую проверку выполняют allauth/FIDO2. Резервные коды создаются
штатным механизмом allauth и показываются один раз. «Продолжить» возвращает к
проверенному локальному next или `/app/`. Отмена не входит в аккаунт и не удаляет
его: восстановить незавершённую регистрацию можно входом по подтверждённому email.
Для локальной проверки используйте `http://localhost:8080`.

## Общий интерфейс

Компоненты официального Shadcn Vue (New York, neutral) находятся в
`frontends/packages/ui`. Nuxt импортирует их напрямую, Django подключает отдельную
Vite-сборку через manifest. Inter и семантические CSS-токены находятся в
`accounts/static/core/theme.css`; внешних запросов к Google Fonts нет.

Для запуска без Docker сначала выполните из `frontends/`:

```sh
npm ci
npm run build:accounts
npm run dev:core
```

После изменений общих компонентов пересоберите `build:accounts`; после изменений
шаблонов с новыми Tailwind-классами также нужна пересборка. Сборка создаёт
игнорируемую директорию `core/src/accounts/static/core/ui/`. В Docker она
создаётся автоматически до collectstatic. Миграции или пересоздание схемы
для этого обновления не требуются.

Обычные формы имеют серверный HTML. Vue получает данные через `json_script`,
сохраняет значения/фокус при подключении и отправляет обычные формы Django.
Пароли не попадают в JSON. CSRF, hidden/next и выбранное submit-действие остаются
в форме. WebAuthn и обработчик резервных кодов запускаются после готовности UI.
При недоступном JavaScript обычные формы продолжают работать. Смотрите также
[устройство UI Kit](../frontends/packages/ui/README.md) и
[согласованные макеты](../docs/core-ui/README.md).

### ФИО и внутренний username

По умолчанию `CORE_AUTH_USERNAME_MODE=generated`: на обычной, социальной и passkey-регистрации нужны имя, фамилия и email. Отчество необязательно. ФИО не уникально; одинаковые имена разрешены. Провайдеры заполняют известные имя и фамилию; недостающие данные пользователь вводит при завершении регистрации.

Username создаётся автоматически из UUID нового аккаунта и остаётся уникальным внутренним полем. Вход по email работает во всех режимах пароля; сам пароль зависит от `CORE_AUTH_PASSWORD_MODE`. В интерфейсе и названиях passkeys показываются ФИО/email. API сохраняет `username` для совместимости и дополнительно возвращает отчество, отображаемое имя и инициалы.

`CORE_AUTH_USERNAME_MODE=required` возвращает выбор username при регистрации и вход по email/username, когда разрешён парольный вход. ФИО заполняется и в этом режиме. Настройка читается из `core/.env` с обычным приоритетом переменных процесса; применяется после перезапуска CORE.

Редактирование ФИО доступно в «Мой профиль» (`/accounts/profile/`). Меняются только три поля текущего пользователя, с проверкой CSRF. Существующие username, UUID, пароли и способы входа не переписываются; для старых профилей без имени временно показывается email. Миграция `0002_user_middle_name` только добавляет необязательное отчество и не требует пересоздания схемы.


## Несколько телефонов и UUID

В «Аккаунт и безопасность → Телефоны» (`/accounts/phone/change/`) можно добавить
номера, подтвердить их кодом в Telegram, выбрать основной и удалить ненужные.
Первый подтверждённый номер становится основным автоматически; следующие его
не заменяют. Перед удалением основного при наличии других подтверждённых
сначала выберите новый основной. Последний подтверждённый телефон можно удалить,
если остаётся другой разрешённый первичный способ входа.

| Переменная | Default | Допустимые значения и назначение |
| --- | --- | --- |
| `CORE_AUTH_PHONE_LOGIN_MODE` | `any_verified` | `any_verified`: вход по любому подтверждённому; `primary_only`: только по основному |
| `CORE_AUTH_MAX_PHONE_NUMBERS` | `5` | Положительное целое; общий лимит подтверждённых и неподтверждённых номеров |

Параметры применяются после пересоздания процесса/контейнера. Уменьшение лимита
не удаляет существующие номера. При выключенном Gateway контакты остаются
доступны для просмотра, выбора основного и удаления; добавить или подтвердить
номер и войти по нему нельзя. Telegram OIDC Login настраивается независимо.
Неподтверждённая запись не резервирует номер; одновременно подтвердить его
могут только для одного аккаунта. Незавершённое добавление контакта не мешает
существующему пользователю входить другими способами.

OTP привязан к UUID записи, владельцу и назначению проверки. Удаление и повторное
добавление тех же цифр не восстанавливает старый код. При завершении OTP и MFA
повторно проверяются доступность способа и принадлежность номера.

Все собственные модели CORE наследуют `dnk_core.models.UUIDModel` и используют
UUIDv4. Связи пользователя с группами и разрешениями имеют явные UUID through-модели;
`user.groups`, `user.user_permissions` и проверки разрешений Django сохраняются.
Новые ManyToMany-поля также требуют явной промежуточной модели с UUID.
Django check `core.E001` проверяет собственные приложения, включая автоматически
созданные through-таблицы, и запускается в CI. Штатные модели Django/allauth
сохраняют исходные ключи. `DEFAULT_AUTO_FIELD` не используется для подмены UUID.

Миграция `0003_phone_contacts_uuid_memberships` переносит текущие телефоны,
членство в группах и индивидуальные разрешения. Подтверждённый старый телефон
становится основным; UUID пользователей, пароли, email, MFA и действующие
авторизованные сессии сохраняются. Старые незавершённые телефонные проверки
нужно начать заново. Перезапись базы не требуется; схемы runtime не изменяются.

Обновление локального Docker-окружения:

```sh
docker compose build core core-web
docker compose stop core
docker compose up -d --no-deps --force-recreate --wait core core-web
```

Compose применяет миграции перед запуском Gunicorn. В production остановите
CORE, выполните `python src/manage.py migrate --noinput` с новой сборкой, затем
запустите сервис. `collectstatic` выполняется при сборке Docker-образа.
Обратная миграция отказывается терять данные, если хотя бы у одного пользователя
уже несколько номеров; в таком случае откат выполняйте восстановлением резервной копии.
