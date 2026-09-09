# Runtime Helm

Репозиторий владеет самостоятельно устанавливаемым chart `dnk-runtime-core` версии 0.3.1:
FastAPI, Vue Console, publisher worker, миграции и необязательные PostgreSQL, Redis, RabbitMQ.
[Настройки и эксплуатация](dnk-runtime-core/README.md). ArgoCD example: `deploy/argocd/dnk-runtime-core.yaml`.

```sh
python -m pip install PyYAML==6.0.3 SQLAlchemy==2.0.48
python helm/build.py
python -m unittest discover -s helm/tests -p 'test_*.py' -v
python helm/build.py --destination dist/helm
```

Сборка проверяет точные версии, SHA256 архивов и содержимое библиотеки `dnk-common`.
Упаковка выполняется во временной копии и не меняет отслеживаемые файлы.
Исходники библиотеки находятся в Control Plane; здесь хранится неизменяемый
`charts/dnk-common-0.3.0.tgz`. Версия, исходная ревизия и контрольные суммы записаны
в `dependencies.lock.json`. Не запускайте `helm dependency update` в рабочем chart:
межрепозиторные зависимости устанавливаются из проверенных архивов, без registry.

При обновлении common получите архив из release artifacts Control Plane, проверьте
его SHA256, замените единственный архив в `charts/`, обновите dependency version,
`Chart.lock` и provenance manifest. Для изменения шаблонов нужен новый номер версии common.
После тестов передайте `dnk-runtime-core-VERSION.tgz` в Control Plane; его umbrella
обновляется отдельным проверяемым изменением. Исходники второго репозитория для
сборки этого chart или образов Runtime не нужны.

Примеры `examples/values-embedded.yaml`, `values-external.yaml`, `values-mixed.yaml`
используют настройки без внешнего ключа `runtime`. Подставьте свои домены и ссылки
на существующие Secrets. Системные IngressClass nginx и cert-manager ClusterIssuer
letsencrypt-production устанавливает оператор. Сохраняйте имя Helm release,
namespace и overrides при переходе с прежнего пути chart: PVC и имена ресурсов
не меняются от переноса файлов. Изменение владельца Helm release — отдельная операция.

```sh
python helm/tests/smoke.py
python helm/tests/runtime_migrations_integration.py --runtime-image dnk-test/runtime:helm-test
```

Интеграционные проверки создают собственные disposable Kind/PostgreSQL окружения,
строят только локальные Runtime backend/frontend images и проверяют HTTPS,
миграции, барьер запуска, upgrade и сохранение данных. Текущий Kubernetes context
не используется. Общий Helm/ArgoCD smoke платформы находится в Control Plane.
