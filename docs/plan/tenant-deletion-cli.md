# Tenancy: полное удаление tenant через CLI

Дата: 2026-10-10. Статус: запланировано, CLI ещё не реализован.

## Цель и границы

Добавить отдельный административный сценарий полного удаления локального tenant
из этого runtime: бизнес-данные, пользователи, файловое хранилище, токены,
tenant-схема, домены и принадлежащие tenant записи общих таблиц.

CLI принимает **runtime tenant UUID**, а не hostname, `external_id` или Core UUID.
Удаляется один tenant за запуск. Поддерживаются `active`, `freeze` и незавершённый
локальный `provisioning`. Повторный запуск продолжает принятую операцию после сбоя.

Tenant под управлением Control Plane удаляется через существующий CP-протокол.
CLI выявляет привязку и возвращает `control_plane_managed` до любых изменений.
Проверяется не только `cp_installations`, но и прочие актуальные привязки,
попытки provisioning и операции удаления. Обход подтверждения Core не добавляется:
поздняя команда provisioning может восстановить данные, а Core продолжит считать
установку существующей. Прямая CLI-команда для CP-tenant не входит в первый срез.

«Полное удаление» относится к активным ресурсам runtime. Резервные копии,
внешние магазины и общие RabbitMQ queues не очищаются этой командой.
Минимальная техническая запись завершённой операции сохраняется для идемпотентности.

## Что уже реализовано

- `control_plane/infrastructure/deletion.py`: принятие CP-команды, состояния
  `deletion_pending → blocked → purging → deleted`, fencing provisioning,
  exclusive admission, очистка Redis, Files, PostgreSQL и CP-записей.
- `tenancy/infrastructure/tenant/persistence/tenant_gate.py`: общий admission
  HTTP, CLI и фоновых процессов; удаление использует exclusive lock.
- `tenancy/infrastructure/adapter/files.py`: адаптер `purge(tenant_id) -> None`.
- `files/application/bucket/command/purge_tenant_storage/`: очистка контейнеров
  с проверкой принадлежности, включая версии объектов и multipart uploads.
- `shared/infrastructure/persistence/tenant_cleanup.py`: явный список общих
  tenant-записей — scheduled jobs, integration inbox и outbox.
- `test/test_tenant_deletion.py`: PostgreSQL, ошибки Files, admission races,
  поздние события и изоляция Redis namespaces для CP-сценария.

Это основа повторного использования, а не готовая CLI-команда. Не создавать
фиктивные CP installation, Core UUID, hostname или user-команды для локального tenant.
Общую очистку вынести за типизированные порты Tenancy; CP сохранить собственные
acceptance, версии протокола, авторизацию и подтверждение purge.

## CLI-контракт

Предлагаемые команды после реализации:

```bash
dnk-manage tenants delete <runtime-tenant-uuid> --dry-run
dnk-manage tenants delete <runtime-tenant-uuid> --confirm <runtime-tenant-uuid>
dnk-manage tenants deletion-status <runtime-tenant-uuid>
```

`--dry-run` и `--confirm` взаимоисключающие; один обязателен. Значение `--confirm`
должно совпадать с позиционным UUID. Это явный контракт необратимой CLI-операции;
интерактивный prompt, `--all` и `--force` не нужны.

Dry-run только читает: UUID, имя, статус, схему, домены, управление CP,
состав ресурсов, существующую операцию и причины запрета. Проверка Files
не создаёт бакеты, не меняет ownership tags и не запускает миграции.
Недоступный внешний ресурс обозначается `unknown`; это не подтверждение отсутствия.
Отчёт — снимок, поэтому выполнение заново проверяет условия под блокировкой.

Удаление работает синхронно в пределах ограниченного времени ожидания admission
и внешних операций. После принятия печатаются `tenant_id`, `operation_id`,
`state`, безопасный `error_code` и признак возможности повторного запуска.
Не выводятся credentials, токены, file contents и полные provider config.

Коды завершения: `0` — успешный preview/status либо подтверждённое `deleted`;
`1` — ошибка инфраструктуры до принятия операции; `2` — неверные аргументы,
неизвестный tenant без операции или запрет управления CP; `3` — операция принята,
но ещё не завершена. Тайм-аут, занятый admission или сбой после принятия возвращают
`3` и сохраняют состояние для повторного запуска той же команды.
Отсутствие tenant-строки без проверки операции и ресурсов не означает успех.

## Данные и Aggregate Roots

Tenancy сохраняет существующие корни `Tenant` и `TenantDomain`.
Добавляется `TenantDeletionOperation`: самостоятельный корень durable процесса,
который должен существовать после физического удаления `Tenant`.

Новая **global migration**, следующая за актуальным head, создаёт в `public`
таблицу `tenant_deletion_operations`:

| Поле | Назначение |
| --- | --- |
| `operation_id` | UUID PK операции |
| `tenant_id` | runtime UUID, UNIQUE, без FK с каскадным удалением |
| `state` | CHECK: `deletion_pending`, `blocked`, `purging`, `deleted` |
| `resource_snapshot` | Временный JSONB снимок координат очистки: схема, домены, принадлежащие контейнеры; без credentials и пользовательского содержимого |
| `error_code` | Nullable безопасный код последнего сбоя |
| `created_at`, `updated_at`, `finished_at` | Audit процесса, `finished_at` nullable |

JSONB здесь хранит технический снимок внешних ресурсов, не контент каталога.
После завершения `resource_snapshot` очищается; остаются UUID, состояние и даты.
Уникальность `tenant_id` даёт одну операцию и стабильный `operation_id` при retry.
Создание tenant с уже удалённым UUID запрещается по технической записи операции.
Обычное создание нового tenant получает новый UUID.

Новые tenant-таблицы и миграции всех бизнес-модулей не нужны. Состояния блокировки
в `TenantStatus` уже есть; `deleted` относится к операции, tenant-строка удаляется.
Переходы выражаются доменными методами Tenant и TenantDeletionOperation.
Операция создаётся через `create`, восстанавливается через `restore`; переходы
монотонны и не допускают возврата удаляемого tenant в `active`.

## Сценарии Application и файлы

Нормативный источник — [архитектурные правила](../architecture/AGENTS.md).
Domain не импортирует SQL, Redis, MinIO или CLI. Application использует порты;
сессии, admission и транзакции собираются во внешнем composition root.

| Сценарий | Вход | Конкретный результат |
| --- | --- | --- |
| `preview_tenant_deletion` | runtime tenant UUID | `PreviewTenantDeletionDTO`: описание цели, CP ownership, ресурсы, операция, blockers |
| `delete_tenant` | runtime tenant UUID | `DeleteTenantResultDTO`: tenant UUID, operation UUID, state, error code, retryable |
| `get_tenant_deletion_status` | runtime tenant UUID | `GetTenantDeletionStatusDTO`: operation UUID, state, даты, error code |

`delete_tenant` принимает намерение и продолжает очистку через небольшой
Application process/service; handler не вызывает другие handlers.
Из-за результата операции этот сценарий возвращает собственный DTO.
Низкоуровневые действия `purge storage`, `erase tokens`, `drop schema` и
`delete shared records` возвращают `None`; пустые DTO для них не создаются.

Планируемая структура:

- `tenancy/domain/tenant_deletion_operation/`: `aggregate.py`, `repository.py`,
  `error.py`, `value_object/` для идентификатора и состояния.
- `tenancy/application/tenant_deletion_operation/query/preview_tenant_deletion/`
  и `query/get_tenant_deletion_status/`: `query.py`, `handler.py`, `dto.py`.
- `tenancy/application/tenant_deletion_operation/command/delete_tenant/`:
  `command.py`, `handler.py`, `dto.py`.
- `tenancy/application/tenant_deletion_operation/`: `process.py`, `port/`
  для read projections, lifecycle serialization, CP ownership, auth cleanup,
  tenant resources cleanup и абстрактного UoW.
- `tenancy/infrastructure/tenant_deletion_operation/persistence/`:
  `model.py`, `mapper.py`, `repository.py`, `query_repository.py`, `query_mapper.py`;
  `infrastructure/tenant_deletion_operation/adapter/` для внешних портов.
- `tenancy/presentation/depends/tenant_deletion.py`: сборка процесса и общих
  dependencies от одной сессии на каждый транзакционный этап.
- `src/management/commands/tenants.py`: parser, CLI validation, отображение
  результатов; регистрация в `src/management/cli.py`.
- Новая global migration и тесты CLI, Domain, архитектуры и интеграций.

CP ownership читается через межмодульный Application-порт и CP-адаптер;
Tenancy Application не импортирует CP ORM. Files вызывается через существующий
порт с tenant-контекстом и общей сессией. Общая очистка ресурсов не зависит
от CP DeletionModel. Перенос существующей очистки сопровождается CP regression tests.

Все методы аннотированы, включая `__init__ -> None` и `execute`; docstrings
по-русски, `__init__.py` пустые. DTO отдельные для каждого use case.
Mapper не исправляет инварианты агрегата; `__post_init__` только у VO.
HTTP-контрактов и FastAPI Request/Response в этом CLI-срезе нет.

## Порядок выполнения и транзакции

1. **Принять намерение.** Под общей блокировкой lifecycle проверить runtime UUID,
   CP ownership, tenant и существующую операцию. Зафиксировать снимок ресурсов,
   операцию `deletion_pending` и состояние Tenant в одной SQL-транзакции.
   Повторный вызов возвращает ту же операцию. CP provisioning и локальное создание
   учитывают эту блокировку и запрет восстановления удаляемого UUID.
2. **Дождаться операций.** После commit новые HTTP/jobs/events/files операции
   отклоняются admission. Получить exclusive TenantGate после завершения
   уже допущенных операций; занятость даёт повторяемый результат, не обход lock.
   Повторно проверить ресурсы и при необходимости обновить снимок: ранее
   допущенный upload мог завершиться после принятия намерения.
3. **Зафиксировать блокировку.** Под exclusive admission сохранить `blocked`,
   затем намерение `purging` отдельными короткими SQL-транзакциями.
   Для локального CLI `--confirm` авторизует оба этапа; второй CP handshake не нужен.
4. **Очистить auth и Files.** Удалить tenant sessions, OTP, OIDC state,
   invitation OTP и CSRF по сохранённым доменам. Удалить только принадлежащие tenant
   контейнеры, включая версии, delete markers и незавершённые multipart uploads.
   Проверка ownership обязательна. Чужой или неоднозначный контейнер блокирует
   завершение. Ни schema drop, ни удаление Files registry до успешного purge.
5. **Завершить SQL-очистку.** Под тем же exclusive admission и общей блокировкой
   tenant-миграций выполнить schema drop, удалить tenant jobs/inbox/outbox,
   tenant domains и tenant-строку. Зафиксировать `deleted`, `finished_at`,
   очистку снимка и error code **в одной SQL-транзакции**.
6. **Подтвердить результат.** Только после commit вывести успех и освободить
   admission. Завершённый повторный вызов возвращает прежнюю квитанцию.

PostgreSQL, Redis и MinIO не имеют общей атомарной транзакции. Внешние операции
идемпотентны, durable intent фиксируется заранее. Ошибка внешнего purge,
SQL commit, тайм-аут или остановка CLI не разрешают снова активировать tenant.
После сбоя данные registry/снимка доступны для продолжения; уже удалённый собственный
бакет и отсутствующие токены допускают безопасный повтор.

Admission удерживается до завершения commit и реально выполняющегося SDK-вызова,
включая отмену coroutine. Не добавлять commits в repositories или Files adapters.
Каждый SQL-этап получает собственный внешний UoW; Application-контракт не раскрывает
AsyncSession/session factory. Не удерживать одну SQL-транзакцию на весь CLI-процесс.

Исторический tenant без Files-таблиц не мигрируется ради удаления. Отсутствие
схемы/registry само по себе не доказывает отсутствие физического хранилища:
проверяются сохранённые координаты и детерминированный системный контейнер с ownership.
Если принадлежность или отсутствие ресурсов нельзя подтвердить, выдаётся blocker.
Бизнес-данные tenant из его схемы, включая Identity и Catalog, удаляются целиком;
общие справочники `reference_data`, инфраструктура и другие tenant сохраняются.
Уже отправленные сообщения broker не «отзываются»: поздняя доставка должна
отклоняться существующим admission и не восстанавливать inbox/jobs.

## Этапы реализации и приёмка

1. Выделить типизированные общие адаптеры очистки из текущего CP-сценария;
   сохранить CP-протокол и пройти его regression tests.
2. Добавить агрегат операции, global migration, domain transitions и три use cases.
3. Добавить CLI composition, dry-run/status, bounded ожидание и повторный запуск.
4. Проверить весь diff по архитектурным требованиям и обязательным файлам.

Обязательные проверки при реализации:

- Parser/help, UUID/confirm mismatch, exit codes, dry-run без любых мутаций.
- Domain factories, монотонность состояний, отдельные DTO и архитектурные границы.
- Реальные PostgreSQL/MinIO/Redis: полный local purge и изоляция соседнего tenant.
- Все tenant-данные, файлы/версии/multipart, токены и shared records отсутствуют;
  receipt сохранён, чувствительный снимок очищен.
- Сбой MinIO/Redis/SQL commit, остановка процесса между этапами и успешный retry.
- Конкурентные команды возвращают одну операцию; upload, HTTP, jobs/events и
  миграции не пересекаются с purge; connection pool не исчерпывается ожиданием lock.
- Частичное provisioning, историческая схема, отсутствие registry/бакета,
  чужой ownership и невозможность доказать отсутствие storage.
- CP-managed tenant отклоняется без мутаций; гонка с CP provisioning закрыта;
  существующие CP deletion tests сохраняют прежнее поведение.
- Late delivery не создаёт новые данные после удаления; техническая запись
  запрещает повторное создание того же UUID.
- Migration upgrade/downgrade, отсутствие autogenerate drift, аннотации,
  форматирование и статические проверки.

Тесты удаления выполняются на disposable ресурсах. Текущий план не запускает
удаление, не меняет рабочие tenant и не добавляет реализованный CLI-контракт.
