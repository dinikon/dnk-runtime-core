# CI/CD для одного разработчика

**Граница реализации: готовим файлы автоматизации, YAML-манифесты и инструкции. Ничего не применяем в существующий кластер, не изменяем рабочий ArgoCD и не запускаем dev/prod deployment. Разворачивать ресурсы для проверки можно только локально, в отдельном временном Kind-кластере с собственным kubeconfig.**

Описанный ниже процесс работает после отдельного подключения пользователем. В репозитории подготовлены команды и workflow; наличие файлов не означает, что окружения уже настроены. Доставка выключена по умолчанию: только значение `DEPLOY_ENABLED=true` соответствующего GitHub environment разрешает обращения к ArgoCD и перемещение Helm-тега `dev`.

## 1. Команды и обычный процесс

| Команда | Действие |
|---|---|
| `make check` | Локальные проверки Python/backend с временной PostgreSQL, frontend и Helm |
| `make check-full` | Базовые проверки, установка/обновление в Kind, миграции и OCI/ArgoCD integration |
| `make release` | Создание и отправка release-ветки с автоматически рассчитанным номером |
| `make publish` | Финализация версии на main, локальная проверка, обратный merge в develop и атомарный push |

Для базовых проверок нужны Python **3.13.9**, uv **0.10.4**, Node.js **24** с npm, Docker и Helm **3.19.0**. Для полного набора — также Kind **0.29.0**, kubectl **1.33.1**, ORAS **1.3.0**, OpenSSL и curl. Локальные команды выпуска требуют Git с настроенной личностью автора и права push в репозиторий. Установка GitHub CLI `gh` локально не нужна: `make publish` читает состояние Releases напрямую через GitHub REST API, используя уже имеющийся `httpx`.

Для приватного репозитория перед запуском экспортируйте `GH_TOKEN` или `GITHUB_TOKEN` с доступом к репозиторию и разрешением **Contents: read** (fine-grained personal access token). `GH_TOKEN` имеет приоритет. Авторизация Git для push настраивается отдельно; Python не читает токены из Git credential helper или `.env`. Пример для zsh: `read -rs 'GH_TOKEN?GitHub token: '; export GH_TOKEN`, затем `make publish`. Для опубликованных релизов публичного репозитория токен необязателен, но без него ниже лимит API-запросов. Ошибки доступа и лимитов останавливают команду с подсказкой; отсутствие готового релиза сохраняет ожидание. См. [GitHub Releases API](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name).

Создание и финализация GitHub Releases командами `ci`/`deliver` в GitHub Actions по-прежнему используют `gh`, доступный на runner.

Подготовка зависимостей: `uv sync --frozen`. Проверки запускают PostgreSQL на случайном локальном порту и удаляют свой контейнер при завершении. Backend проверяется в временной копии исходников с тестовой `.env`; рабочая `.env` не заменяется, рабочие базы не используются. Frontend использует `npm ci` и существующие lint/typecheck/build команды. Kind-тесты создают только собственные кластеры `dnk-test-*`, всегда используют отдельный kubeconfig и явный context; текущий Kubernetes context не переключается.

### Фича

```sh
git switch develop
git pull --ff-only
git switch -c feature/my-feature
# Разработка; коммиты через uv run cz commit.
make check
git switch develop
git pull --ff-only
git merge --no-ff feature/my-feature
make check
git push origin develop
```

**PR не обязателен.** Обычный merge сохраняет исходные Conventional Commits для расчёта версии. Запуск происходит после push целевой ветки, а не после локального merge. `make check-full` запускается отдельно, когда нужны Kubernetes-проверки; `make publish` автоматически запускает базовый `make check`.

### Выпуск

Из чистого, проверенного и отправленного develop, содержащего актуальный main:

```sh
make release
# Работа в созданной release/X.Y.Z; исправления, локальные проверки, git push.
make publish
```

`make release` обновляет refs и создаёт `release/X.Y.Z`. Вместе с веткой атомарно отправляется аннотированный служебный тег `release-start/X.Y.Z`: он фиксирует начальный SHA и базовую версию chart и игнорируется Commitizen. Если текущий main ещё не включён в ветку, сначала нужно слить его и проверить результат локально.

Первый выпуск при отсутствии stable-тегов — **приложение `0.1.0`, chart `0.3.3`**. Исходная версия chart `0.3.2`; перед началом `project.version`, `uv.lock` и `appVersion` согласованы на `0.1.0`. Первый тег — `v0.1.0-rc.1`, затем `v0.1.0`. Уже существующие теги не заменяются.

`make publish` из release:

1. Обновляет refs, проверяет чистое дерево и опубликованный HEAD; ждёт готовый GitHub Pre-release именно этого SHA.
2. Сливает соответствующий RC-тег в main. В теге находятся код и версионный commit Commitizen.
3. Убирает RC-суффикс chart; Commitizen финализирует приложение, `appVersion`, lockfile и changelog и создаёт stable commit/tag.
4. Запускает `make check` для подготовленного main.
5. Сливает main обратно в develop.
6. Отправляет main, develop и stable-тег одним `git push --atomic`.

Во время реализации эти команды проверяются на временных локальных репозиториях. Их обычный запуск после внедрения действительно делает push в настроенный `origin`.

### Hotfix

Для production: создать `hotfix/*` от актуального main, сделать `fix:` commit и выполнить `make publish`. Получается PATCH без RC. Для hotfix от release — обычный merge обратно в release и push; исправление получает RC этой серии.

Готовится один обычный выпуск за раз. Если во время release понадобился production-hotfix, после его успешного выпуска включить новый main в release и повторить `make release`. Chart рассчитывается от нового stable main; при занятом номере приложения создаётся release-ветка с новым рассчитанным номером. История изменений сохраняется, прежние теги остаются. В новой серии приложения RC начинается с 1; при изменении только chart счётчик продолжается. Старую ветку после переименования и завершённые release-ветки можно удалить вручную.

## 2. Триггеры и GitHub Releases

Workflow: `.github/workflows/deploy.yml`. Проверки качества выполняются локально; Actions создаёт версии, собирает и публикует артефакты, а после включения доставки управляет ArgoCD.

| Триггер | Результат |
|---|---|
| Push `develop` | Runtime/Console и уникальный dev chart; dev deployment только при включённой доставке |
| Push `release/**` | На каждый новый commit: RC-тег Commitizen, образы, chart и GitHub Pre-release; без deployment |
| Push `main` | Stable-образы и chart, GitHub draft; после успешной включённой доставки — обычный GitHub Release |
| Re-run / workflow_dispatch на поддерживаемой ветке | Возобновление обработки |
| Feature/hotfix, pull_request, push тегов | Запуска нет |

Первый push release обрабатывает **только начальный HEAD**, без всей прежней истории develop. Далее каждый новый достижимый commit после стартового SHA, включая docs/test и коммиты через merge, получает RC в топологическом порядке. Несколько коммитов одним push дают несколько RC.

На каждый исходный SHA помощник создаёт отдельный checkout. Commitizen создаёт версионный commit и тег `vX.Y.Z-rc.N`. В remote отправляется **только тег**: служебный commit не попадает обратно в release-ветку. Аннотация содержит версию приложения/chart и исходный SHA; для безопасной передачи через Commitizen JSON кодируется как `dnk-cicd:<base64-json>`.

Повтор того же SHA использует прежний тег. Один обработчик на release-ветку последовательно сверяет актуальную историю с тегами, восстанавливая коммиты из пропущенных запусков. Опубликованные RC сохраняются после финализации. GitHub Pre-release создаётся с `prerelease=true`, без Latest; это отдельная запись Releases, а не только тег Git.

Main должен указывать непосредственно на stable-тег, созданный `make publish`, с соответствующими файлами и метаданными версии. При выключенной доставке выпуск остаётся draft. Следующий `make publish` требует завершить предыдущий production-релиз. Для первого подключения нужно включить доставку и повторить workflow текущего main.

## 3. Версии и артефакты

Commitizen настроен в `pyproject.toml`: `cz_conventional_commits`, provider `uv`, `semver2`, `v$version`, changelog, объединение prerelease changelog и точечное обновление `helm/Chart.yaml:appVersion`. `fix/perf/refactor` повышают PATCH, `feat` — MINOR, breaking change — MAJOR. Только docs/test/ci/chore не начинают новую серию, но внутри release каждый commit получает RC.

Chart имеет отдельный счётчик: PATCH на каждый выпуск приложения, включая hotfix. Помощник меняет только верхнеуровневый `version`; Commitizen включает это изменение в тот же commit. Версии вложенных charts не повышаются.

| Публикация | Приложение / appVersion | Chart / OCI tag |
|---|---|---|
| Первый RC | `0.1.0-rc.1` | `0.3.3-rc.1` |
| Второй RC | `0.1.0-rc.2` | `0.3.3-rc.2` |
| Первый stable | `0.1.0` | `0.3.3` |
| Следующий hotfix | `0.1.1` | `0.3.4` |

Адреса GHCR:

- Runtime/API/workers: `ghcr.io/dinikon/runtime/runtime`.
- Console: `ghcr.io/dinikon/runtime/frontend-runtime`.
- Helm: **`ghcr.io/dinikon/dnk-runtime-core/helm`**.

Docker Bake собирает `linux/amd64` и `linux/arm64`. Каждая новая сборка получает `sha-<build-sha>-<run>-<attempt>`; RC/stable дополнительно получают тег версии приложения. `latest` автоматически не публикуется. Ручной Docker Bake без параметров использует локальный тег `local`.

Отсутствующие Runtime и Console передаются одному вызову Bake и собираются параллельно. Уже опубликованные образы повторно не собираются; если одна сборка завершилась, а другая упала, готовый RC/stable-образ проверяется и получает тег версии для использования при следующей попытке. Helm-пакет публикуется только после готовности обоих образов.

Node-этап Console выполняется на `$BUILDPLATFORM`: статические HTML/JS/CSS собираются на родной архитектуре builder и копируются в Nginx для каждой целевой платформы. Вывод Bake идёт непосредственно в Actions с `--progress=plain`; помощник также выводит этапы проверки образов, упаковки и публикации chart. Эти изменения не добавляют кэш между запусками.

Сначала публикуются оба образа. Затем во временной копии chart закрепляются image tags backend/workers/frontend; миграции и initContainers используют тот же Runtime. Там же фиксируется deployment revision. Chart включает локальные зависимости PostgreSQL/Redis/RabbitMQ и `publication.json`, содержащий версии и image digests. Исходный chart при упаковке не меняется; секреты в пакет не добавляются.

Dev получает chart `<текущая-chart-version>-dev.<run>.<attempt>`; `appVersion` соответствует исходному приложению. Дополнительный OCI alias `dev` перемещается **только в разрешённом deployment-этапе**, после публикации полного комплекта.

Chart сохраняет `name: dnk-runtime-core`. Используются `helm package` и ORAS: Helm config `application/vnd.cncf.helm.config.v1+json`, один слой `.tgz` `application/vnd.cncf.helm.chart.content.v1.tar+gzip`. Это даёт точный адрес `/dnk-runtime-core/helm`; обычный `helm push` добавил бы имя chart к repository.

Метаданные OCI manifest и GitHub публикации содержат source/build SHA, версии, image digests и chart digest. Версионные теги никогда не перезаписываются: повтор сверяет метаданные, использует существующие образы/chart и завершает недостающие шаги. Ошибка авторизации registry не считается отсутствием артефакта.

После успешной загрузки GHCR может не сразу возвращать манифест при чтении. Помощник ожидает доступность уникального image tag, присвоенного тега версии и опубликованного chart: до семи проверок с задержками `1, 2, 4, 8, 15, 30` секунд. В логе видны полный адрес артефакта и номер попытки. Повторяется только отсутствие манифеста; ошибки авторизации и несовпадение метаданных останавливают публикацию. Истечение ожидания не означает, что загруженный образ нужно удалять.

## 4. Отдельное подключение пользователем

**Этот раздел — инструкция последующего подключения. В рамках реализации не меняются GitHub settings/secrets, существующий ArgoCD и ресурсы рабочего кластера. YAML ниже только подготовлен.**

### GitHub

Подготовить environments `dev` и `prod` без ручных approvals. В каждом:

| Тип | Имя | Значение |
|---|---|---|
| Variable | `DEPLOY_ENABLED` | Отсутствует / `false` до явного включения; затем точное `true` |
| Variable | `ARGOCD_SERVER` | Доступный runner адрес `host:port`, без `https://`; валидный TLS-сертификат |
| Variable | `ARGOCD_APP` | `dnk-runtime-core-dev` или `dnk-runtime-core` |
| Variable | `ARGOCD_VERSION` | Точная версия CLI, соответствующая серверу, например `v3.x.y` с числовыми компонентами |
| Secret | `ARGOCD_AUTH_TOKEN` | Отдельный токен роли соответствующего Application |

GitHub-hosted runner должен иметь HTTPS-доступ к ArgoCD. CLI использует gRPC-Web, без отключения проверки сертификата. Нужна версия сервера с native OCI source (начиная с 3.1); перед подключением проверить установленную версию и совместимость.

Workflow использует `GITHUB_TOKEN`: `contents: write` для тегов/Releases, `packages: write` для GHCR. Репозиторию Actions нужно предоставить write-доступ ко всем трём пакетам, включая существующие пакеты Runtime/Console. Credentials ORAS берутся из авторизации Docker на runner.

Разрешить собственные push в main/develop без обязательных PR/review/checks. Не требовать linear history: процесс использует merge commits. Запрет force-push сохранить. Не добавлять отдельные workflows на push тегов: теги и Releases создаются в текущем запуске, без цепочки запусков от `GITHUB_TOKEN`.

### ArgoCD и Kubernetes YAML

- `deploy/argocd/project.yaml`: AppProject, разрешённый OCI repository, два namespace, отдельные роли доставки dev/prod.
- `deploy/argocd/dnk-runtime-core-dev.yaml`: Application dev, `targetRevision: dev`, auto-sync. Deployment revision берётся из пакета.
- `deploy/argocd/dnk-runtime-core.yaml`: Application prod, placeholder digest, auto-sync выключен. Реальный digest и deployment revision выбирает включённый workflow.
- `deploy/argocd/examples/credentials.yaml`: примеры OCI repository credentials, namespace-local `imagePullSecrets` и application Secret. Реальные значения не коммитятся.

Источник обоих Applications — `oci://ghcr.io/dinikon/dnk-runtime-core/helm`, `path: .`, без поля `chart`. Helm release name — `dnk-runtime-core`; namespaces раздельные. ArgoCD получает OCI-пакет, распаковывает, рендерит Helm и применяет ресурсы. Image version overrides в Applications не задаются.

Перед самостоятельным применением заменить домены, SMTP и Secret references, подготовить нужные namespaces/Secrets, проверить IngressClass `nginx`, ClusterIssuer и storage. Credentials ArgoCD для чтения chart отдельны от Kubernetes image-pull credentials. Примеры используют токен GitHub с правом чтения приватных packages; реальные токены хранятся вне Git.

Другой GitOps-контроллер не должен возвращать Application к старому source/revision. Существующее отслеживание Git main нужно отключить/заменить в рамках отдельного подключения: флаг GitHub `DEPLOY_ENABLED` не управляет уже работающим ArgoCD Application из прежней схемы.

После настройки пользователь отдельно включает `DEPLOY_ENABLED=true` и повторяет workflow. При выключенном флаге ни CLI, ни registry alias не изменяют окружения; stable GitHub Release остаётся draft. Это постоянная настройка подключения, а не approve для каждого релиза.

## 5. Доставка и восстановление

Будущая доставка сериализована по окружению, начатый rollout не отменяется новым push. Перед переключением пакета помощник повторно проверяет, что build SHA остаётся текущим HEAD целевой ветки; опоздавшая сборка пропускает delivery.

- Dev: переместить alias `dev` → hard refresh → дождаться именно нового digest, успешной миграции и `Synced/Healthy`.
- Prod: установить digest и новый `global.deployment.revision` → полный Sync → дождаться миграций и rollout → опубликовать GitHub Release из draft.

Сохраняются существующие Sync hooks, waves и migration gate. Deployment не начинается при ошибке публикации артефактов. Для повторной production-доставки используется тот же пакет и новый идентификатор операции. Результат dev также проверяется по digest, а не только по имени тега или прежнему Healthy.

При сбое Actions — исправить причину и выполнить Re-run. Можно повторить весь workflow либо только упавший delivery job: `publication.json` хранится в artifact данного run и не зависит от номера попытки delivery. После истечения срока хранения artifact нужно повторить весь workflow.

Re-run выполняет код исходного SHA: изменения помощника на develop не подменяют код уже выпущенного main. При восстановлении старого выпуска сохраняются его stable-тег, исходные SHA и digests. Если образы уже загрузились под уникальными тегами, исправленный помощник может завершить присвоение версионных тегов и упаковку исходного chart; последующий Re-run использует готовый chart и создаёт GitHub Release без пересборки образов.

Локальный `make publish` хранит этап и SHA в `git rev-parse --git-path cicd-publish.json`. При конфликте решить его, сделать merge commit и повторить `make publish`. Если проверка упала из-за временной проблемы окружения и исходники не менялись, достаточно устранить причину и повторить команду: версия повторно не повышается.

Если на этапе `check` нужно исправить исходники или тесты, **не коммитить исправление в подготовленный main**: журнал и stable-тег привязаны к его SHA. Перезапуск такой локальной заготовки выполняется отдельно:

1. Проверить журнал: `phase=check`, локальный main и stable-тег указывают на `main_sha`, develop соответствует `base_develop`, исходная release/hotfix-ветка — `source_sha`.
2. Через `git ls-remote` убедиться, что удалённые main/develop всё ещё равны `base_main`/`base_develop`, а stable-тег **не опубликован**. При изменившихся refs или ошибке доступа остановиться и согласовать историю.
3. Сохранить подготовленный main в резервную локальную ветку, аннотированный stable-тег — в отдельный резервный Git ref, а журнал — в резервный файл.
4. Перенести исправление в исходную release/hotfix-ветку. Вернуть только локальный main на `base_main`, убрать только неопубликованный локальный stable-тег и активный журнал. Сохранённые резервные refs позволяют восстановить заготовку; опубликованные RC остаются на месте.
5. Закоммитить исправление. Для release отправить ветку и дождаться нового RC; затем повторить `make publish`. Для hotfix повторить `make publish` из исправленной hotfix-ветки.

Это восстановление относится только к ещё не отправленной транзакции на этапе `check`. Опубликованные теги не удалять и не перемещать. Если удалённый main/develop изменился во время операции, помощник останавливается для согласования истории, а не делает force-push.

Если исправление уже закоммичено поверх подготовленного main, сначала проверить состав этих дополнительных коммитов. Резервная ветка должна сохранить текущий main целиком; нужные исправления переносятся через cherry-pick в исходную release/hotfix-ветку. Перемещать stable-тег на исправленный main нельзя: исправление release должно сначала получить собственный RC.

Rollback — отдельная операция пользователя: вернуть предыдущий успешный chart digest в ArgoCD, задать новый deployment revision и выполнить полный Sync. Пакет содержит нужные image tags. БД автоматически не откатывается; предыдущий код должен поддерживать уже применённые миграции. После rollback или failed release восстановить согласованность main/prod до следующего выпуска.

## 6. Локальная приёмка

`make check` включает реальные Git/Commitizen-тесты во временных репозиториях и fake GitHub/registry API: первый RC/stable, docs-only, несколько commits одним push, merge, hotfix, пересечение с release, конфликт обратного merge, повтор после проверки/частичной публикации, отсутствие delivery при выключенном флаге.

Тестовые репозитории имеют собственные начальные версии: приложение и его запись в `uv.lock` — `0.1.0`, chart — `0.3.2`, `appVersion` — `0.1.0`. Они задаются только во временной копии и не зависят от версии проверяемого release/main. Поэтому финализация рабочего chart в `0.3.3` не сдвигает ожидаемые версии тестовых выпусков.

`make check-full` дополнительно запускает существующий Kind smoke, PostgreSQL migration integration и `python -m scripts.cicd.local_oci`. Последний устанавливает ArgoCD **только в новый временный Kind**, поднимает временный локальный registry, проверяет OCI media types/pull, смену `dev`, миграции/rollout и повтор применения того же digest с новым deployment revision. Для этого теста используются локальные Runtime/Console images, собранные предыдущим smoke-тестом. HTTP registry разрешён только внутри этого локального теста.

Критерий готовности реализации — файлы и инструкции подготовлены, локальные проверки выполнены. Рабочий deployment и первая публикация в реальный GitHub/GHCR не входят в приёмку этой задачи.

Официальные справочники: [Commitizen bump](https://commitizen-tools.github.io/commitizen/commands/bump/), [Helm OCI](https://helm.sh/docs/topics/registries/), [ORAS push](https://oras.land/docs/commands/oras_push/), [ArgoCD OCI source](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/).
