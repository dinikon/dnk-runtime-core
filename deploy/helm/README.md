# Helm: Core

Chart `dnk-runtime-core` разворачивает полный Core: Django/Gunicorn, Nuxt/Nitro,
Nginx gateway и, по выбору, PostgreSQL и Redis. Runtime будет добавлен следующим
подпакетом. RabbitMQ и MinIO текущему Core не нужны и этим chart не создаются.

Требуются Helm 3.19+ (chart API v2), Kubernetes 1.25+, доступные кластеру образы,
StorageClass либо подготовленные PVC. Для публичного доступа нужны существующий
Ingress-контроллер, DNS и TLS Secret. Chart не устанавливает контроллер,
cert-manager или SMTP-сервер.

## Пакеты и настройки

```text
deploy/helm/dnk-runtime-core/                 # общий пакет
  charts/core/                              # самостоятельный Core
    charts/postgresql/                      # один PostgreSQL 16
    charts/redis/                           # один Redis 7 с AOF
```

Все defaults и комментарии есть в `dnk-runtime-core/values.yaml`, а также в
`dnk-runtime-core/charts/core/values.yaml`. Они одинаковы, кроме префикса `core`
в общем пакете. `core.enabled=false` отключает Core и всю его инфраструктуру
при установке общего пакета. Defaults сами по себе намеренно не устанавливаются:
нужно заполнить публичный origin, теги образов, постоянные ключи и пароли.

| Группа | Назначение |
| --- | --- |
| `application.server` | Единый публичный origin, Host, proxy, язык/часовой пояс |
| `application.security`, `application.mfa` | Постоянные ключи и политика факторов |
| `application.auth`, `application.sessions` | Регистрация, способы входа, лимиты, сессии |
| `application.email`, `application.providers` | SMTP и внешние провайдеры авторизации |
| `backend`, `frontend`, `gateway` | Образы, replicas, Services, ресурсы, probes, pod-настройки |
| `ingress` | Существующий controller class, annotations, TLS Secret |
| `migrations` | Автоматическая подготовка схемы и время ожидания БД/блокировки |
| `postgresql`, `redis` | Встроенный сервис или внешнее подключение, credentials и диски |

Для каждого компонента `pod` содержит `annotations`, `labels`,
`securityContext`, `containerSecurityContext`, `imagePullSecrets`, `nodeSelector`,
`tolerations`, `affinity`. Не переопределяйте selector labels. Backend и frontend
публикуются только как ClusterIP; gateway также поддерживает NodePort/LoadBalancer.
Обычные annotations и probes настраиваются отдельно для каждого Deployment.

Дополнительное окружение Django задаётся в `backend.extraEnv` в формате
Kubernetes `EnvVar`, включая `valueFrom`. Переменные, которыми управляет chart,
повторять нельзя. Эти же дополнительные переменные получает initContainer
миграций. Пример TLS для внешнего PostgreSQL с системными корневыми сертификатами:

```yaml
core:
  backend:
    extraEnv:
      - name: PGSSLMODE
        value: verify-full
      - name: PGSSLROOTCERT
        value: system
```

Настройки приложения преобразуются в существующие `CORE_*`; Nuxt получает только
`NUXT_PUBLIC_SITE_URL`. Значения не загружаются из `.env`: chart задаёт
`CORE_ENV_FILE=""`. Полный контракт приложения описан в `core/.env.example`.

## Сборка образов

Команды выполняются из корня репозитория. Замените registry и tag своими:

```sh
docker build -f core/Dockerfile -t registry.example.com/dnk-core:0.1.0 .
docker build -f frontends/apps/core/Dockerfile --target runtime -t registry.example.com/dnk-core-web:0.1.0 frontends
docker build -f frontends/apps/core/Dockerfile --target gateway -t registry.example.com/dnk-core-frontend:0.1.0 frontends
```

Образы должны быть опубликованы в registry либо заранее загружены в тестовый
кластер. Для приватного registry задайте `pod.imagePullSecrets` нужных компонентов.
Django-образ уже содержит static; запуск `collectstatic` и общий диск для static
не требуются. Образ должен включать новую команду `prepare_deployment`.

## Secrets

Каждое секретное поле имеет единую форму:

```yaml
secretKey:
  value: ""                  # явное значение для создаваемого chart Secret
  existingSecret:
    name: core-credentials   # либо имя существующего Secret
    key: django-secret-key   # и ключ внутри него
```

Нельзя одновременно задавать `value` и `existingSecret`. Chart не генерирует ключи
или пароли. В production обязательны постоянный Django secret и отдельный
Fernet key для MFA. Потеря/замена Fernet key лишает доступа к сохранённым факторам.
Секреты из `value` входят в состояние Helm-релиза; для рабочих установок удобнее
передавать ссылки на существующие Secrets. Все Secrets находятся в namespace релиза.

Пример создания Secret для подготовленных values. Пароли ниже генерируются
однократно в приватном временном файле; для настоящего SMTP подставьте пароль
провайдера. Сохраните рабочие ключи в используемом менеджере секретов до удаления
временного файла:

```sh
kubectl create namespace dniko
umask 077
python3 - <<'PY'
import base64
import os
import secrets
from pathlib import Path

Path('/tmp/dniko-core-secrets.env').write_text('\n'.join([
    'django-secret-key=' + secrets.token_urlsafe(64),
    'mfa-encryption-key=' + base64.urlsafe_b64encode(os.urandom(32)).decode(),
    'postgres-password=' + secrets.token_urlsafe(32),
    'redis-password=' + secrets.token_urlsafe(32),
    'smtp-password=REPLACE_WITH_SMTP_PASSWORD',
]) + '\n')
PY
# Замените SMTP-пароль перед следующей командой.
kubectl -n dniko create secret generic core-credentials --from-env-file=/tmp/dniko-core-secrets.env
rm /tmp/dniko-core-secrets.env
```

TLS Secret `core-tls` создайте из сертификата выбранного публичного домена или
предоставьте через уже используемую автоматизацию сертификатов.

## Установка

Скопируйте подходящий пример и заполните реальные registry, теги, origin,
SMTP-параметры и ссылки на Secrets:

- `examples/values-embedded.yaml`: оба сервиса внутри релиза.
- `examples/values-external.yaml`: оба сервиса внешние.
- `examples/values-mixed.yaml`: внешняя PostgreSQL, встроенный Redis.

Каждый пример самодостаточен поверх defaults. Четвёртая комбинация получается
из embedded-примера через `redis.enabled=false` и `redis.external.host`.

```sh
helm lint deploy/helm/dnk-runtime-core -f my-values.yaml
helm upgrade --install dniko deploy/helm/dnk-runtime-core \
  --namespace dniko --create-namespace -f my-values.yaml --wait --timeout 10m
```

Подпакет устанавливается независимо:

```sh
# core-values.yaml содержит те же настройки без внешнего ключа core.
helm upgrade --install dniko-core deploy/helm/dnk-runtime-core/charts/core \
  --namespace dniko --create-namespace -f core-values.yaml --wait --timeout 10m
```

Все зависимости локальные и включены в исходный chart. Внешние Helm-репозитории
и загрузка сторонних subcharts не требуются. Упаковка обоих вариантов:

```sh
helm package deploy/helm/dnk-runtime-core --destination /tmp
helm package deploy/helm/dnk-runtime-core/charts/core --destination /tmp
```

Для проверки origin и отправки писем production использует `debug=false`, HTTPS
и SMTP. Для изолированного теста допустимо явно выбрать console email backend;
тогда письма доступны в логах, а не доставляются адресатам.

## Внешние подключения и хранение

`postgresql.enabled=false` выбирает `postgresql.external.host/port`. Имя базы,
пользователь и пароль остаются в `postgresql.auth`. Пользователю нужны права на
создание/использование схемы `core` и миграции. Остальные схемы не изменяются.
Миграции требуют прямого подключения или session pooling; transaction pooling
(PgBouncer) несовместим с session advisory lock.

`redis.enabled=false` выбирает `redis.external.host/port` и `redis.auth.password`.
Для ACL/TLS вместо них задайте `redis.external.url.value` либо
`redis.external.url.existingSecret`; URL вида `rediss://user:password@host:6379/1`
хранится в Secret. URL нельзя одновременно задавать с host/password; его DB index
имеет приоритет над `redis.database`. Встроенный Redis имеет 16 logical databases.

Каждый встроенный сервис работает в одном StatefulSet с отдельным PVC.
`persistence.storageClass: null` использует default StorageClass, `""` отключает
динамический provisioning. `existingClaim` подключает подготовленный PVC и не
создаёт новый; в этом случае настройки размера и StorageClass не применяются.
`persistence.enabled=false` использует временный `emptyDir` для тестов.

PVC из `volumeClaimTemplates` сохраняется при uninstall. Повторная установка
с теми же namespace/release/names использует прежние данные; сохраните прежние
credentials. Chart не увеличивает существующие PVC автоматически, не выполняет
major upgrade PostgreSQL, backup или HA. Изменение `auth.password` не меняет пароль
в уже инициализированной PostgreSQL — ротация выполняется отдельно согласованно
с Secret. Для существующих PVC требуются подходящие права файлов: PostgreSQL
Alpine UID/GID 70, Redis Alpine UID 999/GID 1000; настройки доступны в `pod`.

## HTTPS, миграции и обновления

Маршрутизация: Ingress → gateway → Django/Nuxt. Ingress должен перезаписывать
поступающие извне `X-Forwarded-Proto`/`X-Forwarded-For`; gateway сохраняет схему
HTTPS и добавляет свой proxy hop. `trustedProxyCount=2` соответствует этой цепочке;
если цепочка другая, измените значение. Не открывайте backend в обход доверенного
proxy. При отключённом Ingress настройте свой доверенный HTTPS proxy перед gateway.

Перед каждым backend pod запускается initContainer `migrate` из того же образа.
Он ждёт PostgreSQL, получает стабильный session advisory lock для `core`, создаёт
отсутствующую схему и выполняет Django migrations на том же соединении. Основной
контейнер стартует только после успеха. `waitTimeoutSeconds` ограничивает ожидание
подключения и lock, а не длительность самой миграции. При потере соединения
команда завершается ошибкой; Kubernetes может повторить initContainer.

Для миграций, управляемых снаружи, задайте `migrations.enabled=false` и заранее
выполните ту же команду с production-настройками. Нельзя включать reset-scaffold,
fake migrations или автоматический downgrade в процедуру установки.

Обновляйте теги образов и повторяйте `helm upgrade --install ... --wait`.
Изменения создаваемых ConfigMap/Secrets обновляют checksum в pod template.
Изменение содержимого существующего внешнего Secret требует перезапуска затронутых
workloads. При PostgreSQL-ротации сначала согласуйте пароль в самой БД.
Rolling update предполагает совместимость миграций с предыдущим приложением.
`helm rollback` возвращает манифесты/образы, но не откатывает данные и схему БД.

## Диагностика и проверки

```sh
kubectl -n dniko get pods,pvc
kubectl -n dniko logs deploy/dniko-core-backend -c migrate
kubectl -n dniko logs deploy/dniko-core-backend -c backend
kubectl -n dniko describe pod <pod-name>
kubectl -n dniko exec -it deploy/dniko-core-backend -c backend -- python src/manage.py createsuperuser
```

Readiness/liveness Django обращаются к `/api/capabilities/` с публичным Host и
HTTPS-заголовком; это проверка HTTP-приложения, а не мониторинг PostgreSQL/Redis.
Nuxt проверяется через `/`, gateway — через `/_healthz`. Для операционного контроля
зависимостей используйте существующий мониторинг кластера.

CI проверяет матрицу встроенных/внешних подключений, типы и обязательные values,
Secret references, Ingress, отключение Core, lint и package обоих entrypoints.
Отдельный smoke-тест создаёт собственный kind-кластер и приватный kubeconfig,
проверяет первую установку, HTTPS через тестовый TLS proxy, обновление, несколько
реплик, persistence и удаляет свой кластер. Манифест Ingress проверяется отдельно;
smoke не устанавливает production Ingress-контроллер.

```sh
python3 -m pip install PyYAML
python3 -m unittest discover -s deploy/helm/tests -p 'test_*.py' -v
python3 deploy/helm/tests/smoke.py --help
```

Тесты новой команды миграций включены в стандартный Django suite. PostgreSQL-тесты
используют только новую disposable базу через `TEST_CORE_POSTGRES_URL` с CREATEDB.
