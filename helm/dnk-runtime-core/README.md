# DNK Runtime Core

Самостоятельный пакет FastAPI, Vue и publisher worker с системным Ingress. По умолчанию включены собственные PostgreSQL 16, Redis 7 и RabbitMQ 3.13. Console worker включается через `workers.console.enabled`; CronJobs не создаются.

При установке этого каталога настройки из `values.yaml` передаются без префикса. В общем пакете `dnk-platform` они находятся под `runtime`. Общие инструкции, примеры и подготовка Secrets: [Helm README](../README.md).

```sh
helm upgrade --install runtime ./helm/dnk-runtime-core \
  --namespace dnk-runtime --create-namespace --values runtime-values.yaml --wait --timeout 15m
```

До установки задайте HTTPS `application.server.publicOrigin`, `application.security.controlPlaneApiKey`, рабочий SMTP и пароли инфраструктуры. Все секретные поля принимают `value` или `existingSecret: {name, key}`. Secrets должны существовать в namespace релиза. `global.imagePullSecrets` применяется ко всем образам; каждый workload дополнительно принимает `pod.imagePullSecrets`.

`postgresql.enabled`, `redis.enabled`, `rabbitmq.enabled` независимо выбирают встроенный сервис или внешнее подключение. PostgreSQL принимает host/port и `auth`. Redis дополнительно принимает `external.useSsl` и `auth.username`, либо `external.url` с полным `redis://`/`rediss://` URL; база из URL заменяет `redis.database`. RabbitMQ принимает host/port/useSsl и `auth.username/password/vhost`, либо секретный AMQP(S) URL. URL не сочетается с host, password или useSsl; username/vhost RabbitMQ в этом режиме игнорируются. Query-параметры и fragment URL не поддерживаются. Credentials URL кодируются и передаются только через окружение, без подстановки в аргументы процесса.

PVC, созданные StatefulSet, сохраняются после удаления релиза. `persistence.existingClaim` подключает существующий диск; `storageClass: null` использует default StorageClass, `""` отключает выбор StorageClass. Redis использует AOF. Для RabbitMQ сохраняется `/var/lib/rabbitmq`, включая состояние брокера. Изменение `auth.password` не меняет пароль уже инициализированных PostgreSQL/RabbitMQ. HA и автоматическая ротация не предусмотрены.

Перед приложениями выполняется отдельная Job: одна транзакция на одном PostgreSQL-соединении, advisory lock, создание отсутствующих общих таблиц и Alembic-миграции всех tenants. Любая ошибка откатывает всю пачку. Существующие общие таблицы не изменяются: для них в этом этапе нет версионируемых миграций. Миграции должны быть совместимы с предыдущим приложением; Helm rollback не откатывает БД.

Job сохраняется после успешного выполнения. Все workload pods ожидают `Complete=True` у Jobs текущего развёртывания; в umbrella они ждут обе миграции. Только initContainer ожидания получает токен с правом `get` конкретных Jobs. Настройки таймаутов и повторов находятся в `migrations`.

FastAPI и workers используют опубликованный runtime-образ без пересборки: ConfigMap содержит запускающий Python-скрипт и migration runner. В `backend.extraEnv` можно добавить `valueFrom`; управляемые переменные переопределять запрещено. Workers имеют независимые настройки image/replicas/resources/pod и необязательные `probes.startup/readiness/liveness` с полным Kubernetes probe. Frontend получает статическую Nginx-конфигурацию для SPA. Системный Ingress направляет `/api` в backend; ASGI adapter из ConfigMap сохраняет Secure/HttpOnly/SameSite session cookie при HTTPS без пересборки опубликованного образа.

ArgoCD использует Sync waves и сохраняемую Sync Job с `BeforeHookCreation`. Новый Git revision передаётся через `global.deployment.revision` и меняет pod template. Один только push образа `latest` не запускает обновление. Полный Sync повторяет Job; selfHeal той же версии использует сохранённый успех. Для диагностики смотрите состояние Job и логи контейнера `migrations`; credentials в ошибках runner не выводятся.

По умолчанию: `ingress.className: nginx`, `ingress.tls.clusterIssuer: letsencrypt-production`. Cert-manager создаёт TLS Secret; gateway pods не создаются.
