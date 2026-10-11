# Files

Tenant-модуль приватного хранения. Реализация и границы: `docs/plan/files.md`.

Следующий этап — [файловый менеджер в Admin Console](../plan/files.md#следующий-этап-файловый-менеджер-в-admin-console):
список/поиск/пагинация по дискам, загрузка, корзина с восстановлением и
автоочисткой через 30 дней. Domain/persistence, API чтения, мутации и worker/recovery
реализованы; интерфейс остаётся следующим этапом.

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
`purging`. Изменение состояния через Console и физический per-file worker подключены.
Часовая проверка отправляет истёкшую корзину в очередь. Контракты и дальнейшая последовательность —
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
| FILES__CONSOLE_MAX_UPLOAD_BYTES | максимальный размер одного файла в Console, 104857600 (100 МиБ), положительное число |

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
4. Перезапустить `dnk-manage jobs worker`: dispatcher должен обрабатывать
   `files.purge` и `files.trash.cleanup`; registrar запускается сразу и каждый час.
5. На отдельных тестовых файлах проверить API загрузки/корзины/восстановления/
   окончательного удаления. Admin UI относится к следующему срезу.

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
- `GET /api/console/files/items/` → `items, total, page, page_size`;
  список зарегистрированных файлов в состоянии `ready`.
- `GET /api/console/files/trash/` → отдельный контракт страницы корзины;
  состояния `trashed` и `purging`, даты удаления и срок восстановления.
- `GET /api/console/files/overview/` → количество и размер активных файлов,
  корзины, её части `purging` и четыре категории активных файлов.

Все пять endpoint требуют роль `admin` из trusted tenant principal и разрешение
authorization service `files.read` для `stored_file` без resource ID. Проверка
роли работает и с default allow-all adapter; отказ происходит до открытия UoW.
Credentials/config_ref, ключ объекта и purge job ID не входят в HTTP-контракт.
UI пока доступен в разделе
«Файловые хранилища», показывает системный default и только просмотр.
Объём — сумма размеров готовых зарегистрированных файлов, а не disk usage MinIO.

Оба списка принимают `search` (trim, максимум 255 символов), повторяемый
`bucket_id` (максимум 50 UUID), `category` (`documents|images|videos|other`),
`page` (от 1) и `page_size` (`10|20|50|100`, default 20). Поиск по имени
регистронезависим и буквальный, включая `%`, `_` и `\\`; фильтры соединяются AND.
SQL возвращает страницу и total одним statement. Сортировка: активные файлы
по `created_at DESC, id DESC`, корзина по `deleted_at DESC, id DESC`.
Пустая или вышедшая за пределы страница сохраняет правильный total.

Без фильтра выбираются все готовые диски текущего tenant. Явно выбранный
неподготовленный диск даёт `409`, неизвестный или чужой — одинаковый `404`.
Неверные параметры дают `422`, отсутствие сессии — `401`, отсутствие роли
admin или дополнительного разрешения — `403`. Tenant/actor не принимаются
из query. Для overview действует только `bucket_id`; поиск/категория не
меняют сводку. MIME нормализуется без регистра/пробелов/параметров, документный
набор зафиксирован в `application/stored_file/file_category.py`; audio и
архивы относятся к `other`. Все четыре категории возвращаются даже при нулях.

Новые use cases имеют собственные Query/Handler/DTO, HTTP Response/controller
и именованный Depends. SQL read repository/mapper используют сессию внешнего
UoW; не загружают агрегаты и не выполняют внутренние commit или storage I/O.

HTTP-мутации:

- `POST /api/console/files/items/` → `201 UploadFileResponse`
  (`file_id, name, content_type, size_bytes`); multipart `file`, optional `bucket_id`.
- `DELETE /api/console/files/items/{file_id}/` → `200 TrashFileResponse`
  (`file_id, deleted_at, purge_after`); объект остаётся под прежним ключом.
- `POST /api/console/files/items/{file_id}/restore/` → `200 RestoreFileResponse`
  (`file_id, status=ready`); проверяются срок, готовность диска и owned-объект.
- `DELETE /api/console/files/trash/{file_id}/` → `202` без тела;
  переход в `purging` и отдельная `files.purge` job атомарны в SQL.

Мутации требуют trusted tenant admin, реальный session/flow-bound CSRF
(`Origin`, `X-CSRF-Token`, cookie) и соответствующее действие
`files.upload|trash|restore|purge`. Resource ID — file UUID, для upload — None.
Имя и MIME проверяются Domain; tenant/actor/key/dates не принимаются от клиента.
Request/Response каждого HTTP-метода отделены от Command/DTO; методы без тела
не имеют фиктивных схем. Все переходы существующего файла используют lock;
часы читаются после его получения. Повтор trash/purge сохраняет даты/job.
На границе срока и после запроса purge восстановление возвращает `409`.

Console multipart ограничивается до записи очередной части в spool, включая
приём без Content-Length. Фактический `UploadFile.size` передаётся существующему
upload handler; MIME по умолчанию `application/octet-stream`. Spool переходит
на диск после 1 МиБ и закрывается при успехе, ошибке, обрыве и отмене.
Полное тело ограничено file limit + 64 КиБ; заголовки каждой части — 64 КиБ,
текстовое поле — 1 КиБ, принимаются один файл и максимум один bucket ID.
Лимит превышен — `413`, повреждённый multipart/лишние поля — `422`.
Приём ограничен `FILES__OPERATION_TIMEOUT_SECONDS` (`408` по истечении);
передача в MinIO сохраняет собственный bounded timeout/concurrency.
Helm: `application.files.consoleMaxUploadBytes`; Compose и template env
передают тот же setting. Ingress/proxy должен пропускать file limit плюс
multipart overhead; их внешний upload timeout согласуется с backend.

`202` подтверждает durable запрос; штатный `jobs worker` обрабатывает `files.purge`
и удаляет реестр после физического подтверждения. Для корзины используется
`files.trash.cleanup`, без MinIO TTL. Браузерные формы/AdminLayout относятся к срезу UI.

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

## Корзина: worker и восстановление заданий

`files.trash.cleanup` регистрируется при запуске `jobs worker` и каждый час для
подготовленных существующих tenant без повторного onboarding. Registrars модулей
независимы при сбое. Проверяется штатный admission: `freeze` разрешён текущей
политикой TenantGate; deleting/blocked и exclusive gate откладывают обслуживание.

Порция содержит не более 100 candidate IDs и проверяется заново под write lock.
Domain допускает автоматическое удаление после ровно 720 часов в UTC. Состояние
`purging` и `files.purge` сохраняются одной транзакцией. Keyset continuation
записывается вместе с порцией, сохраняет cutoff/cursor и имеет UUID5 ID от parent
job/cursor. Повтор и restart не теряют следующие страницы и не дублируют jobs.

Для `purging` с missing/terminal (`failed`, `canceled`, `done`) job создаётся новый
ID без изменения дат. `scheduled`/`running` не дублируются; expired leases сначала
восстанавливает shared worker. Задания с исчерпанными попытками восстанавливаются
ближайшим часовым проходом. Новое окно начинает сканирование с начала реестра.

Purge worker использует собственные admission/tenant UoW, lock файла и проверки
worker lease до выполнения/перед commit. Старые file job IDs и исчезнувшие записи —
no-op. MinIO port удаляет все owned-версии и delete markers точного ключа, проверяет
bucket tags и metadata каждой версии и подтверждает отсутствие повторным listing.
Бакет и соседние ключи остаются. SQL-запись удаляется только после подтверждения.
Отмена ждёт SDK перед освобождением gate/row lock.

При outage запись остаётся `purging`; shared jobs планируют retry. При сбое SQL
после physical delete повтор допускает отсутствие объекта или owned-бакета.
Потеря lease откатывает SQL, новая доставка повторяет подтверждение.
Очистка не гарантирует удаление в точную секунду: при исправном worker запрос
появится на ближайшей часовой проверке, задержка удаления зависит от очереди/MinIO.

Метрики worker: `files_trash_backlog_files`/`files_trash_backlog_bytes`
(`tenant_id`, `state=expired|pending`), `files_trash_max_purge_delay_seconds`
(старейший overdue срок, включая ожидающие purge),
`files_trash_queued_total` (`kind=new|recovery`), `files_purge_deliveries_total`
(`outcome=committed|stale|deferred|retryable_failure|exhausted`) и
`files_purge_duration_seconds`. Backlog обновляется после commit и отражает
последний scan данного процесса; между проходами это не live quota, а samples
удалённых tenant исчезают после перезапуска процесса. Итоги не содержат имён,
payload/config/SDK responses. Состояния повторов видны также в shared jobs.

Исправлена регистрация обеих hourly Files jobs: проверка таблицы завершает свою
lookup-транзакцию до UoW, поэтому INSERT не откатывается при освобождении admission.

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
`test/test_files_workers_postgres.py` — purge/версии/ownership, 30-дневная граница,
111 кандидатов/continuation, crashes/outages/lease/cancellation, обе регистрации,
штатный recovery/exhausted и повтор без объекта/бакета.
`test/test_files_architecture.py` — полнота 16 сценариев, DTO, зависимости,
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

Срез Read API проверен отдельно: 28 прикладных/HTTP/PostgreSQL/Domain/
архитектурных тестов прошли на текущем Files с изолированной регистрацией
моделей. Регрессия из 96 тестов с настоящими PostgreSQL/MinIO/Redis/RabbitMQ
прошла на текущем Files поверх последнего коммита остальных модулей.
Black, compile и аудит архитектуры/diff выполнены. Общий прогон текущего
workspace остановился на отсутствующем `Catalog product_type_block` в
параллельно изменяемой tenant metadata; совместная проверка окончательной
версии этих изменений остаётся ограничением. Мутации, Admin UI и purge worker
в Read API срез не входят; рабочие tenant-схемы не изменялись.

Срез HTTP-мутаций: 109 регрессионных тестов Files/PostgreSQL/MinIO/миграций/
архитектуры/регистрации/jobs/удаления tenant прошли на текущем Files поверх
последнего коммита остальных модулей; 98 Helm tests успешны. Проверены реальные
CSRF/action permissions, атомарность file/job, concurrent purge requests,
двойная проверка срока restore вокруг storage I/O, rollback после job INSERT
и на commit, пустые/одинаково названные файлы, streaming limit, timeout,
закрытие spool, ошибки storage/ownership и OpenAPI. Black, compile и полный
архитектурный аудит выполнены. Совместный прогон workspace остановился на
параллельно изменяемой Catalog-миграции (`is_variation`: boolean с integer default);
сами файловые операции в успешном прогоне проверены на одноразовых сервисах.
На момент среза 3 worker и Admin UI ещё не были поставлены; рабочие данные не изменялись.


Срез worker/recovery: 121 регрессионный тест прошёл с текущим Files поверх
последнего коммита остальных модулей. Последний совместный workspace-прогон:
107/108 успешны, включая Files/worker/jobs; отдельная ошибка Catalog/Currency
migration downgrade затрагивает ожидаемые `currency_exchange_rate_books/quotes`.
Предыдущий совместный прогон также выявил 13 ошибок tenant deletion (включая
subtests): administrator role, отсутствующая cloud_identities и HTTP admission.
Чужие изменения не исправлялись/не откатывались; полный workspace suite пока
не зелёный. Финальные target-проверки: 8 ownership/bucket/registrar/архитектура,
6 boundary/recovery/backlog/архитектура и 18 offline проверок успешны.
Black (178 файлов), compile, scoped diff check и полный архитектурный аудит
16 сценариев выполнены. Все сервисы одноразовые и удалены; рабочие данные и
rollout не затрагивались. Следующий срез — Admin Console UI.
