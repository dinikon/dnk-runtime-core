# CRM CONTEXT

## Назначение модуля

`crm` — отдельный bounded context внутри `src/modules`, который сейчас реализует минимальный MVP для работы с контактами.

Текущая бизнес-цель модуля:

- создать контакт;
- получить один контакт;
- получить список контактов;
- переименовать контакт;
- удалить контакт.

HTTP-роуты модуля подключаются в общий router проекта через `/api`, поэтому текущие endpoint'ы модуля доступны под префиксом:

- `/api/crm/contacts`

---

## Текущее состояние модуля

Сейчас в `crm` уже собраны:

- `domain` модель контакта;
- application use case'ы для CRUD;
- HTTP presentation слой;
- DI wiring для application слоя.

При этом concrete infrastructure реализации репозиториев пока отсутствуют.

На данный момент:

- `presentation/depends/infrastructure.py` содержит только dependency-слоты;
- оба dependency provider'а поднимают `NotImplementedError`;
- модуль компилируется, но реальные HTTP-операции не смогут выполниться, пока не будут подключены настоящие repository adapters.

---

## Границы ответственности

`crm` отвечает за:

- aggregate `Contact`;
- правила валидности имени контакта;
- command-side сценарии изменения контакта;
- read-side сценарий получения списка контактов.

`crm` не отвечает за:

- определение tenant по host;
- аутентификацию и сессии;
- SQLAlchemy session / UoW;
- storage implementation;
- ORM-модели других модулей;
- инфраструктуру других bounded context.

---

## Структура модуля

```text
src/modules/crm/
  application/
    contact/
      command/
      dto/
      query/
      use_case/
  domain/
    contact/
      value_object/
  infrastructure/
  presentation/
    depends/
    http/
```

Слой `infrastructure` пока намеренно пустой по смыслу: fake-репозитории удалены, реальные адаптеры ещё не добавлены.

---

## Domain модель

### Aggregate Root

Главный aggregate root модуля — `ContactEntity`.

Файл:

- `src/modules/crm/domain/contact/entity.py`

Состояние aggregate:

- `id: EntityIdVO`
- `created_at: datetime`
- `updated_at: datetime`
- `contact_name: ContactNameVO`

### Value Object

`ContactNameVO` находится в:

- `src/modules/crm/domain/contact/value_object/contact_name.py`

Текущий инвариант:

- `last_name` не должен быть пустым.

Важно: сейчас в VO нет нормализации через `strip()`, поэтому строка из пробелов формально не нормализуется и поведение зависит от того, что пришло извне. Это текущее техническое ограничение модели.

### Domain Errors

Модуль использует:

- `ContactNotFoundError`
- `InvalidContactNameError`

Файл:

- `src/modules/crm/domain/contact/error.py`

### Domain Service

`ContactService` координирует command-side операции над aggregate:

- `create_contact`
- `get_contact`
- `rename_contact`
- `delete_contact`

Файл:

- `src/modules/crm/domain/contact/service.py`

Принцип работы сервиса:

- агрегат загружается из доменного репозитория;
- бизнес-изменение выполняется в domain;
- обновлённый aggregate сохраняется обратно через репозиторий.

---

## Repository contracts

### Domain repository

Контракт доменного репозитория находится в:

- `src/modules/crm/domain/contact/repository.py`

Текущий протокол:

- `load(contact_id) -> ContactEntity | None`
- `save(contact) -> ContactEntity`
- `delete(contact_id) -> None`

Это соответствует текущему правилу модуля:

- domain работает только с aggregate;
- domain-слой не зависит от DTO;
- изменение состояния идёт через `load/save/delete`.

### Query repository

Read-side контракт находится в:

- `src/modules/crm/application/contact/query/repository.py`

Текущий протокол:

- `list(limit, offset) -> list[ContactDTO]`

Важно:

- в `ContactQueryRepositoryProtocol` оставлен только метод `list`;
- получение одного контакта сейчас не вынесено в read-model repository и выполняется через загрузку aggregate в domain service.

Это осознанное текущее разделение:

- `list` — query/read side;
- `get one contact` — пока aggregate load через domain.

---

## Application слой

### Commands

Команды находятся в:

- `application/contact/command/create_contact_command.py`
- `application/contact/command/rename_contact_command.py`
- `application/contact/command/delete_contact_command.py`

Команды описывают входные данные для write-side use case'ов.

### Queries

Query-объекты находятся в:

- `application/contact/query/get_contact_query.py`
- `application/contact/query/list_contacts_query.py`

### DTO

Read DTO находится в:

- `application/contact/dto/contact_dto.py`

`ContactDTO` содержит:

- `id`
- `created_at`
- `updated_at`
- `last_name`
- `first_name`
- `middle_name`

### Use cases

Модуль содержит 5 use case'ов:

- `CreateContactUseCase`
- `GetContactUseCase`
- `ListContactsUseCase`
- `UpdateContactUseCase`
- `DeleteContactUseCase`

Ключевое разделение:

- `Create/Update/Delete` работают через `ContactService`;
- `GetContactUseCase` тоже работает через `ContactService`, загружая aggregate и маппя его в `ContactDTO`;
- `ListContactsUseCase` работает через `ContactQueryRepositoryProtocol` и сразу возвращает `list[ContactDTO]`.

---

## Presentation слой

HTTP router собирается в:

- `src/modules/crm/presentation/http/router.py`

Контроллеры модуля:

- `POST /api/crm/contacts`
- `GET /api/crm/contacts`
- `GET /api/crm/contacts/{contact_id}`
- `PUT /api/crm/contacts/{contact_id}`
- `DELETE /api/crm/contacts/{contact_id}`

Все route handler'ы требуют:

- `AuthenticatedRequestContextDep`

Но на текущий момент это используется только как guard уровня доступа. Сам `crm` aggregate пока:

- не содержит `tenant_id`;
- не фильтруется по tenant;
- не использует request context внутри domain/application логики.

Это означает, что tenant-aware поведение для `crm` ещё не реализовано.

---

## Infrastructure ожидания

Чтобы модуль стал рабочим, нужно добавить две concrete реализации:

1. command repository adapter
   - реализует `load/save/delete`
   - работает с `ContactEntity`

2. query repository adapter
   - реализует `list`
   - возвращает `ContactDTO`

Точка подключения инфраструктуры:

- `src/modules/crm/presentation/depends/infrastructure.py`

Именно здесь реальные адаптеры должны быть подставлены вместо текущих `NotImplementedError`.

---

## Текущие ограничения и TODO

- нет concrete persistence реализации;
- нет query adapter'а для списка;
- нет tenant-aware модели и tenant filtering;
- нет ORM-моделей и DB mapping;
- нет тестов модуля `crm`;
- `ContactNameVO` пока валидирует только непустой `last_name` без явной нормализации;
- получение одного контакта идёт через aggregate load, а не через отдельный read-model.

---

## Архитектурное правило для дальнейшего развития

Если модуль будет расширяться дальше, текущий ориентир такой:

- aggregate changes идут только через domain repository `load/save/delete`;
- query-side read models добавляются отдельно и не возвращают domain entity;
- если появится отдельный read-model для `get contact`, его нужно вводить как новый query contract, а не смешивать с domain repository;
- fake repository обратно не возвращать: инфраструктура должна быть либо реальной, либо отсутствующей явно.
