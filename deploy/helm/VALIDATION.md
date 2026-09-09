# Проверка DNK Platform 0.3.0

Изменение: прямой системный Ingress класса `nginx`, cert-manager ClusterIssuer
`letsencrypt-production`, отсутствие gateway pods и сохранение HTTPS session cookie
Runtime через ASGI adapter из chart.

Локально прошёл 61 автоматический тест: строгий YAML, JSON Schema, Helm lint,
упаковка трёх charts, прямые маршруты с нестандартными портами Services,
автоматические/существующие TLS Secrets, коллизии имён сертификатов, блокировка
конфликтующих аннотаций, session/logout cookies и прежние контракты миграций.

Для фактической проверки Ingress и сертификатов:

```sh
python deploy/helm/tests/smoke.py --published-images --system-ingress
```

Стенд использует собственный kind-кластер, ingress-nginx 1.13.3 и cert-manager 1.18.2.
Issuer с именем `letsencrypt-production` в этом стенде подписывает сертификаты
изолированным тестовым CA: проверяются ingress-shim, Certificate, TLS Secrets,
маршрутизация и HTTPS. Публичные ACME/DNS и рабочий ClusterIssuer не изменяются.
Эти версии контроллеров закреплены только для воспроизводимого теста.

Прогон `--published-images --system-ingress` завершился успешно:

- Nginx направляет трафик напрямую в Services пяти Deployment приложений.
- Cert-manager создал оба Certificate и TLS Secret; issuer, домены и статус
  `Ready=True` проверены, HTTPS проверяется с доверенным тестовым CA.
- Прошли маршруты обоих frontend, Control Plane API/login/admin/static,
  настоящий Runtime OTP-вход, Secure/HttpOnly/SameSite cookie, `/me` и logout.
- Опубликованный Runtime запускается через `python -m uvicorn`: это сохраняет
  путь к исходникам при загрузке ASGI adapter из ConfigMap.
- Неверная/отсутствующая Job блокирует новые pods обоих пакетов. Upgrade создаёт
  новые Jobs и запускает по три backend-реплики.
- После перезапуска инфраструктуры и переустановки самостоятельных пакетов
  сохранились PostgreSQL public/tenant данные, Redis, RabbitMQ и все пять PVC.
  Финальная установка standalone использовала исправленную команду запуска;
  HTTPS/OTP проверены повторно.

Тестовый kind-кластер и временный kubeconfig удалены. Публичный выпуск через
Let's Encrypt не проверяется без реальных DNS и доступа к рабочему issuer.
CI обновлён для повторения этого сценария с локально собранными образами.

## Архив результатов предыдущего этапа 0.2.0

Ниже результаты до удаления gateway; они относятся к версии 0.2.0.


Локальный прогон 2026-09-09: Helm 3.19.0, kind 0.29.0, Kubernetes 1.33.1,
Python 3.13, опубликованные образы `ghcr.io/dinikon/runtime/{core,runtime,frontend-core,frontend-runtime}:latest`.
Интеграционные стенды используют временные kubeconfig, собственные kind-кластеры
и тестовые credentials. Рабочий кластер и опубликованные образы не изменяются.

## Автоматические проверки

Прошли 54 теста: 48 комбинаций рендеринга для трёх installable charts,
включение/отключение пакетов и инфраструктуры, inline/existing Secrets,
внешние Redis/AMQP(S) URL, Ingress, scopes RBAC, токены и состояния migration gate,
негативные конфигурации, коллизии длинных имён и совпадение umbrella/standalone defaults.
Проверены строгий YAML без повторяющихся ключей, JSON Schema, Helm lint и
автономная установка из каждого архива без загрузки зависимостей.
`uv lock --check --offline --directory core` подтвердил переименование Python-проекта.

В отдельном PostgreSQL с опубликованным runtime-образом прошли 9 интеграционных
проверок runner: bootstrap и повторный запуск, настоящие Alembic tenant migrations,
параллельные процессы, один backend PID/transaction/lock, откат всей пачки при
ошибке второго tenant, таймауты глобальной/tenant-блокировок, утрата соединения
без переподключения. Тестовые контейнеры и сеть удалены.

## Kubernetes / Helm

Полный smoke-прогон завершился успешно:

- Первый install обоих пакетов: семь Deployment, пять StatefulSet, две Job;
  по две backend-реплики у каждого приложения.
- Настоящий OTP-вход runtime через тестовый TLS proxy: Secure/HttpOnly/SameSite
  cookie, авторизованный `/me`, logout и отклонение завершённой сессии.
- HTTPS-маршруты Nuxt/Vue, Control Plane API, login, admin и static.
- Неверный token и отсутствующая runtime Job удерживают новые pods всех семи
  workloads; восстановленный успешный Job разрешает запуск.
- Helm upgrade создаёт две Job revision 2 и увеличивает backend до трёх реплик.
- После перезапуска пяти инфраструктурных pods сохранились PostgreSQL public/
  tenant-сентинелы, ключи обеих Redis и тестовый RabbitMQ vhost.
- После uninstall сохранились UID всех пяти PVC. Оба самостоятельных charts
  переустановлены с этими дисками; данные и HTTPS-вход проверены повторно.

## ArgoCD

Полный прогон на настоящем ArgoCD v3.1.8 в отдельном kind-кластере завершился
успешно. Проверены:

- Первая установка: инфраструктура готова до Jobs, обе миграции завершены
  до создания Deployment приложений.
- Повторный полный Sync заменяет обе Job, сохраняя UID работающих pods,
  если шаблоны pods не менялись.
- `selfHeal` восстанавливает изменённое число реплик и сохраняет обе успешные Job.
- Задержанная миграция Control Plane удерживает wave 0; при масштабировании
  все семь workloads обоих пакетов остаются в ожидающем initContainer.
  Освобождение блокировки позволяет завершить Sync и запуск приложений.
- Ошибка миграции не применяет новые шаблоны приложений; старые pods продолжают
  работать. Следующая Git-ревизия повторяет миграции и обновляет все семь Deployment.
- После восстановления повторно проверены HTTPS-маршруты обоих приложений,
  настоящий OTP-вход runtime, Secure-cookie и logout.

Тестовый кластер, локальный Git Service и временный kubeconfig удалены.

## Воспроизведение

Установите Docker, Helm, kind, kubectl, Python, curl и openssl. Скрипты сами
создают и удаляют тестовые окружения; текущий Kubernetes context не используется.

```sh
python -m pip install PyYAML==6.0.3 SQLAlchemy==2.0.48
python deploy/helm/build.py
python -m unittest discover -s deploy/helm/tests -p 'test_*.py' -v
python deploy/helm/tests/smoke.py --published-images
python deploy/helm/tests/runtime_migrations_integration.py
python deploy/helm/tests/argocd_smoke.py --published-images
python deploy/helm/build.py --destination dist/helm
```

`--published-images` использует уже доступные опубликованные образы; для приватного
GHCR нужен предварительный Docker login. Без этого флага smoke скрипты собирают
локальные тестовые образы. CI использует локальную сборку и не публикует её.
ArgoCD-стенд закреплён на v3.1.8; repository для него — временная локальная Git-копия,
доступная через тестовый Git Service, без push в GitHub.

## Границы проверки

TLS проверяется через отдельный тестовый proxy, имитирующий доверенный Ingress;
выбор production Ingress controller, DNS, сертификатов и SMTP остаётся настройкой
окружения. Проверка не отправляет реальную почту. Версионирование существующих
runtime public-таблиц и обратные миграции схем не входят в этот этап.
