# Files: план и принятые решения

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
порты 9000/9001 для PyCharm; Control Plane override отключает их через `!reset []`.
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
