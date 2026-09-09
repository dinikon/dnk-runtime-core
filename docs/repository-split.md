# Переход на два репозитория

Исходное состояние: runtime `9bd217c23630e69ffaef9ce3749205755e0dfb34`,
control-plane scaffold `ebcfd913ddde22c435bb994f2186874e388e9cb2`.
[Инвентаризация](repository-split.json) фиксирует исходные пути и SHA-256 переносимых файлов.

Control Plane владеет Django, Core Nuxt, `@dnk/ui`, своим deployment и umbrella chart.
Runtime владеет FastAPI, Console/Shortlink, tenant migrations, workers и своим chart.
Исходники и lockfiles репозиториев независимы; установленные зависимости и результаты
сборки не переносятся. Python остаётся 3.13.9. `accounts`, `dnk_core`, `CORE_*`,
схема `core`, история миграций и HTTP-контракты сохраняются.

## Существующий локальный стенд

Перед переключением сохраните действующую локальную конфигурацию Core вне Git.
В новый `.env` перенесите эффективные параметры старого Compose: ранее он брал
БД из runtime `DB_*`, Redis password из `REDIS_PASSWORD`, поверх `core/.env`.
Сохраните постоянные Django/MFA keys и provider credentials. Новые имена подключения:
`CORE_DB_NAME`, `CORE_DB_USER`, `CORE_DB_PASSWORD`, `CORE_DB_HOST=postgres`,
`CORE_DB_PORT=5432`, `CORE_REDIS_HOST=redis`, `CORE_REDIS_PORT=6379`,
`CORE_REDIS_PASSWORD`, `CORE_REDIS_DB=1`.

Перед остановкой сохраните прежние образы под отдельными rollback-тегами:

```sh
docker image tag "$(docker inspect --format '{{.Image}}' dnk-runtime-core-core-1)" dnk-core:before-split
docker image tag "$(docker inspect --format '{{.Image}}' dnk-runtime-core-core-web-1)" dnk-core-web:before-split
docker image tag "$(docker inspect --format '{{.Image}}' dnk-runtime-core-core-frontend-1)" dnk-core-frontend:before-split
```

Имена контейнеров здесь соответствуют исходному project `dnk-runtime-core`.
В корне runtime восстановите прежний Compose только для остановки старых Core-сервисов:

```sh
git show 9bd217c23630e69ffaef9ce3749205755e0dfb34:docker-compose.yml > /tmp/dnk-before-split.compose.yml
docker compose --project-directory "$PWD" -p dnk-runtime-core -f /tmp/dnk-before-split.compose.yml stop core core-web core-frontend
docker compose --project-directory "$PWD" -p dnk-runtime-core -f /tmp/dnk-before-split.compose.yml rm -f core core-web core-frontend
docker compose -p dnk-runtime-core up -d --wait postgres redis
```

Если исходный project назывался иначе, используйте его фактическое имя во всех
командах и задайте `RUNTIME_DOCKER_NETWORK` соответственно. Не выполняйте `down -v`:
сеть, volumes и существующие данные остаются у runtime.

В control-plane, после подготовки `.env`:

```sh
docker compose up -d --build --wait core-frontend
```

Проверьте публичную главную, `/api/session/`, вход, профиль и Console runtime.
Не запускайте старые и новые Core-контейнеры одновременно: их DNS aliases одинаковы.
Для возврата сначала выполните `docker compose down` в control-plane без удаления
данных. В корне runtime создайте rollback override:

```yaml
services:
  core:
    image: dnk-core:before-split
    env_file:
      - path: ${CONTROL_PLANE_ENV_FILE:?Absolute path to preserved control-plane .env}
        required: true
  core-web:
    image: dnk-core-web:before-split
  core-frontend:
    image: dnk-core-frontend:before-split
```

Сохраните его как `/tmp/dnk-rollback.compose.yml`, задайте `CONTROL_PLANE_ENV_FILE`
абсолютным путём к сохранённому `.env` control-plane и запустите:

```sh
docker compose --project-directory "$PWD" -p dnk-runtime-core -f /tmp/dnk-before-split.compose.yml -f /tmp/dnk-rollback.compose.yml up -d --no-build core-frontend
```

Это использует сохранённые образы и конфигурацию даже после удаления исходного каталога Core. Изменения схем для разделения
не требуются; `--reset-scaffold` к этому переходу не относится.

## Helm и ArgoCD

Порядок обновления: неизменённая common 0.3.0 → runtime chart 0.3.1 → umbrella
с зафиксированным runtime `.tgz`. Исходниками common владеет control-plane;
runtime получает библиотеку архивом. Проверяйте версии, контрольные суммы и
совпадение общей библиотеки, используя инструкции `helm/README.md` каждого репозитория.
Архив зависимости обновляется отдельным изменением; обычная сборка его не обновляет.

Control-plane и platform ArgoCD Applications читают control-plane repo, runtime
Application — runtime repo. Для действующей установки сохраняйте release name,
namespace, values, Secret references и PVC; меняются только repo/path и закреплённые
версии. Не устанавливайте standalone charts поверх ресурсов umbrella и наоборот.

До обновления сохраните текущие ArgoCD source/revision и image/chart versions.
После проверки пакетов и публикации нужных образов переключайте источник deployment.
Откат возвращает эти значения. Публикация и переключение действующего Kubernetes-кластера
не выполняются автоматически при разделении исходников.

## Проверки

Каждый репозиторий проверяет свой backend, frontend, Docker build и самостоятельный
chart. Control-plane дополнительно проверяет umbrella и ArgoCD с runtime-образами,
закреплёнными по digest; для приватных GHCR-пакетов CI нужен доступ на чтение.
Локальные browser-тесты используют отдельный Compose project `dnk-control-plane-e2e`
с собственными PostgreSQL, Redis и сетью. Они не должны использовать общую dev-БД.
