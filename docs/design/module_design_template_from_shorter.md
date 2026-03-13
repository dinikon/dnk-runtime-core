# Module Design Template From `shorter`

## Назначение

Шаблон реализации нового модуля по образцу `src/modules/shorter`.

Использовать как контекст перед написанием кода.

## Reference

- `src/modules/shorter/domain/link/entity.py`
- `src/modules/shorter/domain/template/entity.py`
- `src/modules/shorter/domain/template/services/template_creation_service.py`
- `src/modules/shorter/application/template/command/create_template.py`
- `src/modules/shorter/application/template/dto/result_create_template.py`
- `src/modules/shorter/application/template/use_case/create_template.py`
- `src/modules/shorter/infrastructure/link/repositories/runtime_record_link_repository.py`
- `src/modules/shorter/infrastructure/template/repositories/runtime_record_template_repository.py`
- `src/modules/shorter/infrastructure/services/random_link_code_generator.py`
- `src/modules/runtime_schema/system_models/system_models.yaml`
- `test/test_shorter_domain_template_create_service.py`
- `test/test_shorter_runtime_record_repositories.py`

## Базовая структура модуля

```text
src/modules/<module_name>/
  __init__.py
  application/
    __init__.py
    <feature>/
      __init__.py
      command/
        <action>_<feature>.py
      dto/
        result_<action>_<feature>.py
      use_case/
        <action>_<feature>.py
  domain/
    __init__.py
    errors.py
    <aggregate_a>/
      __init__.py
      entity.py
      value_object.py
      repositories/
        __init__.py
        <aggregate_a>_repository.py
      policies/
        __init__.py
        <policy_name>.py
      services/
        __init__.py
        <aggregate_a>_<action>_service.py
    <aggregate_b>/
      __init__.py
      entity.py
      value_object.py
      repositories/
        __init__.py
        <aggregate_b>_repository.py
    shared/
      __init__.py
      ports/
        __init__.py
        <technical_port>.py
  infrastructure/
    __init__.py
    <aggregate_a>/
      __init__.py
      repositories/
        __init__.py
        runtime_record_<aggregate_a>_repository.py
    <aggregate_b>/
      __init__.py
      repositories/
        __init__.py
        runtime_record_<aggregate_b>_repository.py
    services/
      __init__.py
      <technical_adapter>.py
  presentation/
    depends/
    http/
    api/
```

## Фактическая структура `shorter`

```text
src/modules/shorter/
  application/template/command/create_template.py
  application/template/dto/result_create_template.py
  application/template/use_case/create_template.py
  domain/errors.py
  domain/link/entity.py
  domain/link/value_object.py
  domain/link/repositories/link_repository.py
  domain/template/entity.py
  domain/template/value_object.py
  domain/template/policies/link_code_policy.py
  domain/template/services/template_creation_service.py
  domain/template/repositories/template_repository.py
  domain/shared/ports/link_code_generator.py
  domain/shared/ports/link_code_uniqueness_checker.py
  infrastructure/link/repositories/runtime_record_link_repository.py
  infrastructure/template/repositories/runtime_record_template_repository.py
  infrastructure/services/random_link_code_generator.py
```

## Слои и ответственность

### `domain`

Содержит:

- entities;
- value objects;
- domain errors;
- policies;
- domain services;
- repository ports;
- technical ports.

Не содержит:

- HTTP;
- SQLAlchemy;
- runtime record contracts;
- infrastructure adapters.

### `application`

Содержит:

- command/query DTO;
- result DTO;
- use case.

Ответственность:

- принять primitive input;
- преобразовать в VO;
- вызвать domain service;
- сохранить результат через repository ports;
- вернуть result DTO.

### `infrastructure`

Содержит:

- repository adapters;
- technical service adapters;
- payload/entity mapping.

Ответственность:

- запись в storage;
- чтение из storage;
- реализация domain ports.

### `presentation`

Добавлять только если нужен HTTP/API.

Содержит:

- request/response schema;
- depends;
- router.

## Нейминг

### Папки

- `domain/<aggregate>/entity.py`
- `domain/<aggregate>/value_object.py`
- `domain/<aggregate>/repositories/<aggregate>_repository.py`
- `domain/<aggregate>/services/<aggregate>_<action>_service.py` или `<action>_<aggregate>_service.py`
- `domain/<aggregate>/policies/<policy_name>.py`
- `domain/shared/ports/<port_name>.py`
- `application/<feature>/command/<action>_<feature>.py`
- `application/<feature>/dto/result_<action>_<feature>.py`
- `application/<feature>/use_case/<action>_<feature>.py`
- `infrastructure/<aggregate>/repositories/runtime_record_<aggregate>_repository.py`
- `infrastructure/services/<service_name>.py`

### Классы

- entity: `<Aggregate>Entity`
- id value object: `<Aggregate>IdVO`
- enum value object: `<Aggregate><Meaning>VO`
- repository port: `<Aggregate>RepositoryPort`
- technical port: `<Capability>Port`
- policy: `<Something>Policy`
- domain service: `<Action><Aggregate>Service` или `<Aggregate><Action>Service`
- service result: `<Action><Aggregate>Result` или `<Aggregate><Action>Result`
- command DTO: `<Action><Aggregate>Command`
- result DTO: `Result<Action><Aggregate>DTO`
- use case: `<Action><Aggregate>UseCase`
- use case protocol: `<Action><Aggregate>UseCaseProtocol`
- runtime repository: `RuntimeRecord<Aggregate>Repository`

### Методы

- entity factory: `create(...)`
- use case entrypoint: `execute(...)`
- repository write: `save(...)`
- repository read: `get_by_id(...)`
- existence check: `exists_by_<scope>_and_<field>(...)`
- mapper: `_map_payload(...)`
- primitive coercion: `_coerce_<type>(...)`
- service helper: `_resolve_<value>(...)`, `_ensure_<rule>(...)`, `_generate_<value>(...)`

## Обязательные элементы по образцу `shorter`

### Domain

#### Entities

- `LinkEntity`
- `TemplateEntity`

Шаблон:

```python
@dataclass(slots=True)
class <Aggregate>Entity:
    id: <Aggregate>IdVO
    created_at: datetime

    @classmethod
    def create(cls, *, created_at: datetime, ...) -> "<Aggregate>Entity":
        ...
```

#### Value Objects

- id через наследование от `EntityIdVO`;
- enum значения через `StrEnum`.

Пример из `shorter`:

- `LinkIdVO`
- `TemplateIdVO`
- `TemplateTargetModuleTypeVO`
- `TemplateEntityTypeVO`

#### Errors

Выделять в `domain/errors.py`.

Пример из `shorter`:

- `LinkCodeRequiredError`
- `LinkCodeAlreadyExistsError`
- `LinkCodeLengthNotSupportedError`
- `LinkCodeGenerationAttemptsExceededError`

#### Policies

Выделять отдельным файлом.

Пример:

- `LinkCodePolicy.DEFAULT_LENGTH`

#### Repository Ports

Обязательный минимум:

```python
class <Aggregate>RepositoryPort(Protocol):
    async def save(self, entity: <Aggregate>Entity) -> None: ...

    async def get_by_id(
        self,
        *,
        <aggregate>_id: <Aggregate>IdVO,
    ) -> <Aggregate>Entity | None: ...
```

Пример из `shorter`:

- `LinkRepositoryPort`
- `TemplateRepositoryPort`

#### Technical Ports

Выделять в `domain/shared/ports`.

Пример из `shorter`:

- `LinkCodeGeneratorPort`
- `LinkCodeUniquenessCheckerPort`

#### Domain Service

Использовать, если сценарий координирует несколько сущностей или зависит от port-интерфейсов.

Шаблон:

```python
@dataclass(frozen=True, slots=True)
class <Action><Aggregate>Result:
    ...


class <Action><Aggregate>Service:
    async def create(self, *, ...) -> <Action><Aggregate>Result:
        ...
```

Пример из `shorter`:

- `TemplateCreationService`
- `TemplateCreationResult`

Методы:

- `create(...)`
- `_resolve_code(...)`
- `_generate_unique_code(...)`
- `_ensure_unique_code(...)`

### Application

#### Command DTO

Формат:

```python
@dataclass(frozen=True, slots=True)
class Create<Aggregate>Command:
    ...
```

Пример:

- `CreateTemplateCommand`

#### Result DTO

Формат:

```python
@dataclass(frozen=True, slots=True)
class ResultCreate<Aggregate>DTO:
    ...
```

Пример:

- `ResultCreateTemplateDTO`

#### Use Case

Формат:

```python
class Create<Aggregate>UseCase:
    async def execute(
        self,
        command: Create<Aggregate>Command,
    ) -> ResultCreate<Aggregate>DTO:
        ...
```

Пример:

- `CreateTemplateUseCase`
- `CreateTemplateUseCaseProtocol`

Обязанности:

1. конвертировать primitives в VO;
2. вызвать domain service;
3. сохранить сущности через repository ports;
4. вернуть DTO.

### Infrastructure

#### Repository Adapters

Формат:

```python
class RuntimeRecord<Aggregate>Repository(<Aggregate>RepositoryPort):
    OBJECT_NAME = "<module_name>_<aggregate>"

    async def save(self, entity: <Aggregate>Entity) -> None:
        ...

    async def get_by_id(...) -> <Aggregate>Entity | None:
        ...

    def _map_payload(self, payload: RuntimeRecordPayload) -> <Aggregate>Entity:
        ...
```

Пример из `shorter`:

- `RuntimeRecordLinkRepository`
- `RuntimeRecordTemplateRepository`

Допустимо:

- один adapter реализует несколько портов.

Пример:

- `RuntimeRecordLinkRepository` реализует `LinkRepositoryPort` и `LinkCodeUniquenessCheckerPort`

#### Technical Adapters

Пример:

- `RandomLinkCodeGenerator`

Методы:

- `generate(...)`
- `generate_4()`
- `generate_6()`
- `generate_8()`
- `generate_16()`

## Контракт `runtime_record`

Если persistence строится через `runtime_record`, repository обязан:

- использовать корректный `tenant_id`;
- использовать корректный `object_name_singular`;
- маппить только через `RuntimeRecordPayload.system_values`;
- валидировать обязательные поля при чтении;
- приводить primitive values к domain VO.

### `OBJECT_NAME`

Значение `OBJECT_NAME` в repository должно совпадать с object key в:

- `src/modules/runtime_schema/system_models/system_models.yaml`

Пример из `shorter`:

- `shorter_link`
- `shorter_template`

### Tenant Scope

Tenant scope определить заранее для каждого aggregate.

Пример из `shorter`:

- `RuntimeRecordLinkRepository` использует `link.domain_id.value` как `tenant_id`;
- `RuntimeRecordTemplateRepository` получает `tenant_id` в конструкторе.

## Контракт `runtime_schema`

Для каждого runtime repository нужно добавить system object в:

- `src/modules/runtime_schema/system_models/system_models.yaml`

Нужно определить:

- `key`;
- `name.singular`;
- `name.plural`;
- `fields`;
- relation fields, если есть связи;
- select options, если есть enum/select поля.

Без этого `RuntimeRecord...Repository` не должен считаться завершенным.

## Экспорт через `__init__.py`

Публичные элементы модуля переэкспортировать через `__init__.py` и `__all__`.

Минимум:

- `domain/__init__.py`
- `application/__init__.py`
- `infrastructure/__init__.py`
- `module/__init__.py`

## Тесты

### Unit

Файл-образец:

- `test/test_shorter_domain_template_create_service.py`

Покрыть:

- happy path;
- domain validation;
- domain errors;
- use case orchestration;
- сохранение сущностей;
- result DTO.

Использовать:

- in-memory repository stub;
- fake clock;
- deterministic generator.

### Integration

Файл-образец:

- `test/test_shorter_runtime_record_repositories.py`

Покрыть:

- bootstrap runtime schema;
- upsert/get/find в runtime storage;
- round-trip entity -> storage -> entity.

## Порядок реализации

1. Определить aggregates и feature use case.
2. Создать `domain/errors.py`.
3. Создать `entity.py` и `value_object.py` для каждого aggregate.
4. Создать repository ports.
5. Создать technical ports в `domain/shared/ports`, если нужны внешние зависимости.
6. Создать policies.
7. Реализовать domain service.
8. Создать command DTO, result DTO, use case.
9. Реализовать infrastructure repositories.
10. Реализовать technical adapters.
11. Добавить system objects в `runtime_schema/system_models.yaml`.
12. Написать unit tests.
13. Написать integration tests.
14. Добавить `presentation`, если нужен HTTP/API.

## Запреты

- не помещать SQLAlchemy и runtime record contracts в `domain`;
- не возвращать storage payload из `application`;
- не смешивать request/response schema с application DTO;
- не размещать бизнес-правила в `infrastructure`;
- не использовать `OBJECT_NAME`, которого нет в `system_models.yaml`;
- не пропускать integration tests для runtime repositories.
