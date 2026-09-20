Ниже — целевая архитектура для Django/PostgreSQL с моделью `schema-per-tenant`, DDD + Clean Architecture. Основной принцип: модуль валют отвечает за **валютную политику, курсы и конвертацию**, но не владеет финансовыми документами. `Order`, `Supply`, `Payment`, `Offer` получают от него результат конвертации и сохраняют этот результат как часть собственной исторической записи.

## 1. Границы модуля

Разделил бы систему на четыре части:

```text
shared
   │
   │ Money, CurrencyCode
   ▼
currency bounded context
   │
   ├── справочник валют
   ├── политика tenant
   ├── история functional currency
   ├── ручные курсы
   ├── курсы провайдеров
   ├── поиск курса
   ├── cross-rate
   └── конвертация
        │
        ▼
Orders / Supply / Offers / Payments / Inventory / Reports
```

Важно разделить:

```text
System Settings
.env + tenant override
```

от:

```text
Currency Policy
domain state tenant
```

Например:

```text
NBU_API_URL
NBU_TIMEOUT
NBU_SYNC_INTERVAL
```

→ Settings.

А:

```text
functional_currency = UAH
rate_source = NBU
rate_date_policy = PREVIOUS_AVAILABLE
```

→ Currency bounded context.

---

# 2. Структура проекта

Я бы построил модуль примерно так:

```text
src/
├── shared/
│   └── domain/
│       └── money/
│           ├── currency_code.py
│           ├── money.py
│           ├── converted_money.py
│           ├── conversion_snapshot.py
│           └── errors.py
│
├── modules/
│   └── currency/
│       ├── domain/
│       │   ├── entities/
│       │   │   ├── currency_policy.py
│       │   │   ├── functional_currency_period.py
│       │   │   └── manual_exchange_rate.py
│       │   │
│       │   ├── value_objects/
│       │   │   ├── currency_pair.py
│       │   │   ├── exchange_rate.py
│       │   │   ├── provider_code.py
│       │   │   ├── rate_quote.py
│       │   │   └── rate_resolution.py
│       │   │
│       │   ├── enums/
│       │   │   ├── rate_date_policy.py
│       │   │   ├── rate_derivation.py
│       │   │   └── rate_source_type.py
│       │   │
│       │   ├── services/
│       │   │   ├── cross_rate_calculator.py
│       │   │   └── conversion_calculator.py
│       │   │
│       │   ├── events/
│       │   └── errors.py
│       │
│       ├── application/
│       │   ├── commands/
│       │   │   ├── configure_currency_policy.py
│       │   │   ├── enable_currency.py
│       │   │   ├── disable_currency.py
│       │   │   ├── set_manual_rate.py
│       │   │   └── schedule_functional_currency.py
│       │   │
│       │   ├── queries/
│       │   │   ├── get_currency_policy.py
│       │   │   ├── get_functional_currency.py
│       │   │   ├── resolve_rate.py
│       │   │   └── convert_money.py
│       │   │
│       │   ├── services/
│       │   │   ├── exchange_rate_resolver.py
│       │   │   ├── money_conversion_service.py
│       │   │   └── functional_currency_resolver.py
│       │   │
│       │   ├── ports/
│       │   │   ├── currency_directory.py
│       │   │   ├── currency_policy_repository.py
│       │   │   ├── functional_currency_repository.py
│       │   │   ├── manual_rate_repository.py
│       │   │   ├── provider_rate_repository.py
│       │   │   ├── exchange_rate_provider.py
│       │   │   ├── clock.py
│       │   │   └── unit_of_work.py
│       │   │
│       │   └── dto/
│       │
│       ├── contracts/
│       │   ├── facade.py
│       │   └── dto.py
│       │
│       ├── infrastructure/
│       │   ├── persistence/
│       │   │   ├── public/
│       │   │   │   ├── models.py
│       │   │   │   └── repositories.py
│       │   │   │
│       │   │   └── tenant/
│       │   │       ├── models.py
│       │   │       └── repositories.py
│       │   │
│       │   ├── providers/
│       │   │   ├── nbu/
│       │   │   │   ├── client.py
│       │   │   │   ├── mapper.py
│       │   │   │   └── adapter.py
│       │   │   └── manual/
│       │   │       └── adapter.py
│       │   │
│       │   ├── cache/
│       │   └── tasks/
│       │       └── sync_rates.py
│       │
│       └── presentation/
│           ├── api/
│           ├── admin/
│           └── serializers/
```

Зависимости:

```text
shared
  ↑
domain
  ↑
application
  ↑
infrastructure / presentation
```

`domain` ничего не знает про Django ORM, HTTP, NBU или PostgreSQL.

---

# 3. Что хранить в `public`

## `public.currency`

Главный глобальный reference-data справочник.

```text
currency
────────────────────────────────────
code                char(3) PK
numeric_code        char(3) NULL
name                varchar
minor_units         smallint NULL
symbol              varchar NULL
is_active           boolean
valid_from          date NULL
valid_to            date NULL
created_at
updated_at
```

Пример:

```text
UAH | 980 | Hryvnia  | 2
USD | 840 | US Dollar| 2
JPY | 392 | Yen      | 0
```

`symbol` используется только для отображения.

Никогда:

```text
symbol = "$"
```

не должен идентифицировать валюту.

Источник истины:

```text
code = USD
```

### `minor_units`

Нужен для округления конечных денежных результатов.

Но `Money` не должен автоматически округляться до `minor_units`.

Это важно для:

```text
unit price = 1.234567 USD
quantity = 100
```

Промежуточная точность должна сохраняться.

Округление выполняется на соответствующей бизнес-границе.

---

# 4. Нужно ли хранить provider rates в `public`

Здесь есть два варианта.

Для вашей архитектуры я бы предусмотрел оба типа источников:

```text
GLOBAL PROVIDER DATA
NBU, ECB и т. п.

TENANT DATA
Manual rates, custom provider, overrides
```

Для НБУ один и тот же курс не имеет смысла хранить 500 раз в 500 tenant schema.

Поэтому можно добавить:

```text
public.fx_provider_rate
```

для глобальных провайдеров.

Пример:

```text
fx_provider_rate
────────────────────────────────
id
provider_code
source_currency
target_currency

rate

effective_date
published_at
fetched_at

revision
payload_hash

is_current
```

Например:

```text
NBU
USD → UAH
41.250000000000
2026-09-21
```

Но это оптимизация.

Архитектура application-слоя не должна знать, находится rate:

```text
public
```

или:

```text
tenant schema
```

Она работает через:

```python
ProviderRateRepository
```

---

# 5. Что хранить внутри tenant schema

Так как schema уже соответствует конкретному tenant, `tenant_id` в каждой таблице не нужен.

## 5.1 `currency_policy`

Текущая валютная политика tenant.

```text
currency_policy
─────────────────────────────────
id

default_transaction_currency
rate_provider_code

rate_date_policy
rounding_mode

allow_cross_rate
bridge_currency_code

version

created_at
updated_at
```

Например:

```text
default_transaction_currency = UAH
rate_provider_code = NBU
rate_date_policy = PREVIOUS_AVAILABLE
rounding_mode = HALF_UP
bridge_currency_code = UAH
```

Я бы не помещал сюда `functional_currency`, если она может изменяться во времени.

---

# 6. Functional currency — отдельная timeline

```text
functional_currency_period
─────────────────────────────
id
currency_code

valid_from
valid_to NULL

created_at
created_by
reason
```

Например:

```text
UAH | 2024-01-01 | 2026-12-31
EUR | 2027-01-01 | NULL
```

Это позволяет получить:

```python
functional_currency_resolver.resolve(
    business_date=date(2026, 5, 1)
)
```

→

```text
UAH
```

А:

```text
2027-05-01
```

→

```text
EUR
```

Нужно запретить пересечение периодов.

На PostgreSQL желательно DB constraint / exclusion constraint плюс доменная проверка.

---

# 7. Разрешённые валюты tenant

```text
enabled_currency
────────────────
currency_code PK
enabled
created_at
updated_at
```

Например:

```text
UAH true
USD true
EUR true
PLN false
```

Важно:

`disabled` означает:

> нельзя использовать в новых операциях.

Это не означает:

> удалить / запретить читать старые документы.

Исторические документы обязаны продолжать отображаться.

---

# 8. Ручные курсы

```text
manual_exchange_rate
─────────────────────────────────
id

source_currency
target_currency

rate

effective_date

created_at
created_by

revision
is_current
```

Constraint:

```text
source
target
effective_date
revision
```

Rate лучше делать append-only.

Если пользователь исправил:

```text
USD → UAH
41.20
```

на:

```text
41.25
```

старую запись не удаляем.

Создаётся новая ревизия.

---

# 9. Audit / import execution

Стоит иметь:

```text
fx_rate_import
────────────────────────
id
provider_code

started_at
finished_at

requested_date_from
requested_date_to

status

received_count
created_count
updated_count
error_count

error_message
```

Это сильно упростит эксплуатацию.

Иначе через год невозможно будет понять:

> почему на 14 марта отсутствуют курсы НБУ?

---

# 10. Какие VO должны быть в `shared`

Shared Kernel должен оставаться небольшим.

Я бы положил туда четыре основных понятия.

## `CurrencyCode`

```python
@dataclass(frozen=True, slots=True)
class CurrencyCode:
    value: str
```

Правила:

```text
uppercase
ровно 3 символа
ASCII A-Z
```

Но VO не ходит в БД проверять существование валюты.

То есть:

```python
CurrencyCode("USD")
```

валиден синтаксически.

Проверка:

> существует ли USD в системе?

делается через:

```python
CurrencyDirectory
```

---

# 11. `Money`

```python
@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: CurrencyCode
```

Должен уметь:

```python
money + money
money - money
money * quantity
money / scalar
money.is_zero()
money.is_positive()
```

Но:

```python
Money(10, USD) + Money(10, EUR)
```

должен выбрасывать:

```text
CurrencyMismatchError
```

Никакой неявной конвертации внутри `Money`.

Это критически важно.

---

# 12. `ConversionSnapshot`

Для фиксации того, как была выполнена конвертация.

```python
@dataclass(frozen=True, slots=True)
class ConversionSnapshot:
    source_currency: CurrencyCode
    target_currency: CurrencyCode

    rate: Decimal

    requested_date: date
    effective_date: date

    converted_at: datetime

    provider_code: str

    derivation: RateDerivation

    source_rate_id: str | None = None
    bridge_currency: CurrencyCode | None = None
```

`requested_date` и `effective_date` обязательно разные понятия.

Например пользователь запрашивает:

```text
21.09.2026
```

а последний доступный официальный курс:

```text
18.09.2026
```

Получаем:

```text
requested_date = 2026-09-21
effective_date = 2026-09-18
```

---

# 13. `ConvertedMoney`

Именно этот VO закрывает ваш кейс:

> оригинальная сумма + сумма в системной валюте + курс и дата.

```python
@dataclass(frozen=True, slots=True)
class ConvertedMoney:
    original: Money
    converted: Money
    conversion: ConversionSnapshot
```

Например:

```text
original:
100 USD

converted:
4 125 UAH

conversion:
USD → UAH
41.25
requested_date = 2026-09-21
effective_date = 2026-09-21
provider = NBU
```

Для одинаковой валюты:

```text
100 UAH → 100 UAH
```

я рекомендую всё равно создавать snapshot:

```text
rate = 1
derivation = IDENTITY
provider = INTERNAL
```

Вместо `conversion = NULL`.

Тогда бизнес-код становится намного проще.

---

# 14. Почему `ConvertedMoney` должен быть immutable

Допустим поставка была:

```text
100 USD
→
4125 UAH
```

Через неделю курс стал:

```text
42.10
```

`ConvertedMoney` не должен измениться.

Это snapshot исторического факта.

---

# 15. Дополнительные VO внутри Currency domain

Их уже необязательно помещать в shared.

### `CurrencyPair`

```python
CurrencyPair(
    source=USD,
    target=UAH,
)
```

---

### `ExchangeRate`

```python
@dataclass(frozen=True)
class ExchangeRate:
    pair: CurrencyPair
    value: Decimal
```

Invariant:

```text
rate > 0
```

---

### `RateQuote`

Это ответ resolver до непосредственной конвертации.

```python
@dataclass(frozen=True)
class RateQuote:
    pair: CurrencyPair
    rate: Decimal

    requested_date: date
    effective_date: date

    provider_code: ProviderCode

    derivation: RateDerivation

    source_rate_id: str | None
    bridge_currency: CurrencyCode | None
```

---

### `ProviderCode`

```python
ProviderCode("NBU")
ProviderCode("MANUAL")
ProviderCode("ECB")
```

Не делать Python Enum с жестко заданным набором провайдеров, если планируется plugin architecture.

---

# 16. `RateDerivation`

Enum допустим, потому что это не расширяемый список внешних сущностей, а внутренний алгоритм:

```python
class RateDerivation(Enum):
    DIRECT = "direct"
    INVERSE = "inverse"
    CROSS = "cross"
    IDENTITY = "identity"
```

Например provider хранит:

```text
USD → UAH = 41
```

Запрашиваем:

```text
UAH → USD
```

Resolver получает:

```text
1 / 41
```

и:

```text
derivation = INVERSE
```

---

# 17. `RateDatePolicy`

```python
class RateDatePolicy(Enum):
    EXACT = "exact"
    PREVIOUS_AVAILABLE = "previous_available"
```

Я бы не вводил автоматически:

```text
NEAREST
```

потому что это может привести к использованию курса из будущего.

Для финансовой истории это плохое поведение.

---

# 18. Domain entity `CurrencyPolicy`

Это не Django model.

Например:

```python
class CurrencyPolicy:
    default_transaction_currency: CurrencyCode
    provider_code: ProviderCode
    rate_date_policy: RateDatePolicy
    rounding_mode: RoundingMode
    cross_rates_enabled: bool
    bridge_currency: CurrencyCode
```

Ответственность:

```text
валидировать валютную конфигурацию tenant
```

Но не:

```text
получать курс
ходить в NBU
конвертировать SQL модели
```

---

# 19. `FunctionalCurrencyPeriod`

Domain entity:

```python
class FunctionalCurrencyPeriod:
    currency: CurrencyCode
    valid_from: date
    valid_to: date | None
```

Логика:

```python
contains(date)
overlaps(period)
```

---

# 20. Порты application-слоя

Это один из наиболее важных слоёв.

## `CurrencyDirectory`

Доступ к `public.currency`.

```python
class CurrencyDirectory(Protocol):

    def exists(
        self,
        code: CurrencyCode,
    ) -> bool:
        ...

    def get(
        self,
        code: CurrencyCode,
    ) -> CurrencyInfo:
        ...

    def list_active(self) -> Sequence[CurrencyInfo]:
        ...
```

Application ничего не знает про:

```text
public.currency
```

---

# 21. `CurrencyPolicyRepository`

```python
class CurrencyPolicyRepository(Protocol):

    def get(self) -> CurrencyPolicy:
        ...

    def save(
        self,
        policy: CurrencyPolicy,
    ) -> None:
        ...
```

Tenant определяется текущим schema context.

Поэтому:

```python
repository.get(tenant_id)
```

в schema-per-tenant архитектуре зачастую вообще не нужен.

---

# 22. `FunctionalCurrencyRepository`

```python
class FunctionalCurrencyRepository(Protocol):

    def get_for_date(
        self,
        business_date: date,
    ) -> FunctionalCurrencyPeriod:
        ...

    def list_periods(
        self,
    ) -> Sequence[FunctionalCurrencyPeriod]:
        ...

    def add(
        self,
        period: FunctionalCurrencyPeriod,
    ) -> None:
        ...
```

---

# 23. `ManualRateRepository`

```python
class ManualRateRepository(Protocol):

    def find(
        self,
        pair: CurrencyPair,
        date: date,
        policy: RateDatePolicy,
    ) -> ManualExchangeRate | None:
        ...

    def add(
        self,
        rate: ManualExchangeRate,
    ) -> None:
        ...
```

---

# 24. `ProviderRateRepository`

Для загруженных курсов:

```python
class ProviderRateRepository(Protocol):

    def find(
        self,
        provider: ProviderCode,
        pair: CurrencyPair,
        date: date,
        policy: RateDatePolicy,
    ) -> ProviderRate | None:
        ...

    def save_many(
        self,
        rates: Sequence[ProviderRate],
    ) -> None:
        ...
```

Infrastructure сам решает:

```text
NBU → public table

Custom tenant provider → tenant schema
```

Application service этого не знает.

---

# 25. Контракт внешнего провайдера

```python
class ExchangeRateProviderPort(Protocol):

    @property
    def code(self) -> ProviderCode:
        ...

    async def fetch(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> Sequence[ProviderRateDTO]:
        ...
```

Я бы не позволял Orders напрямую вызывать этот порт.

Правильный путь:

```text
Order
 ↓
CurrencyFacade
 ↓
ExchangeRateResolver
 ↓
RateRepository
```

И отдельно:

```text
scheduled worker
 ↓
NBU Adapter
 ↓
RateRepository
```

---

# 26. Не надо делать NBU API частью обычной конвертации

Плохой сценарий:

```text
Create Supply
    ↓
HTTP NBU
    ↓
save supply
```

Если NBU недоступен — нельзя создать поставку.

Лучше:

```text
NBU API
   ↓
sync task
   ↓
local rate storage
```

и:

```text
Supply
   ↓
local FX resolver
```

Допустимый fallback:

```text
CACHE_ONLY
```

или позже:

```text
ON_DEMAND_AND_PERSIST
```

Но второй режим должен явно конфигурироваться.

---

# 27. `ExchangeRateResolver`

Это основной application service.

```python
class ExchangeRateResolver:

    def resolve(
        self,
        *,
        pair: CurrencyPair,
        requested_date: date,
    ) -> RateQuote:
        ...
```

Алгоритм:

```text
1. source == target?
       → IDENTITY

2. Получить CurrencyPolicy

3. Выбрать source:
       MANUAL / NBU / другой

4. Искать direct rate

5. Если нет:
       искать inverse rate

6. Если разрешено cross-rate:
       попробовать через bridge currency

7. Применить RateDatePolicy

8. Если ничего не найдено:
       RateNotFoundError

9. Вернуть RateQuote
```

---

# 28. Cross-rate

Например:

```text
USD → UAH = 41.25
EUR → UAH = 48.50
```

Нужно:

```text
USD → EUR
```

Расчет:

```text
41.25 / 48.50
```

Полученный `RateQuote`:

```text
derivation = CROSS
bridge_currency = UAH
```

Для аудита желательно сохранить также ids исходных rates.

Можно расширить snapshot:

```python
source_rate_ids: tuple[str, ...]
```

---

# 29. `MoneyConversionService`

```python
class MoneyConversionService:

    def convert(
        self,
        *,
        money: Money,
        target_currency: CurrencyCode,
        requested_date: date,
    ) -> ConvertedMoney:
        ...
```

Внутри:

```text
Money
 ↓
RateResolver
 ↓
RateQuote
 ↓
ConversionCalculator
 ↓
ConvertedMoney
```

---

# 30. `ConversionCalculator`

Это чистый domain service.

Не работает с repository.

```python
class ConversionCalculator:

    def convert(
        self,
        money: Money,
        quote: RateQuote,
    ) -> Money:
        ...
```

Пример:

```text
100 USD × 41.25 = 4125 UAH
```

---

# 31. Округление

Не нужно делать:

```python
round(amount, 2)
```

по всей системе.

Должна быть отдельная политика:

```python
MoneyQuantizer
```

которая получает:

```text
CurrencyInfo.minor_units
RoundingMode
```

Например:

```python
quantizer.quantize(
    Money(...),
    purpose=BOOKING,
)
```

Разумно различать:

```text
CALCULATION
BOOKING
DISPLAY
```

Потому что промежуточные вычисления нельзя округлять слишком рано.

---

# 32. Facade модуля

Остальные bounded contexts не должны импортировать десятки классов Currency.

Предоставьте им один публичный application contract:

```python
class CurrencyFacade(Protocol):

    def get_functional_currency(
        self,
        business_date: date,
    ) -> CurrencyCode:
        ...

    def resolve_rate(
        self,
        *,
        source: CurrencyCode,
        target: CurrencyCode,
        date: date,
    ) -> RateQuoteDTO:
        ...

    def convert(
        self,
        *,
        money: Money,
        target: CurrencyCode,
        date: date,
    ) -> ConvertedMoney:
        ...

    def convert_to_functional(
        self,
        *,
        money: Money,
        business_date: date,
    ) -> ConvertedMoney:
        ...
```

Это основная точка интеграции:

```text
Orders ──────┐
Supply ──────┤
Payments ────┼── CurrencyFacade
Offers ──────┤
Inventory ───┘
```

---

# 33. Что должен сохранять бизнес-документ

Очень важный момент: я бы **не делал одну глобальную mutable таблицу `fx_snapshot`, на которую ссылаются все документы**.

Snapshot является частью исторического состояния документа.

Например `Supply` сохраняет:

```text
original_amount
original_currency

functional_amount
functional_currency

fx_rate

fx_provider
fx_requested_date
fx_effective_date
fx_derivation

fx_source_rate_id
```

Либо в отдельной owned table:

```text
supply_money_snapshot
```

Но ownership:

```text
Supply Aggregate
```

а не Currency module.

---

# 34. Почему snapshot должен принадлежать документу

Currency module сообщает:

```text
сейчас эта конвертация выглядит вот так
```

Supply фиксирует:

```text
в момент проведения документа именно этот курс был использован
```

После этого Currency module может:

```text
получить новую ревизию курса
изменить provider
исправить cache
```

Но:

```text
Supply #123
```

не меняется.

Это один из ключевых DDD boundary.

---

# 35. Пример Supply flow

Поставщик прислал:

```text
100 USD
```

Дата документа:

```text
2026-09-21
```

Supply вызывает:

```python
currency.convert_to_functional(
    Money(Decimal("100"), USD),
    business_date=date(2026, 9, 21),
)
```

Currency context:

```text
functional currency = UAH

USD → UAH
rate = 41.25
effective = 2026-09-21
```

возвращает:

```text
ConvertedMoney

original:
100 USD

converted:
4125 UAH

snapshot:
41.25 / NBU / 2026-09-21
```

Supply сохраняет snapshot.

---

# 36. Offer отличается от проведённого документа

Для Supplier Offer можно иметь два режима.

### Dynamic normalization

Храним:

```text
10 USD
```

UI сегодня показывает:

```text
≈ 412.50 UAH
```

Завтра:

```text
≈ 418 UAH
```

Хорошо для текущего предложения.

### Historical OfferState

Если вы ведёте историю прайс-листа:

```text
OfferState
2026-09-21
10 USD
412.50 UAH
```

тогда фиксируем `ConvertedMoney`.

Это позволит понять:

```text
изменилась ли цена поставщика
```

или:

```text
изменилась только валюта.
```

---

# 37. Product price

Карточка товара может иметь:

```text
purchase_price = 10 USD
```

без conversion snapshot.

Это текущая настройка, а не произошедшая операция.

UI делает динамическую конвертацию.

Но если price используется для создания:

```text
Order
Supply
Invoice
Payment
```

там уже создаётся snapshot.

---

# 38. Date semantics

Каждый consuming context обязан сам определить:

> какая дата является датой валютного курса.

Currency module не решает это самостоятельно.

Например:

```text
Supply:
posted_at

Order:
order_date

Payment:
processed_at

Invoice:
issue_date
```

И вызывает:

```python
convert(..., business_date=...)
```

Это предотвращает скрытую бизнес-логику внутри Currency.

---

# 39. Время и timezone

Currency module должен получать:

```text
date
```

а не вычислять дату из:

```text
datetime.utcnow()
```

Business context сначала преобразует timestamp в tenant timezone и получает business date.

Иначе операция в:

```text
23:30 UTC
```

может попасть уже на следующий день tenant.

---

# 40. Смена functional currency

Это отдельный use case:

```text
ScheduleFunctionalCurrencyChange
```

Например:

```text
UAH → EUR
effective_from = 2027-01-01
```

Handler проверяет:

```text
валюта существует
валюта разрешена tenant
нет пересечения period
дата допустима
```

После этого создаётся:

```text
functional_currency_period
```

Старые документы не трогаются.

---

# 41. Backdated change

Я бы по умолчанию запрещал:

```text
поменять functional currency с даты в прошлом,
если после неё уже есть проведённые документы.
```

Нужен отдельный административный migration process.

Нельзя делать это обычной кнопкой Settings.

---

# 42. Rate revisions

Представим:

```text
NBU rate revision #1
41.25
```

а потом источник исправил:

```text
revision #2
41.26
```

Хранилище может считать:

```text
41.26 current rate
```

Но старый Supply должен продолжить содержать:

```text
41.25
```

потому что такой rate был использован при проведении.

---

# 43. Public ↔ tenant FK

PostgreSQL технически позволяет:

```text
tenant_schema.table
        ↓ FK
public.currency
```

Но если используется `django-tenants` или аналогичный механизм, cross-schema FK может усложнять миграции и ORM.

Поэтому я бы предусмотрел два режима.

Предпочтительный логический контракт:

```text
currency_code CHAR(3)
```

и application validation через:

```text
CurrencyDirectory
```

Дополнительно:

```text
CHECK currency_code ~ '^[A-Z]{3}$'
```

Если ваша tenant-библиотека стабильно работает с cross-schema FK — добавляйте FK.

Но domain architecture не должна зависеть от его наличия.

---

# 44. Persistence models не должны вытекать наружу

Например:

```python
DjangoCurrencyPolicyModel
```

никогда не передаётся в application.

Repository делает mapping:

```text
ORM model
    ↓ mapper
Domain CurrencyPolicy
```

и обратно.

---

# 45. Основные application use cases

Минимально модуль должен поддерживать:

| Use case                      | Назначение                           |
| ----------------------------- | ------------------------------------ |
| `ListCurrencies`              | глобальный справочник                |
| `EnableCurrency`              | разрешить tenant использовать валюту |
| `DisableCurrency`             | запретить новые операции             |
| `ConfigureCurrencyPolicy`     | источник курса, policy               |
| `ScheduleFunctionalCurrency`  | смена основной валюты                |
| `GetFunctionalCurrency`       | валюта учета на дату                 |
| `SetManualRate`               | ручной курс                          |
| `ImportProviderRates`         | синхронизация NBU                    |
| `ResolveExchangeRate`         | определить курс                      |
| `ConvertMoney`                | конвертация                          |
| `ConvertToFunctionalCurrency` | наиболее частая операция             |
| `GetRateHistory`              | UI/audit                             |

---

# 46. Ошибки домена

Сделал бы типизированные exceptions:

```text
CurrencyNotFound
CurrencyDisabled

CurrencyMismatch

InvalidExchangeRate
ExchangeRateNotFound

FunctionalCurrencyNotConfigured
FunctionalCurrencyPeriodOverlap

FunctionalCurrencyChangeNotAllowed

ProviderUnavailable
ProviderRateInvalid

CrossRateUnavailable
```

Не возвращать в бизнес-код:

```text
None
```

при отсутствии курса.

Особенно опасно:

```python
rate = resolver.resolve(...) or Decimal("1")
```

Такого поведения быть не должно.

---

# 47. Что делать если курс отсутствует

По умолчанию:

```text
FAIL CLOSED
```

Например:

```text
USD → UAH
21.09.2026
```

курс не найден.

Операция проведения документа получает:

```text
ExchangeRateNotFound
```

Пользователь должен:

```text
загрузить курс
ввести ручной
исправить настройки
```

Не надо молча брать:

```text
курс сегодняшнего дня.
```

---

# 48. NBU adapter

Структура:

```text
providers/nbu/
├── client.py
├── mapper.py
└── adapter.py
```

`client.py`

только HTTP:

```text
request
timeout
retry
response
```

`mapper.py`

```text
NBU JSON
 ↓
ProviderRateDTO
```

`adapter.py`

реализует:

```python
ExchangeRateProviderPort
```

Domain никогда не знает формат API НБУ.

---

# 49. Settings для NBU

В generic Settings:

```text
currency.providers.nbu.api_url
currency.providers.nbu.timeout
currency.providers.nbu.retry_count
currency.providers.nbu.sync_enabled
currency.providers.nbu.sync_schedule
```

Можно:

```text
ENV
 ↓
system settings
 ↓
tenant override
```

Но выбор:

```text
tenant использует NBU
```

хранится в:

```text
CurrencyPolicy
```

---

# 50. Rate provider plugins

С учетом вашей plugin-oriented CRM я бы сразу сделал registry:

```python
class ExchangeRateProviderRegistry:

    def register(
        self,
        provider: ExchangeRateProviderPort,
    ) -> None:
        ...

    def get(
        self,
        code: ProviderCode,
    ) -> ExchangeRateProviderPort:
        ...
```

Тогда:

```text
NBU plugin
ECB plugin
PrivatBank plugin
Custom Bank plugin
```

реализуют один контракт.

Currency domain не меняется.

---

# 51. Provider capabilities

Полезно сразу предусмотреть:

```python
ProviderCapabilities:
    historical_rates: bool
    supported_currencies: bool
    base_currency: CurrencyCode | None
    bulk_download: bool
```

Например provider может предоставлять только:

```text
XXX → UAH
```

Resolver сам строит inverse/cross rate.

---

# 52. Кэширование

Можно кэшировать:

```text
CurrencyDirectory
CurrencyPolicy
RateQuote
```

Но ключ rate cache должен содержать минимум:

```text
provider
source
target
requested_date
policy
policy_version
```

При изменении ручного курса cache инвалидируется.

---

# 53. Concurrency

Для `currency_policy` нужен:

```text
version
```

для optimistic locking.

Иначе два администратора могут одновременно изменить provider/policy.

Для manual rates:

```text
unique constraints
```

и append-only revisions.

---

# 54. Security / permissions

Отдельные permissions:

```text
currency.view
currency.manage_enabled
currency.manage_policy
currency.manage_rates
currency.change_functional_currency
currency.import_rates
```

Особенно:

```text
change_functional_currency
manual exchange rate
```

не должны быть обычными пользовательскими настройками.

---

# 55. Audit events

Имеет смысл генерировать:

```text
CurrencyEnabled
CurrencyDisabled

CurrencyPolicyChanged

ManualExchangeRateCreated

FunctionalCurrencyScheduled
FunctionalCurrencyActivated

ProviderRatesImported

RateResolutionFailed
```

Это пригодится audit log и вашему будущему AI/automation слою.

---

# 56. Read model для UI

UI не должен собирать настройки из десяти repository.

Сделайте query:

```python
GetCurrencySettingsQuery
```

возвращающий:

```text
functional currency now
future functional currency

default transaction currency

enabled currencies

rate provider

rate date policy

last provider sync
last available rate date
```

---

# 57. UI страницы

Логически их лучше разделить.

### Currency policy

```text
Основная валюта
Источник курса
Политика даты
Cross rate
```

### Enabled currencies

```text
UAH
USD
EUR
PLN
...
```

### Rates

```text
date
USD
EUR
PLN
provider
status
```

### Functional currency history

```text
UAH 2024 → 2026
EUR 2027 →
```

---

# 58. API для других модулей

Не давать им доступ к:

```text
/currency/rates ORM
```

Все работают через:

```python
CurrencyFacade
```

Например Order:

```python
result = currency_facade.convert_to_functional(
    money=order.total,
    business_date=order.order_date,
)
```

---

# 59. Главное разделение моделей

Итоговая модель выглядит так:

```text
PUBLIC
────────────────────────────────

currency

provider_rate             optional/global
provider definition       optional


TENANT
────────────────────────────────

currency_policy

enabled_currency

functional_currency_period

manual_exchange_rate

fx_rate_import            audit

custom_provider_rate      optional
```

А:

```text
conversion snapshots
```

живут **в тех bounded contexts, где возникла финансовая операция**.

---

# 60. Связь с другими контекстами

```text
                 Currency BC
                     │
           ┌─────────┴─────────┐
           │ CurrencyFacade    │
           └─────────┬─────────┘
                     │
   ┌─────────────────┼──────────────────┐
   │                 │                  │
 Catalog          Procurement         Orders
   │                 │                  │
 Offers            Supply           Payments
   │                 │                  │
   └─────────────────┴──────────────────┘
                     │
              ConvertedMoney
```

---

# 61. Что я бы точно не делал

Не использовать:

```text
DB ENUM USD/EUR/UAH
```

как источник истины.

Не хранить:

```text
price Decimal
```

без currency.

Не позволять:

```text
Money USD + Money EUR
```

Не получать NBU API непосредственно при проведении документа.

Не менять старые документы при изменении курса.

Не хранить functional currency как:

```text
settings["currency"]
```

Не позволять silent fallback:

```text
нет курса → берем сегодняшний.
```

Не смешивать:

```text
display currency
functional currency
transaction currency.
```

---

# 62. План реализации по этапам

### Этап 1 — Shared Kernel

Реализовать:

```text
CurrencyCode
Money
ConversionSnapshot
ConvertedMoney
CurrencyMismatchError
```

Покрыть unit tests.

Особое внимание:

```text
Decimal
immutability
same-currency arithmetic
```

---

### Этап 2 — `public.currency`

Создать:

```text
CurrencyModel
```

и seed ISO-4217.

Сделать:

```text
CurrencyDirectoryPort
DjangoCurrencyDirectory
```

---

### Этап 3 — Tenant domain

Создать:

```text
CurrencyPolicy
FunctionalCurrencyPeriod
ManualExchangeRate
CurrencyPair
ExchangeRate
RateQuote
```

и соответствующие repository ports.

---

### Этап 4 — Tenant persistence

Таблицы:

```text
currency_policy
enabled_currency
functional_currency_period
manual_exchange_rate
fx_rate_import
```

Добавить:

```text
constraints
indexes
revision
audit fields
```

---

### Этап 5 — Rate Resolver

Реализовать порядок:

```text
identity
direct
inverse
cross
fail
```

с:

```text
EXACT
PREVIOUS_AVAILABLE
```

---

### Этап 6 — Conversion engine

Реализовать:

```text
MoneyConversionService
ConversionCalculator
MoneyQuantizer
```

И публичный:

```text
CurrencyFacade
```

---

### Этап 7 — Manual mode

Сделать:

```text
manual rates CRUD
revision history
permissions
audit
```

На этом этапе CRM уже полностью работает без NBU.

---

### Этап 8 — NBU adapter

Добавить:

```text
NbuHttpClient
NbuMapper
NbuRateProvider
SyncProviderRatesCommand
scheduler
retry
audit
```

---

### Этап 9 — Functional currency lifecycle

Реализовать:

```text
ScheduleFunctionalCurrencyChange
GetFunctionalCurrencyOnDate
period overlap protection
backdated change protection
```

---

### Этап 10 — интеграция бизнес-контекстов

Последовательно подключать:

```text
Supplier Offer
Supply
Order
Payment
Inventory valuation
Reports
```

Не пытаться сразу мигрировать все модели.

---

### Этап 11 — UI

Добавить:

```text
Currency Policy
Enabled Currencies
Manual Rates
Provider Status
Functional Currency History
```

Display currency пользователя хранить отдельно.

---

### Этап 12 — Hardening

Обязательно протестировать:

```text
выходные
отсутствующий курс
inverse rate
cross rate
смена provider
ревизия курса
смена functional currency
disabled currency
same currency conversion
ошибка API
повторный import
конкурирующие updates
```

---

# 63. Набор критических тестовых сценариев

Особенно важны:

```text
100 USD → UAH
```

по direct rate.

```text
UAH → USD
```

по inverse rate.

```text
USD → EUR
```

через UAH.

```text
UAH → UAH
```

identity.

Курс requested:

```text
Sunday
```

а effective:

```text
Friday
```

при `PREVIOUS_AVAILABLE`.

И:

```text
Sunday
```

должен вернуть ошибку при `EXACT`.

---

# 64. Итоговая ответственность слоев

| Слой               | Ответственность                                                |
| ------------------ | -------------------------------------------------------------- |
| `shared`           | примитивы `Money`, `CurrencyCode`, immutable monetary snapshot |
| `domain`           | правила валют, rate и functional currency                      |
| `application`      | orchestration use cases                                        |
| `ports`            | контракты storage/providers                                    |
| `infrastructure`   | Django ORM, PostgreSQL, NBU, cache                             |
| `contracts`        | публичный API Currency BC                                      |
| `presentation`     | REST/UI/Admin                                                  |
| consuming contexts | фиксация исторической стоимости документа                      |

И самое важное архитектурное правило:

```text
Currency BC
определяет курс и выполняет конвертацию

Но

Order / Supply / Payment
владеют историческим результатом этой конвертации.
```

Именно такое разделение не позволит валютному модулю со временем превратиться в глобальную связанную подсистему, от которой невозможно отделить каталог, закупки, заказы и финансовый учет.
