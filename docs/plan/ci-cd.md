# CI/CD для одного разработчика

**Граница реализации: готовим файлы автоматизации, YAML-манифесты и инструкции. Ничего не применяем в существующий кластер, не изменяем рабочий ArgoCD и не запускаем dev/prod deployment. Разворачивать ресурсы для проверки можно только локально, в отдельном временном Kind-кластере с собственным kubeconfig.**

GitHub Actions занимается только публикацией образов, Helm-пакетов и GitHub Releases. GitHub Deployments и environments `dev`/`prod` не используются. Контроллер внутри закрытого контура самостоятельно читает Git/GHCR и применяет нужную версию. У Actions нет команд доступа к кластеру или API ArgoCD.

## 1. Команды и обычный процесс

| Команда | Действие |
|---|---|
| `make check-cicd` | Быстрые тесты CI/CD: временные Git-репозитории, fake API, кэш и логирование |
| `make check` | Локальные проверки Python/backend с временной PostgreSQL, frontend и Helm |
| `make check-full` | Базовые проверки, установка/обновление в Kind, миграции и OCI/ArgoCD integration |
| `make release` | Создание и отправка release-ветки с автоматически рассчитанным номером |
| `make publish` | Финализация версии на main, локальная проверка, обратный merge в develop и атомарный push |

Для базовых проверок нужны Python **3.13.9**, uv **0.10.4**, Node.js **24** с npm, Docker и Helm **3.19.0**. Для полного набора — также Kind **0.29.0**, kubectl **1.33.1**, ORAS **1.3.0**, OpenSSL и curl. Локальные команды выпуска требуют Git с настроенной личностью автора и права push в репозиторий. Установка GitHub CLI `gh` локально не нужна: `make publish` читает состояние Releases напрямую через GitHub REST API, используя уже имеющийся `httpx`.

Для приватного репозитория перед запуском экспортируйте `GH_TOKEN` или `GITHUB_TOKEN` с доступом к репозиторию и разрешением **Contents: read** (fine-grained personal access token). `GH_TOKEN` имеет приоритет. Авторизация Git для push настраивается отдельно; Python не читает токены из Git credential helper или `.env`. Пример для zsh: `read -rs 'GH_TOKEN?GitHub token: '; export GH_TOKEN`, затем `make publish`. Для опубликованных релизов публичного репозитория токен необязателен, но без него ниже лимит API-запросов. Ошибки доступа и лимитов останавливают команду с подсказкой; отсутствие готового релиза сохраняет ожидание. См. [GitHub Releases API](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name).

Команда `ci` создаёт опубликованные GitHub Releases через `gh`, доступный на runner. Stable Release появляется после готовности обоих образов и Helm-пакета; ожидания доставки и этапа draft нет.

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

Workflow: `.github/workflows/deploy.yml`, название **Build and publish**, один job `publish`. Структура модулей, логи Jobs и кэш описаны в [руководстве по поддержке CI/CD](../operations/ci-cd.md). Проверки качества выполняются локально; Actions создаёт версии и публикует артефакты. В workflow нет `environment`, deployment job, ArgoCD CLI и Kubernetes-команд.

| Триггер | Результат |
|---|---|
| Push `develop` | Runtime/Console с тегом `dev-<8 символов SHA>`, dev chart и обновление Helm alias `dev` |
| Push `release/**` | На каждый новый commit: RC-тег Commitizen, образы, chart и опубликованный GitHub Pre-release |
| Push `main` | Stable-образы и chart, сразу опубликованный GitHub Release, обновление image alias `latest` |
| Re-run / workflow_dispatch на поддерживаемой ветке | Возобновление обработки |
| Feature/hotfix, pull_request, push тегов | Запуска нет |

Первый push release обрабатывает **только начальный HEAD**, без всей прежней истории develop. Далее каждый новый достижимый commit после стартового SHA, включая docs/test и коммиты через merge, получает RC в топологическом порядке. Несколько коммитов одним push дают несколько RC.

На каждый исходный SHA помощник создаёт отдельный checkout. Commitizen создаёт версионный commit и тег `vX.Y.Z-rc.N`. В remote отправляется **только тег**: служебный commit не попадает обратно в release-ветку. Аннотация содержит версию приложения/chart и исходный SHA; для безопасной передачи через Commitizen JSON кодируется как `dnk-cicd:<base64-json>`.

Повтор того же SHA использует прежний тег. Один обработчик на release-ветку последовательно сверяет актуальную историю с тегами, восстанавливая коммиты из пропущенных запусков. Опубликованные RC сохраняются после финализации. GitHub Pre-release создаётся с `prerelease=true`, без Latest; это отдельная запись Releases, а не только тег Git.

Main должен указывать непосредственно на stable-тег, созданный `make publish`, с соответствующими файлами и метаданными версии. Stable Release создаётся с `draft=false`; старый draft при повторе обработки публикуется после проверки готовых артефактов. Следующий `make publish` требует готовую публикацию предыдущей версии в GitHub, но не проверяет состояние кластера. Если предыдущая публикация упала, повторить её workflow. GitHub Release означает доступность версии для установки; установленную версию и её здоровье показывает внутренний контроллер.

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

- Runtime/API/workers: `ghcr.io/dinikon/dnk-runtime-core/runtime`.
- Console: `ghcr.io/dinikon/dnk-runtime-core/frontend-runtime`.
- Helm: **`ghcr.io/dinikon/dnk-runtime-core/helm`**.

Docker Bake собирает `linux/amd64` и `linux/arm64`. Образы Runtime и Console получают одинаковую схему тегов:

| Источник | Тег образа | Плавающий тег |
|---|---|---|
| `develop`, SHA `12345678abcdef…` | `dev-12345678` | Нет |
| `release/X.Y.Z` | `X.Y.Z-rc.N` | Нет |
| `main` | `X.Y.Z` | `latest` |

Dev использует первые восемь символов исходного commit SHA. Полный SHA сохраняется в OCI annotations и `publication.json`: совпадение короткого префикса у разных коммитов останавливает публикацию, а не перезаписывает образ. Сборка сразу публикует конечный тег; длинные временные `sha-…` теги больше не создаются. Повтор того же коммита или версии использует существующие образы даже при другом run/attempt. Ранее опубликованные теги сохраняются.

`latest` у обоих образов перемещается только после готовности stable-образов, chart и GitHub Release из актуального main. Dev и RC его не изменяют. Перед каждым перемещением помощник обновляет refs и сверяет полный SHA с HEAD удалённой ветки: повтор старого запуска не возвращает alias на старую версию. Частичный сбой перемещения aliases можно повторить без пересборки. Ручной Docker Bake без параметров использует локальный тег `local`.

Отсутствующие Runtime и Console передаются одному вызову Bake и собираются параллельно. Уже опубликованные образы повторно не собираются; если одна сборка завершилась, а другая упала, готовый образ уже имеет конечный тег и после проверки используется при следующей попытке. Helm-пакет публикуется только после готовности обоих образов.

Node-этап Console выполняется на `$BUILDPLATFORM`: статические HTML/JS/CSS собираются на родной архитектуре builder и копируются в Nginx для каждой целевой платформы. Вывод Bake идёт непосредственно в Actions с `--progress=plain`; помощник также выводит этапы проверки образов, упаковки и публикации chart. Между запусками используется BuildKit registry cache в GHCR: отдельный кэш на образ и ветку, `mode=max`, чтение fallback-кэшей main/develop. Job также явно включает кэш uv по `uv.lock`. Подробности и отключение — в [руководстве](../operations/ci-cd.md#кэш-и-ускорение).

Сначала публикуются оба образа. Затем во временной копии chart закрепляются image tags backend/workers/frontend; миграции и initContainers используют тот же Runtime. Там же фиксируется deployment revision. Chart включает локальные зависимости PostgreSQL/Redis/RabbitMQ и `publication.json`, содержащий версии и image digests. Исходный chart при упаковке не меняется; секреты в пакет не добавляются.

Dev получает chart `<текущая-chart-version>-dev.<run>.<attempt>`; `appVersion` соответствует исходному приложению. Дополнительный OCI alias `dev` перемещается после публикации полного комплекта для актуального HEAD develop. Это публикация указателя в GHCR; обращения к кластеру нет. Старый запуск не перемещает alias назад.

Chart сохраняет `name: dnk-runtime-core`. Используются `helm package` и ORAS: Helm config `application/vnd.cncf.helm.config.v1+json`, один слой `.tgz` `application/vnd.cncf.helm.chart.content.v1.tar+gzip`. Это даёт точный адрес `/dnk-runtime-core/helm`; обычный `helm push` добавил бы имя chart к repository.

Метаданные OCI manifest и GitHub публикации содержат source/build SHA, версии, image digests и chart digest. Версионные теги никогда не перезаписываются: повтор сверяет метаданные, использует существующие образы/chart и завершает недостающие шаги. Ошибка авторизации registry не считается отсутствием артефакта.

После успешной загрузки GHCR может не сразу возвращать манифест при чтении. Помощник ожидает доступность конечного image tag и опубликованного chart: до семи проверок с задержками `1, 2, 4, 8, 15, 30` секунд. В логе видны полный адрес артефакта и номер попытки. При перемещении alias дополнительно ожидается именно выбранный digest, даже если registry пока возвращает старый манифест. Повторяется только отсутствие ожидаемого манифеста; ошибки авторизации и несовпадение метаданных останавливают публикацию. Истечение ожидания не означает, что загруженный образ нужно удалять.

## 4. Настройки GitHub и закрытого контура

Workflow использует встроенный `GITHUB_TOKEN` с `contents: write` для тегов/Releases и `packages: write` для GHCR. Репозиторию Actions нужен write-доступ ко всем трём пакетам Runtime/Console/Helm, включая уже существующие. ORAS использует авторизацию Docker на runner.

GitHub environments `dev`/`prod`, переменные `DEPLOY_ENABLED`, `ARGOCD_SERVER`, `ARGOCD_APP`, `ARGOCD_VERSION` и secret `ARGOCD_AUTH_TOKEN` больше не нужны. Новый workflow не создаёт GitHub Deployments. Старые записи Deployments остаются историей; удаление GitHub settings, секретов и исторических записей не выполняется автоматически.

Разрешить собственные push в main/develop без обязательных PR/review/checks. Процесс использует merge commits; запрет force-push сохранить. Отдельный workflow на push тегов не нужен: теги и Releases создаются в текущем запуске.

Кластер самостоятельно читает источники через разрешённый исходящий доступ к Git/GHCR или их внутреннему зеркалу. Подготовленные YAML остаются примерами для отдельного подключения пользователем:

- `deploy/argocd/project.yaml`: AppProject с разрешённым OCI repository и двумя namespace; ролей для токенов GitHub Actions нет.
- `deploy/argocd/dnk-runtime-core-dev.yaml`: Application dev, `targetRevision: dev`, auto-sync. Deployment revision берётся из пакета.
- `deploy/argocd/dnk-runtime-core.yaml`: Application prod с placeholder digest. Нужную версию и способ Sync выбирает конфигурация внутри контура.
- `deploy/argocd/examples/credentials.yaml`: примеры credentials для чтения chart, `imagePullSecrets` и application Secret без реальных значений.

Источник OCI Applications — `oci://ghcr.io/dinikon/dnk-runtime-core/helm`, `path: .`, без поля `chart`. Helm release name — `dnk-runtime-core`; namespaces раздельные. ArgoCD внутри контура получает OCI-пакет, рендерит Helm и применяет ресурсы. Нужна версия ArgoCD с поддержкой native OCI source.

Production Application с фиксированным digest не выбирает новый chart автоматически. После публикации нужно обновить digest в отслеживаемой GitOps-конфигурации и выполнить Sync согласно внутренней политике. Само появление image tag `latest` не меняет выбранный chart: в пакете backend/workers/frontend и миграции закреплены на тегах конкретной версии. Для управления окружениями можно использовать отдельную GitOps-ветку или репозиторий.

Перед самостоятельным применением подготовить namespaces/Secrets, реальные домены, SMTP, IngressClass, ClusterIssuer и storage. Credentials ArgoCD для чтения chart и credentials Kubernetes для чтения образов настраиваются внутри контура; реальные токены в Git не сохраняются. Существующие migration hooks и waves сохраняются.

**Ресурсы рабочего кластера и настройки работающего ArgoCD в рамках изменений репозитория не применяются и не изменяются.**

## 5. Повторы и восстановление

При сбое публикации выполнить Re-run. Помощник сверяет версии, полный source/build SHA и использует существующие артефакты. Если один образ уже готов, собирается только недостающий. Если chart готов, повторно используются весь пакет и записанные digests; затем завершается публикация Release и обновление aliases. GitHub Release и floating tags появляются после полного набора артефактов, а не после частично успешной сборки.

`publication.json` сохраняется в artifact запуска и внутри Helm-пакета. Artifact `publication-<run_id>-<attempt>` также содержит `publication.log` и отдельные записи готовых RC из `publications/`; он сохраняется на 14 дней даже после ошибки публикации. Статусы и длительности этапов доступны в Job Summary. Готовый JSON подтверждает наличие артефактов, а результат создания Release и обновления aliases проверяется по соответствующим этапам. Run/attempt остаются служебными метаданными и частью версии dev chart, но не входят в новые теги образов. Dev chart также получает уникальный `global.deployment.revision`.

Re-run выполняет код исходного SHA. Новая схема начинает действовать в запусках с обновлённым workflow; изменения на develop не подменяют код ранее выпущенного main. Уже опубликованные версионные теги не перемещаются и не удаляются.

Локальный `make publish` хранит этап и SHA в `git rev-parse --git-path cicd-publish.json`. При конфликте решить его, сделать merge commit и повторить `make publish`. Если проверка упала из-за временной проблемы окружения и исходники не менялись, достаточно устранить причину и повторить команду: версия повторно не повышается.

Если на этапе `check` нужно исправить исходники или тесты, **не коммитить исправление в подготовленный main**: журнал и stable-тег привязаны к его SHA. Перезапуск такой локальной заготовки выполняется отдельно:

1. Проверить журнал: `phase=check`, локальный main и stable-тег указывают на `main_sha`, develop соответствует `base_develop`, исходная release/hotfix-ветка — `source_sha`.
2. Через `git ls-remote` убедиться, что удалённые main/develop всё ещё равны `base_main`/`base_develop`, а stable-тег **не опубликован**. При изменившихся refs или ошибке доступа остановиться и согласовать историю.
3. Сохранить подготовленный main в резервную локальную ветку, аннотированный stable-тег — в отдельный резервный Git ref, а журнал — в резервный файл.
4. Перенести исправление в исходную release/hotfix-ветку. Вернуть только локальный main на `base_main`, убрать только неопубликованный локальный stable-тег и активный журнал. Сохранённые резервные refs позволяют восстановить заготовку; опубликованные RC остаются на месте.
5. Закоммитить исправление. Для release отправить ветку и дождаться нового RC; затем повторить `make publish`. Для hotfix повторить `make publish` из исправленной hotfix-ветки.

Это восстановление относится только к ещё не отправленной транзакции на этапе `check`. Опубликованные теги не удалять и не перемещать. Если удалённый main/develop изменился во время операции, помощник останавливается для согласования истории, а не делает force-push.

Если исправление уже закоммичено поверх подготовленного main, сначала проверить состав этих дополнительных коммитов. Резервная ветка должна сохранить текущий main целиком; нужные исправления переносятся через cherry-pick в исходную release/hotfix-ветку. Перемещать stable-тег на исправленный main нельзя: исправление release должно сначала получить собственный RC.

Rollback выполняется внутри контура: вернуть предыдущий chart digest в GitOps-конфигурации, задать новый `global.deployment.revision` и выполнить Sync. Новый revision нужен и для намеренного повторного применения того же пакета с migration hooks. Пакет содержит image tags своей версии. БД автоматически не откатывается; предыдущий код должен поддерживать уже применённые миграции. Состояние установки отслеживается в ArgoCD отдельно от опубликованных GitHub Releases.

## 6. Локальная приёмка

`make check` включает реальные Git/Commitizen-тесты во временных репозиториях и fake GitHub/registry API: первый RC/stable, docs-only, несколько commits одним push, merge, hotfix, пересечение с release, конфликт обратного merge, повтор после проверки/частичной публикации, отсутствие GitHub Deployments и обращения к кластеру, публикация Release без draft, короткие dev-теги, обновление latest только из актуального main и восстановление aliases.

Тестовые репозитории имеют собственные начальные версии: приложение и его запись в `uv.lock` — `0.1.0`, chart — `0.3.2`, `appVersion` — `0.1.0`. Они задаются только во временной копии и не зависят от версии проверяемого release/main. Поэтому финализация рабочего chart в `0.3.3` не сдвигает ожидаемые версии тестовых выпусков.

`make check-full` дополнительно запускает существующий Kind smoke, PostgreSQL migration integration и `python -m scripts.cicd.local_oci`. Последний устанавливает ArgoCD **только в новый временный Kind**, поднимает временный локальный registry, проверяет OCI media types/pull, смену `dev`, миграции/rollout и повтор применения того же digest с новым deployment revision. Для этого теста используются локальные Runtime/Console images, собранные предыдущим smoke-тестом. HTTP registry разрешён только внутри этого локального теста.

Критерий готовности реализации — файлы и инструкции подготовлены, локальные проверки выполнены. Рабочий deployment и первая публикация в реальный GitHub/GHCR не входят в приёмку этой задачи.

Официальные справочники: [Commitizen bump](https://commitizen-tools.github.io/commitizen/commands/bump/), [Helm OCI](https://helm.sh/docs/topics/registries/), [ORAS push](https://oras.land/docs/commands/oras_push/), [ArgoCD OCI source](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/).
