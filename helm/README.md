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

## Один runtime для многих тенантов

Один Helm-релиз обслуживает все tenant-домены через общие backend/frontend Services.
Задайте `ingress.hosts: ['*.dniko.app']`: для каждого совпавшего домена `/api`
с `pathType: Prefix` направляется в backend, `/` — во frontend. Например:

```text
https://tenant1.dniko.app/       → frontend Service
https://tenant1.dniko.app/api/…  → backend Service, Host: tenant1.dniko.app
https://acme2.dniko.app/         → тот же frontend Service
https://acme2.dniko.app/api/…    → тот же backend Service, Host: acme2.dniko.app
```

Готовый overlay: [values-multitenant.yaml](examples/values-multitenant.yaml).
Применяйте его поверх настроенных values с вашими существующими Secrets и инфраструктурой:

```sh
helm lint helm -f my-values.yaml -f helm/examples/values-multitenant.yaml --strict
helm template dnk-runtime-core helm \
  -f my-values.yaml -f helm/examples/values-multitenant.yaml
```

`ingress.hosts` содержит доменные имена без протокола, порта и пути. Пустой список
сохраняет прежнее поведение: один hostname из `application.server.publicOrigin`.
Непустой список полностью определяет hosts в `rules` и `tls`, без автоматического
добавления `publicOrigin`. Можно указать несколько wildcard-зон и точных имён;
сертификат должен покрывать весь список.

`application.server.publicOrigin` остаётся конкретным HTTPS origin, например
`https://runtime.dniko.app`, а не `https://*.dniko.app`. В текущем chart его схема
также включает Secure-флаг session cookie. Этот параметр не выбирает тенанта
и не задаёт API URL фронтенда. Зарезервируйте служебный hostname отдельно от имён тенантов.

Перед применением overlay настройте:

1. **DNS:** wildcard-запись `*.dniko.app` на публичный адрес Ingress controller
   (A/AAAA или CNAME на его DNS-имя). На одном сервере это может быть его внешний IP,
   если порты 80/443 действительно обслуживает Ingress controller. Внутренний IP
   backend Service для DNS не подходит. Создание нового тенанта внутри этой зоны
   не требует отдельной DNS-записи или изменения Helm.
2. **TLS:** сертификат на `*.dniko.app`. Для Let’s Encrypt нужен DNS-01 solver
   у ClusterIssuer с доступом к DNS-зоне. Overlay использует существующий
   `letsencrypt-production`; сначала добавьте ему Cloudflare DNS-01 по
   [инструкции](../deploy/cert-manager/README.md). HTTP-01 для остальных имён
   сохраняется. Runtime chart не создаёт и не обновляет ClusterIssuer.
   Issuer только с HTTP-01 wildcard не выпустит. Для готового сертификата укажите
   `clusterIssuer: ''` и имя TLS Secret в namespace runtime. При наличии issuer
   cert-manager создаёт и обновляет Secret, указанный в `secretName`.
3. **Ingress controller:** используйте существующий `IngressClass` и сохраняйте
   исходный `Host` при передаче в backend. Не задавайте `rewrite-target`,
   `upstream-vhost` или перенаправление всех tenants на `runtime.dniko.app`.
   FastAPI уже содержит префикс `/api`; удаление этого префикса сломает endpoints.
   Backend/frontend Services остаются `ClusterIP`.
4. **Control-plane:** зарегистрируйте конкретный `tenant1.dniko.app` в runtime
   при создании тенанта (`tenant_domain.host`, без `https://` и `/api`). Wildcard
   Ingress пропускает запросы, а runtime ищет точное имя в `tenant_domains`.
   Запись `*.dniko.app` в этой таблице не заменяет регистрацию отдельных тенантов.

Console уже использует относительный `VITE_API_BASE_URL=/api` по умолчанию.
Оставьте его относительным при сборке frontend image; значение с другим доменом
нарушит эту схему. При открытии `tenant1.dniko.app` UI вызывает
`GET /api/console/tenants/resolve` на том же домене. Runtime возвращает
`exists` и `available`: неизвестное имя даёт `exists: false`, а активный тенант
на активном домене — `available: true`. Страница login получает ответ и выбирает
состояние формы. Сейчас недоступный workspace отображается вместо формы ввода email;
сетевой сбой также отображается как недоступный workspace.

Отдельный API-домен и CORS для такой схемы не требуются. Поле `api_host` в resolve
остаётся частью ответа, но Console не переключает по нему адрес API. Session cookie
не имеет `Domain` и остаётся привязана к текущему домену; не расширяйте её на
`.dniko.app`. Backend дополнительно проверяет tenant/domain/host сессии.

После установки проверьте `/` и `/api/console/tenants/resolve` на зарегистрированном
`tenant1.dniko.app` и на незарегистрированном имени этой зоны. На обоих доменах `/`
должен загрузить UI; resolve второго должен вернуть JSON с `exists: false`,
а не HTML или Ingress 404.
Wildcard `*.dniko.app` в Ingress покрывает один уровень имён: он не включает
`dniko.app` и `a.b.dniko.app`. Для доменов клиента вне этой зоны нужны отдельные
DNS, host-правило и TLS-покрытие.

Справка: [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/),
[cert-manager DNS-01](https://cert-manager.io/docs/configuration/acme/dns01/),
[cert-manager Ingress](https://cert-manager.io/docs/usage/ingress/).

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
