# dnk-runtime-core Helm chart

`helm/` — корень самостоятельного пакета **dnk-runtime-core 0.3.2**. Он устанавливает
FastAPI, workers и Console; исходники соседнего репозитория и OCI registry для сборки не нужны.
Общий пакет `dnk-platform` удалён. Каждый сервис устанавливается своим релизом.

```text
helm/
  Chart.yaml
  Chart.lock
  values.yaml
  values.schema.json
  templates/        # Deployment, Service, Ingress, Jobs, ConfigMap, Secret и helpers
  charts/           # только локальные инфраструктурные зависимости
  tests/
  examples/
  build.py
```

В `charts/` включены PostgreSQL, Redis и RabbitMQ. Общие helper-шаблоны входят непосредственно
в `templates/`; отдельной зависимости `dnk-common` больше нет. Стандартный каталог
Helm называется `templates/`. Настройки описаны в [values.yaml](values.yaml).

## Установка

Скопируйте подходящий пример: [embedded](examples/values-embedded.yaml),
[external](examples/values-external.yaml) или [mixed](examples/values-mixed.yaml).
Замените домены и Secret references. Все параметры находятся на верхнем уровне,
без оболочки `controlPlane:` или `runtime:`. Значения по умолчанию требуют настройки
ключей и паролей перед установкой.

```sh
helm lint helm -f my-values.yaml --strict
helm template dnk-runtime-core helm -f my-values.yaml
helm upgrade --install dnk-runtime-core helm \
  --namespace dnk-runtime-core --create-namespace -f my-values.yaml \
  --wait --wait-for-jobs --timeout 20m
```

Runtime сохраняет tenant authentication, `CONTROL_PLANE_API_KEY` и `dnk-manage`.
Перед установкой задайте управляющий API key, SMTP и постоянные пароли инфраструктуры.
Ingress направляет `/api` в FastAPI, остальные пути — в Console. Runtime миграции
выполняются атомарной пачкой под advisory lock; существующие tenant-схемы сохраняются.

Любую инфраструктурную зависимость можно переключить на внешний сервер отдельно:
`enabled: false` и параметры `external`. Для внешнего Redis поддерживается URL
`redis://` или `rediss://` из Secret. Сохраняйте существующие БД, пользователей и
Redis logical database при переходе; смена значений в chart не меняет пароль уже
инициализированной БД.

## Secrets и HTTPS

Секрет задаётся через `value` **либо** `existingSecret: {name, key}` в namespace
релиза. Chart не генерирует ключи и отвергает конфликтующие источники. Registry
credentials передаются через `global.imagePullSecrets`; они доступны также
миграционным Jobs и ожидающим initContainer. Содержимое внешних Secrets не
отслеживается: после ротации выполните явный rollout затронутых workloads.

`application.server.publicOrigin` должен быть HTTPS origin. По умолчанию используются
существующие `IngressClass nginx` и `ClusterIssuer letsencrypt-production`.
cert-manager создаёт сертификат по аннотации Ingress. Для готового TLS Secret задайте
`ingress.tls.clusterIssuer: ""` и `ingress.tls.secretName`. Chart не устанавливает
системные контроллеры. Маршруты сохраняют исходные пути, без rewrite-target.

## Миграции, обновление и откат

Миграционный Job выполняется при install/upgrade и полном ArgoCD Sync. Workloads
ожидают успешный Job с актуальным deployment token; устаревший, отсутствующий или
неуспешный Job не открывает барьер. В ArgoCD инфраструктура разворачивается раньше
миграций, приложения — после них. Повторный полный Sync пересоздаёт Job, selfHeal
не удаляет успешно завершённую миграцию. `global.deployment.revision` связывает
барьер и rollout с ревизией Git. `migrations.enabled: false` используется только
при внешнем управлении миграциями.

Для существующего самостоятельного релиза сохраняйте release name, namespace,
values, Secret references, `fullnameOverride` и PVC. Версия 0.3.2 меняет расположение
chart и его метаданные, сохраняя имена и поведение ресурсов. StatefulSet PVC остаются
после удаления релиза; используйте постоянные credentials при повторной установке.

Прежняя umbrella-установка не переключается автоматически на два релиза: сохраните
её прежний chart/образы до отдельного переноса владения ресурсами. Не устанавливайте
самостоятельные релизы поверх ресурсов существующей umbrella. Откат возвращает
сохранённые chart, values и образы предыдущего релиза.

ArgoCD example: [Application](../deploy/argocd/dnk-runtime-core.yaml), путь источника — `helm`.
Имена релизов, ресурсов и namespaces в примере сохранены.

## Упаковка и проверки

Прямые команды Helm работают без подготовительного скрипта:

```sh
helm package helm --destination dist/helm
```

Обёртка дополнительно проверяет структуру и локальные зависимости, копирует chart
во временный каталог и не меняет исходники:

```sh
python helm/build.py --destination dist/helm
python -m unittest discover -s helm/tests -p 'test_*.py' -v
python helm/tests/smoke.py
```

`Chart.yaml` и `Chart.lock` фиксируют версии локальных инфраструктурных charts.
Обновляйте исходники зависимости и её версию в `Chart.yaml` отдельным изменением.
Для обновления `Chart.lock` запустите `helm dependency update --skip-refresh` на
временной копии `helm/` и перенесите обратно только lockfile; сгенерированные архивы
не добавляйте рядом с исходниками тех же dependencies. Обычная упаковка не вызывает
dependency update. `.helmignore` исключает тесты, примеры и Python tooling
из архива. Результат — `dist/helm/dnk-runtime-core-0.3.2.tgz`.

Smoke создаёт и удаляет собственный Kind-кластер и собирает только образы этого
репозитория. `--reuse-test-images` использует заранее собранные локальные теги
`dnk-test/*:helm-test`; это явный режим для локальных проверок. Подробные результаты
и границы проверок — в [VALIDATION.md](VALIDATION.md).

Транзакции и tenant migrations проверяются отдельно:

```sh
python helm/tests/runtime_migrations_integration.py --runtime-image dnk-test/runtime:helm-test
```
