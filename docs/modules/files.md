# Files

Tenant-модуль приватного хранения. Реализация и границы: `docs/plan/files.md`.

Следующий этап — [файловый менеджер в Admin Console](../plan/files.md#следующий-этап-файловый-менеджер-в-admin-console):
список/поиск/пагинация по дискам, загрузка, корзина с восстановлением и
автоочисткой через 30 дней. Первый срез Domain/persistence реализован;
новые API, worker и интерфейс остаются следующими этапами.

## Состояния файлов и корзина

`StoredFile` поддерживает `uploading → ready → trashed → purging → purged`.
Корзина хранит исходный объект под прежним ключом. `deleted_at`, `deleted_by`
и `purge_after` фиксируют удаление и срок ровно 720 часов в UTC; повторное
удаление не продлевает его. Восстановление возможно строго до срока и только
из `trashed`. В `purging` записаны `purge_requested_at` и `purge_job_id`;
подтверждение устаревшей job отклоняется. Замена job сохраняет даты корзины.

Write repository предоставляет `get_for_update` на сессии внешнего UoW:
ожидающий lock читает актуальную запись, включая refresh ранее загруженной ORM-модели.
`purged` используется только в Domain после подтверждения удаления storage;
затем `remove(aggregate)` удаляет SQL-запись в той же транзакции. Промежуточный
`save` состояния `purged` запрещён SQL-ограничением.

Tenant-миграция `0021_files_lifecycle` сохраняет старые записи и добавляет
поля/ограничения/индексы. Её downgrade блокирует таблицу перед проверкой и
отказывается терять записи `trashed`/`purging`. Применение к рабочим схемам
в рамках реализации не выполнялось.

Существующее внутреннее чтение и статистика дисков учитывают только `ready`.
Orphan cleanup защищает все зарегистрированные ключи, включая `trashed` и
`purging`. Сами Console-операции корзины и автоматический запуск purge по сроку
ещё не подключены. Контракты и дальнейшая последовательность —
[в плане](../plan/files.md#выполненный-срез-1-domain-и-persistence).

## Конфигурация Instance

`DnkConfig.FILES` читает переменные проекта:

| Переменная | Назначение / default |
| --- | --- |
| FILES__ENDPOINT | обязательный host:port без scheme/path |
| FILES__ACCESS_KEY | обязательный secret |
| FILES__SECRET_KEY | обязательный secret |
| FILES__SECURE | TLS, true |
| FILES__REGION | optional, пустая строка |
| FILES__TIMEOUT_SECONDS | HTTP connect/read, 30; максимум 60 |
| FILES__OPERATION_TIMEOUT_SECONDS | передача файла, 600; максимум 600 |
| FILES__CONCURRENCY | число одновременных SDK операций, 4 |

Нужны права на создание, tags, policy inspection, перечисление и удаление
бакетов/объектов/версий/multipart uploads в namespace `dnk-tenant-*`.
Этот namespace используется только Files. Пустой бакет без tags может быть
принят после незавершённого создания; непустой или чужой tagged-бакет отвергается.

Helm передаёт настройки через `application.files`. Access key и secret key
поддерживают `existingSecret` либо `value` по общему контракту secrets chart.
Helm не создаёт внешний MinIO: его DNS, TLS и network isolation готовятся на Instance.
В Compose MinIO подключён к `file-storage` (`internal: true`); backend и workers
имеют доступ к этой сети по `minio:9000`. API и консоль опубликованы только на
`127.0.0.1`, порты задаются `MINIO_API_PORT` (9000) и `MINIO_CONSOLE_PORT` (9001).
Для публикации локальных портов MinIO дополнительно подключён к отдельной bridge
сети `file-storage-local`: Docker не публикует порты контейнера, подключённого
только к internal-сетям. Другие сервисы к локальной сети не подключаются.
Control Plane override отключает публикацию портов через `!reset []` и оставляет
MinIO только в `file-storage` через `!override [file-storage]`.
Для локального запуска backend используется `FILES__ENDPOINT=127.0.0.1:9000`
(либо выбранный API-порт) и `FILES__SECURE=false`. Значения `.env` в текущем
workspace не изменяются автоматически.

После изменения Compose пересоздайте только MinIO: `docker compose up -d minio`.
Проверка с хоста: `curl -f http://127.0.0.1:9000/minio/health/live` (либо выбранный
API-порт). Если `create_tenant.py` уже завершился ошибкой на подготовке хранилища,
tenant остаётся в статусе `provisioning`. Продолжите его создание командой
`dnk-manage files resume <tenant_uuid>`, вместо повторного создания tenant.

## Rollout и восстановление

1. Подготовить закрытый MinIO и настройки для backend, jobs и Control Plane worker.
2. Применить tenant-миграции: `dnk-manage tenant-migrations upgrade --all`.
3. Зарегистрировать и подготовить бакеты старых Tenant:
   `dnk-manage files prepare --all` либо `dnk-manage files prepare <tenant_uuid>`.
4. Проверить Console `/files`, затем подключать потребителей.

`files prepare` не меняет tenant status. `files resume <tenant_uuid>` продолжает
local onboarding и активирует Tenant после готовности бакета. Для Control Plane
Tenant повторная установка проходит штатным worker; local resume их отклоняет.
При ошибке CLI выводит tenant ID и тип ошибки без credentials и SDK response.

SQL downgrade не удаляет физические данные. Перед откатом миграции нужно
явно удалить tenant storage штатным процессом удаления Tenant либо сохранить
данные для восстановления. Нельзя удалять реестр, оставляя дальнейшую очистку
без координат бакетов.

## API Console

- `GET /api/console/files/providers/` → массив `id, name, kind, is_system`.
- `GET /api/console/files/buckets/?provider_id=<uuid>` → массив
  `id, provider_id, name, status, files_count, size_bytes`.

Оба endpoint требуют authenticated principal и используют текущую tenant-схему.
Credentials/config_ref не входят в HTTP-контракт. UI доступен в разделе
«Файловые хранилища», показывает системный default и только просмотр.
Объём — сумма размеров готовых зарегистрированных файлов, а не disk usage MinIO.

## Контракт потребителя

В своём Application слой потребитель объявляет порт загрузки/чтения и собственный
DTO. Infrastructure adapter вызывает `UploadFileHandler`/`GetFileContentHandler`
через внешнюю сборку `build_files_handlers(session, resolver)`.
Сессия передаётся из того же tenant UoW, в котором сохраняется бизнес-ссылка.
Схема должна быть привязана к trusted tenant, а TenantGate удерживаться до
завершения операции; module handler не открывает и не фиксирует UoW.
При ошибке загрузки потребитель откатывает UoW целиком.

Upload принимает BinaryIO, точный размер, filename, MIME и optional bucket ID;
возвращает file UUID и метаданные. Источник должен поддерживать ограниченное
чтение `read(n)`. Проверяются слишком короткие и слишком длинные источники,
включая нулевую длину; SDK передаёт крупные файлы multipart без чтения целиком.

Get возвращает управляемый async stream с порциями до 64 KiB и метаданными.
Поток независим от DB-сессии, но caller сохраняет admission до окончания чтения.
Используйте `try/finally: await result.stream.aclose()` и при раннем прекращении
отдачи. Отсутствующий ID и ID другого tenant дают `FileNotFoundError`.
Конкретный бизнес-модуль выбирает download endpoint, ACL, Content-Disposition,
Content-Type и cache policy. Files не знает о товарах, контактах или документах.

## Обслуживание

Jobs worker регистрирует `files.cleanup` каждый час; первая job создаётся
в SQL-транзакции onboarding. Cleanup касается только ready-бакетов и объектов
старше 24 часов, owned по имени/tags/metadata, без записи в файловом реестре.
Также abort выполняется для старых multipart uploads с module UUID key.
Защитный интервал больше максимального времени upload.

Для установленного MinIO используется собственное обслуживание multipart:
его S3 lifecycle action `AbortIncompleteMultipartUpload` не поддерживается
этой версией сервера. См. [S3 compatibility MinIO](https://minio.community/community/minio-object-store/reference/s3-api-compatibility.html).
Python SDK 7.2.20 предоставляет list/abort multipart только private methods;
они изолированы в адаптере, версия закреплена `uv.lock`, совместимость покрывают
реальные интеграционные проверки. При обновлении SDK повторить эти проверки.

Purge Tenant очищает физическое хранилище прежде schema drop. Сбой MinIO
оставляет Tenant заблокированным для повторной попытки и сохраняет реестр.
Storage adapters работают вне event loop; отмена ожидает завершения текущего
SDK вызова, чтобы его внешние эффекты не продолжались после release admission.

## Проверки

`test/test_files.py` — инварианты, размеры, расширяемый resolver, потоки/отмена.
`test/test_files_lifecycle.py` — 30-дневная граница, DST/UTC, фабрики, повторы,
замена job и устаревшие подтверждения.
`test/test_files_lifecycle_postgres.py` — миграция с данными, guarded downgrade,
ограничения, rollback, условное удаление, locks и конкурентные restore/purge.
`test/test_files_architecture.py` — полнота сценариев, DTO, зависимости,
аннотации/docstrings, фабрики и границы транзакций.
`test/test_files_postgres.py` — настоящие PostgreSQL/MinIO: пустые и multipart
файлы, tenant isolation, private access, rollback/orphan cleanup, provisioning
retry, ownership, purge и безопасный read-only HTTP.
Тестовые сервисы `scripts/cicd/check_environment.py` создаются изолированно
и удаляются после запуска. Проверки Control Plane, tenant deletion, Identity
и миграций покрывают интеграцию с жизненным циклом Tenant.

Проверки этой реализации: 80 сценариев Files/Tenancy/Control Plane/Identity/
миграций успешно выполнены; пропущенная Redis namespace проверка отдельно
успешно выполнена на disposable Redis. Архитектура и module registration
проверены отдельно; 98 offline Helm tests прошли. Console прошёл `vue-tsc -b`,
ESLint, Vite build и Chromium QA с API fixtures на ширинах 1440 и 390 px:
статистика, read-only controls, refresh, error, empty state, отсутствие overflow.
Полный backend suite первоначально выполнил 674 теста и выявил ошибку только
в новом cancellation mock; она исправлена и сценарий повторно прошёл.
Production rollout и браузерное подключение к реальному Instance в этот запуск
не выполнялись. Google Drive и endpoints потребителей остаются следующими этапами.

Срез Domain/persistence корзины проверен отдельно: 81 уникальный тест Files,
миграций, архитектуры, регистрации модулей, scheduled jobs и удаления tenant
прошёл после обновления ожидаемого tenant head. Изолированные сервисы удалены.
Новые Console API/UI, purge worker и production rollout в этот срез не входят.
