# Проверка разделения репозиториев — 2026-09-09

Исходный runtime commit: `9bd217c23630e69ffaef9ce3749205755e0dfb34`.
Каркас control-plane: `ebcfd913ddde22c435bb994f2186874e388e9cb2`.
Проверки выполнялись на Python 3.13.9, Node 24, PostgreSQL 16, Helm 3.19.0 и
одноразовых Kubernetes kind-кластерах. Рабочие PostgreSQL/Redis не использовались
для тестов с изменением данных.

| Проверка | Результат |
| --- | --- |
| Независимые frozen Python/npm installs | Пройдены для обоих репозиториев |
| Runtime backend с PostgreSQL | 145 пройдено, 1 дополнительный тест пропущен |
| Control-plane backend с PostgreSQL | 202 пройдено |
| Django checks / отсутствие новых migrations | Пройдено |
| Неизменность Django source/tests | 155 файлов совпадают с исходными |
| Runtime OpenAPI до/после | Полное совпадение: 6 путей, 17 схем |
| Console lint, реальный vue-tsc -b, production build | Пройдено |
| Core/UI lint, typecheck, Nuxt/account-assets build | Пройдено |
| Browser: required / optional / passwordless / primary-only phone | 16 + 4 + 4 + 2 сценария пройдено |
| Docker builds | Runtime API, Console, Django, Nuxt, Core gateway пройдены |
| Runtime Helm contracts и packaging | 43 теста пройдено |
| Runtime migration integration | 9 PostgreSQL/container тестов пройдено |
| Standalone Runtime Kubernetes smoke | Ingress/TLS, OTP/cookies/logout, migration barriers, upgrade, restart и сохранение PVC/данных пройдены |
| Семантическое сравнение Helm до/после | 48 сценариев совпадают с учётом версии chart и зависящего от неё checksum |
| Архив Runtime в control-plane | 48/48 файлов совпадают с исходниками chart после нормализации Helm |

Console ранее проверял только references-only tsconfig. Включён `vue-tsc -b`,
исправлены выявленные ошибки типов и два неиспользуемых экспорта отсутствующей
библиотеки. Новых frontend-зависимостей или обновлений их версий нет; итоговые
Console JS/CSS hashes совпадают с прежней сборкой.

## Известная прежняя ошибка

При явном включении `DNK_TEST_DATABASE_URL` тест
`ScheduledJobsConcurrentClaimTests.test_concurrent_workers_do_not_claim_same_postgresql_job`
падает с `sqlalchemy.exc.MissingGreenlet` при чтении `model.updated_at` после flush.
Сбой воспроизведён отдельно на исходном коде с исходным окружением и после разделения.
Он не вызван переносом; бизнес-логика jobs не изменялась. Стандартный CI с
`TEST_POSTGRES_URL` этот дополнительный тест пропускает.

## Локальный переход

Core-контейнеры переведены в Compose project `dnk-control-plane` на той же внешней
сети runtime. Эффективные настройки Core совпадают; идентификаторы аккаунтов и
записи `django_migrations` проверены до и после. Главная и `/api/session/` возвращают
200, а `/api/me/` для гостя — 401. Runtime API, PostgreSQL, Redis и их volumes
сохранены. Прежние Core-образы закреплены тегами `before-split` для отката.

Тестовые Compose/PostgreSQL/kind-ресурсы удаляются после проверок. Инструкция
переключения и отката находится в [repository-split.md](repository-split.md).
Результаты umbrella и ArgoCD находятся в репозитории control-plane.
