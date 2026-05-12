# Develop Style

Эталонный модуль проекта: `src/modules/inventory`.

Этот документ фиксирует правила структуры и стиля разработки backend-модулей.
Если новый код не имеет отдельного архитектурного решения, его нужно писать по
образцу `inventory`.

## Базовый Принцип

Проект использует модульную Clean Architecture / DDD-структуру:

- `domain` содержит бизнес-модель и правила.
- `application` содержит сценарии использования и DTO/command/query контракты.
- `infrastructure` содержит адаптеры к runtime data, БД и внешним сервисам.
- `presentation` содержит HTTP entrypoints и сборку зависимостей.

Зависимости направлены внутрь:

```text
presentation -> application -> domain
presentation -> infrastructure -> application/domain protocols
infrastructure -> application/domain protocols
domain -> shared primitives only
```

`domain` не должен импортировать `presentation`, `infrastructure`, FastAPI,
SQLAlchemy, Pydantic или runtime gateway.

## Структура Модуля

Для нового bounded context используйте такую форму:

```text
src/modules/<module>/
├── __init__.py
├── domain/
│   └── <aggregate>/
│       ├── __init__.py
│       ├── entity.py
│       ├── error.py
│       ├── repository.py
│       ├── service.py
│       └── value_object/
├── application/
│   └── <aggregate>/
│       ├── command/
│       ├── dto/
│       ├── query/
│       └── use_case/
├── infrastructure/
└── presentation/
    ├── depends/
    └── http/
```

Если модуль владеет несколькими близкими понятиями, разделяйте их по поддоменам
как `inventory/product` и `inventory/category`. Не смешивайте сущности,
команды, use case и HTTP-схемы разных поддоменов в одном большом файле.

## Domain Layer

Domain layer отвечает за бизнес-инварианты.

Правила:

- Сущности оформляются как `@dataclass(slots=True)`.
- Value objects оформляются как `@dataclass(slots=True, frozen=True)`.
- Валидация примитивов находится в value object, а не в controller/use case.
- Создание сущности идет через factory-метод `create`, если нужно выставить
  `created_at`, `updated_at` или нормализовать входные данные.
- Изменение сущности идет через метод entity, например `update`.
- Domain service координирует несколько repository/aggregate и использует
  `ClockPort` для времени.
- Domain errors живут рядом с aggregate в `error.py`.
- Repository в domain является `Protocol`, а не реализацией.

Пример из `inventory`:

- `ProductEntity.create(...)` создает товар с едиными `created_at/updated_at`.
- `ProductEntity.update(...)` меняет поля и обновляет `updated_at` только при
  реальном изменении.
- `SkuVO` нормализует строку и запрещает пустой SKU.
- `ProductService` проверяет существование категории перед созданием или
  обновлением товара.

## Application Layer

Application layer содержит сценарии и контракты между presentation/domain.

Правила:

- На каждое действие создается отдельный use case:
  `CreateProductUseCase`, `GetProductUseCase`, `ListProductsUseCase`.
- Use case вызывается через `async def __call__(...)`.
- Для входа в command-сценарии используйте immutable dataclass:
  `@dataclass(slots=True, frozen=True)`.
- Для выхода используйте DTO dataclass, а не Pydantic schema.
- Query use case может зависеть от query repository и возвращать DTO напрямую.
- Command use case обычно зависит от domain service и мапит entity в DTO.
- Use case не должен знать про HTTP status codes, FastAPI, request context или
  SQLAlchemy session.
- Для use case и repository contracts используйте `Protocol`, если зависимость
  нужна снаружи слоя.

Именование:

- `command/create_<thing>_command.py`
- `query/list_<things>_query.py`
- `query/repository.py`
- `dto/<thing>_dto.py`
- `use_case/create_<thing>.py`

## Infrastructure Layer

Infrastructure layer реализует порты domain/application.

Правила:

- Реализация repository находится в `infrastructure`.
- Repository реализует нужные `Protocol`: command, query или оба.
- Runtime object name хранится константой класса, например `_OBJECT_NAME`.
- Tenant scope всегда передается параметром метода, repository не хранит tenant
  в состоянии объекта.
- Runtime row мапится в domain entity или DTO внутри repository.
- Преобразования `UUID`, `datetime`, optional/string значений делаются явно и с
  проверкой типов.
- Ошибки not found поднимаются как domain errors.
- Инфраструктура не должна возвращать сырые runtime rows в application layer.

Для runtime-моделей повторяйте подход `ProductRuntimeRepository`:

- `_resolve_descriptor(tenant_id)` получает descriptor через
  `RuntimeObjectResolverProtocol`.
- `save` сам выбирает insert/update по наличию строки.
- `list` задает явные filters, sorting и page spec.
- `_row_to_entity` и `_row_to_dto` разделены.

## Presentation Layer

Presentation layer отвечает только за протокол входа/выхода.

Правила:

- HTTP controller лежит в
  `presentation/http/<aggregate>/controller/<action>.py`.
- Request schemas лежат в `requests`.
- Response schemas лежат в `responses`.
- В HTTP используются Pydantic `BaseModel`, но они не уходят в application.
- Controller достает tenant из `AuthenticatedRequestContextDep`.
- `tenant_id` не принимается из HTTP payload.
- Controller создает command/query object и вызывает use case.
- Controller мапит application DTO в response schema.
- Controller переводит domain/runtime/schema errors в `HTTPException`.
- Роутер поддомена экспортирует `router`, а общий
  `presentation/http/router.py` подключает все action routers.

Префиксы должны быть предметными и стабильными. Для `inventory` используется:

```text
/inventory/products
/inventory/categories
```

## Dependency Injection

DI собирается только в `presentation/depends`.

Правила:

- `presentation/depends/infrastructure.py` создает gateways, repositories и
  infrastructure adapters.
- `presentation/depends/application.py` создает domain services и use cases.
- Dependency aliases оформляются через `typing.Annotated` и `fastapi.Depends`.
- Функции называются `get_<dependency>()`.
- Алиасы называются `<Dependency>Dep`.
- UoW/session подключается через shared dependency, а не создается вручную.
- Use case получает уже собранный service/repository, а не создает их сам.

## Tenant Scope И Идентификаторы

Правила:

- Tenant scope передается через `EntityIdVO`.
- Domain identifiers оформляются отдельными VO:
  `ProductIdVO`, `CategoryIdVO`.
- На HTTP/runtime boundary UUID конвертируется в VO и обратно.
- Внутри domain/application не передавайте голые `UUID`, если есть конкретный
  value object.
- Новый id для HTTP create генерируется в controller и передается в command.

## Ошибки

Правила:

- Бизнес-ошибки являются domain errors и лежат в `domain/<aggregate>/error.py`.
- Not found ошибка должна быть отдельной: `<Thing>NotFoundError`.
- Ошибки валидации value object не должны быть `ValueError`.
- HTTP layer мапит domain errors в 4xx.
- Infrastructure/runtime/schema conflicts мапятся отдельно от domain validation.

## Экспорт И Импорты

Правила:

- В `__init__.py` поддомена экспортируйте публичные классы через `__all__`.
- Внутри модуля используйте абсолютные импорты от `src.modules...`.
- Не импортируйте private helpers между слоями.
- Не создавайте циклические зависимости между поддоменами.
- Если один aggregate ссылается на другой, используйте его public VO/protocol,
  как `ProductService` использует `CategoryCommandRepositoryProtocol`.

## Асинхронность

Правила:

- I/O сценарии, repositories, gateways и HTTP handlers являются async.
- Use case `__call__` является async.
- Domain entity/value object методы остаются синхронными.
- Не смешивайте sync DB access с async controller/use case.

## Документация Кода

Стиль текущего проекта допускает короткие русскоязычные docstring.

Правила:

- Docstring должен объяснять назначение класса или метода.
- Не описывайте очевидное построчно.
- Для public classes, use cases, repositories, controllers и DI factory
  docstring обязателен.
- Комментарии в теле кода добавляйте только для нетривиального решения.

## Тесты

Новый или измененный модуль должен иметь тесты по риску изменения.

Минимальный набор:

- value object validation;
- entity create/update behavior;
- domain service behavior and domain errors;
- use case orchestration;
- repository mapping and runtime gateway interaction;
- HTTP controller success/error mapping;
- DI smoke test, если добавлены новые dependencies.

Тесты должны проверять границы слоев: controller не должен тестировать
внутреннюю реализацию entity, а domain tests не должны поднимать FastAPI.

## Что Не Делать

- Не помещать бизнес-логику в controller.
- Не передавать Pydantic schemas в application/domain.
- Не импортировать infrastructure из domain/application.
- Не хранить tenant в repository instance.
- Не использовать голые dict как DTO между слоями.
- Не возвращать runtime rows наружу из repository.
- Не создавать общий `utils.py` для разной доменной логики.
- Не ловить все ошибки через `except Exception` в controller.
- Не писать SQLAlchemy/runtime access прямо в use case.

## Чеклист Нового Модуля

Перед завершением работы проверьте:

- структура повторяет `inventory`;
- domain не зависит от FastAPI/Pydantic/SQLAlchemy/runtime gateway;
- все входные примитивы валидируются через VO или Pydantic на HTTP boundary;
- commands frozen и slots;
- use cases тонкие и вызываются через `__call__`;
- repositories реализуют Protocol и явно мапят данные;
- DI находится в `presentation/depends`;
- HTTP не принимает `tenant_id` из payload;
- ошибки мапятся в понятные HTTP status codes;
- публичные классы экспортированы через `__all__`;
- добавлены или обновлены релевантные тесты;
- документация модуля в `docs/modules/<module>.md` обновлена, если изменилась
  публичная функциональность.

## Source Of Truth

- `src/modules/inventory/domain/product/entity.py`
- `src/modules/inventory/domain/product/service.py`
- `src/modules/inventory/application/product/use_case/create_product.py`
- `src/modules/inventory/infrastructure/product_runtime_repository.py`
- `src/modules/inventory/presentation/depends/application.py`
- `src/modules/inventory/presentation/depends/infrastructure.py`
- `src/modules/inventory/presentation/http/router.py`
