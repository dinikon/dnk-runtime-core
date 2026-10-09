# План учета товарных остатков: Warehousing и Inventory

Дата: 2026-10-09. Статус: целевой план нового функционала; реализация еще не начата.
Требования из постановки фиксируются как основа модели. Дополнительные решения
помечены как предложения и уточняются до реализации соответствующего этапа.
Уточнение границ MVP: учет только в штуках; справочник единиц, упаковки,
конвертация и расчет/контроль вместимости отложены на следующие этапы.

Связанные документы:

- [Обязательные архитектурные правила](../architecture/AGENTS.md).
- [План Catalog](catalog.md), в особенности граница SKU, Variant и габаритов.
- [Tenant-миграции](../data/tenant-migrations.md).
- [Правила Unit of Work](../architecture/AGENTS.md#unit-of-work).

## 1. Исходное состояние и цель

В текущей рабочей копии прежний Inventory удаляется ревизией
`0016_remove_inventory`; его маршруты и SQL-модели исключены из регистрации.
Catalog проектируется заново и пока не имеет реализации в `src/modules/catalog/`.
Новый учет не строится поверх удаленного SKU CRUD. Исторические миграции
сохраняются; новые модели и миграции вводятся после актуального tenant head.
Удаленные данные не восстанавливаются автоматически.

Цель — вести физические запасы и резервы, получать доступность для продажи,
проводить документы, перемещения и инвентаризации с защитой от повторного
проведения и конкурентного расходования одного количества.

Два bounded context:

| Контекст | Владеет | Предоставляет соседям |
| --- | --- | --- |
| Warehousing | Склады, зоны, адреса, иерархия, ограничения размещения | Application-контракты структуры и проверки размещения |
| Inventory | Учетные SKU, партии, запасы, резервы, документы, журнал, инвентаризации | Application-контракты SKU, остатков, доступности и операций |
| Catalog | Product, Variant, товарный контент и связь продаваемой позиции с учетным SKU | Снимок физической/виртуальной позиции через Application-контракт |

**Изменяемое количество принадлежит Inventory.** Warehouse, WarehouseZone,
StorageLocation, InventoryItem и StockLot не содержат текущего остатка.
StorageLocation хранит вместимость и ограничения, но не `quantity` и не
коллекцию запасов. Inventory использует ID склада и адреса.

## 2. Применимые архитектурные требования

Нормативный документ `docs/architecture/AGENTS.md` прочитан полностью.
Для реализации обоих модулей применяются следующие требования:

1. Четыре слоя; порядок каталогов: модуль → слой → Aggregate Root → назначение.
   Общие для нескольких агрегатов политики, порты, SQL-модели и Depends
   располагаются на уровне своего слоя. Названия `command`, `query`, `port`,
   `value_object`, `error.py` используются последовательно.
2. Domain — обычный Python без SQLAlchemy, FastAPI, Pydantic, HTTP и логирования.
   Application зависит от Domain и абстрактных портов. Infrastructure реализует
   их, Presentation вызывает Application. Чужие Domain/SQL-модели не импортируются.
3. Агрегаты самостоятельны и связаны ID. Внутренние строки документов и записи
   транзакции не получают отдельных write repositories.
4. Aggregate и Entity имеют явные `create(...)` и `restore(...)`; восстановление
   не создает события создания. Инварианты защищены фабриками и domain-методами.
   Прямые изменения состояния из Application и проверки агрегата в mapper запрещены.
5. `__post_init__` допустим только для VO. Command, Query, DTO и snapshots
   не используют его. Все методы и функции имеют аннотации входов и результата,
   включая `__init__ -> None`, фабрики, ports и `Handler.execute`.
6. Command и Query неизменяемы, не содержат Request, session и ORM.
   Каждый сценарий с результатом имеет свой `dto.py` и конкретный DTO.
   Для результата без данных используется `-> None`, без пустого DTO.
7. Domain Repository загружает/сохраняет Aggregate Root. Query Repository
   объявляется в Application и возвращает проекции конкретных сценариев;
   чтение списка не восстанавливает агрегаты.
8. Domain Service/Policy содержит чистые правила и не обращается к repository.
   Application координирует загрузку снимков, domain-методы и сохранение.
   Повторно используемая orchestration находится в Application service;
   handlers не вызывают друг друга.
9. Один процесс — одна tenant-транзакция. Внешняя сборка Depends открывает UoW
   и передает одну session всем репозиториям, адаптерам и Outbox этого процесса.
   В данном функционале handlers и repositories не вызывают commit/rollback
   и не открывают вложенные UoW. Ошибка commit не дает успешного HTTP-ответа.
10. Domain Events создаются в Domain; Application преобразует их в интеграционные
    сообщения. Outbox записывается до commit в общей транзакции. Доставка отдельно,
    после commit; потребители идемпотентны. Переиспользуются существующие shared
    UoW, Outbox, ClockPort и порт генерации UUID.
11. Каждый HTTP-метод имеет отдельный controller и собственные Request/Response
    при наличии тела. Router только регистрирует маршруты и зависимости.
    Для запроса без тела Request не нужен, для 204 Response не создается.
12. Depends — composition root. Authentication и authorization берутся напрямую
    из Presentation Identity; tenant и actor происходят из доверенного контекста.
    TenantBase, выбор схемы, admission и миграции остаются у Tenancy.
13. SQL-модели — отдельные файлы; `__init__.py` новых пакетов пустые, импорты прямые.
    Mapper выполняет только преобразования, QueryMapper называет методы
    `to_details`, `to_list_item`, `to_projection`, а не `to_domain`.
14. Явные имена классов отражают роль: `...Command`, `...Query`, `...Handler`,
    `...ResultDTO`, `...RepositoryProtocol`, `SqlAlchemy...Repository`,
    `...Request`, `...Response`. Классы и методы получают русские docstrings,
    объясняющие назначение, инварианты, отсутствие результата и транзакционность.
15. Логи не заменяют журнал и аудит. `*.committed` записывается только после
    успешного завершения UoW; один stack trace на границе, без полных payload
    и секретов. Domain не логирует. Время хранения — timezone-aware UTC.

Структуры из постановки адаптируются к этим правилам: общий
`application/commands/` заменяется сценариями под конкретными агрегатами,
а `document/receipt.py`, `document/transfer.py` и общий `repositories.py` —
отдельными каталогами Aggregate Roots.

## 3. Границы агрегатов

### 3.1. Warehousing

| Aggregate Root / каталог | Состояние и поведение | Инварианты |
| --- | --- | --- |
| Warehouse / `warehouse` | ID, код, название, тип, статус, настройки | Уникальный код в tenant, допустимые переходы статуса |
| WarehouseZone / `warehouse_zone` | ID склада, код зоны, тип, статус, правила хранения | Один склад, уникальный код в его пределах, согласованные ограничения |
| StorageLocation / `storage_location` | ID склада/зоны/родителя, адрес, тип, статус, вместимость, ограничения | Уникальный адрес в складе, принадлежность складу, отсутствие циклов, допустимый родитель |

StorageLocation — самостоятельный Aggregate Root. Изменение ячейки загружает
ее и необходимые снимки предков, а не все адреса склада. Zone и Warehouse
также не содержат коллекции тысяч ячеек.

ID склада у зоны и ячейки не меняется обычным обновлением. Перенос запасов
между складами выполняется Inventory, а не изменением `warehouse_id` адреса.
Изменение родителя проверяет всех затронутых предков; конкурирующие изменения
иерархии одного склада сериализуются, иначе две операции могут создать цикл.

LocationPolicy — чистая доменная политика Warehousing. Получает неизменяемые
снимки склада, зоны, адреса и состояния запасов; характеристики SKU и заполнение
добавляются при реализации контроля вместимости после MVP.
Проверяет активность, принадлежность, разрешенный статус/тип товара, ограничения
хранения. Проверка вместимости относится к следующему этапу. Снимки загружает
Application, сама политика не читает БД.
Inventory вызывает ее через публичный Application-контракт Warehousing и свой
порт; чужой domain service не импортируется в Inventory.

Вместимость StorageLocation остается опциональной. В MVP ограничения по объему
и массе выключены; расчет занятого объема/массы и его контроль не выполняются.
Неизвестные вместимость, габариты, масса и занятость представлены отсутствующим
значением, а не нулем. Отсутствие этих характеристик не блокирует приемку MVP.

После MVP допустимая вместимость остается у Warehousing, а занятость рассчитывает
Inventory из всех физически размещенных запасов. Проверка выполняется под
блокировкой адреса в общей UoW. Количества разных SKU и UOM нельзя складывать
как общие «штуки». При включении контроля отсутствие необходимых характеристик
должно блокировать размещение; будущий API не может заявлять включенный контроль
до реализации расчета и проверок.

**Предложение для MVP:** деактивация склада/зоны/адреса, исключение адреса из
продажи и ужесточение ограничений требуют проверки влияния через порт Inventory.
Деактивация с ненулевым запасом отклоняется; изменение, делающее размещение
недопустимым по действующим правилам хранения или нарушающее резервы, также
отклоняется. Контроль вместимости в эту проверку MVP не входит. Остатки не исчезают
из отчетов при изменении структуры.

### 3.2. Inventory

| Aggregate Root / каталог | Состояние и внутренние объекты | Инварианты |
| --- | --- | --- |
| InventoryItem / `inventory_item` | Учетный SKU, код, политика, базовая UOM, активность, характеристики единицы | Корректный режим учета, защищенные изменения политики |
| StockLot / `stock_lot` | Item ID, номер партии, производство, срок годности, блокировка | Принадлежность одному Item, согласованные даты |
| StockReservation / `stock_reservation` | Потребность, Item, склад, owner, зарезервировано/потреблено/освобождено | Потребление и освобождение не превышают активный остаток резерва |
| GoodsReceipt / `goods_receipt` | Черновик приемки и GoodsReceiptLine | Положительные строки, проведение один раз, проведенное неизменяемо |
| StockTransfer / `stock_transfer` | Склады, строки, отправленное/принятое количество, статус | Приемка не больше отправленного, контроль каждой частичной приемки |
| StockIssue / `stock_issue` | Документ выдачи и StockIssueLine, ссылки на резервы | Подтвержденный расход только допустимого запаса |
| StockWriteOff / `stock_write_off` | Строки и причины списания | Положительное количество, неизменяемость после проведения |
| StockAdjustment / `stock_adjustment` | Строки корректировки, основание, при необходимости Count ID | Общие правила проведения, контроль повторного применения |
| StockCount / `stock_count` | Область, строки подсчета, учетный снимок, результаты, статус | Расхождения применяются один раз, результаты согласованы с областью |
| StockTransaction / `stock_transaction` | Тип операции, документ, ключ идемпотентности, время, actor, StockLedgerEntry[] | Ненулевые записи, допустимый состав операции, неизменяемость после записи |

Все корни имеют собственные Domain Repository Protocol, `aggregate.py`,
`error.py`, VO и события при необходимости. Строки документов принадлежат
их документу, StockLedgerEntry — транзакции, StockCountLine — инвентаризации.
Документ отгрузки не содержит весь складской остаток.

Общие правила нескольких агрегатов находятся в `domain/stock/`:
StockPostingPolicy, AvailabilityPolicy, StockScope, StockDimension,
StockStatus, Quantity VO, StockBalance и StockAvailability.

- StockBalance — неизменяемый снимок транзакционной проекции, не бизнес-агрегат.
- StockAvailability — результат вычисления, не источник истины для проведения.
- StockLedgerEntry — учетная запись внутри StockTransaction. Второе независимое
  хранилище StockMovement не вводится; движения читаются проекцией журнала.
- Проверки достаточности, сохранения резервов и сохранения количества для
  внутренних операций выполняют политики на свежих снимках под блокировками.

## 4. Связь InventoryItem и Catalog.Variant

InventoryItem — самостоятельная идентичность складируемой единицы, а не копия
карточки. Несколько Catalog.Variant могут ссылаться на один InventoryItem;
они используют общие остатки и резервы. InventoryItem не имеет обязательного
единственного `variant_id` и не принадлежит жизненному циклу Product.

В плане Catalog поле называется `sku_id`. Для этой модели оно ссылается на
`InventoryItem.id`; SKU и InventoryItem не становятся двумя сущностями учета.
Итоговое имя поля (`sku_id` или `inventory_item_id`) согласуется в контрактах
Catalog до их реализации. На такую ссылку не ставится глобальный UNIQUE.
Предложение Catalog о запрете повторения SKU внутри одного Product требует
согласования отдельно; Inventory не вводит такой запрет и поддерживает повторное
использование учетной единицы несколькими Variant.

Виртуальная позиция не связывается с InventoryItem. Физический Variant может
быть черновиком без связи. Смена/удаление связи не удаляет InventoryItem,
его партии, документы или историю.

Регистрация Item принимает учетный код и политику. Опциональный исходный
`product_id + variant_id` служит для проверки складируемости через
CatalogVariantReaderProtocol, а не для определения владельца Item.
Без исходного Variant регистрируется самостоятельная физическая учетная единица.
Привязка Variant — сценарий Product в Catalog через порт проверки Inventory.
Handlers регистрации Item и привязки Variant не вызывают друг друга.

Размеры и масса единицы остаются у Inventory, как в плане Catalog, но в MVP
они опциональны и не обязательны для регистрации Item или приемки.
Транспортная упаковка и PackingPlan не входят в складской MVP.

InventoryPolicy включает `tracking_mode`, `base_uom`, `allow_fractional`,
`track_expiration`, `allow_negative_stock=False`.

- Все SKU в MVP учитываются в штуках: `base_uom="piece"`,
  `allow_fractional=False`. Поля сохраняются в модели для дальнейшего расширения.
  Фабрика регистрации автоматически устанавливает эти значения; пользователь
  не выбирает единицу, а API регистрации и обновления политики не принимает
  `base_uom` и `allow_fractional` как изменяемые поля.
- Справочник единиц, другие UOM, дробный учет, упаковки и коэффициенты пересчета
  откладываются. Все документы, движения, резервы и результаты подсчета MVP
  выражают количество в базовой единице `piece`.
- MVP реализует `NONE` и `LOT`. SERIAL и LOT_AND_SERIAL — следующие этапы:
  API отклоняет их, пока нет учета серийных экземпляров и их идентичности.
- Проверка `requires_lot()` для полной модели учитывает LOT и LOT_AND_SERIAL;
  проверка только равенства LOT из наброска непригодна для расширения.
- В режиме NONE `lot_id` запрещен; в LOT обязателен и должен принадлежать Item.
- Учет срока годности требует партий; обязательность `expires_at` определяется
  политикой Item. Политика запрещает некорректное сочетание настроек.
- После первого движения `base_uom` и `tracking_mode` не меняются обычным
  обновлением. Миграция количеств и режимов — отдельная управляемая процедура.
- Отрицательный физический и транзитный баланс в MVP запрещен всегда.

StockLot хранит `inventory_item_id`, `lot_number`, `manufactured_at`, `expires_at`,
`is_blocked`, `created_at`, но не остаток. Одна партия может находиться в нескольких
адресах и складах. **Предложение:** номер партии уникален внутри Item;
производство и срок годности после первого движения не исправляются обычным PATCH.
Блокировка партии проходит тот же контроль резервов и синхронизацию, что смена
статуса запасов.

### 4.1. Добавление единиц и упаковок после MVP

Справочник и новые базовые единицы вводятся для новых SKU. Существующие остатки
и движения продолжают обозначать штуки; добавление справочника не меняет их
смысл и не пересчитывает неизменяемый журнал. Смена базовой единицы существующего
Item с движениями требует отдельной управляемой миграции.

При добавлении упаковок строки документа сохраняют исходное количество,
исходную единицу и использованный коэффициент пересчета, а также количество
в базовой единице. Например, «2 коробки × 12 штук» записывается как 24 штуки
в баланс и журнал. Изменение коэффициента упаковки не пересчитывает проведенные
документы. Такие поля и сценарии добавляются вместе с поддержкой упаковок,
не создавая незавершенной конвертации в MVP.

## 5. Измерения, количества и журнал

### 5.1. Физический запас

StockDimension физического запаса:

```text
inventory_item_id
warehouse_id
location_id
lot_id             optional только при допустимом tracking mode
owner_id
stock_status
```

В MVP физический баланс всегда привязан к адресу. Для склада без адресного
хранения создается явный адрес по умолчанию. `location_id=None` не обозначает
неизвестное физическое размещение. Owner обязателен: собственная организация
tenant, определенная через доверенный контекст/согласованный Application-порт.
Tenant ID и организация-владелец не считаются одной идентичностью автоматически.
Ответственное хранение и несколько владельцев откладываются, но owner входит
в ключ баланса и резерва с первого этапа.

| StockStatus | Значение | Участвует в доступности продажи |
| --- | --- | --- |
| AVAILABLE | Физически пригоден к продаже | При выполнении остальных условий |
| QUARANTINE | Ожидает проверки | Нет |
| DAMAGED | Брак/повреждение | Нет |
| BLOCKED | Учетная блокировка | Нет |

Резерв не является StockStatus. Заблокированная партия исключает доступность
всех своих измерений без переименования их физического статуса.

Количество хранится в `Decimal` и `NUMERIC(24,6)`, не float. В MVP единственная
базовая единица — `piece`; конвертация не выполняется.
Количество операции положительное; signed delta ненулевой; баланс неотрицателен.
Все количественные значения MVP целые: дробные количества в документах,
резервах, движениях, корректировках и результатах инвентаризации отклоняются
без округления. Значение `Decimal("2.000000")` допустимо, `Decimal("2.5")` — нет.
NaN, Infinity и превышение точности также отклоняются. Для этих разных смыслов
используются раздельные VO, а не один положительный Quantity для всех полей.

### 5.2. Неизменяемый журнал и текущий баланс

StockTransaction содержит `id`, `operation_type`, `document_reference`,
`idempotency_key`, `occurred_at`, `performed_by`, `recorded_at`, записи и,
для компенсации, `reverses_transaction_id`.

| Операция | Записи |
| --- | --- |
| Приемка извне | +Q на физический адрес |
| Перенос A → B | −Q по измерению A, +Q по измерению B |
| Смена статуса | −Q со старым статусом, +Q с новым |
| Отгрузка/списание за пределы учета | −Q с физического адреса |
| Корректировка | Signed delta по конкретному измерению с основанием |

Для внутренних операций сумма равна нулю отдельно для каждой пары Item + Lot +
Owner; статус и адрес могут меняться в рамках допустимого перехода. Приемка
и внешний расход не требуют искусственного отрицательного баланса контрагента.
Источник и назначение внутреннего движения должны различаться.

Журнал добавляется и баланс синхронно обновляется в той же транзакции.
StockPostingService в Application загружает снимки, вызывает StockPostingPolicy
и чистые методы агрегатов, затем через порты пишет журнал и проекцию.
Сервис не содержит самих правил достаточности и не делает commit.
StockBalanceRepositoryProtocol — Application-порт работы с технической
проекцией; он не имитирует Domain Repository и не принимает HTTP DTO.

Проведенная транзакция и строки не редактируются и не удаляются обычным API.
Исправление создает новую операцию с ссылкой на исходную, проверяет текущую
достаточность и учитывает зависимые документы. Нельзя просто сменить знак всех
записей, игнорируя уже отгруженный запас или принятый transfer.
**Предложение MVP:** одна полная компенсация исходной транзакции, с UNIQUE
по `reverses_transaction_id`; повтор с другим ключом не создает вторую компенсацию.
Частичные компенсации требуют отдельного контроля накопленных количеств и
откладываются. Если появились зависимые операции, сначала разрешаются они.
Признак компенсации исходного документа читается проекцией связей журнала,
а не изменением исходных проведенных строк.

### 5.3. Товар в пути между складами

Dispatch и Receive — разные операции и разные UoW. **Предложение:** Inventory
вводит `StockScopeKind.PHYSICAL | IN_TRANSIT`. Физическая область сохраняет
измерения выше; транзитная содержит `transfer_id`, ID строки, исходный и
целевой склады, Item, Lot, Owner и статус груза. Это специализированный VO
учетной области, а не искусственная ячейка Warehousing.

Отправка пишет −Q физического запаса и +Q транзитного. Приемка пишет −Q
соответствующего транзита и +Q на фактический адрес назначения. Транзит
исключается из физического on_hand складов и из EligibleOnHand; отчеты показывают
его отдельно. У каждой частичной приемки свой ключ идемпотентности.

Строка transfer контролирует `received <= dispatched <= planned` и сохраняет
Item/Lot/Owner. Приемка может разбиваться по адресам и допустимым статусам,
например AVAILABLE/QUARANTINE, с сохранением количества. Необъяснимая недостача
не исчезает: остается в пути до отдельного решения о возврате/списании.
До отправки черновик отменяется; после отправки возврат/компенсация — новые
учетные операции. Простой статус документа «в пути» без учета Q недостаточен.

## 6. Резервы и доступность

Мягкий резерв MVP создается на Item + Warehouse + Owner под
`source_type`, `source_id`, `source_line_id`. Он не выбирает Lot и Location.
Будущий StockAllocation для жесткого выделения партии/адреса — вне MVP.

```text
active_reserved = quantity_reserved − quantity_consumed − quantity_released
available = eligible_on_hand − active_reserved
```

StockReservation защищает `active_reserved >= 0` через `reserve`, `release`,
`consume`, `cancel`. Создание/увеличение проверяет AvailabilityPolicy на свежем
снимке под блокировкой общей области. **Предложение:** одна активная запись
на потребность + Item + склад + owner; увеличение — явный сценарий.

EligibleOnHand для продажи включает только физическую область AVAILABLE,
активные допустимые адреса, незаблокированные и непросроченные партии.
В расчет передается `eligibility_at`: дата операции или ожидаемой отгрузки.
Дата годности оценивается в согласованной временной зоне склада; точная
семантика «годен до даты включительно» фиксируется до реализации LOT.

Срок годности может уменьшить доступность без новой записи журнала.
Существующий мягкий резерв не гарантирует неизменную пригодность партии
в будущем: при выдаче выполняется повторная проверка. Query возвращает
`eligible_on_hand`, `active_reserved`, `available_to_reserve=max(0, available)`,
`reservation_shortage=max(0, -available)` и дату вычисления. Дефицит не скрывается.
Запрос доступности — снимок; право на резерв подтверждает только команда.

При IssueStock резерв остается активным до подтвержденного расхода.
Одновременно уменьшаются физический баланс и собственный резерв. Повторное
вычитание «отобранного» количества не допускается; отдельного PICKED в MVP нет.
Выдача без резерва не может расходовать количество, необходимое другим резервам.

Операции списания, переноса на другой склад, смены статуса, блокировки партии,
уменьшения баланса и изменения доступности адреса проверяют:

```text
eligible_on_hand_after >= active_reserved_after
```

Проверка применяется к затронутой доступности и дате операции; уже возникший
из-за срока годности дефицит не устраняется фиктивным расходом. Расход непригодного
запаса, который не уменьшает EligibleOnHand, рассматривается отдельно политикой.
Если нужный запас зарезервирован, пользователь сначала освобождает/переназначает
потребность явной операцией. Документ не освобождает чужие резервы автоматически.

## 7. Согласованность, блокировки и идемпотентность

StockScopeLockerProtocol — Application-порт. **Предложение для PostgreSQL:**
tenant-local `inventory_stock_scopes` с уникальным ключом Item + Warehouse + Owner,
`INSERT ... ON CONFLICT DO NOTHING`, затем `SELECT ... FOR UPDATE`. Строка
существует даже при нулевом запасе: блокировка только существующих StockBalance
не защищает пустую область. SQL и session остаются в Infrastructure.

Все команды, меняющие баланс, резервы или пригодность, используют один протокол:

1. Получить общие блокировки жизненного цикла затронутых складов и активных
   областей инвентаризации, проверить состояние склада/области.
2. В стабильном порядке заблокировать учетные политики Item/Lot, затем все
   StockScope, метаданные затронутых адресов и изменяемые документы/резервы.
   При нескольких складах и SKU ключи сортируются одинаково у всех операций.
3. После блокировок повторно загрузить баланс, резервы, документ, пригодность
   и метаданные адресов; чтения до блокировки не используются для решения
   о проведении. Заполнение добавляется при реализации контроля вместимости.
4. Вызвать Domain policies и методы; записать документы, резервы, транзакцию,
   баланс, запись идемпотентности и Outbox в одной session.
5. Внешний UoW завершает транзакцию. Любая ошибка откатывает весь результат.

Конкретная иерархия shared/exclusive locks для Item, Lot и адресов уточняется
на этапе ядра и проверяется тестами deadlock/retry. Она должна охватывать
гонки изменения TrackingMode с первым движением, блокировки партии с резервом
и деактивации адреса с приемкой. Конкурентное заполнение одной ячейки разными
SKU проверяется при добавлении контроля вместимости после MVP.
Изменение метаданных получает несовместимую блокировку с операциями, использующими
эти метаданные; один только snapshot без такой синхронизации недостаточен.

Warehousing получает влияние запасов через свой Application-порт
InventoryLocationImpactReaderProtocol. Его адаптер обращается к публичному
Application service Inventory на той же session. Обратный Inventory adapter
использует публичный Application service Warehousing. Эти сервисы читают снимки
и проверяют правила, не вызывают друг друга рекурсивно и не запускают handlers.
Жизненные циклы метаданных и количеств имеют общий согласованный порядок locks.

Перенос между складами блокирует исходную и целевую область. Приемка и выдача
нескольких строк проверяются как единая операция; частично успешного документа
из-за последовательного commit строк нет. Допустимые частичные приемки transfer
являются отдельными явно заданными операциями.

Идемпотентность команд с внешним повтором:

- Область ключа: tenant + тип сценария + idempotency_key; canonical payload hash
  включает документ/строки/количества, а не технические request_id.
- Такой же ключ и payload возвращают сохраненный результат исходной операции.
  Другой payload с тем же ключом дает конфликт.
- UNIQUE записи идемпотентности и ссылок проведения документа защищают
  конкурентный повтор. Один документ нельзя провести дважды и с разными ключами.
- Результат и business writes фиксируются атомарно. Для `-> None` хранится
  подтверждение выполнения, а HTTP повтор снова возвращает 204.
- Конфликт записи разбирается безопасно через savepoint или повтор всей
  операции во внешней сборке; handler не продолжает работу в сломанной транзакции.
- Deadlock/serialization failure допускает ограниченный retry всей транзакции
  вне handler с тем же ключом. Бизнес-отказ не повторяется автоматически.

Идемпотентность не заменяет блокировки остатков. Ни резерв, ни выдача не строятся
по схеме «прочитал → проверил → записал» без синхронизации.

## 8. Реестр сценариев и контрактов

Все команды получают доверенный tenant/actor; queries — tenant и параметры
чтения. UUID, Decimal и даты в DTO не заменяются ORM/domain-агрегатами.
Ревизия передается в команды изменения документа/структуры как expected_revision.
Указанные HTTP-пути относительны `/api/console`; варианты имен — целевые контракты.

Обозначения портов в таблицах:

- W, Z, L: Warehouse, WarehouseZone, StorageLocation Domain Repository Protocol.
- I, B, R, G, T, E, O, A, C, J: InventoryItem, StockLot, StockReservation,
  GoodsReceipt, StockTransfer, StockIssue, StockWriteOff, StockAdjustment,
  StockCount, StockTransaction Domain Repository Protocol.
- P: StockPostingService с StockScopeLocker, StockBalanceRepository,
  StockPostingRepository (проекция/идемпотентность), WarehouseLocationReader,
  соответствующими Domain repositories, Clock и Outbox.
- V: CatalogVariantReader; X: InventoryLocationImpactReader и структура Warehousing.
- Q: Query Repository соответствующего сценария, объявленный в Application.

### 8.1. Warehousing: команды

| Сценарий / Aggregate Root | Вход помимо контекста | `Handler.execute ->` и поля результата | Порты | HTTP |
| --- | --- | --- | --- | --- |
| CreateWarehouse / warehouse | code, title, type, policy | CreateWarehouseResultDTO(id, code, status, revision) | W | POST /warehousing/warehouses → 201 |
| UpdateWarehouse / warehouse | id, title, policy, expected_revision | UpdateWarehouseResultDTO(id, title, revision) | W, X | PATCH /warehousing/warehouses/{id} → 200 |
| ChangeWarehouseStatus / warehouse | id, status, expected_revision | None | W, X | POST /warehousing/warehouses/{id}/change-status → 204 |
| CreateWarehouseZone / warehouse_zone | warehouse_id, code, type, policy | CreateWarehouseZoneResultDTO(id, warehouse_id, code, revision) | Z, W | POST /warehousing/zones → 201 |
| UpdateWarehouseZone / warehouse_zone | id, type, policy, expected_revision | UpdateWarehouseZoneResultDTO(id, revision) | Z, X | PATCH /warehousing/zones/{id} → 200 |
| ChangeWarehouseZoneStatus / warehouse_zone | id, status, expected_revision | None | Z, X | POST /warehousing/zones/{id}/change-status → 204 |
| CreateStorageLocation / storage_location | warehouse_id, zone_id, parent_id, address, type, capacity, policy | CreateStorageLocationResultDTO(id, warehouse_id, address, revision) | L, W, Z | POST /warehousing/locations → 201 |
| UpdateStorageLocation / storage_location | id, address, capacity, policy, expected_revision | UpdateStorageLocationResultDTO(id, address, revision) | L, X | PATCH /warehousing/locations/{id} → 200 |
| MoveStorageLocationInHierarchy / storage_location | id, parent_id, zone_id, expected_revision | MoveStorageLocationInHierarchyResultDTO(id, parent_id, zone_id, revision) | L, Z, X | POST /warehousing/locations/{id}/move-in-hierarchy → 200 |
| ChangeStorageLocationStatus / storage_location | id, status, expected_revision | None | L, X | POST /warehousing/locations/{id}/change-status → 204 |

В MVP `capacity` опциональна и отсутствует/null: ограничения вместимости
не включаются. Create/Update Request не позволяют установить действующие лимиты
объема или массы; попытка передать конфигурацию контроля, отличную от null, отклоняется
с 422 как неподдерживаемая в MVP. Query Response отражает отсутствие вместимости,
не подставляя ноль. Настройка лимитов и показ занятого объема добавляются после MVP.

PATCH изменяет только явно переданные поля; изменение жизненного цикла не
скрывается в универсальном update. Архивирование предпочтительнее удаления
объектов, на которые ссылается журнал; hard delete API в MVP не планируется.

### 8.2. Inventory: команды

Для операций проведения требуются idempotency_key и основание. Позиции передают
Item, Lot, Owner, адрес/статус и целое количество в базовой UOM `piece`.
Выбор единицы и ввод упаковок в Request отсутствуют. Каждый вид строк имеет
собственный Command line contract; общий `DocumentDTO` не вводится.

| Сценарий / Aggregate Root | Вход помимо контекста | `Handler.execute ->` и поля результата | Порты | HTTP |
| --- | --- | --- | --- | --- |
| RegisterInventoryItem / inventory_item | code, policy без выбора UOM/дробности, optional характеристики и исходный Variant | RegisterInventoryItemResultDTO(id, code, base_uom, allow_fractional, tracking_mode, revision) | I, V при Variant | POST /inventory/items → 201 |
| UpdateInventoryItemPolicy / inventory_item | id, разрешенные настройки без base_uom/allow_fractional, expected_revision | UpdateInventoryItemPolicyResultDTO(id, policy, revision) | I, J, locker | PATCH /inventory/items/{id}/policy → 200 |
| RegisterStockLot / stock_lot | item_id, lot_number, manufactured_at, expires_at | RegisterStockLotResultDTO(id, item_id, lot_number, revision) | B, I | POST /inventory/lots → 201 |
| ChangeStockLotBlock / stock_lot | id, is_blocked, reason, expected_revision | None | B, I, P, R | POST /inventory/lots/{id}/change-block → 204 |
| CreateGoodsReceipt / goods_receipt | warehouse_id, external_reference, строки | CreateGoodsReceiptResultDTO(id, status, revision) | G, I, B, location reader | POST /inventory/receipts → 201 |
| UpdateGoodsReceiptDraft / goods_receipt | id, replacement строк, expected_revision | UpdateGoodsReceiptDraftResultDTO(id, status, revision) | G, I, B, location reader | PATCH /inventory/receipts/{id} → 200 |
| CancelGoodsReceipt / goods_receipt | id, reason, expected_revision | None | G | POST /inventory/receipts/{id}/cancel → 204 |
| PostGoodsReceipt / goods_receipt | id, expected_revision, ключ | PostGoodsReceiptResultDTO(document_id, transaction_id, status, posted_at) | G, P | POST /inventory/receipts/{id}/post → 200 |
| MoveStock / stock_transaction | исходное/целевое измерения, quantity, ключ | MoveStockResultDTO(transaction_id, occurred_at) | P | POST /inventory/stock/move → 200 |
| ChangeStockStatus / stock_transaction | измерение, target_status, quantity, reason, ключ | ChangeStockStatusResultDTO(transaction_id, occurred_at) | P | POST /inventory/stock/change-status → 200 |
| CreateStockTransfer / stock_transfer | source/destination warehouse, строки | CreateStockTransferResultDTO(id, status, revision) | T, I, B, location reader | POST /inventory/transfers → 201 |
| CancelStockTransfer / stock_transfer | id, reason, expected_revision; только до отправки | None | T | POST /inventory/transfers/{id}/cancel → 204 |
| DispatchStockTransfer / stock_transfer | id, строки отправки, expected_revision, ключ | DispatchStockTransferResultDTO(document_id, transaction_id, status, dispatched_at) | T, P | POST /inventory/transfers/{id}/dispatch → 200 |
| ReceiveStockTransfer / stock_transfer | id, количества по transfer line, адресам/статусам, revision, ключ | ReceiveStockTransferResultDTO(document_id, transaction_id, status, received_at) | T, P | POST /inventory/transfers/{id}/receive → 200 |
| ReserveStock / stock_reservation | item_id, warehouse_id, owner, source IDs, quantity, eligibility_at, ключ | ReserveStockResultDTO(id, quantity_reserved, active_quantity, status) | R, I, P | POST /inventory/reservations → 201 |
| IncreaseStockReservation / stock_reservation | id, quantity, eligibility_at, revision, ключ | IncreaseStockReservationResultDTO(id, active_quantity, revision) | R, P | POST /inventory/reservations/{id}/increase → 200 |
| ReleaseStockReservation / stock_reservation | id, quantity, reason, revision, ключ | None | R, locker, Outbox | POST /inventory/reservations/{id}/release → 204 |
| CancelStockReservation / stock_reservation | id, reason, revision, ключ | None | R, locker, Outbox | POST /inventory/reservations/{id}/cancel → 204 |
| IssueStock / stock_issue | источник потребности, строки фактического расхода, optional reservation_id, ключ | IssueStockResultDTO(document_id, transaction_id, posted_at, consumed_reservations) | E, R, P | POST /inventory/issues → 201 |
| WriteOffStock / stock_write_off | строки, причины, ключ | WriteOffStockResultDTO(document_id, transaction_id, posted_at) | O, P | POST /inventory/write-offs → 201 |
| AdjustStock / stock_adjustment | измерения, signed delta, reason, ключ | AdjustStockResultDTO(document_id, transaction_id, posted_at) | A, P | POST /inventory/adjustments → 201 |
| CompensateStockTransaction / stock_transaction | original_id, явные компенсирующие строки, reason, ключ | CompensateStockTransactionResultDTO(transaction_id, original_id, occurred_at) | J, затронутые документы, P | POST /inventory/transactions/{id}/compensate → 201 |
| StartStockCount / stock_count | warehouse_id, область, ключ | StartStockCountResultDTO(id, status, snapshot_at, revision) | C, balance reader, scope gate | POST /inventory/counts → 201 |
| SubmitStockCount / stock_count | id, измерения и counted_quantity, expected_revision | SubmitStockCountResultDTO(id, status, revision, discrepancies) | C | POST /inventory/counts/{id}/submit → 200 |
| ApproveStockCount / stock_count | id, expected_revision, ключ | ApproveStockCountResultDTO(count_id, adjustment_id, transaction_id, approved_at) | C, A, P | POST /inventory/counts/{id}/approve → 200 |
| CancelStockCount / stock_count | id, reason, expected_revision | None | C, scope gate | POST /inventory/counts/{id}/cancel → 204 |

RegisterInventoryItemCommand не принимает `base_uom` и `allow_fractional`:
фабрика Item устанавливает `piece` и `False`. RegisterInventoryItemResponse
возвращает оба значения. UpdateInventoryItemPolicyRequest/Command не содержат
этих изменяемых полей; попытка передать их в HTTP дает 422. Его Response
возвращает текущую политику, включая `base_uom="piece"`, `allow_fractional=False`.
Проверка фабрики/restore сохраняет эти инварианты и для вызовов вне HTTP.

Одношаговые IssueStock, WriteOffStock и AdjustStock создают и проводят документ
в одной UoW. Их документные Aggregate Roots сохраняются и доступны для чтения;
отдельный черновой жизненный цикл для этих операций в MVP не требуется.
При нулевых расхождениях ApproveStockCount завершает сеанс без пустого adjustment
и транзакции: соответствующие ID в его DTO имеют тип `UUID | None`.

### 8.3. Queries

| Сценарий / каталог Application | Вход | `Handler.execute ->` | HTTP |
| --- | --- | --- | --- |
| GetWarehouse / warehouse | id | GetWarehouseDetailsDTO | GET /warehousing/warehouses/{id} |
| ListWarehouses / warehouse | status, type, cursor, limit | ListWarehousesResultDTO(items: tuple[ListWarehouseItemDTO, ...], next_cursor) | GET /warehousing/warehouses |
| GetWarehouseZone / warehouse_zone | id | GetWarehouseZoneDetailsDTO | GET /warehousing/zones/{id} |
| ListWarehouseZones / warehouse_zone | warehouse_id, cursor, limit | ListWarehouseZonesResultDTO(items: tuple[ListWarehouseZoneItemDTO, ...], next_cursor) | GET /warehousing/zones |
| GetStorageLocation / storage_location | id | GetStorageLocationDetailsDTO | GET /warehousing/locations/{id} |
| ListStorageLocations / storage_location | warehouse_id, zone_id, parent_id, status, cursor, limit | ListStorageLocationsResultDTO(items: tuple[ListStorageLocationItemDTO, ...], next_cursor) | GET /warehousing/locations |
| GetInventoryItem / inventory_item | id | GetInventoryItemDetailsDTO | GET /inventory/items/{id} |
| ListInventoryItems / inventory_item | code/search, is_active, cursor, limit | ListInventoryItemsResultDTO(items: tuple[ListInventoryItemRowDTO, ...], next_cursor) | GET /inventory/items |
| GetStockLot / stock_lot | id | GetStockLotDetailsDTO | GET /inventory/lots/{id} |
| ListStockLots / stock_lot | item_id, is_blocked, expiry filters, cursor, limit | ListStockLotsResultDTO(items: tuple[ListStockLotRowDTO, ...], next_cursor) | GET /inventory/lots |
| GetStockBalance / stock_transaction | полное физическое/транзитное измерение | GetStockBalanceResultDTO(dimension, quantity, base_uom, as_of) | GET /inventory/stock/balance |
| ListStockBalances / stock_transaction | Item, Warehouse, Location, Lot, Owner, Status, scope kind, cursor, limit | ListStockBalancesResultDTO(items: tuple[ListStockBalanceItemDTO, ...], next_cursor) | GET /inventory/stock/balances |
| GetStockAvailability / stock_transaction | Item, Warehouse, Owner, eligibility_at | GetStockAvailabilityResultDTO(eligible_on_hand, active_reserved, available_to_reserve, reservation_shortage, base_uom, as_of) | GET /inventory/stock/availability |
| ListStockMovements / stock_transaction | измерения, document, date range, cursor, limit | ListStockMovementsResultDTO(items: tuple[ListStockMovementItemDTO, ...], next_cursor) | GET /inventory/stock/movements |
| GetStockReservation / stock_reservation | id | GetStockReservationDetailsDTO | GET /inventory/reservations/{id} |
| ListStockReservations / stock_reservation | Item, Warehouse, source IDs, status, cursor, limit | ListStockReservationsResultDTO(items: tuple[ListStockReservationRowDTO, ...], next_cursor) | GET /inventory/reservations |
| GetStockDocument / общий query | document_type, id | GetStockDocumentResultDTO(document_type, details: GoodsReceiptDetailsDTO \| StockTransferDetailsDTO \| StockIssueDetailsDTO \| StockWriteOffDetailsDTO \| StockAdjustmentDetailsDTO) | GET /inventory/documents/{document_type}/{id} |
| ListStockDocuments / общий query | document_type, warehouse, status, date range, cursor, limit | ListStockDocumentsResultDTO(items: tuple[ListStockDocumentItemDTO, ...], next_cursor) | GET /inventory/documents |
| GetStockCount / stock_count | id | GetStockCountDetailsDTO | GET /inventory/counts/{id} |
| ListStockCounts / stock_count | warehouse_id, status, cursor, limit | ListStockCountsResultDTO(items: tuple[ListStockCountItemDTO, ...], next_cursor) | GET /inventory/counts |

GetStockDocument — специально ограниченный сценарий чтения нескольких видов
документов. Его DTO содержит типизированный discriminated union, а не `dict`
с произвольными полями или универсальную write-модель. StockCount читается отдельно.
Общие `application/query/get_stock_document` и `list_stock_documents` допустимы,
поскольку относятся к нескольким агрегатам; они не создают Document Aggregate Root.

Все DTO и HTTP Response, содержащие количество, явно возвращают `base_uom`
в соответствующей строке или результате; для MVP это `piece`. Item details/list
также возвращают `base_uom` и `allow_fractional`. Поле единицы не участвует
в выборе пользователем и не обозначает поддержку упаковок или пересчета.

Каждый Q реализуется Infrastructure Query Repository + QueryMapper. Остаток
отсутствующей строки для валидного измерения равен нулю; неизвестный Item/адрес
дает not found. Пагинация стабильна, с дополнительным ID в сортировке.
Доступность читается одним согласованным DB snapshot, а не набором запросов,
которые могут увидеть разные моменты commit.

### 8.4. Обязательные файлы каждого сценария

Каждая строка командной таблицы разворачивается в:

```text
application/<aggregate_root>/command/<scenario>/command.py
application/<aggregate_root>/command/<scenario>/handler.py
application/<aggregate_root>/command/<scenario>/dto.py       если результат не None
presentation/<aggregate_root>/http/controller/<scenario>.py
presentation/<aggregate_root>/http/request/<scenario>.py    если есть тело запроса
presentation/<aggregate_root>/http/response/<scenario>.py   если ответ имеет тело
presentation/<aggregate_root>/depends.py                    get_<scenario>_handler
presentation/<aggregate_root>/router.py                     регистрация endpoint
```

Для Query используются `query/<scenario>/query.py`, `handler.py`, `dto.py`;
свои controller/response и Depends. Общие документные queries располагаются
на уровне Application и имеют HTTP-файлы в `presentation/http/`, зависимости
в `presentation/depends/documents.py`. Для stock queries под StockTransaction
маршруты `/stock/...` не меняют архитектурное владение.

Все вложенные DTO принадлежат сценарию: например, PostGoodsReceiptResultDTO
не переиспользуется как ReceiveStockTransferResultDTO. DTO «policy» в таблице
также разворачивается в типизированные поля/вложенный DTO своего use case.
Query contracts, persistence adapters и доменные repositories определены
для каждого агрегата; общие технические порты используются только по назначению.

### 8.5. Порты, снимки и адаптеры

| Application-порт / владелец | Вход и результат | Infrastructure adapter |
| --- | --- | --- |
| CatalogVariantReaderProtocol / Inventory | tenant, product_id, variant_id → CatalogVariantForInventorySnapshot; только идентичность и признаки физической позиции | `inventory/infrastructure/adapter/catalog_variant_reader.py`, публичный Application reader Catalog |
| WarehouseLocationReaderProtocol / Inventory | tenant, адреса и параметры размещения → WarehousePlacementSnapshot / результат допустимости; характеристики и заполнение добавляются после MVP для контроля вместимости | `inventory/infrastructure/adapter/warehouse_location_reader.py`, публичный Application service Warehousing с LocationPolicy |
| InventoryLocationImpactReaderProtocol / Warehousing | tenant, область склада/зоны/адреса и предложенное изменение → InventoryLocationImpactSnapshot | `warehousing/infrastructure/adapter/inventory_location_impact_reader.py`, публичный Application service Inventory |
| StockScopeLockerProtocol / Inventory | tenant, отсортированные StockScope и контекст freeze → None; locks действуют до конца UoW | `inventory/infrastructure/persistence/stock_scope_locker.py` |
| StockBalanceRepositoryProtocol / Inventory | scope/dimensions → tuple[StockBalance, ...]; применение проверенных записей StockTransaction → None | `inventory/infrastructure/persistence/stock_balance_repository.py` |
| StockPostingRepositoryProtocol / Inventory | ключ + payload hash → сохраненный результат конкретного сценария или отсутствие; запись результата/связи проведения → None | `inventory/infrastructure/persistence/stock_posting_repository.py` |
| StockAvailabilityReaderProtocol / Inventory | scope + eligibility_at → StockAvailabilitySnapshot со свежими количествами, резервами и признаками пригодности | `inventory/infrastructure/persistence/stock_availability_reader.py` и адаптер структуры Warehousing |
| Lifecycle/CountScope gates / владельцы метаданных и Inventory | tenant, область, режим lock → None; чтение freeze → CountScopeStateSnapshot | Адаптеры блокировок внутри соответствующего модуля на общей session |

Snapshots для доменных решений неизменяемы и определены в принимающем контексте.
Adapter переводит публичные DTO поставщика в эти снимки; чужой Aggregate,
SQL row или транспортный DTO в Domain не передается. AvailabilityPolicy
вычисляет доступность из снимка, а не доверяет кэшированному числу query API.
Query repositories возвращают только DTO своего сценария. Общий порт
идемпотентности хранит типизированные результаты зарегистрированных сценариев;
`dict` и единый универсальный business DTO не заменяют эти контракты.

Все перечисленные ports и их методы получают конкретные аннотации.
Методы проверки, блокировки и записи без данных имеют `-> None`. Публичные
Application services поставщиков получают порты на внешне открытой session;
они не открывают новый UoW ради межмодульного вызова.

## 9. Целевая структура модулей

Список Aggregate Roots ниже определяет каталоги во всех четырех слоях:

```text
warehousing: warehouse, warehouse_zone, storage_location
inventory:   inventory_item, stock_lot, stock_reservation, goods_receipt,
             stock_transfer, stock_issue, stock_write_off, stock_adjustment,
             stock_count, stock_transaction
```

Для каждого корня применяется структура:

```text
src/modules/<module>/
├── domain/<aggregate_root>/
│   ├── aggregate.py
│   ├── repository.py
│   ├── error.py
│   ├── value_object/
│   ├── entity/                         только внутренние Entity корня
│   └── event/                          при наличии доменных событий
├── application/<aggregate_root>/
│   ├── command/<scenario>/
│   │   ├── command.py
│   │   ├── handler.py
│   │   └── dto.py                      только для результата с данными
│   ├── query/<scenario>/
│   │   ├── query.py
│   │   ├── handler.py
│   │   └── dto.py
│   └── port/query_repository.py
├── infrastructure/<aggregate_root>/persistence/
│   ├── repository.py
│   ├── mapper.py
│   ├── query_repository.py
│   └── query_mapper.py
├── infrastructure/persistence/models/<model>.py
└── presentation/<aggregate_root>/
    ├── depends.py
    ├── router.py
    └── http/
        ├── controller/<scenario>.py
        ├── request/<scenario>.py
        └── response/<scenario>.py
```

Общие компоненты Inventory:

```text
domain/stock/                         VO, snapshots, policies, ошибки ядра
application/port/                    stock_scope_locker.py,
                                     stock_balance_repository.py,
                                     stock_posting_repository.py,
                                     warehouse_location_reader.py,
                                     catalog_variant_reader.py,
                                     stock_availability_reader.py
application/service/                 stock_posting.py, availability.py,
                                     location_impact.py
application/query/                   get_stock_document, list_stock_documents
application/event/                   mapping доменных событий в сообщения
infrastructure/persistence/          stock_scope_locker.py,
                                     stock_balance_repository.py,
                                     stock_posting_repository.py,
                                     stock_availability_reader.py
infrastructure/adapter/              catalog_variant_reader.py,
                                     warehouse_location_reader.py
presentation/depends/                stock.py, documents.py
presentation/router.py               сборка router модуля
```

Warehousing добавляет чистую LocationPolicy в `domain/storage_location/`,
Application-порты влияния Inventory и блокировок жизненного цикла, service
проверки размещения и Infrastructure adapter влияния Inventory.
Общие Clock/UUID/Outbox импортируются напрямую из shared; пустые локальные
обертки над ними не создаются. StockJournalRepository — роль append-only
Domain Repository StockTransaction, а не второй repository тех же записей.
Пустые каталоги и неиспользуемые файлы заранее не создаются.

## 10. Документы и инвентаризация

Общее правило документа: черновик редактируем; проведенный неизменяем;
переходы принадлежат его агрегату. Не все документы используют один enum:
receipt достаточно DRAFT/POSTED/CANCELLED, transfer требует состояний отправки
и частичной приемки, count — подсчета и утверждения. Общими могут быть VO
DocumentReference и причина, но не универсальный lifecycle.

StockCount: **предложение MVP — подсчет с заморозкой физических движений
в выбранной области.** Start фиксирует учетный снимок и persisted freeze marker
в короткой UoW. SQL-транзакция не удерживается на время работы кладовщика.
Все последующие posting-команды проверяют marker под общей блокировкой.
Область включает склад и явные адреса/фильтры; новые измерения внутри области
тоже защищены, даже если их не было в снимке. Пересекающиеся активные counts
запрещены; блокируется изменение соответствующей структуры размещения.

Submit сохраняет фактические количества, в том числе обнаруженные измерения
с учетным нулем. Отсутствующая строка — «не подсчитано», не автоматический ноль.
Нулевое количество — явный результат. CountScope и StockCount проверяют полноту,
партии, дубликаты измерений и допустимость результатов.

Approve в одной UoW создает StockAdjustment с ссылкой на Count, проводит
расхождения через тот же StockPostingService, переводит Count в APPROVED
и снимает freeze. Только эта операция может провести собственные расхождения
в замороженной области. UNIQUE Count → Adjustment и статус защищают повтор.
Если расхождение нарушает активные резервы, approve отклоняется; результат
подсчета сохраняется, резервы разрешаются отдельными операциями.
Cancel снимает freeze и сохраняет историю сеанса. Сбой approve не оставляет
частично примененных расхождений и не снимает freeze.

Учет без заморозки с reconciliation по журналу после snapshot — следующий этап.
MVP не сравнивает старый снимок с новым балансом как будто между ними не было
движений. Мягкие резервы во время freeze допустимы только по явно согласованной
политике; **предложение — запрещать новые/увеличенные резервы, разрешать release
и cancel**, чтобы можно было разрешить дефицит до approve.

## 11. Хранение и интеграция с платформой

Планируемые tenant-local таблицы:

- Warehousing: `warehousing_warehouses`, `warehousing_zones`,
  `warehousing_storage_locations`.
- Inventory: `inventory_items`, `inventory_lots`, `inventory_reservations`,
  таблицы документов и их строк по каждому виду, `inventory_stock_counts`,
  `inventory_stock_count_lines`, `inventory_stock_transactions`,
  `inventory_stock_ledger_entries`, `inventory_stock_balances`,
  `inventory_stock_scopes`, записи идемпотентности и freeze областей.

Имена с префиксом отделяют новую модель от исторических `skus`/`warehouses`.
Окончательные названия и decomposition технических таблиц уточняются при
проектировании migration; границы агрегатов не выводятся из списка таблиц.

Ограничения и индексы:

1. Уникальные code Item/Warehouse, адрес внутри Warehouse, код Zone внутри
   Warehouse, номер Lot внутри Item и ключи идемпотентности.
2. Уникальное нормализованное измерение баланса. Nullable Lot не допускает
   дубликатов: явный NULLS NOT DISTINCT либо отдельные partial unique indexes.
   Для физического и транзитного scope — свои согласованные CHECK/unique keys.
3. FK строк на владельца-документ/транзакцию; принадлежность Lot своему Item
   и Location своему Warehouse подкрепляется составными ограничениями там,
   где это возможно. SQL не заменяет проверки Domain.
4. CHECK quantity >= 0 для баланса; reserved/consumed/released >= 0 и
   consumed + released <= reserved; signed delta != 0; корректный scope kind.
5. Индексы balance Item + Warehouse + Owner, Location, Lot + expiry,
   активных reservation по области, движений по дате/ID/документу,
   непогашенного транзита и активных freezes.
6. Optimistic revision для документов и метаданных; для количеств используется
   протокол блокировок. UPDATE/DELETE проведенного журнала ограничены адаптером
   и правами хранения; способ DB-защиты append-only уточняется в migration.

Миграции вводятся новыми ревизиями после фактического head, не изменением
`0001_warehouses`, `0011_inventory_skus` или удаляющей ревизии. Они не импортируют
текущие ORM-модели, не делают commit и не содержат фиксированных tenant schemas.
Исторические имена сохраняются в регистрации. Новые SQL-модели регистрируются
в `src/modules/tenant_persistence.py`, routers — в `src/modules/router.py`.
У двух tenant одна и та же ссылка UUID не дает доступа к чужой схеме.

Существующие `test_module_registration.py` и `test_architecture_boundaries.py`
сейчас требуют отсутствия Inventory. При вводе модуля эти ожидания заменяются
проверками новой регистрации и разрешенных границ, сохраняя запреты на старые
пути. Тесты удаления исторической модели и migration ownership остаются.

События StockChanged и ReservationChanged передают tenant, затронутый Item,
Warehouse/Owner, transaction/reservation ID, message_id и согласованную версию.
Они сигнализируют об изменении; потребитель при необходимости перечитывает
проекцию. Их доставка не обеспечивает инвариант остатков: он защищен синхронно.
Заказы/Channels используют публичные порты и события. Прямое редактирование
StockBalance из импортера или Console исключено.

HTTP ошибки: 404 для неизвестных объектов; 409 для недостатка/конфликта
проведения/ревизии/идемпотентности; 422 для некорректного контракта; 403 для
недостаточных прав. Стабильные error codes различают причины. Authentication,
CSRF для изменений и authorization — существующие зависимости Identity.

## 12. Этапы реализации и критерии готовности

Этапы выполняются вертикальными срезами: Domain → Application/ports →
Infrastructure/migration → Presentation/Depends → проверки → документация.
Console включается после готовности HTTP-контрактов соответствующего среза.

| Этап | Состав работ | Условие завершения |
| --- | --- | --- |
| 0. Контракты и решения | Связь Catalog/Item, owner, режимы учета, locks, transit, count policy; DTO/HTTP с фиксированной piece и целым Decimal | Закрыты блокирующие решения этапа 1; зафиксирован один владелец каждого поля и границы MVP |
| 1. Warehousing | Warehouse/Zone/Location, фабрики, структура, LocationPolicy без расчета/контроля вместимости, репозитории, queries, миграции, API | Адреса и статусы корректны, циклы/дубликаты/чужие склады отклоняются; capacity опциональна и выключена; snapshot contract готов |
| 2. Item и Lot | Учетная политика с piece/allow_fractional=False, код, опциональные габариты/масса, партии, связь с Catalog через ports | NONE/LOT работают, общий Item для Variant; выбор UOM отсутствует, целые количества и политика защищены; характеристики не обязательны для приемки |
| 3. Ядро проведения | Transaction/Ledger, Balance, locks/idempotency, PostingPolicy/Service, Outbox, receipt, move, status, queries | Журнал и баланс атомарны; повторы не дублируются; конкурентные расходы безопасны |
| 4. Резервы и расход | AvailabilityPolicy, reserve/increase/release/cancel, IssueStock, write-off, adjustment, compensation, проверки влияния Warehousing | Последний SKU нельзя зарезервировать дважды; расход не нарушает чужие резервы; rollback полный |
| 5. Transfer | Документ, учет транзита, dispatch, partial receive, отмена черновика | Ничего не теряется в пути; нельзя принять больше отправленного или дважды принять одну операцию |
| 6. StockCount | Freeze, snapshot, submit, approve через adjustment, cancel | Расхождения применяются один раз; новые измерения защищены; freeze переживает сбой и снимается корректно |
| 7. Console и смежные модули | Структура склада, Items/Lots, баланс/доступность/журнал, документы/резервы/count, разрешенные действия и причины отказа | Основные сценарии проверены через API и UI; отсутствует прямой ввод текущего остатка |
| 8. Приемка и эксплуатация | Tenant upgrades, нагрузка/конкурентность, журнал→баланс reconciliation, метрики, документация | Все обязательные проверки ниже пройдены; нет известных архитектурных нарушений |

Проверки влияния Inventory на деактивацию Warehousing завершаются на этапе 4;
до этого эксплуатационное изменение структуры с запасом не объявляется готовым.
Регистрация Item может развиваться с fake Catalog port до реализации Catalog,
но приемка реальной привязки Variant требует обоих Application-контрактов.

Вне MVP: SERIAL/LOT_AND_SERIAL, отрицательные остатки, жесткая аллокация,
отдельный picking/packing lifecycle, справочник единиц, другие UOM, дробный учет,
упаковки и конвертация, расчет занятого объема/массы и контроль вместимости,
ответственное хранение, себестоимость/финансовая оценка, offline операции
и незамороженный count. При расширении единиц/упаковок выполняется раздел 4.1;
при включении вместимости — правила раздела 3.1.
Эти ограничения не уменьшают обязательные проверки точности первого релиза.

## 13. План проверок реализации

### Domain и архитектура

- Фабрики create/restore всех корней и Entity, разрешенные переходы, запрет
  редактирования проведенного, отсутствие событий создания при restore.
- Инварианты Item/Lot, Decimal/UOM, reserve/release/consume, строки документов,
  сохранение количества в move/transfer/status, неповторяемый count approve.
- Регистрация/restore Item с `base_uom="piece"`, `allow_fractional=False`,
  запрет дробных количеств и скрытого округления, сохранение NUMERIC(24,6),
  запрет обычной смены единицы после первого движения.
- Чистые LocationPolicy, PostingPolicy и AvailabilityPolicy на снимках,
  дата годности и часовой пояс; отсутствие габаритов/массы не блокирует приемку
  MVP и не трактуется как нулевой объем или масса.
- AST/import checks направлений слоев, чужих моделей, session/ORM в контрактах,
  __post_init__ только VO, аннотаций всех методов, прямых записей состояния,
  commit/rollback в handlers/repositories, пустых __init__, docstrings.
- Сверка каждой строки реестра с command/query, handler, своим DTO/None,
  портами/адаптерами и отдельными controller/request/response/Depends.

### PostgreSQL, транзакции и конкурентность

- Два параллельных reserve на последний SKU: успешен один, общий active reserve
  не превышает допустимый запас; то же при изначально отсутствующей scope row.
- Reserve против issue/write-off/status/lot block и деактивации адреса;
  две выдачи последнего количества; receipt против изменения политики Item.
- Перекрестные transfers/moves и иерархические изменения: отсутствие циклов,
  единый порядок locks, ограниченный retry после deadlock.
- Два одинаковых idempotency key, разные payload, повтор документа с другим
  ключом, повтор частичной приемки, повтор approve и compensation.
- Внедренный сбой после записи документа/ledger/balance/reserve/Outbox и ошибка
  commit: ни частичного результата, ни успешного HTTP-ответа.
- Два tenant, одинаковые коды/UUID, запрет чужих ссылок и корректные FK/unique;
  полная миграция нового tenant и upgrade tenant после удаления прежней модели.
- Count freeze, новые измерения, явный ноль/неподсчитанная строка, обнаруженная
  партия, cancel, нулевые расхождения, конфликт резерва на approve.
- Сверка SUM(ledger delta) по нормализованному измерению с StockBalance.
  Repair/rebuild — отдельная служебная операция под блокировками, не HTTP PATCH.

### HTTP, Console и эксплуатация

- Независимые Request/Response/OpenAPI каждого метода, различие отсутствующего
  поля и null, корректные 201/200/204, Decimal сериализация без float.
- В Request регистрации/обновления политики нет выбора `base_uom` и
  `allow_fractional`; их передача отклоняется. Количественные Response содержат
  `base_uom="piece"`; UI не предлагает другие единицы и упаковки.
- Дробное количество отклоняется с 422; приемка без габаритов/массы успешна
  при выполнении остальных правил. Capacity отсутствует/null, а попытка
  включить контроль вместимости в MVP отклоняется.
- Доверенный tenant/actor, authentication/authorization/CSRF, стабильные ошибки;
  статус документа и доступные действия соответствуют доменной модели.
- Пагинация и фильтры, отдельный транзит, общий баланс повторно используемого Item,
  признаки дефицита и дата расчета доступности.
- UI: приемка → резерв → расход; перенос; карантин; transfer с частичной
  приемкой; count с расхождением; повтор запроса после потери ответа.
- Метрики длительности locks, конфликтов/бизнес-отказов, retry, расхождений
  ledger/balance и задержки Outbox; `committed` только после commit.

### Проверки будущего расширения после MVP

- Новые единицы для новых SKU не меняют смысл существующих остатков и журнала;
  смена единицы Item с движениями выполняется только управляемой миграцией.
- Строки документа сохраняют исходное количество/UOM и коэффициент упаковки;
  изменение коэффициента не меняет уже проведенные документы и баланс.
- При включенной вместимости отсутствие необходимых характеристик блокирует
  размещение. Изменение габаритов SKU с остатком проверяет затронутые адреса.
- Разные SKU одновременно заполняют одну ячейку: под блокировкой адреса
  вместимость не превышается. Расчет учитывает все физические статусы запасов,
  не удваивает объем из-за резервов и не включает транзит.

Эти проверки не являются условиями приемки MVP и выполняются вместе
с реализацией соответствующего расширения.

Базовые команды репозитория:

```sh
uv run python -m unittest discover -s test -p 'test_*.py' -v
uv run black --check src test migrations
git diff --check
```

Новые тесты `test_warehousing_architecture.py`, `test_inventory_architecture.py`
и PostgreSQL concurrency suites входят в общий unittest discovery. Интеграционные
тесты запускаются с `TEST_POSTGRES_URL` на одноразовой БД; отсутствие переменной
и пропуски отмечаются ограничением, а не доказательством готовности.
Отдельный type checker не настроен в текущем `pyproject.toml`: выбранный инструмент
и его конфигурация добавляются в этапе реализации, если требуется проверка типов.

Перед завершением каждого среза проверяется весь его diff по разделу 2,
матрица обязательных файлов и соответствующие функциональные/статические проверки.
Успешные тесты поведения не заменяют архитектурный review.

## 14. Решения, которые нужно закрыть до соответствующего этапа

| Решение | Зафиксированное правило или предложение | Срок |
| --- | --- | --- |
| Имя связи Catalog и повторение Item | Item ID как SKU, many Variant → one Item; локальное ограничение внутри Product обсуждается отдельно | До контрактов Catalog/Item |
| Организация-владелец | Явный owner_id и Application-порт; не подменять Tenant ID | Этап 0 |
| UOM и точность MVP — зафиксировано | Только piece, allow_fractional=False; целые значения в Decimal/NUMERIC(24,6), без выбора единицы и округления | Реализовать на этапе 2 |
| Габариты и масса MVP — зафиксировано | Опциональны, принадлежат Inventory; отсутствие не блокирует приемку и не заменяется нулем | Реализовать на этапе 2 |
| Другие единицы и упаковки | Справочник и новые UOM для новых SKU; фиксация исходных количеств/единиц/коэффициентов без переосмысления истории | После MVP, до реализации расширения |
| LOT и сроки годности | NONE/LOT, однозначная граница expiry в зоне склада, защищенные даты после движения | До этапа 2 |
| Политика деактивации | Отклонять несовместимые изменения действующих правил хранения; синхронная проверка влияния запасов/резервов | До приемки этапа 4 |
| Вместимость MVP — зафиксировано | Опциональна, контроль выключен; расчет занятого объема/массы и контроль лимитов отложены | После MVP, до включения контроля |
| Полный протокол locks и retries | Общие lifecycle gates + scope rows + locks документов/адресов, стабильный порядок | До этапа 3 |
| StockScope транзита | Отдельная IN_TRANSIT область с transfer/line ID, не физическая ячейка | До этапа 5 |
| Частичная отправка/приемка и потери | Явные количества по строкам; потери/возвраты отдельными документами | До этапа 5 |
| Count policy | Заморозка движений и новых резервов, release/cancel разрешены, ноль задается явно | До этапа 6 |
| Основания, права, backdating и компенсация | Отдельные permissions и reason codes, occurred_at не заменяет recorded_at; зависимые документы проверяются | До API проведения |
| Заказы и Channels | Публичные Application-порты/события; внешнее наличие не перезаписывает баланс без документа | До смежных интеграций |

Этот документ фиксирует план, архитектурные ограничения и критерии приемки.
Наличие плана не означает, что модули, новые миграции или складские операции
уже реализованы и проверены.
