# Проверка Runtime после разделения

Проверено локально 2026-09-09: Helm 3.19.0, Kind 0.29.0, Kubernetes 1.33.1,
Python 3.13.9, PyYAML 6.0.3 и SQLAlchemy 2.0.48.

| Проверка | Результат |
| --- | --- |
| `python -m unittest discover -s helm/tests -p 'test_*.py' -v` | 43 теста прошли |
| `python helm/build.py --destination dist/helm` | `dnk-runtime-core-0.3.1.tgz` успешно собран |
| `python helm/tests/runtime_migrations_integration.py --runtime-image dnk-test/runtime:helm-test` | 9 PostgreSQL/container тестов прошли |
| `python helm/tests/smoke.py --reuse-test-images` | Standalone Kind smoke прошел; кластер удален |

Офлайн проверки охватывают YAML/schema/render, версии и SHA256 зависимостей,
совпадение common-library, отказ при измененном архиве или дублирующем subchart,
а также отсутствие изменений исходников после упаковки.

В изолированном Kind проверены настоящий nginx Ingress и cert-manager с тестовым CA,
OTP-вход, session cookie Secure/HttpOnly/SameSite, logout, барьер отсутствующей или
устаревшей migration Job, upgrade, перезапуск StatefulSet и повторная установка
с прежними PVC и сохраненными данными PostgreSQL, Redis и RabbitMQ.

Проверка транзакций охватывает конкурирующие batches/CLI, advisory locks, потерю
соединения, откат всей пачки при сбое второго tenant, повторный bootstrap и
сохранение существующих данных. Все БД и контейнеры этой проверки были временными.

Для Kind использованы локальные образы из разделенного проекта, заранее помеченные
`dnk-test/runtime:helm-test` и `dnk-test/frontend-runtime:helm-test`.
Обычный запуск без `--reuse-test-images` собирает их из текущего репозитория.
Текущий Kubernetes context и работающий локальный Compose-стенд не изменялись.

Дополнительно сопоставлены 48 вариантов рендера прежней и новой структуры
(16 Runtime, 16 Control Plane, 16 umbrella). После ожидаемого повышения версии
app/platform charts до 0.3.1 результаты совпадают: имена, selectors, PVC,
миграции и контракты конфигурации сохранены. Проверка общего ArgoCD принадлежит
репозиторию Control Plane и здесь не заявляется.
