# Files: план и принятые решения

Первый этап ниже описывает существующее приватное хранилище. Следующий этап —
[файловый менеджер в Admin Console](#следующий-этап-файловый-менеджер-в-admin-console).
Статус следующего этапа на 2026-10-11: запланирован, реализация не начата.

## Границы первого этапа

Files — низкоуровневый tenant-модуль: подключения, приватные контейнеры,
реестр файлов и потоковые операции. Один Instance использует свой MinIO;
каждый Tenant получает системное подключение и один приватный бакет.
Подключение `is_system=true` использует проектный Config, который читает `.env`.
Credentials не сохраняются в tenant-таблицах и не возвращаются клиенту.

Console показывает подключения, бакеты, число файлов и объём. Первый этап
целиком read-only: без форм подключения, создания бакетов и редактирования.
Системное подключение отмечено `Default / System`.

Google Drive остаётся следующим этапом: расширение через реестр адаптеров,
отдельную конфигурацию, модель credentials и собственные capabilities.
Имена контейнеров MinIO не следует переносить на папки Drive.

## Архитектурный перечень

Нормативный источник — `docs/architecture/AGENTS.md`.

- Aggregate Roots: `StorageProvider`, `Bucket`, `StoredFile`.
- Структура: `domain/<aggregate>/`, `application/<aggregate>/command|query/`,
  `infrastructure/<aggregate>/persistence/`, `presentation/<aggregate>/`.
- Domain IDs используют `EntityIdVO`; DTO и persistence явно преобразуют UUID.
- Domain использует явные `create/restore`; состояние изменяют доменные методы.
  `__post_init__` допустим только в Value Objects.
- Application зависит от Domain и абстрактных портов, без SDK, Config, ORM и HTTP.
- Каждый сценарий имеет собственные Command/Query, Handler и DTO результата.
  Для результата `None` отдельный DTO отсутствует.
- Persistence mapper преобразует модели; repositories не фиксируют транзакции.
- HTTP Response отделён от Application DTO. GET без body не требует Request.
- Внешняя сборка передаёт одну сессию UoW всем репозиториям процесса.
- Все методы аннотированы; классы и методы документированы; `__init__.py` пусты.
- Межмодульное взаимодействие проходит через Application contracts и адаптеры.
- Функциональные проверки дополняются отдельной проверкой архитектурных границ.

## Сценарии и обязательные контракты

| Сценарий | Вход | Результат | HTTP / сборка |
| --- | --- | --- | --- |
| register_system_storage | tenant_id | RegisterSystemStorageResultDTO | Tenancy adapter |
| provision_system_bucket | tenant_id, bucket_id | ProvisionSystemBucketResultDTO | onboarding / management |
| upload_file | tenant_id, BinaryIO, size, name, MIME, optional bucket_id | UploadFileResultDTO | adapter потребителя |
| get_file_content | tenant_id, file_id | GetFileContentResultDTO со stream | adapter потребителя |
| list_providers | tenant_id | tuple[ProviderListItemDTO, ...] | GET providers, controller, response, Depends |
| list_buckets | tenant_id, optional provider_id | tuple[BucketListItemDTO, ...] | GET buckets, controller, response, Depends |
| cleanup_orphaned_objects | tenant_id, older_than | CleanupOrphanedObjectsResultDTO | scheduled job |
| purge_tenant_storage | tenant_id | None | tenant deletion adapter |
| activate_tenant (Tenancy) | tenant_id | None | local onboarding / Control Plane |

Для каждого сценария в Files предусмотрены `command.py` либо `query.py`,
`handler.py` и собственный `dto.py`, кроме purge. Порты внешнего хранилища и
проекций находятся в `application/port/`. Доменные repository contracts —
в соответствующих Aggregate Roots. Сборка — `infrastructure/assembly.py`;
HTTP Depends создают обработчики на сессии внешнего UoW.

## Хранение и транзакции

Tenant-схема содержит `files_providers`, `files_buckets`, `files_registry`.
SQL-миграция `0020_files` создаёт структуры без сетевых обращений.
Provider хранит ссылку `system_minio`; конфигурация приходит из `DnkConfig.FILES`.
IDs системных provider/bucket детерминированы от tenant UUID.
Имя бакета — `dnk-tenant-<tenant_uuid_hex>`; ключ файла — UUID без исходного имени.

Onboarding разделён на сохраняемые этапы:

1. SQL: Tenant `provisioning`, домен, tenant-схема, системный provider, бакет
   `preparing`, администратор, первая job обслуживания. Commit снаружи.
2. MinIO: идемпотентное создание, ownership tags, проверка отсутствия публичной
   policy; затем бакет `ready` и внешний commit.
3. Проверка готовности, доменная активация Tenant; Control Plane дополнительно
   проверяет owner/cloud binding и fencing token.

Сбой MinIO сохраняет первый этап для повторной попытки. Control Plane
повторяет попытки штатным worker; local onboarding продолжает `files resume`.
Старые активные Tenant получают хранилище командой `files prepare` после миграций.
Management не активирует Tenant, которыми управляет Control Plane.

Upload участвует в UoW вызывающего модуля и не выполняет внутренних commit.
Бизнес-ссылка и запись реестра откатываются вместе. MinIO не участвует в SQL
транзакции: физический объект после rollback удаляет обслуживание через 24 часа.
Максимальная длительность передачи ограничена 600 секундами.
Потребитель удерживает tenant admission на время файловой операции.

Очистка запускается hourly, перечисляет объекты порциями и удаляет только старые
owned-объекты без записи в реестре. Также прерывает старые незавершённые multipart
uploads. Зарегистрированные файлы не удаляются по отсутствию бизнес-ссылок.
Статистика показывает готовые записи реестра без orphan/multipart/служебных расходов.

Удаление Tenant сначала получает exclusive admission, удаляет owned-бакеты,
включая версии и multipart uploads, и только затем удаляет schema/global records.
Чужие ownership tags блокируют удаление; повторное удаление своих ресурсов безопасно.

## Доставка файла

Files возвращает backend-потребителю поток и технические метаданные. Files не
публикует бинарный HTTP endpoint, presigned URL и redirect. Потребляющий модуль
проверяет доступ к своей сущности, получает файл через адаптер и отдаёт поток
через собственный endpoint. Ответственность за бизнес-ACL и HTTP-заголовки лежит
на этом модуле. Поток обязательно закрывается при EOF, ошибке или отмене.

MinIO доступен только backend/worker. Docker Compose использует отдельную
internal network. В dev Compose по отдельному запросу разрешены только loopback
порты 9000/9001 для PyCharm. Для их публикации MinIO в dev также подключён к
отдельной bridge-сети `file-storage-local`, в которой нет других сервисов.
Control Plane override отключает порты через `!reset []` и убирает локальную
сеть через `!override [file-storage]`.
Для внешнего MinIO в Kubernetes
эквивалентную изоляцию обеспечивает инфраструктура Instance.

## Этапы реализации и приёмка

1. Domain/ports/use cases и SQL registry, tenant metadata registration.
2. MinIO adapter: потоковое чтение, multipart upload, размеры, таймауты,
   bounded concurrency, освобождение соединений и ownership.
3. Durable onboarding и активация; CLI backfill; purge в tenant deletion.
4. Hourly orphan/multipart cleanup на общих jobs.
5. Read-only Console API и UI с загрузкой, ошибкой, empty state и обновлением.
6. Domain, архитектура, реальный PostgreSQL/MinIO, Control Plane, deletion,
   tenant migrations, Console typecheck/lint/build/browser; документация rollout.

В этой итерации потребление Files проверяется тестовым адаптером на общей
транзакции. Подключение конкретных бизнес-модулей выполняется отдельными изменениями.

## Следующий этап: файловый менеджер в Admin Console

### Цель и принятые границы

Перенести раздел файлов в `AdminLayout` и предоставить администратору единый
список файлов всех дисков: поиск, фильтры, пагинацию, загрузку, перемещение
в корзину, восстановление и окончательное удаление. Через 30 дней файлы
из корзины автоматически передаются на физическое удаление.

В коде модуль называется `files`. «Диск» в интерфейсе — существующий `Bucket`,
а подключение — `StorageProvider`. Создание дополнительных подключений/дисков
и интеграция Google Drive остаются отдельным этапом. В текущей конфигурации
будет один системный диск; контракт списка поддерживает несколько дисков.

Источник списка — `files_registry`: файлы, успешно загруженные через Files
в зарегистрированные бакеты текущего tenant. Перечисление физических объектов
MinIO при открытии страницы не требуется. Незарегистрированные объекты после
rollback обслуживает существующая orphan cleanup; импорт произвольных объектов
из MinIO или каталогов ОС в этот этап не входит.

Первый этап остаётся основой: приватность MinIO, tenant isolation, UUID-ключи,
потоковая загрузка и UoW потребителя сохраняются. Новым HTTP-методом будет
загрузка из консоли; скачивание, preview, presigned URL и redirect на MinIO
этим планом не вводятся. Получение содержимого по-прежнему принадлежит
endpoint потребляющего бизнес-модуля.

### Что уже есть и что требуется изменить

| Область | Текущее состояние | Планируемое изменение |
| --- | --- | --- |
| Console | `/files` в `AppLayout`, пункт «Файловые хранилища» | `/admin/files` в `AdminLayout`, пункт «Файлы» |
| Список | Только подключения и бакеты со статистикой | Единая серверная таблица файлов и отдельная корзина |
| Upload | Внутренний `UploadFileHandler`, без Console endpoint | Multipart HTTP-контракт и форма, использующие существующий handler |
| StoredFile | Lifecycle корзины реализован в Domain и persistence; HTTP-мутаций ещё нет | Подключить сценарии управления и worker к готовым переходам |
| Обслуживание | `files.cleanup`, orphan/multipart старше 24 часов | Отдельные `files.trash.cleanup` и `files.purge`, срок корзины 30 дней |
| Доступ | Files GET требуют authenticated context | Управление Files в Console доступно только tenant admin; сервер проверяет права |

### Применимые архитектурные требования

Нормативный источник — [архитектурные правила](../architecture/AGENTS.md),
прочитанные полностью при подготовке плана. Перед реализацией проверить
актуальную редакцию. Для этого этапа обязательны:

1. Самостоятельные Aggregate Roots: `StorageProvider`, `Bucket`, `StoredFile`.
   Корзина — состояние `StoredFile`, отдельного агрегата `Trash` нет.
   Ссылки между корнями — по ID; работа с файлами не создаёт отдельную модель диска.
2. Сохранить порядок `module/layer/aggregate/responsibility`. Новые сценарии
   размещать в `application/stored_file/{command|query}/<scenario>/`;
   новые файловые query ports/adapters — внутри `stored_file`, общие storage
   ports и сборку нескольких корней — на уровне соответствующего слоя.
3. Domain не импортирует HTTP, ORM, SDK, Config и logger. Application зависит
   от Domain и абстрактных портов; транспортные `UploadFile`/Request и
   `AsyncSession` туда не передаются.
4. `StoredFile.create/restore` проверяют целостность состояния; переходы
   выполняются публичными доменными методами. Инварианты корзины и сроков
   не переносятся в VO, persistence mapper, repository или controller.
   `__post_init__` разрешён только в VO.
5. Каждый use case имеет собственный Command/Query, `handler.py`, конкретный
   DTO результата и `execute` с явным возвращаемым типом. Сценарии `-> None`
   обходятся без пустого DTO. Обработчики не вызывают друг друга; общая
   координация при необходимости выносится в небольшой Application service.
6. Write repository загружает/сохраняет агрегат; query repository возвращает
   проекции без восстановления агрегатов для таблицы. ORM не выходит наружу.
   Mapper только преобразует данные, без I/O и исправления бизнес-инвариантов.
7. Один атомарный процесс использует одну сессию внешнего UoW. Repositories
   не выполняют commit/rollback; handlers не открывают вложенный UoW.
   Запись задания и переход в `purging` атомарны в SQL. Если появятся
   интеграционные сообщения, Outbox записывается до commit в той же транзакции.
8. HTTP controller, Request для тела и Response каждого метода — отдельные
   файлы. GET и мутации без тела не получают фиктивный Request; ответ без тела
   не получает фиктивную Response. Application DTO не служит HTTP-схемой.
   Router только регистрирует маршруты и dependencies; `depends.py` собирает порты.
9. Identity владеет доверенным контекстом и авторизацией; Files импортирует
   зависимости из файлов определения. Межмодульная интеграция с jobs и
   бизнес-потребителями проходит через Application contracts и адаптеры.
10. Все методы, включая `__init__ -> None`, фабрики, ports, `execute` и HTTP,
    имеют аннотации параметров и результата; классы/методы — русские docstrings.
    Имена отражают сценарий и роль; новые `__init__.py` пусты, импорты прямые.
11. Внешние эффекты MinIO не считаются частью SQL-транзакции. Должны быть
    описаны повторные попытки, ownership, отмена и восстановление после сбоя.
12. Domain не логирует. Итоги `*.committed` записываются только после commit,
    техническое исключение со stack trace — на одной внешней границе. Логи
    содержат безопасные IDs/счётчики/коды причин, без credentials, содержимого,
    имён пользовательских файлов и полных SDK responses.
13. Функциональные тесты дополняются независимой проверкой архитектуры,
    обязательных файлов сценариев, HTTP-контрактов и всего diff.

### Жизненный цикл файла и корзины

`StoredFile` получает `StoredFileStatus` и поля `deleted_at`, `deleted_by`,
`purge_after`, `purge_requested_at`, `purge_job_id`. Времена — timezone-aware UTC;
`deleted_by` и `purge_job_id` — ссылки по UUID, без объектов пользователя/job.

| Состояние | Доступность | Допустимый переход |
| --- | --- | --- |
| `uploading` | Не показывается в списке | `mark_uploaded(actual_size) → ready` |
| `ready` | Обычный список и внутреннее чтение содержимого | `move_to_trash(actor_id, now) → trashed` |
| `trashed` | Только корзина; содержимое недоступно | `restore_from_trash(now) → ready` до истечения срока; `request_purge(now, job_id) → purging` вручную; `request_expired_purge(now, job_id) → purging` по сроку |
| `purging` | Корзина с отметкой «Удаляется», восстановление запрещено | `mark_purged(job_id) → purged` после подтверждения storage adapter |
| `purged` | Не показывается, содержимое недоступно | Repository удаляет подтверждённый агрегат из реестра в той же SQL-транзакции |

Доменная политика фиксирует `purge_after = deleted_at + timedelta(days=30)`:
ровно 30 × 24 часа, без зависимости от локальной даты/DST. Повторное удаление
`trashed` идемпотентно, сохраняет исходные даты и не продлевает срок. Повторное
восстановление уже `ready` идемпотентно. Восстановление возможно только при
`now < purge_after`; при равенстве срок уже истёк, независимо от запуска worker.
После восстановления новый перенос в корзину начинает новый 30-дневный период.

В `ready` и `uploading` поля корзины пусты. В `trashed` обязательны дата, автор
и срок, поля purge пусты. В `purging` дополнительно обязательны дата запроса
и job ID. `create/restore` проверяют эти комбинации и порядок времён.
Метод `replace_purge_job(job_id)` допускается только для `purging` и сохраняет
даты первоначального удаления; `is_current_purge_job(job_id)` защищает от
устаревшей доставки. SQL constraints дублируют допустимые комбинации,
не заменяя Domain.

`purged` — промежуточное доменное состояние подтверждения, в SQL оно не хранится.
После `mark_purged(job_id)` вызывается `repository.remove(aggregate)` в том же UoW,
без промежуточного `save`. SQL-запись остаётся `purging` до удаления; её job ID
должен совпадать с подтверждённым. Повторный `remove` отсутствующей записи безопасен.

При переносе в корзину объект остаётся в исходном бакете с прежним ключом.
Новый бакет/путь для корзины и копирование содержимого не нужны. При восстановлении
проверяются готовность диска, существование объекта и ownership; потерянный
объект не превращается в доступный файл. Все изменения одного файла выполняются
под `SELECT FOR UPDATE`, включая проверку срока, восстановление и purge.

Перемещение в корзину действует на файл во всём tenant. Внутренний
`get_file_content` продолжает отдавать только `ready`; бизнес-ссылки потребителей
не удаляются автоматически. Диалог объясняет, что файл станет недоступен
в использующих его разделах и может быть восстановлен в течение 30 дней.
Текущие Catalog/CRM/Channels не подключены к Files; перед их интеграцией
согласовать защиту используемых файлов через порт потребителя, без чтения
чужих таблиц из Files. Уже открытый поток может завершиться после trash;
гарантия запрета действует на новые запросы чтения.

### Use cases, входы и конкретные результаты

Во всех сценариях `tenant_id` приходит из доверенного контекста/worker,
`actor_id` для пользовательских изменений — из principal. Время передаётся
через общий `ClockPort`; браузер не задаёт даты корзины или срок хранения.
UUID в DTO/Command/Query соответствуют существующим Application-контрактам;
при работе с агрегатами используются `EntityIdVO`.

| Сценарий | Вход | `Handler.execute` возвращает | Необходимые порты |
| --- | --- | --- | --- |
| `list_files` (query) | tenant_id, search, bucket_ids, category, page, page_size | `ListFilesResultDTO` | `StoredFileQueryRepositoryProtocol` |
| `list_trashed_files` (query) | tenant_id, search, bucket_ids, category, page, page_size | `ListTrashedFilesResultDTO` | `StoredFileQueryRepositoryProtocol` |
| `get_files_overview` (query) | tenant_id, bucket_ids | `GetFilesOverviewResultDTO` | `StoredFileQueryRepositoryProtocol` |
| `upload_file` (существующий command) | tenant_id, BinaryIO, точный size_bytes, name, content_type, optional bucket_id | `UploadFileResultDTO` | Существующие provider/bucket/file repositories и `StorageResolverProtocol` |
| `trash_file` (command) | tenant_id, file_id, actor_id | `TrashFileResultDTO` | `StoredFileRepositoryProtocol`, ClockPort |
| `restore_file` (command) | tenant_id, file_id, actor_id | `RestoreFileResultDTO` | File/bucket/provider repositories, storage resolver, ClockPort |
| `request_file_purge` (command) | tenant_id, file_id, actor_id | `None` | File repository, `FilePurgeQueueProtocol`, ClockPort, UUID generator |
| `cleanup_expired_trash` (command) | tenant_id, now, after_id optional, batch_size | `CleanupExpiredTrashResultDTO` | File repository, file query repository, purge queue, UUID generator |
| `purge_file` (command, worker) | tenant_id, file_id, job_id | `None` | File/bucket/provider repositories, storage resolver |

Конкретные поля результатов:

- `ListFilesResultDTO`: `items: tuple[ListFilesItemDTO, ...]`, `total: int`,
  `page: int`, `page_size: int`. Строка: `file_id`, `bucket_id`, `bucket_name`,
  `provider_id`, `provider_name`, `name`, `content_type`, `category`,
  `size_bytes`, `created_at`.
- `ListTrashedFilesResultDTO`: собственные `items`, `total`, `page`, `page_size`.
  `ListTrashedFilesItemDTO` содержит метаданные строки, `status`, `deleted_at`,
  `purge_after`, `purge_requested_at`. DTO обычного списка не используется
  как универсальный контракт корзины.
- `GetFilesOverviewResultDTO`: `active_count`, `active_size_bytes`,
  `trashed_count`, `trashed_size_bytes`, `pending_purge_count`,
  `pending_purge_size_bytes`, `categories: tuple[FilesOverviewCategoryDTO, ...]`.
  Категория: `category`, `files_count`, `size_bytes`. Значения trash включают
  `purging`, pending purge — их отдельная часть.
- `UploadFileResultDTO`: существующие `file_id`, `name`, `content_type`,
  `size_bytes`. Отдельный upload-сценарий только ради Console не создаётся.
- `TrashFileResultDTO`: `file_id`, `deleted_at`, `purge_after`.
- `RestoreFileResultDTO`: `file_id`, `status` (готовый файл).
- `CleanupExpiredTrashResultDTO`: `queued_count`, `requeued_count`,
  `next_after_id: UUID | None`. Это итог постановки в очередь,
  а не число физически удалённых объектов.
- `request_file_purge` и `purge_file`: `-> None`, без `dto.py`.

### Обязательные файлы и сборка

Для каждой строки таблицы сценариев, включая изменяемый `upload_file`, проверить
`application/stored_file/{command|query}/<scenario>/`: `command.py` либо
`query.py`, `handler.py`, `dto.py` для всех результатов кроме `None`, пустой
`__init__.py`. Существующий `get_file_content` сохраняет собственный DTO и handler;
его проекция должна исключать все состояния кроме `ready`.

Новые/изменяемые элементы по слоям:

| Размещение внутри `src/modules/files/` | Назначение |
| --- | --- |
| `domain/stored_file/aggregate.py`, `status.py`, `repository.py`; `domain/error.py` | Фабрики, методы корзины, typed status, ошибки, `get_for_update` и `remove` подтверждённого агрегата |
| `application/stored_file/port/query_repository.py` | Списки/overview/candidate IDs; результаты чтения конкретных сценариев |
| `application/stored_file/port/purge_queue.py` | `FilePurgeQueueProtocol`: постановка job без commit; получение terminal/missing IDs порциями |
| `application/stored_file/file_category.py` | Единая классификация для read-side; без SQL/SDK и domain-инвариантов |
| `application/port/storage.py` | Добавить проверку существования owned-объекта и удаление всех версий одного ключа; SDK exceptions преобразуются в ошибки порта |
| `infrastructure/stored_file/persistence/{repository,mapper,query_repository,query_mapper}.py` | Write locking/removal, mapping lifecycle, новые SQL-проекции |
| `infrastructure/persistence/models/stored_file.py` | Колонки, constraints и индексы реестра |
| `infrastructure/stored_file/jobs/purge_queue.py` | Адаптер shared jobs Application-контрактов на той же SQL-сессии |
| `infrastructure/storage/minio_adapter.py`, `infrastructure/assembly.py` | Ownership/версии, сборка новых обработчиков на внешней сессии |
| `presentation/stored_file/{router,depends}.py`, `presentation/router.py` | Регистрация HTTP и именованные зависимости каждого HTTP handler |
| `presentation/depends/admin.py` | Доверенный tenant admin context, отдельно от бизнес-правил Files |
| `presentation/jobs/{trash_cleanup,purge_file}.py`, `infrastructure/jobs.py` | Внешние worker UoW, hourly регистрация и отдельные job types |
| Внешний `src/management/commands/jobs.py` | Подключение job handlers и periodic registrar к штатному worker |
| Новая tenant migration после текущего head | Upgrade/downgrade полей, constraints и индексов; без сетевых обращений |

`StoredFileRepositoryProtocol.get_for_update(...) -> StoredFile` восстанавливает
агрегат через mapper; `remove(aggregate: StoredFile) -> None` удаляет запись
после доменного подтверждения purge. Query port получает параметры пагинации/
поиска и возвращает DTO, не ORM. Для обслуживания candidate IDs читаются
порциями с keyset по `file_id`, после чего каждая запись повторно проверяется
под write lock; исчезнувшие/восстановленные записи пропускаются безопасно.

`FilePurgeQueueProtocol.schedule(tenant_id, file_id, job_id, run_at) -> None`
использует shared `ScheduleScheduledJobUseCase` с `schedule_once`.
`terminal_or_missing(tenant_id, job_ids) -> frozenset[UUID]` адаптирует существующий
Application repository contract shared jobs и не раскрывает его SQL-модель.
Сборка передаёт обоим адаптерам сессию того же UoW. Queue не публикует сообщения
в брокер до commit и не открывает отдельную транзакцию.

`presentation/stored_file/depends.py` предоставляет именованные
`get_<scenario>_handler`/`<Scenario>HandlerDep` для семи HTTP-сценариев.
Worker получает `cleanup_expired_trash` и `purge_file` из внешней assembly;
фиктивные HTTP Depends для внутренних сценариев не нужны.

### HTTP-контракты Console

Base URL остаётся `/api/console/files`; перенос layout не меняет API prefix.
Все методы получают authenticated tenant admin context, mutation methods — CSRF.
`tenant_id`, `actor_id`, object key, config reference и credentials отсутствуют
в пользовательском вводе. UUID другого tenant даёт такой же `404`, как отсутствующий.

| Метод и путь относительно base | Controller / Request / Response в `presentation/stored_file/http/` | Результат |
| --- | --- | --- |
| `GET /items/` | `controller/list_files.py`, без Request body, `response/list_files.py` | `200 ListFilesResponse` со своим `ListFilesItemResponse` |
| `GET /trash/` | `controller/list_trashed_files.py`, без Request body, `response/list_trashed_files.py` | `200 ListTrashedFilesResponse` со своим `ListTrashedFilesItemResponse` |
| `GET /overview/` | `controller/get_files_overview.py`, без Request body, `response/get_files_overview.py` | `200 GetFilesOverviewResponse` |
| `POST /items/` | `controller/upload_file.py`, `request/upload_file.py`, `response/upload_file.py` | `201 UploadFileResponse`; multipart `file` и optional `bucket_id` |
| `DELETE /items/{file_id}/` | `controller/trash_file.py`, без Request body, `response/trash_file.py` | `200 TrashFileResponse`, исходная дата удаления и крайний срок |
| `POST /items/{file_id}/restore/` | `controller/restore_file.py`, без Request body, `response/restore_file.py` | `200 RestoreFileResponse` |
| `DELETE /trash/{file_id}/` | `controller/request_file_purge.py`, без Request/Response body | `202 Accepted`, явный `Response`; физическое удаление выполняет worker |

Существующие `GET /providers/` и `GET /buckets/` используются для фильтра и вкладки
дисков; Console-доступ также ограничивается admin. Для backend-потребителей
доступность Files через Application-контракты определяется их собственными ACL.

Параметры обоих списков: `search` (trim, до 255 символов), повторяемый
`bucket_id` (до 50 UUID; отсутствие означает все диски), `category` optional
из `documents|images|videos|other`, `page >= 1`, `page_size` из `10|20|50|100`
(default 20). Поиск — регистронезависимая подстрока исходного имени;
`%`, `_` и `\\` экранируются как буквальные символы. Фильтры соединяются AND.
Неизвестный/чужой bucket ID даёт `404`; некорректные параметры — `422`.

SQL выполняет фильтрацию, COUNT и offset pagination; UI не скачивает весь
реестр. Порядок активного списка: `created_at DESC, id DESC`, корзины:
`deleted_at DESC, id DESC`. COUNT и items читаются из одного согласованного
снимка на время query (например, одним SQL statement); между запросами страницы
возможны обычные изменения из-за новых загрузок/удалений.

Overview учитывает выбранные диски, но не search/category: карточки показывают
общую статистику дисков, таблица — текущий результат поиска. Классификация
по нормализованному MIME: `image/*`, `video/*`, фиксированный документный набор
PDF/text/CSV/RTF/Office/OpenDocument, остальное (включая audio/archives) — `other`.
Единый набор MIME и его точные соответствия фиксируются в `file_category.py`
и проверяются одинаково для overview и обоих списков.

Ошибки: `401` без сессии, `403` без admin/CSRF, `404` отсутствующий ресурс,
`409` конфликт состояния, истёкшее восстановление или неготовый диск,
`413` превышение upload limit, `422` некорректные поля,
`503` недоступное внешнее хранилище. Ошибки SDK и секреты в ответ не попадают.

Для admin dependency недостаточно одного `AuthorizationServiceDep`: сейчас
его default adapter разрешает всё. Проверить роль `admin` из доверенного
principal и, если настроен дополнительный authorization service, его решение.
Frontend guard не заменяет серверную проверку. Контекст и authorization
dependencies импортировать из Identity, проверку Console Files собрать явно.
Для дополнительной проверки зафиксировать действия `files.read`, `files.upload`,
`files.trash`, `files.restore`, `files.purge`, resource type `stored_file` и ID
при наличии; список/overview используют действие `files.read` без resource ID.

### Загрузка и SQL-миграция

Форма принимает один файл и готовый диск; по умолчанию системный. При фильтре
одного диска форма предварительно выбирает его. Другой диск выбирается явно.
Одинаковые имена разрешены: каждая загрузка имеет отдельный UUID-ключ и никогда
не перезаписывает существующий объект.

Multipart Request принадлежит Presentation. Controller получает spool/file
handle, фактический размер `UploadFile.size` (не общий multipart Content-Length),
имя и MIME, преобразует их в существующий `UploadFileCommand` с `BinaryIO`.
Если MIME отсутствует, используется `application/octet-stream`. Имена проверяет
`FileNameVO`. Источник закрывается в `finally` при успехе, ошибке и отмене.

Предлагаемый Console limit — 100 МиБ, Instance setting
`FILES__CONSOLE_MAX_UPLOAD_BYTES=104857600`. Он относится к HTTP-загрузке,
не ограничивает внутренний consumer API. Применить лимит во время приёма
multipart (включая запрос без Content-Length), а не только после записи spool;
ограничения ingress/proxy согласовать с multipart overhead. Файл не читается
целиком в память; действуют существующие bounded concurrency и 600-second timeout.
UI показывает ход передачи и отдельный этап подтверждения сервером;
100% передачи ещё не означает успешный commit.

В новой tenant migration добавить nullable lifecycle поля и обновить status
constraint. Старые `uploading/ready` записи сохраняют ID, object key, метаданные;
новые поля у них NULL. Индексы: активный порядок `(status, created_at, id)`,
диск/состояние/порядок, корзина `(status, deleted_at, id)`, срок
`(purge_after, id)` для `trashed`; индекс подстрочного поиска выбирать по EXPLAIN
на репрезентативном объёме. При необходимости `pg_trgm` готовится на Instance
и документируется явно; обязательную extension без проверки rollout не добавлять.

Миграция не удаляет physical objects и не переписывает `0020_files`.
Downgrade разрешён только при отсутствии `trashed/purging` записей: иначе
явно остановиться, пока корзина не восстановлена/очищена. Нельзя превратить
запрос на удаление в `ready` или потерять его координаты при откате схемы.

### Автоочистка и восстановление после сбоев

Использовать штатные shared scheduled jobs, а не отдельный cron или MinIO TTL.
`files.trash.cleanup` регистрируется для подготовленных активных tenant каждый
час и при запуске registrar. Первая проверка старых tenant появляется после
deploy без повторного onboarding. Для `freeze` сначала проверить допустимость
admission; запрет обслуживания означает отложенную очистку, а не обход gate.

`cleanup_expired_trash` читает до 100 candidate IDs: `trashed` с
`purge_after <= now` и оставшиеся `purging`. Под lock доменный метод повторно
проверяет состояние/срок. Для новых purge создаёт job ID, сохраняет состояние
и `files.purge` в одной SQL-транзакции. Для `purging` с terminal/missing job
назначает новый ID доменным методом и ставит новую job; активная/retrying job
не дублируется. Это восстанавливает в том числе задания с исчерпанными попытками.

Batch обрабатывается в отдельном внешнем UoW. `next_after_id` позволяет продолжить
сканирование keyset-страницами; continuation сохраняет исходный cutoff `now`
и cursor в payload, ставится атомарно с batch перед commit и имеет уникальный
детерминированный ID от родительской job и cursor. Первый batch следующего
часового окна начинает новый проход. Нельзя постоянно читать только первые
100 `purging` записей и блокировать обслуживание следующих файлов.

Ручной `request_file_purge` выполняет тот же доменный переход и постановку
`files.purge` на ближайший запуск в одном UoW. Повторный запрос для уже
`purging` даёт `202` и не меняет job/dates. Задания содержат только tenant/file/job
IDs и безопасные параметры; request-scoped session в worker не передаётся.

`FilesPurgeJobHandler` открывает собственные admission, tenant connection и UoW,
восстанавливает файл под lock и проверяет текущий `purge_job_id`. Старая job
и уже отсутствующая запись обрабатываются как no-op. Storage adapter проверяет
ownership бакета и метаданных объекта, удаляет все версии и delete markers
именно данного ключа, подтверждает отсутствие содержимого. Затем handler
вызывает `mark_purged`, удаляет запись реестра и завершает внешний UoW.
Обычный MinIO `remove_object(key)` при versioning оставляет версии; для этого
сценария нужен явный контракт удаления всех версий, не purge всего бакета.

Если MinIO недоступен, файл остаётся `purging`, очередь повторяет попытку.
Если объект удалён, а SQL commit/процесс завершился сбоем, повторная job видит
тот же `purging`; отсутствие объекта считается успешным результатом и позволяет
повторить удаление записи. Реестр нельзя удалять до подтверждения storage.
Отмена ожидает завершения текущего SDK вызова до release admission/lock.
Устаревшая доставка после назначения нового job ID не затрагивает файл.

Срок 30 дней — нижняя граница физического удаления. При здоровом worker запрос
на удаление появится на ближайшей hourly проверке (обычно до часа после срока),
само удаление зависит от очереди; простой worker/MinIO может увеличить задержку.
UI показывает `purge_after` и состояние ожидания, не обещает удаление до секунды.
Метрики: просроченные файлы/байты, максимальная задержка, pending purge,
retry/failures; логировать агрегированные итоги после commit.

Существующий `files.cleanup` продолжает чистить только orphan/multipart старше
24 часов. `contains_key` учитывает записи всех состояний, включая корзину и
`purging`, поэтому этот механизм не удалит их раньше срока. Tenant deletion
использует прежний exclusive admission и purge storage независимо от корзины;
штатно отменяет tenant jobs перед удалением схемы.

### Console и визуальная композиция

Ориентир — приложенный screenshot [Shadcn UI Kit File Manager](https://shadcnuikit.com/dashboard/file-manager):
спокойный admin shell, заголовок с Upload, четыре карточки категорий,
сводка объёма и таблица файлов. Реализация использует существующий Vue 3 /
shadcn-vue (`new-york`, neutral tokens, Inter, `@lucide/vue`), уже установленный
Reka UI и TanStack Vue Query/Table. React-компоненты шаблона не переносятся.

Маршруты `filesRoutes` подключить к children `/admin`, имена:
`admin-files`, `admin-files-trash`, `admin-files-disks`. URL:
`/admin/files`, `/admin/files/trash`, `/admin/files/disks`. Старый `/files`
перенаправить на `/admin/files`, сохраняя применимые query parameters.
Убрать Files из workspace navigation; добавить «Файлы» с иконкой диска
в admin navigation «Модули». Вкладка «Диски» использует существующий
`FileStoragePage.vue` для просмотра подключений/бакетов.

Композиция страницы:

1. Существующий `AdminLayout` с Sidebar/Breadcrumb. Заголовок «Файлы»,
   описание и основная кнопка «Загрузить файл», вторичная «Обновить».
2. Четыре `Card`: «Документы», «Изображения», «Видео», «Другие» с числом
   и объёмом активных файлов. Нажатие выбирает category filter. Полная
   Card composition; без фиктивного quota/progress из демо.
3. Сводка: активные файлы и корзина, включая ожидающее физическое удаление.
   Объём — сумма зарегистрированных размеров, не фактический disk usage.
   Свободное место и процент заполнения показывать только после появления
   реального quota contract; значений «2 TB»/процентов из прототипа нет.
4. `Tabs`: «Файлы», «Корзина» со счётчиком, «Диски». URL хранит выбранную
   вкладку; search/bucket IDs/category/page/page_size — query state.
5. Над таблицей `InputGroup` с поиском и `Popover`/`Command` с выбором
   нескольких дисков, вариант «Все диски», кнопка сброса фильтров.
   Search debounce 300 ms, при изменении фильтра page сбрасывается на 1.
6. Одна `Table`/Data Table всех дисков: имя с MIME-иконкой, диск, размер,
   дата загрузки, действия. В active строке видимая кнопка удаления.
   В корзине — дата удаления, крайний срок, «Восстановить» и
   «Удалить навсегда»; для `purging` — `Badge` «Удаляется» без восстановления.
7. Переиспользовать `shared/pagination/OffsetPagination.vue`: диапазон,
   общее число и размер страницы. После удаления последней строки последней
   страницы перейти на предыдущую; сохранять текущий поиск/диски.

`UploadFileDialog.vue`: `DialogTitle`, `FieldGroup/Field`, file input с выбором
или drag-and-drop, диск `Select`, имя/размер, `Progress`, submit и отмена.
Drag-and-drop дополняет доступный native file input. Ошибки отображаются
в поле/Alert, выбранный файл остаётся при исправимой ошибке; двойной submit
блокируется. После сетевого сбоя не повторять upload автоматически: ответ
мог потеряться после commit; сначала обновить список. В текущем контракте
повторная отправка создаёт новый файл, строгая upload-idempotency — отдельное расширение.

`TrashFileDialog.vue` и `PurgeFileDialog.vue` используют `AlertDialog` с именем
файла; permanent purge явно сообщает о невозможности восстановления.
После успешных мутаций — `vue-sonner` toast и invalidation списков, overview,
дисков для текущего tenant. Для файлов в `purging` корзина обновляется каждые
5 секунд, пока страница видима; после завершения polling прекращается.

Предлагаемые файлы в `frontends/apps/console/src/modules/files/`:
`pages/FilesPage.vue`, существующий `pages/FileStoragePage.vue`,
`ui/FilesOverview.vue`, `ui/FilesFilters.vue`, `ui/FilesTable.vue`,
`ui/TrashFilesTable.vue`, три диалога, `model/query-keys.ts`,
`model/use-files-query.ts`, `model/use-trash-query.ts`,
`model/use-files-overview-query.ts`, `model/use-file-mutations.ts`;
расширить `api/files.api.ts`, `model/types.ts`, `routes.ts`.
Query keys включают tenant и все параметры; obsolete GET отменяются через
AbortSignal, запоздалый ответ не подменяет результаты нового поиска/tenant.

Переиспользовать уже установленные shadcn-vue primitives. Для новых блоков
проверить официальный Vue registry и API, адаптируя пример к установленной
версии TanStack v8. Официальные опоры:
[Data Table](https://www.shadcn-vue.com/docs/components/data-table),
[Field](https://www.shadcn-vue.com/docs/components/field),
[Sidebar](https://www.shadcn-vue.com/docs/components/sidebar).
Использовать semantic color tokens, встроенные variants и `gap-*`; Title
для диалогов, label/error associations, `aria-invalid`, keyboard focus,
Select/Dropdown/Command items внутри соответствующей Group.

Состояния: Skeleton при первом запросе, Alert + retry при ошибке, разные Empty
для отсутствия файлов/результатов поиска/пустой корзины, disabled mutations,
неподготовленный диск и expired restore. На мобильном — карточки строк с теми
же действиями, перенос фильтров и диалоги без горизонтального overflow;
проверить light/dark theme и клавиатурную навигацию.

### Порядок реализации и критерии приёмки

#### Выполненный срез 1: Domain и persistence

Реализован 2026-10-11. Aggregate Roots остаются `StorageProvider`, `Bucket`,
`StoredFile`; состояние корзины принадлежит последнему. Применены требования
выше: фабрики и инварианты в Domain, прямые импорты, аннотации и русские docstrings,
mapper без I/O/правил, repository на сессии внешнего UoW, без commit/rollback.

Контракты среза:

| Операция | Вход | Результат |
| --- | --- | --- |
| `StoredFile.create/restore` | ID, неизменяемые метаданные; для restore состояние и lifecycle-поля | `StoredFile` с проверенными инвариантами и UTC-временем |
| `move_to_trash` | `actor_id: EntityIdVO`, `now: datetime` | `None`; перенос на 720 часов, повтор не меняет даты/автора |
| `restore_from_trash` | `now: datetime` | `None`; восстановление строго до срока, повтор для ready безопасен |
| `request_purge/request_expired_purge` | `now: datetime`, `job_id: EntityIdVO` | `None`; ручное либо просроченное удаление, повтор сохраняет текущую job |
| `replace_purge_job` | `job_id: EntityIdVO` | `None`; замена только в purging без продления срока |
| `is_current_purge_job` | `job_id: EntityIdVO` | `bool` |
| `mark_purged/ensure_purged` | Текущий job ID / без входа | `None`; подтверждение и проверка разрешения удалить запись |
| `repository.get_for_update` | `identifier: EntityIdVO` | `StoredFile`; lock до конца внешней транзакции и refresh ORM identity map |
| `repository.remove` | Подтверждённый `StoredFile` | `None`; условный DELETE по ID, состоянию и текущей job |

Файлы: `domain/stored_file/{aggregate,status,error,repository}.py`,
`infrastructure/stored_file/persistence/{mapper,repository}.py`, ORM-модель
и новая tenant-ревизия `0021_files_lifecycle` после неизменённой `0020_files`.
Миграция добавляет nullable lifecycle-поля, ограничения комбинаций и сроков,
индексы списков и частичный индекс просроченной корзины. Старые ID, ключи,
метаданные и uploading/ready записи сохраняются. Downgrade берёт table lock
перед проверкой и отказывается работать при trashed/purging.

Новых Application use cases, DTO, HTTP-контрактов и Depends в этом срезе нет.
Сохраняются восемь существующих сценариев и конкретные результаты из раздела
первого этапа. Чтение/статистика учитывают только ready; проверка ключа для
orphan cleanup учитывает все зарегистрированные состояния.

Проверки: 81 уникальный тест Files/lifecycle/архитектуры/миграций/регистрации/
scheduled jobs/удаления tenant успешно проверен. Первоначальный прогон 80 тестов
выявил устаревшее ожидание head `0020_files` в регистрации модулей; оно обновлено,
17 затронутых offline-проверок повторно прошли, включая дополнительный Domain test.
Настоящие PostgreSQL/MinIO/Redis/RabbitMQ запускались в одноразовых контейнерах
на копии исходников с тестовой конфигурацией. Проверены upgrade с данными,
guarded downgrade и его гонка с trash, обе гонки restore/purge, refresh после lock,
rollback, stale job, отсутствие schema drift при autogenerate, сохранность
trash/purging при orphan cleanup и возврат исходного содержимого после restore.
Форматирование, compile и независимая проверка diff по архитектуре выполнены.

Рабочие tenant-схемы не мигрировались. Срез задаёт правила и хранение состояния;
автоочистка корзины, новые API и Admin Console выполняются на следующих этапах.

| Этап | Работы | Критерий готовности |
| --- | --- | --- |
| 1. Domain и миграция — выполнен | Lifecycle, фабрики/ошибки/locks, поля и constraints | Старые записи сохранены; инварианты и конкурентные переходы проверены |
| 2. Read API | Два списка, overview, query ports/adapters, admin Depends | Search/диски/пагинация работают на сервере; HTTP DTO и архитектурные файлы полны |
| 3. Мутации | Console upload, trash, restore, request purge; очередь в общем UoW | CSRF/admin/tenant проверены; rollback не оставляет ложный успех |
| 4. Worker | Hourly trash cleanup, per-file purge, recovery, версии/ownership | Срок 30 дней, безопасные retries/crashes и отсутствие раннего удаления |
| 5. Console | Admin routes/navigation, shadcn-композиция, форма и корзина | Все пользовательские сценарии и responsive/error/empty/pending состояния проверены |
| 6. Rollout | Docs, настройки upload/worker, tenant migration, smoke test | Реальный tenant проходит загрузку → поиск → корзину → восстановление/удаление |

Проверки реализации:

- Domain: фабрики и неверные комбинации lifecycle; repeat trash не продлевает
  срок; restore до/на/после 30 дней, повторный цикл, запрет восстановления
  `purging`, stale job ID. Использовать управляемые часы, не ждать 30 дней.
- Query/HTTP/PostgreSQL: пустой список, literal search `%/_/\\`, Unicode/регистр,
  одинаковые имена, несколько дисков, boundaries page/page_size, корректные
  total/overview, неподготовленные/чужие диски, одинаковые timestamps,
  admin/member/anonymous, CSRF, все заявленные ошибки и OpenAPI schemas.
- Upload/MinIO: пустой файл, предел/превышение, без Content-Length,
  multipart, bounded memory, точный размер, ошибка/отмена/rollback после put,
  закрытие источника, одинаковые имена без перезаписи.
- Корзина/worker: 30-дневная граница, более 100 кандидатов, continuation,
  restart и exhausted jobs, повторная доставка, гонки restore/trash/purge,
  storage outage, crash после physical delete до SQL commit, отсутствие
  объекта, ownership mismatch, versioned bucket и освобождение всех версий.
- Интеграция: orphan cleanup сохраняет trash/purging; чтение `ready` работает,
  корзина недоступна; tenant admission/deletion и отмена jobs сохраняют
  прежние гарантии. Tenant migration upgrade с данными, guarded downgrade,
  autogenerate без schema drift.
- Архитектура: расширить scenario matrix `test/test_files_architecture.py`
  на девять контрактов этого этапа. Заменить ожидание полного read-only HTTP
  на явный whitelist новых методов, сохраняя запрет presigned/download.
  Проверить обязательные файлы, DTO/Response, factories, annotations/docstrings,
  imports, пустые init, SQL/session boundaries и весь diff отдельно от функций.
- Статика и браузер: backend formatter/архитектурные проверки, выбранные
  Files/Postgres/jobs/tenancy/registration tests; Console typecheck, lint,
  build, реальный browser flow на desktop 1440 px и mobile 390 px, обе темы,
  клавиатура, быстрый поиск, загрузка/ошибки, сохранение URL, отсутствие
  console errors/overflow и корректный cache invalidation.

Rollout: применить tenant migration, доставить новые config/worker/frontend,
проверить регистрацию `files.trash.cleanup` для существующих tenant и наличие
`files.purge` в dispatcher. Перед destructive smoke test создать отдельные
тестовые файлы. Для проверки срока использовать тестовый clock/environment,
не изменять даты рабочих файлов. Обновить [документацию Files](../modules/files.md)
и API contracts по фактическим результатам реализации.

### Проверка плана и ограничения

План сопоставлен с текущими Files use cases, схемой `0020_files`, Console
router/layout/navigation, установленными Vue/shadcn-компонентами и shared jobs.
В нём перечислены Aggregate Roots, применимые правила, входы/результаты всех
сценариев, обязательные файлы, порты/адаптеры, HTTP-контракты/Depends,
транзакции, recovery и критерии приёмки всех шести пунктов запроса.

Проверки подготовки плана: ссылки и anchors двух изменённых документов,
полнота девяти use-case и семи HTTP-контрактов, `git diff --check` — успешно.
Три текущих архитектурных теста Files (полнота сценариев, зависимости/фабрики/
аннотации/транзакции, разделение HTTP-контрактов) прошли. Они проверяют
существующую реализацию, а не ещё не созданные сценарии этого этапа.

Domain/persistence, SQL-миграция и тесты среза 1 реализованы; остальные этапы
остаются планом. Эти проверки не подтверждают работу будущих endpoints,
Admin UI или worker. Реальный quota и импорты внешних объектов отсутствуют; мгновенное
удаление ровно в момент истечения срока не гарантируется при сбоях очереди/storage.
