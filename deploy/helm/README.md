# DNK Platform — Helm и ArgoCD

`dnk-platform` устанавливает два независимых приложения: Django/Nuxt Control Plane
и FastAPI/Vue Runtime. В обоих пакетах есть backend, frontend, Nginx gateway,
PostgreSQL, Redis и отдельная Job миграций. Runtime также включает RabbitMQ и
publisher worker; console worker выключен по умолчанию.

Это новая установка. Старые имена Helm-релиза не переносятся автоматически.
Python-проект Core теперь называется `dnk-control-plane`; каталог `core`, импорты
`dnk_core`, настройки `CORE_*`, схема `core` и адреса опубликованных образов сохранены.

## Структура

```text
deploy/helm/dnk-platform/
  values.yaml                         # global, controlPlane, runtime
  charts/
    dnk-common/                       # общая библиотека барьера миграций
    dnk-control-plane/                # самостоятельно устанавливаемый chart
      charts/postgresql/
      charts/redis/
    dnk-runtime-core/                 # самостоятельно устанавливаемый chart
      charts/postgresql/
      charts/redis/
      charts/rabbitmq/
deploy/argocd/
  dnk-platform.yaml
  dnk-control-plane.yaml
  dnk-runtime-core.yaml
```

Все настройки доступны в [общем values.yaml](dnk-platform/values.yaml).
При самостоятельной установке используются
[Control Plane values](dnk-platform/charts/dnk-control-plane/values.yaml) или
[Runtime values](dnk-platform/charts/dnk-runtime-core/values.yaml), без внешнего
ключа `controlPlane` или `runtime`. Глобальные registry credentials и deployment
revision задаются в `global`. Внутренний `global.migrations.coordinator` оставьте
равным значению по умолчанию соответствующего chart.

`application` содержит настройки продукта; `backend`, `frontend`, `gateway` —
образы, реплики, ресурсы, probes и размещение pods. У runtime добавлена группа
`workers`; publisher включён, console включается отдельно. `migrations` управляет
ожиданием БД и блокировки, ожиданием Jobs, сроком выполнения Job и повторами.
`postgresql`, `redis`, `rabbitmq` независимо переключаются на внешние сервисы
через `enabled: false`. Отключение встроенного RabbitMQ означает внешнее подключение;
отключение событий задаётся `application.events.enabled` вместе с workers.

Неизвестные поля и некорректные сочетания проверяются JSON Schema и шаблонами.
`backend.extraEnv` поддерживает `valueFrom`; дублировать управляемые переменные
нельзя. Секретные дополнительные переменные также задавайте через `secretKeyRef`.

## Образы

| Компонент | Образ по умолчанию |
| --- | --- |
| Control Plane backend | `ghcr.io/dinikon/runtime/core:latest` |
| Control Plane frontend | `ghcr.io/dinikon/runtime/frontend-core:latest` |
| Runtime backend и workers | `ghcr.io/dinikon/runtime/runtime:latest` |
| Runtime frontend | `ghcr.io/dinikon/runtime/frontend-runtime:latest` |
| Оба gateway | `nginx:1.27-alpine` |

У опубликованных образов `pullPolicy: Always`. Gateway использует конфигурацию
из chart, отдельный gateway-образ собирать не нужно. Для своей сборки из корня
репозитория:

```sh
docker build -f core/Dockerfile -t my-registry/dnk-control-plane:my-tag .
docker build -f frontends/apps/core/Dockerfile --target runtime -t my-registry/frontend-core:my-tag frontends
docker build -f Dockerfile -t my-registry/dnk-runtime-core:my-tag .
docker build -f frontends/Dockerfile -t my-registry/frontend-runtime:my-tag frontends
```

Публикация образов не выполняется этим chart. Для приватного GHCR создайте
namespace и registry Secret в нём. Подготовьте закрытый файл
`ghcr-dockerconfig.json` с Docker `auths` для `ghcr.io` и credentials с правом чтения
пакетов (файл со ссылкой только на локальный credential helper не подходит):

```sh
kubectl create namespace dnk-platform
kubectl -n dnk-platform create secret generic ghcr-pull \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson="$SECRETS_DIR/ghcr-dockerconfig.json"
```

Укажите `global.imagePullSecrets: [{name: ghcr-pull}]`. При самостоятельных установках
Secrets должны находиться в namespace каждого релиза. Registry credentials
используются также Jobs и ожидающими initContainer у frontend/gateway.

## Secrets, HTTPS и почта

Поддерживается единый формат: `value` **либо** `existingSecret: {name, key}`.
Одновременно задавать оба источника нельзя. Пустые поля по умолчанию не являются
готовыми паролями; chart ничего не генерирует. Для production используйте Secrets
и не коммитьте их значения в Git или values.

Подготовьте файлы с постоянными значениями в закрытом каталоге, например `$SECRETS_DIR`.
Django key можно получить через `secrets.token_urlsafe(64)`, Fernet key — через
`cryptography.fernet.Fernet.generate_key()`. Сохраните результат один раз. Команды
создания Secrets ниже читают файлы, чтобы значения не попадали в аргументы:

```sh
kubectl -n dnk-platform create secret generic control-plane-credentials \
  --from-file=django-secret-key="$SECRETS_DIR/django-secret-key" \
  --from-file=mfa-encryption-key="$SECRETS_DIR/mfa-encryption-key" \
  --from-file=postgres-password="$SECRETS_DIR/control-plane-postgres-password" \
  --from-file=redis-password="$SECRETS_DIR/control-plane-redis-password" \
  --from-file=smtp-password="$SECRETS_DIR/smtp-password"
kubectl -n dnk-platform create secret generic runtime-credentials \
  --from-file=control-plane-api-key="$SECRETS_DIR/control-plane-api-key" \
  --from-file=postgres-password="$SECRETS_DIR/runtime-postgres-password" \
  --from-file=redis-password="$SECRETS_DIR/runtime-redis-password" \
  --from-file=rabbitmq-password="$SECRETS_DIR/rabbitmq-password" \
  --from-file=smtp-password="$SECRETS_DIR/smtp-password"
```

Не добавляйте перевод строки в файлы ключей/паролей. Настройки примеров содержат
имена `replace-me-*`: замените их созданными именами, включая TLS и registry Secret.
Внешний Ingress controller, TLS certificate Secret, DNS и рабочий SMTP предоставляет
оператор. `application.server.publicOrigin` — один источник URL и hostname для
Ingress, gateway и Control Plane Nuxt; production требует HTTPS.

Gateway доверяет `X-Forwarded-Proto` входящего Ingress и сохраняет Host/forwarded
headers; прямой публичный обход доверенного proxy следует исключить сетевой
конфигурацией кластера. Control Plane направляет `/api`, `/accounts`, `/admin`,
`/static` в Django; остальные маршруты в Nuxt. Django-статика включена в образ.
Runtime направляет `/api` в FastAPI, остальные пути в статический Vue frontend.
Chart заменяет встроенную frontend-конфигурацию с Compose-host `api`. Для HTTPS
runtime gateway добавляет `Secure`, `HttpOnly`, `SameSite=Lax` к session cookie
текущего опубликованного образа.

ConfigMap содержит несекретные настройки и скрипты. Значения секретов поступают
через `secretKeyRef`; Redis/RabbitMQ URL преобразуются в окружении Python wrapper
без вывода credentials и без передачи их в command/args. Изменение конфигураций
chart обновляет соответствующие pods. Изменение содержимого внешнего Secret
не отслеживается: выполните явный rollout после ротации.

## Установка целиком или отдельно

Примеры values:

- [Всё встроено](examples/values-embedded.yaml).
- [Вся инфраструктура внешняя](examples/values-external.yaml).
- [Смешанный режим](examples/values-mixed.yaml).

Скопируйте пример в собственный файл и замените placeholders. PostgreSQL, Redis
и RabbitMQ каждого пакета по умолчанию имеют отдельные Services и диски. Чтобы
использовать общий внешний сервер, явно настройте оба пакета, желательно с разными
БД/пользователями и Redis logical databases. Для внешнего Redis можно передать
полный `redis://` или `rediss://` URL из Secret, для RabbitMQ — `amqp://` или
`amqps://` URL либо host/port/auth. При использовании URL удалите отдельно заданные
host/password. В runtime URL определяет Redis DB и SSL.

```sh
python deploy/helm/build.py
helm lint deploy/helm/dnk-platform -f my-values.yaml
helm upgrade --install dnk-platform deploy/helm/dnk-platform \
  --namespace dnk-platform --create-namespace -f my-values.yaml \
  --wait --wait-for-jobs --timeout 20m
```

Установить только Control Plane через общий chart:

```sh
helm upgrade --install dnk-control deploy/helm/dnk-platform \
  --namespace dnk-control --create-namespace -f my-values.yaml \
  --set runtime.enabled=false --wait --wait-for-jobs --timeout 20m
```

Либо напрямую, с отдельным values без внешнего ключа:

```sh
helm upgrade --install dnk-control deploy/helm/dnk-platform/charts/dnk-control-plane \
  --namespace dnk-control --create-namespace -f control-plane-values.yaml \
  --wait --wait-for-jobs --timeout 20m
helm upgrade --install dnk-runtime deploy/helm/dnk-platform/charts/dnk-runtime-core \
  --namespace dnk-runtime --create-namespace -f runtime-values.yaml \
  --wait --wait-for-jobs --timeout 20m
```

Встроенная инфраструктура рассчитана на одну реплику, без автоматической HA.
PostgreSQL 16, Redis 7 (AOF), RabbitMQ 3.13 используют StatefulSets и PVC.
`persistence.storageClass: null` выбирает default StorageClass; `""` отключает выбор
класса. `existingClaim` использует существующий writable PVC. Созданные через
`volumeClaimTemplates` PVC сохраняются после uninstall; для переустановки сохраните
имя релиза/ресурса и исходные credentials. Автоматическая смена пароля уже
инициализированного PostgreSQL/RabbitMQ не поддерживается.

## Миграции и обновления

| ArgoCD wave | Ресурсы |
| --- | --- |
| -30 | ConfigMap, Secrets, ограниченный RBAC |
| -20 | Встроенные БД, Redis, RabbitMQ и их Services |
| -10 | Migration Jobs: `Sync`, `BeforeHookCreation` |
| 0 | Приложения, workers, frontend, gateway, Ingress |

Это `Sync` hooks: `PreSync` не позволил бы подготовить встроенную БД при первой
установке. В Helm Job является обычным ресурсом, имя включает `.Release.Revision`;
Helm hook-аннотаций нет. Job остаётся после успеха, без TTL и `HookSucceeded`.

Каждое приложение имеет initContainer ожидания. Общий chart автоматически задаёт
ему Jobs всех включённых пакетов; standalone ждёт только свою Job. Допуск требует
`Complete=True`, отсутствия `deletionTimestamp` и совпадения deployment token.
Отсутствие Job или другая revision вызывает ожидание; `Failed=True` блокирует запуск.
ServiceAccount может только `get` конкретных Jobs, а API token смонтирован только
в ожидающий initContainer. Основные контейнеры не получают этот token.

Control Plane выполняет имеющуюся в опубликованном образе `prepare_deployment`:
ожидание PostgreSQL, session advisory lock, создание отсутствующей схемы `core`,
миграции Django на соединении, удерживающем lock. Сброса схем нет.

Runtime выполняет runner из ConfigMap: одна транзакция и одно соединение, advisory
lock, создание отсутствующих общих таблиц, затем Alembic для всех tenant-схем.
Ошибка откатывает всю пачку; после получения блокировки переподключений нет.
Отсутствующая tenant-схема считается ошибкой. Версионируемых миграций существующих
`public`-таблиц пока нет: bootstrap создаёт отсутствующие таблицы, но не изменяет
структуру уже существующих.

`waitTimeoutSeconds` ограничивает ожидание PostgreSQL/lock,
`gateTimeoutSeconds` — ожидание Jobs, `activeDeadlineSeconds` — полную длительность
Job, `backoffLimit` — повторы после ошибки. Старые работающие pods при ошибке новых
миграций специально не останавливаются. Для безопасного rolling upgrade миграции
должны быть совместимы с предыдущей версией приложения. Helm rollback не откатывает
схему БД; перед обновлением сделайте резервную копию. Для обычного Helm failed release
повторите через `helm upgrade`, чтобы получить новую revision/Job.

## ArgoCD

Основной файл: [dnk-platform.yaml](../argocd/dnk-platform.yaml).
Самостоятельные варианты: [Control Plane](../argocd/dnk-control-plane.yaml),
[Runtime](../argocd/dnk-runtime-core.yaml). Установите один подходящий вариант;
не направляйте одновременно несколько Applications на одни ресурсы.

Замените domains, SMTP, ingress class и все `replace-me-*` ссылки в `helm.values`.
Создайте Secrets в целевом namespace до полного Sync. Настройте ArgoCD доступ к
приватному SSH repository и AppProject `productions`, разрешающий repository и
целевой namespace. Сохраните charts и вложенные библиотечные архивы в Git на
`targetRevision`: ArgoCD читает удалённый repository. Затем примените выбранный
Application обычным процессом GitOps.

Helm parameter передаёт `$ARGOCD_APP_REVISION` в `global.deployment.revision`.
Новая Git revision меняет token и pod annotations: новые pods подтягивают `latest`.
Публикация только нового `latest` не запускает deployment автоматически; обновите
Git revision. Для воспроизводимых обновлений можно задать неизменяемые теги.

Контракт синхронизации (интеграционный стенд закреплён на ArgoCD v3.1.8):

- Полный Sync, новая Git revision, Helm install/upgrade запускают миграции заново.
- Полный Sync той же revision повторяет Job, но не перезапускает pods, если их
  шаблон не изменился.
- SelfHeal той же revision — частичная синхронизация без hooks; использует сохранённую
  успешную Job. Если Job удалена вручную, выполните полный Sync для восстановления.
- Selective Sync не запускает hooks. Для установки и миграций нужен полный Sync;
  `ApplyOutOfSyncOnly=true` не задавайте.

См. [phases и waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
и [build environment](https://argo-cd.readthedocs.io/en/stable/user-guide/build-environment/).

## Диагностика и проверки

```sh
kubectl -n dnk-platform get pods,jobs,pvc
kubectl -n dnk-platform logs job/dnk-platform-dnk-control-plane-migrate-r1
kubectl -n dnk-platform logs job/dnk-platform-dnk-runtime-core-migrate-r1
kubectl -n dnk-platform logs deploy/dnk-platform-dnk-control-plane-backend -c wait-migrations
kubectl -n dnk-platform describe job dnk-platform-dnk-runtime-core-migrate-r1
kubectl -n dnk-platform exec -it deploy/dnk-platform-dnk-control-plane-backend -c backend -- \
  python src/manage.py createsuperuser
```

Для Helm upgrades подставьте текущую release revision в имя Job. При ошибке проверьте
наличие Secrets, доступность БД, полномочия пользователя на схему, статусы Jobs,
deployment token и timeout. Не удаляйте успешную Job для обычного масштабирования.

```sh
python -m pip install PyYAML==6.0.3 SQLAlchemy==2.0.48
python -m unittest discover -s deploy/helm/tests -p 'test_*.py' -v
python deploy/helm/build.py --destination dist/helm
```

CI выполняет строгий YAML/schema/render contract, lint и упаковку всех трёх charts.
Интеграционные scripts в `deploy/helm/tests/` используют отдельные disposable kind
и PostgreSQL окружения, проверяют Helm/ArgoCD и атомарность runtime migration batch.
Они не должны использовать рабочий Kubernetes context. Результаты фактического
локального прогона фиксируются в `deploy/helm/VALIDATION.md`.
