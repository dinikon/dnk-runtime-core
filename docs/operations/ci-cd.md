# Поддержка и оптимизация CI/CD

Правила выпуска и восстановления описаны в [плане CI/CD](../plan/ci-cd.md).
Этот документ объясняет устройство кода, диагностику Jobs и принятые оптимизации.

## Структура

| Файл | Ответственность |
| --- | --- |
| `.github/workflows/deploy.yml` | Триггеры, права job, инструменты, запуск публикации и сохранение диагностики |
| `scripts/cicd/__main__.py` | Аргументы команд, настройка логирования и код завершения |
| `scripts/cicd/feature.py` | Публикация образов и Helm из чистой feature-ветки, канал feat |
| `scripts/cicd/image_registry.py` | Проверка образов через Docker Buildx без ORAS |
| `scripts/cicd/chart_registry.py` | Helm OCI и alias feat через HTTP API с авторизацией Docker |
| `scripts/cicd/pipeline.py` | Сценарии develop/main/release, последовательность RC и запись результатов |
| `scripts/cicd/artifacts.py` | Координация: готовые образы → Helm chart |
| `scripts/cicd/images.py` | Docker Bake, кэш, повторное использование образов, восстановление частичных сборок |
| `scripts/cicd/charts.py` | Временная копия Helm chart с закреплёнными версиями образов |
| `scripts/cicd/registry.py` | ORAS, OCI media types и ограниченное ожидание видимости манифестов |
| `scripts/cicd/github.py` | Чтение GitHub Releases через REST и публикация через `gh` |
| `scripts/cicd/aliases.py` | Обновление `dev`/`latest` после повторной проверки remote HEAD |
| `scripts/cicd/repository.py` | Git refs, временные worktrees, метаданные тегов и Commitizen |
| `scripts/cicd/gitops.py` | Release/RC и возобновляемая локальная транзакция stable-выпуска |
| `scripts/cicd/checks.py` | Именованные этапы локальных проверок |
| `scripts/cicd/check_environment.py` | Изолированная копия исходников и временная PostgreSQL |
| `scripts/cicd/observability.py` | Контекст логов, длительности этапов, Actions groups и Job Summary |
| `scripts/cicd/common.py` | Запуск процессов, версии и атомарная запись JSON |
| `scripts/cicd/local_oci.py` | Интеграционная проверка OCI/ArgoCD в отдельном временном Kind |
| `test/cicd/` | Тесты по подсистемам; общие временные репозитории и fake API в `support.py` |

Публичные операции документированы docstrings. Публикация сохраняет один job:
RC требуют последовательной нумерации, а GitHub Release и aliases зависят от
готовности всех артефактов. Независимые Runtime и Console уже собираются параллельно
одним вызовом Bake. YAML остаётся небольшим; бизнес-логика находится в Python.

## Образы из feature-ветки

Из корня этого проекта, находясь в чистой `feature/*`, выполните:

```sh
make publish-feature
```

Команда публикует `ghcr.io/dinikon/dnk-runtime-core/runtime` и
`ghcr.io/dinikon/dnk-runtime-core/frontend-runtime` с тегом
`feat-<первые 8 символов SHA HEAD>`, например `feat-a1b2c3d4`.
Затем собирает Helm chart с этими образами и публикует его в
`ghcr.io/dinikon/dnk-runtime-core/helm` с версией
`<исходная-chart-version>-feat.g<SHA8>`, например `0.3.5-feat.ga1b2c3d4`.
Тег `feat` у Helm указывает на digest последнего успешно опубликованного комплекта.
В control plane та же команда запускается отдельно и использует SHA того проекта.

Staged/unstaged изменения, новые и удалённые файлы, конфликты, другая ветка и detached
HEAD останавливают запуск до обращения к registry. Проверка работает даже при
`status.showUntrackedFiles=no`. Игнорируемые Git файлы допустимы и не входят в сборку:
образы и chart берутся из временного worktree зафиксированного коммита. Исходные
версии, Git-ветки и теги не меняются; временные файлы удаляются при успехе и ошибке.

Нужны зависимости `uv sync --frozen`, Git, Docker с Buildx, Helm и авторизация Docker
в GHCR с правом публикации образов и пакета `/helm`: `docker login ghcr.io`.
ORAS не требуется. Для Helm используется стандартный OCI HTTP API с учётными
данными Docker из `config.json` или credential helper. Секреты не выводятся в лог.
Сборка образов явно использует `linux/amd64` и `linux/arm64`.

Chart сохраняет исходный `appVersion`, закреплённые image tags, `publication.json`
и `global.deployment.revision=feat-<полный SHA>`. Это запускает новый rollout и
миграционные hooks при смене коммита. OCI-пакет содержит Helm config и один tgz layer,
поддерживаемый native OCI-источником ArgoCD.

Повторный `make publish-feature` использует готовые образы и chart, проверяя полный
SHA, версии и метаданные. После частичной ошибки выполняются только недостающие шаги.
Коллизия короткого SHA или ошибка доступа останавливает публикацию. `feat` обновляется
после проверки chart; незавершённая сборка не заменяет предыдущий комплект. Если во
время публикации сменились локальная ветка или HEAD, готовые артефакты сохраняются,
но `feat` не перемещается. Все feature-ветки используют общий канал `feat`.

### Однократная настройка ArgoCD на feat

У существующего Application выберите `targetRevision: feat` и включите auto-sync.
Адрес источника остаётся `oci://ghcr.io/dinikon/dnk-runtime-core/helm`, `path: .`.
Пример merge patch — `deploy/argocd/examples/feature-channel.patch.yaml`:

```sh
kubectl --context <ваш-контекст> -n argocd patch application dnk-runtime-core-dev \
  --type merge --patch-file deploy/argocd/examples/feature-channel.patch.yaml
```

Если Application управляется из Git или ApplicationSet, внесите те же поля в его
источник конфигурации, чтобы контроллер не вернул `targetRevision: dev`.
Сохраните существующие domains, values, Secrets и imagePullSecrets; image tags и
`global.deployment.revision` не должны переопределять значения опубликованного chart.

После публикации ArgoCD обнаружит новый digest при следующем обновлении источника;
задержка зависит от reconciliation и кэша, а не от времени завершения make.
Для немедленной проверки используйте Hard Refresh в ArgoCD. Сам publisher не
обращается к кластеру. Обычный канал `dev` и production сохраняют свои настройки.
См. [OCI sources](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/) и
[reconciliation settings](https://argo-cd.readthedocs.io/en/stable/operator-manual/argocd-cm-yaml/).

Опциональный кэш: `CICD_BUILD_CACHE=registry make publish-feature`; его идентичность
берётся из фактической feature-ветки. Проверки качества запускаются отдельно через
`make check`. Git push, повышение исходных версий и GitHub Release не выполняются.

## Логи Jobs

Каждый этап пишет `Started`, затем результат `status=success` или `status=failed`
с `duration` в секундах. Строка содержит UTC timestamp, уровень и контекст:
команда, ветка, SHA запуска, run id, attempt и текущий этап. В RC дополнительно
видны исходный SHA, позиция в очереди и тег. Проверки registry показывают адрес,
номер повтора и задержку; повторное использование артефактов отмечается отдельно.

Пример формата:

```text
2026-09-11T09:15:00Z INFO Started | branch="develop" sha="..." run_id="123" attempt="1" stage="Publish images"
2026-09-11T09:15:12Z INFO Finished: status=success duration=12.00s | branch="develop" ...
```

В GitHub Actions верхние этапы сворачиваются в группы. Job Summary содержит таблицу
статусов и длительностей, включая вложенные этапы и ошибки. Вложенные длительности
включены в родительские: складывать все строки для оценки общего времени нельзя.
Ошибка записи Summary выводит предупреждение и не меняет результат публикации.

Подробности процессов локально:

```sh
uv run --frozen python -m scripts.cicd --log-level DEBUG check
```

`DEBUG` добавляет имя процесса, код выхода и длительность. Логгер не выводит argv
или окружение: там могут находиться пароли и токены. Вывод внешних инструментов
по-прежнему передаётся как есть; нельзя добавлять в скрипты печать секретов.

Workflow сохраняет `publication-<run_id>-<attempt>` на 14 дней даже после ошибки:

- `publication.log` — потоковый вывод команды публикации и внешних инструментов;
- `publication.json` — последний готовый набор артефактов;
- `publications/vX.Y.Z-rc.N.json` — отдельная запись каждого готового RC в запуске.

JSON записывается **после готовности артефактов, до вызова GitHub Releases**.
Поэтому наличие файла не доказывает успешное создание Release или обновление
aliases: проверяйте соответствующие этапы в Summary. Если второй RC упал,
результат первого остаётся доступен. Повторная попытка имеет собственный artifact
и не затирает диагностику предыдущей. Если установка инструментов упала раньше
публикации, `publication.log` отсутствует; причина остаётся в логе setup-шага Actions.

## Кэш и ускорение

Job явно включает кэш uv с ключом зависимостей по `uv.lock`. QEMU настраивается
только для `arm64`; целевые платформы образов остаются `amd64` и `arm64`.

`CICD_BUILD_CACHE=registry` включает BuildKit registry cache через параметры Bake.
Он использует текущую авторизацию GHCR и отдельные mutable tags
`<image-repository>:buildcache-<первые 16 hex SHA256 имени ветки>`.
Каждая пара образ/ветка имеет свой кэш. Job читает кэш своей ветки и fallback-кэши
`main`/`develop`, но записывает только свой. Это исключает конкуренцию веток за
один cache tag; уже существующая concurrency сериализует запуск одной ветки.

`mode=max` сохраняет промежуточные слои, включая Node-сборку Console. Отсутствующий
кэш допускает обычную сборку, а `ignore-error=true` относится только к экспорту
кэша. Ошибки сборки и публикации конечного образа продолжают останавливать job.
Кэш никогда не используется как доказательство готовности артефакта: финальные
теги проверяются по полному source SHA и версии приложения.

Кэш-теги находятся в существующих image repositories, поэтому новых credentials
не требуется. Они занимают дополнительное место в GHCR. Для отключения достаточно
удалить `CICD_BUILD_CACHE` из workflow; локальный Bake по умолчанию не публикует кэш.
Периодическую очистку кэшей завершённых release-веток можно добавить отдельно.

Поддержка registry cache и параметров экспорта описана в
[Docker registry cache](https://docs.docker.com/build/cache/backends/registry/).
Группы и сводки используют стандартные
[GitHub workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands).

## Проверки и дальнейшие улучшения

```sh
make check-cicd  # Git/Commitizen, fake GitHub/registry, кэш, логи и workflow
make check       # Backend с временной PostgreSQL, Helm и frontend
make check-full  # Дополнительно отдельный Kind и OCI/ArgoCD integration
```

Для `check-cicd` нужны зависимости `uv sync --frozen`, Git и Helm. Docker daemon,
кластер, GitHub token и доступ к реальному registry этому набору не нужны.

Следующие шаги стоит выбирать по измерениям Summary:

1. Сравнить холодную и повторную сборку: время `Build missing images`, cache hits
   в Bake и размер кэша. Процент ускорения без запусков на runner не измерен.
2. Если после кэша основное время занимает ARM-сборка backend, оценить отдельный
   ARM runner и сборку manifest list из двух native builds. Это меняет схему Jobs
   и требует отдельной проверки восстановления после частичных публикаций.
3. При переходе к обязательным серверным проверкам добавить быстрый job с
   `check-cicd` и отдельные backend/frontend проверки. Текущий процесс намеренно
   оставляет проверки качества локальными; branch protection не изменяется.

Рефакторинг не запускает реальную публикацию и не применяет ресурсы рабочего кластера.
