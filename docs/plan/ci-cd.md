# Минимальный CI/CD для одного разработчика

Статус: согласуемый проект процесса. Команды `make` ниже — предлагаемый интерфейс автоматизации, их ещё нужно реализовать. Текущие workflows пока не изменены.

**Локально:** разработка, линт, тесты, проверки, расчёт номера выпуска через Commitizen и merge.
**В GitHub Actions:** создание prerelease-версий через Commitizen, публикация GitHub Pre-release/Release, сборка двух образов, GHCR и доставка через существующий ArgoCD.

PR не обязателен. Обычный порядок: проверить локально → merge локально → push. Отдельных approve, ботов, расписания релизов и staging-окружения нет.

## 1. Ветки и триггеры

| Ветка | Назначение | Что запускает push |
| --- | --- | --- |
| `feature/*` | Разработка от `develop` | Ничего |
| `develop` | Рабочая стабильная версия | Сборка и deployment dev |
| `release/X.Y.Z` | Зафиксированный состав следующего выпуска из `develop`; проверяется локально | Для каждого нового коммита: версия `X.Y.Z-rc.N`, Git-тег Commitizen, образы и GitHub Pre-release |
| `hotfix/*` | Исправление от `main` или конкретной release-ветки | Ничего |
| `main` | Финальная версия `X.Y.Z` для production | Сборка, deployment prod и GitHub Release без признака prerelease |

`pull_request` и push Git-тега deployment не запускают. **Локальный merge ничего не разворачивает: запуск происходит после push целевой ветки на GitHub.**

## 2. Твой обычный процесс

### Разработать фичу

Создаёшь рабочую ветку от свежего develop:

```sh
git switch develop
git pull --ff-only
git switch -c feature/tenant-export
```

Пишешь код, фиксируешь изменения через `uv run cz commit`. Перед переносом запускаешь локально `make check`.

Готовую фичу сливаешь сам:

```sh
git switch develop
git pull --ff-only
git merge --no-ff feature/tenant-export
make check
git push origin develop
```

Здесь повторная локальная проверка относится к результату merge. GitHub собирает Runtime и Console, публикует образы и обновляет dev. В интерфейсе dev можно посмотреть результат. Feature-ветку после успешного переноса можно удалить.

**PR создавать не нужно.** Используем обычный merge с сохранением Conventional Commits, поэтому Commitizen видит исходные `feat:`/`fix:`. Merge можно сделать и через IDE.

### Подготовить выпуск

Когда хочешь выпустить текущий develop, запускаешь из него:

```sh
make release
```

Команда обновляет refs, проверяет чистое рабочее дерево и синхронизацию develop с main. Затем Commitizen рассчитывает следующую версию, например `0.2.0`; команда создаёт `release/0.2.0`, переключает тебя в неё и отправляет ветку на GitHub. Номер вручную не вводишь. Первый push создаёт prerelease `v0.2.0-rc.1` для начального состояния ветки.

В этой ветке проверяешь выпуск локально, при необходимости исправляешь баги. После каждого нового коммита и push автоматически появляется следующий prerelease. Новые фичи остаются в develop для следующего выпуска. Prerelease публикуется в GitHub и GHCR; отдельного deployment release-ветки нет.

### Каждый коммит в release — отдельный prerelease

```text
release/0.2.0: начальный commit → v0.2.0-rc.1 → GitHub Pre-release
release/0.2.0: следующий commit → v0.2.0-rc.2 → GitHub Pre-release
release/0.2.0: ещё один commit  → v0.2.0-rc.3 → GitHub Pre-release
main: публикация выпуска      → v0.2.0      → GitHub Release → prod
```

Публикация начинается после отправки коммита на GitHub. Если одним push отправлены несколько новых коммитов, каждому создаётся свой prerelease по порядку, включая `docs:`/`test:` commits. При создании release-ветки публикуется только её начальный HEAD, без повторного выпуска всей истории develop. Слияние hotfix также запускает публикацию новых коммитов release.

`X.Y.Z` берётся из имени release-ветки и не меняется на каждом исправлении; увеличивается только `rc.N`. Уже созданные tags и GitHub Pre-releases сохраняются после финального выпуска. Повторная обработка того же исходного SHA использует его существующий prerelease, а не увеличивает номер ещё раз.

### Отправить выпуск в prod

Из готовой release-ветки:

```sh
make publish
```

Команда выполняет локально:

1. Обновляет refs и теги, требует чистое рабочее дерево и опубликованный prerelease именно для текущего HEAD release. Все локальные изменения должны быть отправлены; если публикация ещё идёт, команда ждёт её завершения. Текущий main должен входить в историю release.
2. Сливает в main тег последнего prerelease через merge commit. Он содержит весь текущий код release и подготовленные Commitizen файлы версии.
3. **На main** Commitizen переводит `0.2.0-rc.N` в `0.2.0`: обновляет версию приложения, `uv.lock`, Helm `appVersion`, changelog и создаёт финальный commit с Git-тегом `v0.2.0`. Новое повышение до `0.2.1` здесь не выполняется.
4. Запускает локальный `make check` для финальной версии.
5. Сливает main обратно в develop, возвращая туда исправления и версию.
6. Отправляет main, develop и тег одним атомарным push. При конфликте останавливается до отправки; конфликт решаешь локально.

После push автоматически обновляются prod из main и dev из develop. Для `v0.2.0` публикуется обычный GitHub Release; прежние `v0.2.0-rc.N` остаются предрелизными публикациями. В GitHub Actions смотришь результат доставки. Дополнительных кнопок и PR нет. Release-ветку удаляешь после успешного deployment.

При повторном запуске после локальной ошибки или сбоя push команда продолжает подготовленный выпуск: второй bump и второй тег не создаются.

## 3. Hotfix

### Баг в production

Создаёшь ветку от актуального main:

```sh
git switch main
git pull --ff-only
git switch -c hotfix/tenant-login
```

Исправляешь баг, делаешь `fix:` commit и запускаешь `make publish` из hotfix-ветки. Для hotfix от main prerelease не требуется: команда сливает исправление в main, где Commitizen формирует только PATCH, например `0.2.0 → 0.2.1`. Локальная проверка, обратное слияние и push выполняются так же. После push публикуется GitHub Release, обновляется prod, а исправление возвращается в develop.

### Баг в готовящемся release

Создаёшь hotfix от этой release-ветки, исправляешь баг и сливаешь обратно в неё обычным merge. Проверяешь локально и делаешь push release: CI создаёт следующие prerelease-версии. Отдельный patch-релиз не появляется: исправление входит в готовящийся выпуск. `make publish` запускаешь из release-ветки, когда готов весь выпуск.

Для простоты готовь один выпуск за раз. Если срочный prod hotfix понадобился во время подготовки release, после hotfix влей новый main в release и проверь результат локально. Если номер release уже занят hotfix, перед следующим push повтори `make release` из текущей release-ветки: в этом режиме команда пересчитывает номер и переименовывает ветку, сохраняя изменения. Для новой серии RC-счёт начинается с 1. Опубликованные теги не перемещаются.

## 4. Минимальная автоматизация

Нужны всего три локальные команды:

| Команда | Действие |
| --- | --- |
| `make check` | Существующие линт, тесты backend/frontend, проверки Helm и миграций — локально; PostgreSQL integration использует отдельную тестовую БД |
| `make release` | Рассчитать номер, создать release-ветку и отправить её для первого prerelease |
| `make publish` | Перенести последний prerelease или prod hotfix в main, сформировать финальную версию, проверить локально и отправить выпуск |

Рабочие feature/hotfix-ветки создаются обычной командой Git. Настройка Commitizen:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version_provider = "uv"
version_scheme = "semver2"
tag_format = "v$version"
major_version_zero = false
update_changelog_on_bump = true
changelog_merge_prerelease = true
version_files = ["helm/Chart.yaml:appVersion"]
```

`fix`, `perf`, `refactor` повышают PATCH; `feat` — MINOR; breaking change — MAJOR. Только docs/test/ci/chore не начинают новую серию выпусков, но в уже созданной release-ветке любой новый commit получает следующий RC. Provider `uv` согласует версию приложения с lockfile: [документация Commitizen](https://commitizen-tools.github.io/commitizen/config/version_provider/).

Для начального расчёта локальная команда использует `cz bump --get-next`. В release номер `X.Y.Z` фиксирован, а CI выбирает следующий свободный `rc.N` и передаёт его Commitizen: например, `cz bump 0.2.0-rc.2 --yes --changelog`. Явная автоматически рассчитанная версия обеспечивает RC даже для docs-only commit. При завершении выпуска на main выполняется `cz bump 0.2.0 --yes --changelog`. В обоих случаях **commit и Git-тег создаёт Commitizen**; примеры номеров подставляет автоматизация. См. [Commitizen bump](https://commitizen-tools.github.io/commitizen/commands/bump/).

Версия Helm chart остаётся отдельной; chart берётся из того же Git SHA, что и исходники образов, без отдельной публикации chart.

## 5. Что делает CI/CD

Достаточно одного `deploy.yml`, запускаемого на push в `develop`, `release/**` и `main`:

```text
push develop   → собрать Runtime + Console → GHCR → ArgoCD dev
push release/* → Commitizen RC + Git-тег → образы → GHCR + GitHub Pre-release
push main      → финальные образы → GHCR → ArgoCD prod → GitHub Release
```

Для `release/*` CI последовательно обрабатывает все ещё не опубликованные коммиты ветки. Для каждого создаёт в отдельном checkout служебный commit с RC-версией и тегом Commitizen, отправляет **тег**, собирает образы из этого тега и создаёт GitHub Pre-release с changelog, исходным SHA и ссылками на образы. Служебный commit доступен через тег и не отправляется обратно в release-ветку: твоя рабочая история не меняется и цикл новых prerelease не возникает. `make publish` затем переносит выбранный тег в main.

На одну release-ветку работает один обработчик; он восстанавливает пропущенные коммиты по истории и соответствию «исходный SHA → RC-тег». Теги и соответствия сохраняются при сбое, поэтому повторный запуск продолжает публикацию того же RC. Создание тега и GitHub публикации выполняется в текущем workflow; отдельного запуска по тегу нет. Для Git-тегов и GitHub Releases достаточно `GITHUB_TOKEN` с `contents: write`, для GHCR — `packages: write`.

GitHub Pre-release — отдельная запись в Releases с признаком `prerelease: true`, а не только Git-тег. Финальная запись `vX.Y.Z` из main имеет `prerelease: false`. Для публикации используется уже существующий тег (`--verify-tag`); prerelease не помечается Latest. См. [GitHub Release create](https://cli.github.com/manual/gh_release_create).

Доставка для `develop`/`main`:

1. Берёт точный SHA события push и собирает оба образа через существующий Docker Bake.
2. Публикует их с уникальным тегом `sha-<commit>-<run>-<attempt>`; `latest` не используется. У каждого повтора сборки свой тег. Для RC и финального выпуска оба образа также получают версионный тег, например `0.2.0-rc.2` или `0.2.0`: он присваивается один раз и не перезаписывается. При повторе уже опубликованной версии используются сохранённые образы.
3. Только после публикации обоих образов обновляет нужный ArgoCD Application: `targetRevision` равен исходному SHA; backend, workers, migration Job и initContainer используют новый runtime image tag, frontend — новый Console image tag. `global.deployment.revision` получает уникальный идентификатор этого deployment.
4. Запускает полный Sync и ждёт завершения rollout, включая штатный migration Job chart. Это доставка приложения; линт, тесты и приёмочные сценарии в CI не запускаются.
5. Сохраняет SHA и image tags в результате запуска, отмечает deployment успешным или неуспешным. После успешного prod deployment публикует финальный GitHub Release с changelog. До этого запись может оставаться draft; существующий stable Git-тег при сбое не удаляется.

Существующий ArgoCD позволяет менять revision и Helm parameters через [app set](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_set/), а завершение доставки ждать через [app wait](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_wait/). Достаточно двух Applications — dev и prod. CI управляет их revision/image parameters напрямую; отдельный GitOps-репозиторий не нужен.

Applications закрепляются на SHA, auto-sync отключается; revision и tags обновляются вместе перед явным Sync. Нынешнее отслеживание движущегося `main` нужно убрать, иначе раскатка может начаться до публикации образов. Эти поля не должен перезаписывать другой контроллер.

В одном окружении deployment выполняется последовательно; начатую миграцию новый push не отменяет. Перед обновлением Application job сверяет свой SHA с текущей целевой веткой, чтобы опоздавшая сборка не вернула старый код. Prod-сборка выполняется из main заново: это отдельная сборка от ранее развёрнутой на dev.

Если сборка не удалась, deployment не начинается. После сбоя доставки повторяешь нужный запуск. Для rollback возвращаешь в ArgoCD SHA и оба image tags предыдущего успешного запуска, задаёшь новый идентификатор операции `global.deployment.revision` и выполняешь полный Sync. Откат образов не откатывает БД; старый код должен быть совместим с уже применёнными миграциями. Пока main и фактический prod расходятся после сбоя/rollback, сначала восстанови согласованность, затем начинай следующий выпуск или hotfix.

## 6. Что потребуется внедрить

- Добавить три локальные команды и конфигурацию Commitizen. Один раз согласовать стартовый stable tag, `project.version`, `uv.lock` и нынешний Helm `appVersion`.
- Добавить обработку каждого нового release-коммита, создание RC-тегов Commitizen и GitHub Pre-release; из main публиковать финальный GitHub Release.
- Перенести проверки из `.github/workflows/ci.yml` и `helm.yml` в `make check`; автоматические CI-проверки отключить, сборку и доставку оставить в `deploy.yml`.
- В Docker Bake убрать автоматическое добавление `latest` и передавать уникальный image tag из workflow.
- Подготовить ArgoCD dev/prod, доступ CI к ArgoCD и запись в существующие GHCR-пакеты. Секреты приложений остаются в окружениях.
- Разрешить собственный push в develop/main, без обязательных PR/review/CI checks; запрет force-push можно сохранить.
