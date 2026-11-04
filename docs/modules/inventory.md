# Inventory: Domain-модель товара, складов, плановых документов и физического журнала

Модуль `inventory` содержит самостоятельные корни `InventoryItem`,
`PackagingType`, `StockLot`, `StockSerial`, `Warehouse`, `StockLocation`, `StockPosition`,
`StockPosting`, `StockDocument`, `StockExecution`, `AvailabilityPool` и `StockReservation`
в `domain/inventory_item/`, `domain/packaging_type/`, `domain/stock_lot/`,
`domain/stock_serial/`, `domain/warehouse/`, `domain/stock_location/`, `domain/stock_position/`,
`domain/stock_posting/`, `domain/stock_document/`, `domain/stock_execution/`,
`domain/availability_pool/` и `domain/stock_reservation/`.
Общие значения названий, кодов тары и единиц находятся в `domain/value_object/`.

Нормативные требования: [архитектура backend](../architecture/backend.md).
Целевой состав системы: [план Inventory](../plan/inventory.md).

## Учётный вариант товара

`InventoryItem` описывает конкретную учётную позицию. Например, банка масла
объёмом 1 л может учитываться в `PCS`, а наливное масло — в `L`.
Объём содержимого готовой банки является характеристикой варианта товара.
Он не определяет единицу складского учёта автоматически.

| Поле | Назначение |
| --- | --- |
| `id` | Постоянный `InventoryItemIdVO` |
| `sku` | Обязательный ручной `SkuVO` |
| `base_uom` | Базовая единица учёта `UomCodeVO` |
| `quantity_rules` | Обязательный `QuantityRulesVO`: шаг количества в базовой единице |
| `tracking_mode` | `NONE`, `LOT`, `SERIAL`, `LOT_AND_SERIAL` |
| `expiration_mode` | `NONE`, `OPTIONAL`, `REQUIRED` |
| `barcodes` | Неизменяемый tuple идентификаторов товара `ItemBarcode` |
| `packagings` | Неизменяемый tuple вариантов упаковки `ItemPackaging` |

Упаковки и штрихкоды необязательны. `create` по умолчанию создаёт пустые
коллекции, `tracking_mode=NONE`, `expiration_mode=NONE`.
`quantity_rules` передаётся явно в `create` и `restore`; Domain не выбирает
правила автоматически по единице или размерности.
Обязательной базовой упаковки и `base_packaging_id` нет. Вариант с содержимым
`1` пользователь может создать и удалить на общих основаниях.

Партии, серийные экземпляры, остатки, резервы и движения находятся за пределами
этого агрегата. Фактические даты годности здесь не хранятся.

## Значения и уникальность

Строковые VO убирают пробелы по краям и запрещают пустые значения,
управляющие и форматирующие символы Unicode. `SkuVO` применяет `casefold`:
`ABC` и `abc` равны и хранятся как `abc`. Длина после нормализации — от 1 до 25
символов. SKU вводится вручную и заменяется через `change_sku` без изменения ID.

Штрихкод сохраняет ведущие нули и регистр. Коды единиц и варианты кодов тары
сравниваются точно после trim. Контракт Catalog SKU не импортируется.

Внутри tenant-схемы SKU должен быть уникален среди InventoryItem,
а один штрихкод принадлежит только одному InventoryItem. В разных tenant
одинаковые значения допустимы. Атомарные ограничения БД и обработка конкурентных
конфликтов относятся к будущему срезу хранения. Сейчас Domain обеспечивает
каноническое сравнение SKU и отсутствие повторов штрихкодов внутри позиции.

## Штрихкод идентифицирует только товар

`ItemBarcode` содержит только `id: ItemBarcodeIdVO` и `barcode: BarcodeVO`.
Принадлежность товару определяется включением Entity в агрегат InventoryItem.
Ссылок на упаковку, количество и единицу измерения у штрихкода нет.

`add_barcode`, `change_barcode` и `remove_barcode` проверяют собственные значения,
уникальность ID и кодов внутри позиции. Добавление, изменение и удаление упаковок
не меняет штрихкоды и не требует их переназначения.

Поиск товара по штрихкоду относится к будущему Query-сценарию. Domain-метода
`resolve_barcode`, возвращающего упаковку, нет. Сканирование само по себе
не задаёт количество операции: количество, единица или выбранная упаковка
указываются отдельно в будущей строке складской операции.

## Тип тары и вариант упаковки

`PackagingType` описывает пользовательский форм-фактор: ящик, мешок, канистру
или палету. Поля: `id`, `code`, `name`, `is_active`.
Тип тары не ограничивает единицы учёта через `allowed_uoms`.
Он может применяться к товарам, учитываемым в штуках, массе или объёме.

Фабрики `create/restore` проверяют собственные значения. Методы `rename`,
`change_code`, `activate`, `deactivate` возвращают новый экземпляр с прежним ID.
При назначении нового варианта InventoryItem получает `PackagingTypeSnapshot`
и проверяет его корректность, активность и соответствие `packaging_type_id`.
Чужой корень агрегата и репозиторий в Domain не передаются.
Существующие назначения восстанавливаются без требования актуальной активности типа.

`ItemPackaging` — дочерняя Entity товара:

| Поле | Назначение |
| --- | --- |
| `id` | Идентификатор варианта упаковки |
| `packaging_type_id` | Ссылка на форм-фактор тары |
| `code` | Уникальный код варианта внутри товара |
| `name` | Пользовательское название |
| `content_quantity` | Конечный положительный Decimal в `PackagingQuantityVO` |
| `content_uom` | Явная единица содержимого `UomCodeVO` |

Например, товар «Масло, банка 1 л» с базовой единицей `PCS` может иметь вариант
«Ящик» с содержимым `12 PCS`. Для наливного масла с базовой единицей `L`
вариант «Канистра» может содержать `5 L`, а «Бутылка» — `500 ML`.
Миллилитры доступны для литрового товара автоматически из системного справочника;
пользователь не вводит множитель `ML → L`.

## Системные единицы и точный пересчёт

Индивидуального поля `uom_conversions`, Entity ItemUomConversion и настроек
коэффициентов у товара нет. `base_uom` должен ссылаться на известную единицу
общего неизменяемого Domain-справочника `uom_catalog.py`.
Коды точные и регистрозависимые: `KG` допустим, `kg` не является кодом справочника.
`UomCodeVO` проверяет строковое значение, а справочник и агрегат — наличие кода.

| Размерность | Опорная единица | Доступные коды |
| --- | --- | --- |
| Количество | `PCS` | `PCS` |
| Масса | `KG` | `UG`, `MG`, `G`, `KG`, `CENTNER`, `T` |
| Объём | `L` | `ML`, `L`, `M3` |
| Длина | `M` | `UM`, `MM`, `CM`, `DM`, `M`, `KM` |
| Площадь | `M2` | `MM2`, `CM2`, `DM2`, `M2`, `HA`, `KM2` |

`UG` — микрограмм, `UM` — микрометр (микрон), `CENTNER` — метрический центнер,
равный 100 кг. У каждого `UomDefinitionVO` есть код, `UomDimension` и конечный
положительный Decimal-масштаб относительно опорной единицы своей размерности.
Все определения общие для товаров и tenant; SQL-справочник и пользовательские
множители не создаются.

`list_uoms()` возвращает все определения, `get_uom(code)` — одно,
`get_compatible_uoms(code)` — все единицы той же размерности.
Свойство `InventoryItem.available_uoms` вычисляется по базовой единице:
выбор KG автоматически даёт доступ ко всей группе массы.

Чистая `UomConversionPolicy.convert` получает `QuantityVO`, исходную и целевую
единицы. Формула: `quantity * source.factor_to_reference / target.factor_to_reference`.
Метод `InventoryItem.to_base_quantity(quantity=..., uom=...)` использует ту же
Policy, затем проверяет результат через `QuantityValidationPolicy` и возвращает
допустимый QuantityVO в базовой единице товара, не меняя агрегат.

`QuantityVO` принимает только конечный неотрицательный Decimal, включая ноль.
Факторы и количества не превращаются в float. Пересчёт выполняется в собственном
Decimal Context с достаточной точностью для системных масштабов; внешний context
не влияет на результат. Потеря точности или переполнение даёт доменную ошибку,
без тихого округления и без Infinity. Сначала рассчитывается отношение масштабов,
чтобы избежать лишнего промежуточного переполнения.

Примеры: `2500 G → 2.5 KG`, `1500 ML → 1.5 L`, `350 CM → 3.5 M`,
`50000 CM2 → 5 M2`. Между размерностями пересчёт запрещён: масса в объём требует
плотности, длина в площадь — ширины и отдельного бизнес-правила.

## Количество и его изменение

Общие значения Domain разделяют физическое количество, его изменение и правила учёта:

| VO | Назначение и собственные ограничения |
| --- | --- |
| `QuantityVO` | Конечный неотрицательный Decimal, включая ноль |
| `StockDeltaVO` | Конечный Decimal с любым знаком, включая ноль |
| `QuantityRulesVO` | Конечный положительный Decimal-шаг количества |

`StockDeltaVO` находится в `domain/value_object/stock_delta.py` и описывает
увеличение или уменьшение количества. Примеры: `StockDeltaVO(Decimal("5"))`,
`StockDeltaVO(Decimal("-5"))`, `StockDeltaVO(Decimal("0"))`.
Он сохраняет исходный Decimal без округления, включая знак нуля и конечные нули.
Сырые int, float, bool и строки не преобразуются; NaN, sNaN и обе бесконечности
отклоняются с `InvalidStockDeltaError`. VO неизменяем и не зависит от внешнего
Decimal context.

Кратность шагу и результирующий остаток проверяют QuantityValidationPolicy
и StockQuantityPolicy. StockLedgerEntry запрещает нулевую дельту журнала,
сохраняя допустимость нуля в общем StockDeltaVO и StockPosition.apply_delta().
UomConversionPolicy принимает неотрицательную величину QuantityVO; знак движения
сохраняется отдельно в quantity_delta записи.

## Шаг количества

Неизменяемый `QuantityRulesVO` содержит только `step: Decimal` — конечный
положительный шаг количества от нуля. Некорректный шаг вызывает
`InvalidQuantityRulesError`; float, bool, ноль, отрицательные и нечисловые
значения не принимаются.

Допустимое количество равно `n * step`, где n — целое неотрицательное число.
Шаг полностью определяет допустимую дробность. Конечные нули не влияют на
значение: шаги `1.000` и `1` эквивалентны. Микрограммы в килограммах можно
учитывать с `step=0.000000001` без дополнительной настройки.

| Пример товара | Базовая единица | Шаг |
| --- | --- | --- |
| Банки | `PCS` | `1` |
| Наливное масло | `L` | `0.001` |
| Гречка | `KG` | `0.001` |
| Обои | `M2` | `0.01` |
| Провод | `M` | `0.1` |

Это примеры явно задаваемых настроек, а не обязательные значения для размерностей.

```python
from decimal import Decimal

from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO

rules = QuantityRulesVO(step=Decimal("0.05"))
# Передаётся как quantity_rules=rules в InventoryItem.create/restore.
```

Чистая `QuantityValidationPolicy.validate(quantity=..., rules=...) -> None`
получает QuantityVO уже в базовой единице и проверяет точную кратность шагу.
Для шага `0.05` количество `1.2500` принимается, `1.23` и `1.251`
вызывают `QuantityStepError`.
Проверка точная и не зависит от внешнего Decimal context; округления нет.

При базовой единице KG и шаге `0.001` значения `1250 G → 1.25 KG`
и `1 G → 0.001 KG` принимаются, а `1 MG → 0.000001 KG` отклоняется.
Число знаков исходного количества
не ограничивается, если результат в базовой единице удовлетворяет правилам.

Общий QuantityVO и UomConversionPolicy не знают правил конкретного товара.
QuantityVO по-прежнему допускает любое конечное неотрицательное Decimal,
включая дробные штуки; запрет дробных штук задаётся правилами InventoryItem.
Ноль допустим для общего количества и правил; положительность будущих строк
операций будет отдельным инвариантом документа. Содержимое упаковки всегда положительно.

## Прослеживаемость, единицы и количество

| TrackingMode | Базовая единица | Правила количества | ExpirationMode |
| --- | --- | --- | --- |
| `NONE` | Любая известная системная единица | Явно заданный корректный QuantityRulesVO | `NONE`, `OPTIONAL` |
| `LOT` | Любая известная системная единица | Явно заданный корректный QuantityRulesVO | `NONE`, `OPTIONAL`, `REQUIRED` |
| `SERIAL` | Только `PCS` | Только `step=1` | `NONE`, `OPTIONAL`, `REQUIRED` |
| `LOT_AND_SERIAL` | Только `PCS` | Только `step=1` | `NONE`, `OPTIONAL`, `REQUIRED` |

`TrackingMode.requires_serial` истинно для SERIAL и LOT_AND_SERIAL. Для этих
режимов InventoryItem проверяет базовую единицу PCS и шаг 1.
Нарушение даёт `InvalidTrackingConfigurationError`, без assert и без автоматической
подмены входных настроек. Проверка выполняется в общей валидации агрегата:
при создании, восстановлении и через методы изменения. Даже целочисленный шаг 2
для серийного учёта запрещён. Численно равный шаг `1.000` допустим:
конечные нули Decimal не меняют его значения.

Серийный товар допускает количества `0`, `1`, `12.000`, но не `0.5` или `1.001`.
Это правило целого количества экземпляров. StockSerial задаёт идентичность
одного экземпляра; соответствие количества серийным ID будет проверяться
в будущих складских операциях.
Упаковка на `12 PCS` разрешена, на `0.5 PCS` — нет. Для нулевого содержимого
упаковки сохраняется общий запрет.

NONE и LOT не накладывают дополнительных ограничений на единицу и шаг:
допустимы масса, объём, длина, площадь и количество. Для PCS целочисленность
в этих режимах задаётся явно через QuantityRulesVO; дробные PCS разрешены,
если выбранные правила их допускают. Неизвестные коды единиц запрещены во всех режимах.

## Инварианты содержимого упаковки

- ID и коды вариантов упаковки уникальны внутри товара.
- Количество содержимого обязательно, положительно и задаётся через Decimal;
  ноль, отрицательные, NaN, бесконечность и неявный float отклоняются.
- Базовая единица товара и единица содержимого известны системному справочнику.
- Размерность содержимого совпадает с размерностью базовой единицы товара.
- После точного пересчёта содержимое кратно шагу товара.
  Проверка выполняется при добавлении, изменении и восстановлении агрегата.
- `500 ML` разрешены для товара с базовой единицей L и шагом `0.001`
  без настройки конвертации. При шаге `1` такая упаковка отклоняется.
- Упаковку можно удалить независимо от наличия штрихкодов товара.

Количество и единица содержимого задаются пользователем: мешок конкретной гречки
содержит 25 KG, канистра масла — 5 L. Эти значения относятся к ItemPackaging,
а системные отношения KG/G и L/ML общие и пользователем не задаются.

## Режимы годности

| Режим | Поведение |
| --- | --- |
| `NONE` | Работа с датами годности выключена |
| `OPTIONAL` | Необязательная дата-заметка; как NONE, без влияния на доступность, резервы, отгрузку, FEFO и автоматические действия |
| `REQUIRED` | Дата обязательна до проведения поступления; контроль срока включен |

`controls_expiration` истинно только у `REQUIRED`. `NONE` и `OPTIONAL`
совместимы с любым TrackingMode; `REQUIRED` требует `LOT`, `SERIAL`
или `LOT_AND_SERIAL`. Учёт партии сам по себе не включает контроль срока.
Фактические даты партии находятся в StockLot. В текущем срезе
StockExpirationPolicy проверяет допустимость заполнения и обязательность даты.
StockAvailabilityPolicy рассчитывает пригодность физического остатка по явно
переданной календарной дате. Правила приёмки просроченного товара и FEFO
остаются последующими складскими сценариями.

## Партия товара

`StockLot` — самостоятельный Aggregate Root без дочерних Entity.
InventoryItem не владеет коллекцией партий. Партия содержит:

| Поле | Назначение |
| --- | --- |
| `id` | Постоянный `StockLotIdVO` |
| `inventory_item_id` | Принадлежность конкретному InventoryItem |
| `number` | Обязательный `LotNumberVO` — номер производителя или вручную заданный номер |
| `dates` | `StockDatesVO` — календарные даты партии |

Количество, склад, локация, владелец и состояние запасов принадлежат будущему
StockPosition. Одна партия может находиться в нескольких учётных позициях.

`LotNumberVO` применяет trim, запрещает пустые значения и управляющие/форматирующие
символы Unicode, сохраняет регистр и ведущие нули. `000Lot-a` и `000LOT-A` —
разные номера. Номер должен быть уникален в рамках InventoryItem одной tenant-схемы.
Атомарная уникальность пары `(inventory_item_id, number)` относится к будущему
SQL-срезу; текущий Domain не проверяет другие партии.

Общий `StockDatesVO` находится в `domain/value_object/stock_dates.py` и содержит
`manufactured_on: date | None` и `expires_on: date | None`.
Обе даты необязательны; `StockDatesVO()` представляет отсутствие дат.
Для REQUIRED такая карточка пока не готова к поступлению.
Принимается только календарный date: datetime, строки и неявные преобразования
запрещены. Если обе даты заданы, производство не может быть позже окончания
срока годности; равные даты допустимы. Исторические и будущие даты разрешены.
Структурная корректность дат проверяется и для OPTIONAL, без оценки просрочки.
Нарушение типа или порядка дат вызывает общий `InvalidStockDatesError`.

`InventoryItem.tracking_snapshot()` возвращает неизменяемый
`InventoryItemTrackingSnapshot` с `inventory_item_id`, `tracking_mode` и
`expiration_mode`. Снимок не содержит коллекций или ссылки на корень товара.
Потребитель проверяет тип снимка и его полей. Актуальный снимок для команды
в дальнейшем будет передавать Application; Domain самостоятельно его не загружает.

Чистая `StockLotPolicy.ensure_compatible` проверяет соответствие товара и
допускает партию только для LOT и LOT_AND_SERIAL. NONE и SERIAL отклоняются
с `LotTrackingNotAllowedError`, чужой товар — с `StockLotItemMismatchError`.

Поведение фабрик и методов StockLot:

- `create(identifier=..., inventory_item=..., number=..., dates=...)` выводит
  принадлежность товару из снимка, проверяет партийный учёт и допустимость дат.
  В NONE запрещён заполненный `expires_on`; дата производства допустима.
  OPTIONAL допускает необязательную дату-заметку, REQUIRED — неполную карточку.
- `restore(identifier=..., inventory_item_id=..., number=..., dates=...)`
  восстанавливает собственные значения без текущего снимка товара и сохраняет ID
  и исторические даты. Текущие межагрегатные ограничения проверяются при использовании.
- `change_dates(dates, inventory_item=...)` проверяет собственные значения,
  принадлежность и текущие настройки, возвращает новый экземпляр с прежними
  ID и номером. Ошибка сохраняет исходную партию неизменной.
- `ensure_ready_for_receipt(inventory_item=...) -> None` проверяет текущую
  совместимость и полноту срока через StockExpirationPolicy. Для REQUIRED
  отсутствие `expires_on` даёт `ExpirationDateRequiredError`.

`StockExpirationPolicy.ensure_dates_allowed` проверяет допустимость заполнения;
`ensure_ready_for_receipt` дополнительно требует дату только для REQUIRED.
NONE со сроком даёт `ExpirationDateNotAllowedError`. OPTIONAL с прошедшей
датой-заметкой проходит проверку. Проверка полноты не определяет допустимость
приёмки просрочки, в том числе для REQUIRED, и не заменяет будущих правил проведения.
В текущем срезе документ и проведение поступления ещё не реализованы.

Например, для уже созданного InventoryItem с LOT и REQUIRED:

```python
from datetime import date
from uuid import uuid4

from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO

snapshot = item.tracking_snapshot()
lot = StockLot.create(
    identifier=StockLotIdVO(uuid4()),
    inventory_item=snapshot,
    number=LotNumberVO("000LOT-a"),
    dates=StockDatesVO(),
)
# Проверка готовности lot сейчас дала бы ExpirationDateRequiredError.
completed = lot.change_dates(
    StockDatesVO(manufactured_on=date(2026, 1, 1), expires_on=date(2028, 1, 1)),
    inventory_item=snapshot,
)
completed.ensure_ready_for_receipt(inventory_item=snapshot)
# Исходный lot остаётся без дат; ID и номер completed совпадают с lot.
```

`StockLot.snapshot()` возвращает неизменяемый `StockLotSnapshot` с `id`,
`inventory_item_id` и `dates`. Он используется для проверки серийного экземпляра
без передачи другого Aggregate Root.

Изменение номера и контролируемые исправления дат после проведённых операций
с сохранением истории относятся к последующим срезам. Проверка факта использования
партии в текущий `change_dates` не входит: движения ещё не реализованы.

## Серийный экземпляр товара

`StockSerial` — самостоятельный Aggregate Root, идентифицирующий один физический
экземпляр. У него нет дочерних Entity, количества, остатков и текущей локации.
InventoryItem и StockLot не владеют коллекциями серийных экземпляров.

| Поле | Назначение |
| --- | --- |
| `id` | Постоянный `StockSerialIdVO` |
| `inventory_item_id` | Принадлежность конкретному товару |
| `number` | Обязательный `SerialNumberVO` |
| `lot_id` | `StockLotIdVO` для экземпляра партии либо None |
| `dates` | Собственный `StockDatesVO` для самостоятельного экземпляра либо None |

SerialNumberVO применяет trim, запрещает пустоту и управляющие/форматирующие
символы Unicode, сохраняет регистр и ведущие нули. `000SN-a` и `000SN-A` — разные
номера. Уникальность `(inventory_item_id, number)` в tenant-схеме не зависит от
склада и относится к будущему атомарному ограничению БД. Domain не проверяет
другие экземпляры. Серийный номер не является ItemBarcode.

| TrackingMode | Создание экземпляра | Партия | Даты |
| --- | --- | --- | --- |
| `NONE`, `LOT` | Запрещено | — | — |
| `SERIAL` | Разрешено | Отсутствует | Собственный StockDatesVO, в том числе пустой |
| `LOT_AND_SERIAL` | Разрешено | Обязательна | Только из снимка партии; собственное поле dates равно None |

Чистая `StockSerialPolicy.resolve_dates` проверяет типы снимков и собственного
состояния, серийный режим, принадлежность товару и возвращает выбранный StockDatesVO.
Для экземпляра партии снимок обязан совпадать с сохранённым lot_id и относиться
к тому же InventoryItem. Передача партии в режиме SERIAL отклоняется.
StockExpirationPolicy проверяет выбранные даты: NONE запрещает срок,
OPTIONAL допускает заметку, REQUIRED требует срок только перед поступлением.

Фабрики и методы:

- `create(identifier=..., inventory_item=..., number=..., dates=..., lot=...)`
  получает InventoryItemTrackingSnapshot и необязательный StockLotSnapshot.
  ID товара и партии выводятся из снимков. Параметр dates обязателен:
  для SERIAL передаётся StockDatesVO, для LOT_AND_SERIAL — None.
  Пустой срок REQUIRED разрешён при создании обоих вариантов.
- `restore(identifier=..., inventory_item_id=..., number=..., lot_id=..., dates=...)`
  проверяет собственные типы и наличие ровно одного источника: либо собственных дат,
  либо ссылки на партию. Снимки при восстановлении не требуются; ID сохраняются.
- `change_dates(dates, inventory_item=...)` доступен только самостоятельному SERIAL.
  Возвращает новый экземпляр с прежними ID и номером; отказ сохраняет исходный.
  Даты LOT_AND_SERIAL изменяются через StockLot.
- `ensure_ready_for_receipt(inventory_item=..., lot=...) -> None` проверяет
  текущую совместимость и полноту даты. Для LOT_AND_SERIAL снимок партии обязателен
  при каждом вызове; отсутствие или некорректный снимок отклоняется.

Источник дат не копируется из партии в экземпляр. Новый снимок партии отражает
её текущие даты; старые снимки неизменяемы. Application должен передавать
актуальные снимки; Domain самостоятельно данные не загружает.
Проверка готовности по-прежнему не определяет допустимость приёмки просрочки.

Например, для товара `item` с LOT_AND_SERIAL и уже созданной партии `lot`:

```python
from uuid import uuid4

from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.value_object.identifier import StockSerialIdVO
from src.modules.inventory.domain.stock_serial.value_object.serial_number import SerialNumberVO

serial = StockSerial.create(
    identifier=StockSerialIdVO(uuid4()),
    inventory_item=item.tracking_snapshot(),
    number=SerialNumberVO("000SN-a"),
    lot=lot.snapshot(),
    dates=None,
)
serial.ensure_ready_for_receipt(
    inventory_item=item.tracking_snapshot(),
    lot=lot.snapshot(),
)
# Для REQUIRED дата должна быть заполнена в lot.
```

Номер и принадлежность партии неизменяемы в текущем срезе. Исправления после
проведения, проверка использования, соответствие серийных ID количеству операции
и защита от одновременного учёта одного экземпляра в разных позициях относятся
к последующим складским сценариям. SQL, API и проведение движений не реализуются.

## Карточка склада

`Warehouse` — самостоятельный Aggregate Root без дочерних Entity.
В текущем срезе он описывает идентичность и административную активность склада:

| Поле | Назначение |
| --- | --- |
| `id` | Постоянный `WarehouseIdVO` |
| `code` | Обязательный канонический `WarehouseCodeVO` |
| `name` | Обязательный `WarehouseNameVO` |
| `is_active` | Настоящий bool административной активности |
| `default_storage_location_id` | StockLocationIdVO основной STORAGE либо None |

`WarehouseCodeVO` применяет `trim + casefold`: MAIN и main равны,
каноническое значение — main. Ведущие нули сохраняются. WarehouseNameVO
применяет trim и сохраняет регистр. Оба VO запрещают пустоту, управляющие
и форматирующие символы Unicode. Ошибки: InvalidWarehouseCodeError
и InvalidWarehouseNameError. UUID склада типизирован и не взаимозаменяем
с идентификаторами других агрегатов.

Канонический код должен быть уникален в tenant-схеме. Атомарное ограничение БД
относится к будущему срезу хранения; Domain не проверяет другие склады.

Фабрики и методы:

- `create(identifier=..., code=..., name=...)` создаёт активную карточку без основной локации.
- `restore(identifier=..., code=..., name=..., is_active=..., default_storage_location_id=...)` принимает полное
  состояние и сохраняет идентичность. Сырые значения, VO другого назначения
  и значения активности вроде 0, 1 или строки отклоняются с InvalidWarehouseValueError.
- `rename(name)` и `change_code(code)` возвращают новый экземпляр с прежним ID
  и активностью. Справочные данные можно менять и у неактивного склада.
- `activate()` и `deactivate()` возвращают новый корректный экземпляр.
  Повторные переключения допустимы и дают эквивалентное состояние.
- `ensure_available() -> None` проверяет собственное состояние и активность.
  Неактивный склад отклоняется с WarehouseInactiveError.
- `snapshot()` возвращает WarehouseSnapshot с id, is_active и default_storage_location_id.
- `set_default_storage_location(location)` принимает StockLocationSnapshot активной
  STORAGE того же склада и возвращает новый склад с её ID. Повторное назначение
  допустимо; остальные данные, включая активность, сохраняются. Настройка разрешена
  и для неактивного склада без его автоматической активации.

Деактивация означает административную блокировку. Проверки остатков,
незавершённых документов и физического закрытия склада относятся к будущим
складским сценариям. Исходный экземпляр остаётся неизменным при успехе и отказе.

```python
from uuid import uuid4

from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO

warehouse = Warehouse.create(
    identifier=WarehouseIdVO(uuid4()),
    code=WarehouseCodeVO(" MAIN "),
    name=WarehouseNameVO("Основной склад"),
)
warehouse.ensure_available()
blocked = warehouse.deactivate()
# blocked.ensure_available() вызовет WarehouseInactiveError.
active = blocked.activate()
active.ensure_available()
```

Активность карточки проверяет только административное разрешение.
Готовность к проведению операций дополнительно потребует локаций и их настроек.
Требование автоматического создания основной локации STORAGE сохраняется:
будущий Application-сценарий создаст Warehouse и StockLocation в одной транзакции.
Текущий Warehouse.create создаёт только карточку склада.

WarehouseSettings и проверки готовности конкретных складских операций добавляются
в соответствующих срезах. Коллекции локаций, товаров, остатков и документов
в Warehouse не добавляются. SQL и API в этот срез не входят.

## Локации склада

StockLocation — самостоятельный Aggregate Root без дочерних Entity и остатков.
Он содержит:

| Поле | Назначение |
| --- | --- |
| id | StockLocationIdVO |
| warehouse_id | WarehouseIdVO принадлежности складу |
| parent_location_id | StockLocationIdVO родителя либо None для корневого адреса |
| code | LocationCodeVO: trim + casefold |
| name | LocationNameVO: trim с сохранением регистра |
| location_type | LocationType: STORAGE, RECEIVING, SHIPPING, QUARANTINE, TRANSIT |
| is_active | Настоящий bool локальной активности |

Код и название обязательны и запрещают управляющие/форматирующие символы Unicode.
Канонический код должен быть уникален в сочетании `(warehouse_id, code)` одной
tenant-схемы; одинаковые коды на разных складах допустимы. Атомарная уникальность,
существование склада/родителя и внешние ключи относятся к срезу хранения.

`create(identifier=..., warehouse=..., code=..., name=..., location_type=..., parent=...)`
получает WarehouseSnapshot и необязательный StockLocationSnapshot родителя.
LocationPlacementPolicy требует активный склад, тот же склад родителя и отсутствие
самоссылки. warehouse_id и parent_location_id выводятся из снимков. Новая локация активна.
Назначение локации не изменяет состояние товара автоматически.

`restore` принимает все семь собственных полей, проверяет типы и прямую самоссылку
без снимков и обхода дерева. Склад, родитель и тип после создания неизменяемы.
Переподчинение ветвей и проверка полной цепочки предков — отдельный будущий сценарий.
Текущий Domain не проверяет глобальную целостность произвольно восстановленного дерева.

`rename`, `change_code` и `activate` возвращают новый проверенный экземпляр.
`deactivate(warehouse=...)` принимает WarehouseSnapshot и запрещает деактивацию,
если его default_storage_location_id ссылается на текущий адрес:
выбрасывается DefaultStorageLocationInUseError. Требуется сначала назначить другую
активную STORAGE. Защита действует и для неактивного склада. Для остальных
адресов повторная деактивация идемпотентна.

Активность локальная: переключение родителя не изменяет детей и не блокирует их
посредством наследования. Неактивный родитель допустим как структурная ссылка
при создании ребёнка. `ensure_available(warehouse=...)` через LocationAvailabilityPolicy
требует совпадения склада и двух активных флагов: Warehouse и самой локации.
Это административная проверка; правила отбора, карантина, транзита и размещения
конкретного товара относятся к будущим операциям и ограничениям.

`StockLocation.snapshot()` возвращает StockLocationSnapshot с id, warehouse_id,
location_type и is_active. Новые снимки неизменяемы, имеют явную проверку собственных
типов через ensure_valid; Policy проверяет также тип самого переданного контракта.
Другая принадлежность даёт StockLocationWarehouseMismatchError, самоссылка —
InvalidLocationHierarchyError, неактивный адрес — StockLocationInactiveError.

DefaultStorageLocationPolicy проверяет назначение и защиту основной локации.
STORAGE того же склада должна быть активна на момент назначения; другие типы,
чужой склад и некорректные снимки отклоняются доменными ошибками.
Warehouse.ensure_available сохраняет административную проверку даже при отсутствии
основной локации. Восстановление Warehouse проверяет только тип ссылки и не загружает адрес.

Последовательность подготовки склада в Domain для уже созданного warehouse:

```python
from uuid import uuid4

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import StockLocationIdVO
from src.modules.inventory.domain.stock_location.value_object.location_type import LocationType
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO

storage = StockLocation.create(
    identifier=StockLocationIdVO(uuid4()),
    warehouse=warehouse.snapshot(),
    code=LocationCodeVO("STORAGE"),
    name=LocationNameVO("Основная зона хранения"),
    location_type=LocationType.STORAGE,
)
prepared = warehouse.set_default_storage_location(storage.snapshot())
storage.ensure_available(warehouse=prepared.snapshot())
# storage.deactivate(warehouse=prepared.snapshot()) потребует переназначить основной адрес.
```

Domain не загружает снимки и не определяет, устарели ли они. Будущий Application
должен получать актуальные данные и атомарно согласовывать назначение, переназначение
и деактивацию локаций в tenant-UoW с защитой конкурентных изменений. Только этот
срез обеспечит гарантию при параллельных командах. Автосоздание STORAGE в публичном
сценарии, SQL, API, вместимость, физический адрес и ограничения товаров пока не реализованы.

## Физическая учётная позиция

StockPosition — самостоятельный Aggregate Root без дочерних Entity, резервов
и истории движений. Поля:

| Поле | Назначение |
| --- | --- |
| id | StockPositionIdVO |
| dimensions | Неизменяемый StockDimensionsVO |
| base_uom | Базовая единица UomCodeVO, зафиксированная из снимка товара |
| on_hand_qty | Конечный неотрицательный QuantityVO |
| version | Целая неотрицательная версия, без bool |

StockDimensionsVO содержит inventory_item_id, location_id, явный owner_id,
необязательные lot_id и serial_id, stock_status. Каждая ссылка типизирована.
StockOwnerIdVO — ссылка на контрагента/юрлицо владельца; она не выводится из tenant
или оператора склада. Существование и права владельца проверит будущий внешний сценарий.
Склад определяется через неизменяемую принадлежность локации и не дублируется в ключе.

StockStatus: SELLABLE, QUARANTINE, DAMAGED, BLOCKED. Состояние запаса независимо
от назначения локации и факта истечения даты. Склад, товар, владелец, партия,
серия и состояние не меняются через методы позиции. Перемещение или изменение
состояния потребует уменьшения исходной позиции и увеличения другой.

В tenant-схеме требуется одна позиция на сочетание
`(inventory_item_id, location_id, owner_id, lot_id, serial_id, stock_status)`.
Атомарная уникальность в срезе хранения должна охватывать и сочетания с NULL:
отсутствие партии/серии не разрешает дубликаты. Domain не ищет другие позиции.

Для физических количеств используются новые минимальные контракты:

- `InventoryItem.stock_snapshot()` возвращает InventoryItemStockSnapshot с ID,
  base_uom, quantity_rules и tracking_mode. Геттер проверяет собственный агрегат;
  потребитель проверяет тип снимка, его поля, известную единицу и правила серий.
- `StockSerial.snapshot()` возвращает StockSerialSnapshot с id, inventory_item_id
  и lot_id. Даты и другие Aggregate Roots внутрь него не включаются.
- Существующие снимки Warehouse, StockLocation и StockLot используются повторно.

StockDimensionsPolicy сверяет товар, конкретную локацию и её склад, а также
проверяет матрицу прослеживаемости:

| TrackingMode | LOT | SERIAL |
| --- | --- | --- |
| NONE | Отсутствует | Отсутствует |
| LOT | Обязателен | Отсутствует |
| SERIAL | Отсутствует | Обязателен |
| LOT_AND_SERIAL | Обязателен | Обязателен и принадлежит этой партии |

ID и товар в снимках партии/серии должны совпадать с измерениями. Лишние снимки
и отсутствие обязательных снимков отклоняются; корни агрегатов не передаются.
Для конкретного serial_id разрешены только PCS и остаток 0 или 1.
Проверка единичного положительного остатка серии во всех позициях tenant потребует
StockPosting, ограничений хранения и конкурентной защиты. Локальный агрегат
не подтверждает глобальную уникальность присутствия экземпляра.

Фабрики и переход количества:

- `create(identifier=..., dimensions=..., inventory_item=..., location=..., warehouse=..., lot=..., serial=...)`
  проверяет снимки и создаёт только нулевой остаток версии 0. Базовая единица
  выводится из снимка товара.
- `restore(identifier=..., dimensions=..., base_uom=..., on_hand_qty=..., version=...)`
  восстанавливает полный собственный состав без текущих снимков и I/O.
  Проверяются типы, известная единица, версия и ограничение серии PCS / 0–1.
  Шаг и текущий режим проверяются при последующем использовании со снимками.
- `apply_delta(delta, inventory_item=..., location=..., warehouse=..., lot=..., serial=...)`
  повторно проверяет контекст и совпадение базовой единицы, применяет StockQuantityPolicy
  и возвращает новый экземпляр с прежними ID и измерениями. Ненулевая дельта
  увеличивает version на 1. Нулевая дельта после проверок возвращает исходную позицию.
- `apply_posting_entry(entry, expected_version=..., inventory_item=..., location=..., warehouse=..., lot=..., serial=...)`
  дополнительно связывает запись Ledger с конкретными ID позиции, базовой единицей
  и ожидаемой версией. Расчёт делегируется apply_delta(); подробный контракт приведён ниже.

StockQuantityPolicy проверяет кратность текущего остатка, модуля дельты и результата
через QuantityValidationPolicy. Арифметика использует собственный Decimal Context,
не зависит от внешних precision/rounding/traps и не возвращает округлённые значения.
Уход в минус даёт NegativeStockQuantityError, нарушение шага — QuantityStepError,
превышение количества конкретной серии — InvalidSerialStockQuantityError.
Несовпадение единицы позиции и товара даёт StockPositionUomMismatchError без пересчёта
или переинтерпретации уже существующего остатка.

Внутренняя рабочая точность арифметики ограничена 1 000 000 значащих цифр для
безопасной обработки большого разрыва порядков. Переполнение или невозможность
точного результата в этих пределах дают StockQuantityArithmeticError.
Это технический предел вычисления; дополнительного поля precision у товара нет.
Нулевая дельта и точные крайние значения сохраняются без ненужного разворачивания.

Физическая позиция существует и в неактивном складе/адресе или состоянии BLOCKED.
Эти состояния не стирают её количество. Разрешение конкретного проведения,
проверки дат поступления и отгрузки относятся к Policy соответствующих операций.
StockAvailabilityPolicy отдельно рассчитывает пригодный к резервированию запас.
on_hand_qty не уменьшается при резервировании; AvailabilityPool отдельно вычитает
общий действующий резерв из пригодного количества. Изменение version в Domain не заменяет идемпотентность
и проверку конкурентной записи в Application/SQL.

Пример для товара item с NONE, базовой единицей KG и шагом 0.05,
подготовленного склада prepared, адреса storage и явного StockOwnerIdVO owner_id:

```python
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.dimensions import StockDimensionsVO
from src.modules.inventory.domain.stock_position.value_object.identifier import StockPositionIdVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus

dimensions = StockDimensionsVO(
    inventory_item_id=item.id,
    location_id=storage.id,
    owner_id=owner_id,
    lot_id=None,
    serial_id=None,
    stock_status=StockStatus.SELLABLE,
)
context = dict(
    inventory_item=item.stock_snapshot(),
    location=storage.snapshot(),
    warehouse=prepared.snapshot(),
)
position = StockPosition.create(
    identifier=StockPositionIdVO(uuid4()),
    dimensions=dimensions,
    **context,
)
changed = position.apply_delta(StockDeltaVO(Decimal("1.25")), **context)
# changed: on_hand_qty=1.25, version=1; исходный position остаётся нулевым.
```

Это Domain-переход в памяти. Будущий Application-сценарий проведения должен сохранять
StockPosting и новое состояние позиции в одной транзакции. SQL, API и атомарное
проведение пока отсутствуют; Domain-модель журнала описана ниже.
SupplierAvailability остаётся внешним наблюдением и не создаёт физические позиции.

## Неизменяемый журнал физических движений

StockPosting — самостоятельный Aggregate Root завершённого проведения. Он владеет
неизменяемыми дочерними StockLedgerEntry; собственных репозиториев у записей нет.
Черновик, подтверждение плана и редактирование плановых строк принадлежат StockDocument;
фактическое исполнение принадлежит StockExecution. У StockPosting нет методов
редактирования, удаления и установки статуса.

| Поле StockPosting | Тип |
| --- | --- |
| id | StockPostingIdVO |
| source | PostingSourceVO с execution_id: StockExecutionIdVO |
| operation_type | StockOperationType |
| posted_at | datetime с часовым поясом, нормализованный в UTC |
| entries | Непустой tuple[StockLedgerEntry, ...] |
| reversal_of_id | StockPostingIdVO или None |

ID и время передаются явно; Domain не генерирует их и не вызывает часы.
StockExecutionIdVO ссылается на отдельный корень исполнения. Существование записи,
принадлежность tenant и запрет повторного проведения проверит будущий сценарий хранения.

| Поле StockLedgerEntry | Тип |
| --- | --- |
| id | StockLedgerEntryIdVO |
| position_id | StockPositionIdVO |
| quantity_delta | Ненулевой StockDeltaVO в базовой единице |
| base_uom | UomCodeVO |
| conversion | QuantityConversionSnapshotVO |

Одна позиция встречается в проведении ровно один раз; ID записей также уникальны.
Повторы отклоняются без скрытого объединения. Нулевая дельта, включая -0.000,
даёт ZeroStockLedgerDeltaError. Проверки собственного состава повторяются
при использовании снимков и непосредственно сконструированных записей.

QuantityConversionSnapshotVO содержит положительное исходное quantity: QuantityVO,
системную uom: UomCodeVO и конечный положительный factor_to_base: Decimal.
Например, 5000 G × 0.001 = 5 KG. Знак задаёт quantity_delta; исходное количество
не становится отрицательным при расходе или компенсации.

- QuantityConversionSnapshotVO.create() получает коэффициент из системного справочника.
- StockLedgerEntry.create() и обычный StockPosting.create() повторно сверяют его
  с текущим системным коэффициентом. Произвольные межразмерные пересчёты запрещены.
- StockLedgerEntry.restore() проверяет точное равенство сохранённого произведения
  модулю дельты без замены коэффициента текущим. StockPosting.restore() сохраняет
  этот состав. Поэтому исторический коэффициент остаётся авторитетным при восстановлении.
- Арифметика не зависит от внешних Decimal precision/rounding/traps и не округляет
  результат. Непредставимый точный пересчёт даёт InvalidQuantityConversionError,
  несовпадение величин или нового коэффициента — QuantityConversionMismatchError.

Пользовательская упаковка пока не является исходной единицей этого VO.
Её содержимое и идентичность потребуют отдельного снимка в расширении StockExecution.

### Поддержанные операции и проверка контекста

| StockOperationType | Правило обычного проведения |
| --- | --- |
| RECEIPT | Каждая дельта положительная |
| ISSUE | Каждая дельта отрицательная |
| INTERNAL_MOVE | Точный баланс расхода и прихода между локациями одного склада |

StockPostingPolicy проверяет состав, знаки и ссылки на позиции. Для каждой записи
требуется ровно один StockPositionSnapshot с id, dimensions и base_uom, полученный
через StockPosition.snapshot(). Лишние, повторные или отсутствующие снимки,
различающиеся единицы и два ID позиции с одинаковыми измерениями отклоняются.
Снимок не содержит текущего количества или версии и не доказывает наличие товара.

StockMovementBalancePolicy дополнительно получает ровно участвующие снимки
StockLocation и требует один склад. Приход и расход сравниваются отдельно по
товару, владельцу, партии, серии, состоянию и базовой единице. Общий нулевой
итог не разрешает подменить товар или изменить состояние. Внутри группы
локации различаются; несколько товаров и распределение по адресам разрешены.
Суммирование точное и использует безопасную арифметику StockQuantityPolicy.

Для конкретного серийного экземпляра дельта равна +1 или -1 PCS. В одном
проведении допускается не больше одного прихода и одного расхода serial_id.
Положительное присутствие серии в других позициях tenant проверит будущий
сценарий с блокировками и ограничениями БД.

Журнал описывает физические факты и сам не разрешает проведение в неактивной
локации, продажу BLOCKED или поступление без обязательной даты. Проверки
активности, допустимости операции и сроков годности добавятся при её исполнении.
ADJUSTMENT, WRITE_OFF, STATUS_CHANGE, RETURN и межскладские этапы пока не поддержаны
StockOperationType; они остаются в целевом плане документов и расширений правил.

### Создание, восстановление и компенсация

StockPosting.create() получает поля проведения, entries и снимки positions;
для INTERNAL_MOVE дополнительно locations. Создаётся только обычное проведение,
без аргумента reversal_of_id. Для RECEIPT/ISSUE отдельные снимки locations не передаются.

StockPosting.restore() принимает весь собственный состав, включая reversal_of_id,
нормализует время и проверяет поля, уникальность записей, сохранённый пересчёт
и знаки обычных операций. Текущие позиции и локации не загружаются. Баланс
по измерениям и соответствие исходному проведению компенсации требуют внешних
снимков при создании; восстановление не подтверждает эти межагрегатные отношения заново.

StockPosting.create_reversal() получает проверенный StockPostingSnapshot оригинала,
новые ID проведения и всех записей, новое основание, время не раньше оригинала
и снимки позиций/локаций. entry_ids соответствуют порядку original.entries.
Фабрика сама создаёт полный набор противоположных дельт: произвольные строки
компенсации передать нельзя. Позиции, единицы и снимки пересчёта сохраняются,
тип операции наследуется, reversal_of_id ссылается на оригинал. Обычное правило
знаков RECEIPT/ISSUE к компенсации не применяется. Исходное проведение не изменяется.

Компенсация компенсации может создать следующий факт с новой ссылкой в цепочке.
Запрет повторной компенсации одного оригинала и глобальная уникальность ID/основания
требуют будущего хранения. Наличие достаточного остатка для обратного движения
проверяется через StockPosition.apply_delta(), а не самим снимком журнала.

Пример для ранее подготовленной позиции position в KG:

```python
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.stock_execution.value_object.identifier import StockExecutionIdVO
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import StockLedgerEntry
from src.modules.inventory.domain.stock_posting.value_object.identifier import StockPostingIdVO
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import StockLedgerEntryIdVO
from src.modules.inventory.domain.stock_posting.value_object.operation_type import StockOperationType
from src.modules.inventory.domain.stock_posting.value_object.posting_source import PostingSourceVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import QuantityConversionSnapshotVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO

conversion = QuantityConversionSnapshotVO.create(
    quantity=QuantityVO(Decimal("5000")),
    uom=UomCodeVO("G"),
    base_uom=position.base_uom,
)
entry = StockLedgerEntry.create(
    identifier=StockLedgerEntryIdVO(uuid4()),
    position_id=position.id,
    quantity_delta=StockDeltaVO(Decimal("5")),
    base_uom=position.base_uom,
    conversion=conversion,
)
posting = StockPosting.create(
    identifier=StockPostingIdVO(uuid4()),
    source=PostingSourceVO(StockExecutionIdVO(uuid4())),
    operation_type=StockOperationType.RECEIPT,
    posted_at=datetime(2026, 11, 3, 12, tzinfo=UTC),
    entries=(entry,),
    positions=(position.snapshot(),),
)
compensation = StockPosting.create_reversal(
    identifier=StockPostingIdVO(uuid4()),
    source=PostingSourceVO(StockExecutionIdVO(uuid4())),
    posted_at=datetime(2026, 11, 3, 13, tzinfo=UTC),
    original=posting.snapshot(),
    entry_ids=(StockLedgerEntryIdVO(uuid4()),),
    positions=(position.snapshot(),),
)
# posting: +5 KG; compensation: -5 KG. Сама position здесь не изменяется.
```

Создание журнала ещё не доказывает возможность применить дельты. Будущий
Application-сценарий проверяет актуальный контекст каждого изменения через
StockPosition.apply_delta(), в том числе шаг, уход в минус и предел 0–1 серии,
и сохраняет StockPosting вместе со всеми новыми позициями в одном UoW.
Domain-фабрика не выполняет эти изменения, не открывает транзакций и не заменяет
идемпотентность, защиту версий и Outbox. Отдельный write API прямого остатка не добавлен.

## Плановый складской документ

StockDocument — самостоятельный Aggregate Root намерения выполнить операцию.
Он владеет неизменяемыми StockDocumentLine, связан с Warehouse и владельцем по ID
и не содержит физических позиций, партий, серий или записей журнала.

| Поле StockDocument | Тип и назначение |
| --- | --- |
| id | StockDocumentIdVO |
| operation_type | Существующий StockOperationType: RECEIPT, ISSUE, INTERNAL_MOVE |
| warehouse_id | WarehouseIdVO одного склада документа |
| owner_id | Явный StockOwnerIdVO |
| source | DocumentSourceVO или None для ручного документа |
| status | StockDocumentStatus |
| lines | tuple[StockDocumentLine, ...] |
| created_at, updated_at | Явно переданное aware datetime, нормализованное в UTC |
| version | Целая неотрицательная версия без bool |

DocumentSourceVO содержит непустые system и reference без управляющих символов.
Внешние пробелы удаляются, регистр обеих строк сохраняется. Ссылка не загружает
другой агрегат, не подтверждает его существование и не заменяет идемпотентность.
Номера документов, интеграции с основаниями и проверка владельца пока не реализованы.

### Плановая строка и снимок товара

StockDocumentLine содержит id: StockDocumentLineIdVO, inventory_item_id,
исторический sku: SkuVO, base_uom: UomCodeVO, planned_qty: QuantityVO,
conversion: QuantityConversionSnapshotVO и executed_qty: QuantityVO.
План строго положительный; накопленное исполнение находится от нуля до плана.
remaining_qty вычисляется как planned_qty − executed_qty без отдельного поля.
Плановое количество строго положительное
для всех видов операций; направление будущих дельт определит тип операции.

StockDocumentLine.create() получает ID строки, InventoryItemDocumentSnapshot,
исходные quantity и uom. Базовая единица и SKU выводятся из снимка товара,
planned_qty точно вычисляется из сохранённого пересчёта, а не принимается произвольно.
StockDocumentLinePolicy проверяет тот же товар и базовую единицу, текущий системный
коэффициент и кратность результата шагу. SERIAL и LOT_AND_SERIAL требуют PCS/step=1;
план на 12 экземпляров разрешён без предварительного выбора их серийных ID.

InventoryItem.document_snapshot() проверяет исходный товар и возвращает только
ID, SKU, base_uom, quantity_rules и tracking_mode. Снимок неизменяем; упаковки,
штрихкоды и режим годности в него не включаются. Сам документ ещё не принимает товар:
LOT/SERIAL, обязательные даты и фактические адреса проверяются при создании StockExecution.

StockDocumentLine.restore() сохраняет полный собственный состав и проверяет типы,
положительность, одну размерность единиц и равенство planned_qty сохранённому
произведению. Исторический коэффициент и SKU не заменяются актуальными значениями.
При добавлении, изменении количества и подтверждении план повторно сверяется
с текущими снимками. Несовместимая базовая единица даёт StockDocumentUomMismatchError;
нарушение шага — QuantityStepError. Черновую строку со старым некратным количеством
можно исправить по новым правилам либо удалить.

### Жизненный цикл и методы

```text
DRAFT → CONFIRMED → PARTIALLY_EXECUTED → COMPLETED
          └──────────────────────────→ COMPLETED
DRAFT / CONFIRMED (без исполнения) → CANCELLED
```

- create создаёт пустой DRAFT версии 0 по снимку активного склада с явными
  владельцем и временем. Реквизиты операции после создания не меняются методами корня.
- add_line добавляет Entity по снимку её товара. ID строк уникальны; повторяющийся
  товар с разными ID строк разрешён без скрытой агрегации.
- change_line меняет исходные quantity/uom с сохранением ID строки, товара,
  исторического SKU и базовой единицы. Новая строка получает текущий SKU;
  переименование товара не переписывает уже добавленные строки.
- remove_line удаляет только существующую строку и может снова сделать черновик пустым.
  get_line возвращает собственную неизменяемую Entity по типизированному ID.
- confirm получает снимок того же активного склада и ровно по одному актуальному
  снимку каждого уникального товара плана. StockDocumentConfirmationPolicy запрещает
  пустой документ, лишние/отсутствующие/повторные снимки и несовместимые строки.
- cancel отменяет DRAFT или CONFIRMED без исполненных количеств, сохраняя строки.
  Текущие снимки товаров/склада для отмены не требуются. PARTIALLY_EXECUTED и COMPLETED
  простой отменой не закрываются; такой вызов даёт StockDocumentNotDraftError.
- Подтверждённый, частично исполненный, завершённый или отменённый документ
  не разрешает редактирование плановых строк и повторное подтверждение.
- register_execution принимает StockExecutionDocumentSnapshot по текущей версии
  и увеличивает выполненные количества конкретных плановых строк. Статус становится
  PARTIALLY_EXECUTED или COMPLETED; полное выполнение первым фактом сразу завершает план.

Каждое фактическое изменение возвращает новый документ с прежним ID/created_at,
новым updated_at и version +1. Время изменения не раньше предыдущего; равные
моменты допустимы. Численно равный ввод в той же единице возвращает прежний объект
без смены версии, времени и формата сохранённых Decimal. Проверки контекста
и хронологии выполняются и для такого вызова. Смена исходной единицы при прежнем
базовом количестве является изменением снимка пересчёта и увеличивает версию.

StockDocument.restore() принимает все собственные поля без снимков текущих
товаров/склада. Проверяются типы, уникальность строк, их собственные значения,
UTC-хронология, версия и согласованность статуса с прогрессом. DRAFT/CONFIRMED/CANCELLED
требуют нулевого исполнения; PARTIALLY_EXECUTED — ненулевого неполного; COMPLETED —
полного исполнения каждой строки. Подтверждённые и исполняемые документы непустые.
StockDocumentLine.restore() явно принимает executed_qty, без неявного обнуления истории.
Текущий шаг, активность склада
и межагрегатная совместимость повторно проверяются перед подтверждением.
Прямое создание dataclass не обходит проверки публичных методов.

Пример для ранее подготовленных item в KG с шагом 0.05, warehouse и owner_id:

```python
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import StockDocumentLine
from src.modules.inventory.domain.stock_document.value_object.document_source import DocumentSourceVO
from src.modules.inventory.domain.stock_document.value_object.identifier import StockDocumentIdVO
from src.modules.inventory.domain.stock_document.value_object.line_id import StockDocumentLineIdVO
from src.modules.inventory.domain.stock_posting.value_object.operation_type import StockOperationType
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO

draft = StockDocument.create(
    identifier=StockDocumentIdVO(uuid4()),
    operation_type=StockOperationType.RECEIPT,
    warehouse=warehouse.snapshot(),
    owner_id=owner_id,
    source=DocumentSourceVO("procurement", "PO-001"),
    created_at=datetime(2026, 11, 3, 9, tzinfo=UTC),
)
line = StockDocumentLine.create(
    identifier=StockDocumentLineIdVO(uuid4()),
    inventory_item=item.document_snapshot(),
    quantity=QuantityVO(Decimal("50000")),
    uom=UomCodeVO("G"),
)
planned = draft.add_line(
    line,
    inventory_item=item.document_snapshot(),
    updated_at=datetime(2026, 11, 3, 9, 1, tzinfo=UTC),
)
confirmed = planned.confirm(
    warehouse=warehouse.snapshot(),
    inventory_items=(item.document_snapshot(),),
    updated_at=datetime(2026, 11, 3, 9, 2, tzinfo=UTC),
)
# draft: DRAFT, 0 строк, version=0.
# planned: DRAFT, план 50 KG, version=1.
# confirmed: CONFIRMED, тот же план 50 KG, version=2. Остатки не менялись.
```

CONFIRMED означает зафиксированный план. Создание StockPosting, применение дельт,
резервирование и фактический приём/выдача в этот переход не входят.
StockExecution связывает фактические строки с ID плановых строк и позволяет
проверять частичное выполнение, например 100 = 40 + 35 + 25, и превышение плана.
Хранение, конкурентная защита версии, API, Outbox и атомарное проведение остаются
будущим Application/SQL-срезам.

## Фактическое исполнение документа

StockExecution — отдельный immutable Aggregate Root с полями id: StockExecutionIdVO,
document_id: StockDocumentIdVO, document_version: int, operation_type,
warehouse_id, owner_id, executed_at в UTC и непустым tuple StockExecutionLine.
В первом срезе нет редактируемого черновика, статуса проведения или собственных
часов. Факт создаётся в памяти после проверок; сам по себе он не означает commit.

StockExecutionLine — дочерняя Entity с id: StockExecutionLineIdVO,
document_line_id, inventory_item_id, base_uom, положительным quantity,
QuantityConversionSnapshotVO и одним из маршрутов:

| Маршрут | Физические измерения |
| --- | --- |
| ReceiptExecutionRouteVO | destination: StockDimensionsVO |
| IssueExecutionRouteVO | source: StockDimensionsVO |
| InternalMoveExecutionRouteVO | source и destination: StockDimensionsVO |

Маршрут строго соответствует операции. Внутреннее перемещение меняет только
локацию; товар, владелец, партия, серия и состояние сохраняются. Две локации
различаются и принадлежат складу документа. Одна фактическая quantity выражает
обе стороны, поэтому перемещение 10 кг увеличивает исполнение плана на 10, а не 20.
Внешняя сторона прихода/расхода не становится фиктивной физической позицией.

Строки одной плановой строки могут использовать разные адреса и партии.
ID фактических строк уникальны. Один serial_id не повторяется в разных строках;
внутри одного маршрута перемещения он используется на обеих сторонах. Для серии
нужна quantity=1 PCS; план на 12 экземпляров исполняется 12 выбранными сериями.
Маршрут обязан соответствовать товару строки и владельцу документа.

### Создание и физический контекст

StockExecution.create() принимает документный снимок, время, строки и ровно
участвующие снимки warehouse, inventory_items, locations, lots и serials.
Строки и корни других агрегатов не подменяют снимки.

- StockDocument.execution_snapshot() возвращает StockDocumentExecutionSnapshot
  с ID, операцией, складом, владельцем, статусом, версией, updated_at и лимитами
  StockDocumentLineExecutionSnapshot: ID строки, товар, единица, план, исполнение.
- InventoryItem.execution_snapshot() возвращает InventoryItemExecutionSnapshot:
  ID, base_uom, quantity_rules, tracking_mode и expiration_mode, без SKU/коллекций.
- StockSerial.execution_snapshot() возвращает StockSerialExecutionSnapshot с ID,
  товаром, lot_id и собственными dates. SERIAL имеет собственные StockDatesVO;
  LOT_AND_SERIAL — ссылку на партию без копии дат. Старый snapshot() остаётся минимальным.
- Снимки склада, локаций и партий используются повторно. Лишние, отсутствующие
  и повторные снимки отклоняются; один снимок может обслуживать несколько строк.

StockExecutionDocumentPolicy требует CONFIRMED или PARTIALLY_EXECUTED,
версию плана и совпадение документа/операции/склада/владельца. Количества
суммируются по document_line_id; товар и единица должны совпадать с этой строкой.
Выполнение не превышает её remaining_qty. Свободный лимит другой строки того же
товара не покрывает превышение. executed_at не раньше updated_at снимка плана.

StockExecutionContextPolicy проверяет текущий коэффициент, базовую единицу и шаг,
активный склад и каждую фактическую локацию через LocationAvailabilityPolicy,
а измерения — через StockDimensionsPolicy. NONE не допускает LOT/SERIAL;
LOT требует партию; SERIAL — экземпляр без партии; LOT_AND_SERIAL — экземпляр
соответствующей партии того же товара.

Для RECEIPT используется StockExpirationPolicy.ensure_ready_for_receipt(): REQUIRED
требует дату партии или самостоятельного экземпляра. OPTIONAL остаётся заметкой
и не фильтрует операции по дате. Правила приёмки просрочки, продаж по срокам,
FEFO и ограничения назначения зон в этот срез не добавлены; наличие даты не означает
проверку её относительно текущего дня. Исполнение также не доказывает наличие
достаточного физического остатка: это проверит StockPosition.apply_delta() при проведении.
Ввод в пользовательских упаковках остаётся отдельным расширением; здесь используются
системные единицы и сохранённый QuantityConversionSnapshotVO.

StockExecution.restore() принимает весь собственный состав без актуальных снимков.
Он сохраняет ID, версию основания, исходные количества и коэффициенты; проверяет
типы, UTC-время, непустоту, уникальность строк/серий, соответствие маршрута операции
и владельца/товара. Повторные проверки текущих дат, активности, шага и лимита плана
выполняются при создании, а не при восстановлении исторического факта.

### Регистрация прогресса и версии

StockExecution.snapshot_for_document() возвращает минимальный StockExecutionDocumentSnapshot
с ID исполнения, ID/версией документа, операцией, складом, владельцем, временем
и tuple ExecutedDocumentLineQuantityVO. Итоги группируются по ID плановой строки;
маршруты и исходные пересчёты сохраняются в самом исполнении, не копируются в документ.

StockDocument.register_execution(snapshot, updated_at=...) повторяет проверку
совместимости и оставшегося плана перед увеличением executed_qty. Версия основания
обязана совпадать с текущей версией документа. Время регистрации не раньше факта;
при успехе возвращается новый документ с version +1 и неизменными планом/SKU.
Повтор исходного снимка отклоняется по устаревшей версии или завершённому состоянию.
Глобальная дедупликация ID исполнения и конкурентная защита всё ещё требуют SQL/UoW.
Коллекции всех исполнений и бесконечного списка их ID внутри документа нет.

QuantityArithmeticPolicy точно складывает и вычитает QuantityVO для группировки,
прогресса и remaining_qty через безопасную арифметику StockQuantityPolicy.
Внешний Decimal context не влияет на результат; технический предел промежуточной
арифметики и контролируемый StockQuantityArithmeticError сохраняются.

Пример для подтверждённого document с одной строкой на 100 KG, подготовленных
item, warehouse и location этого склада, без LOT/SERIAL:

```python
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import StockExecutionLine
from src.modules.inventory.domain.stock_execution.value_object.identifier import StockExecutionIdVO
from src.modules.inventory.domain.stock_execution.value_object.line_id import StockExecutionLineIdVO
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import ReceiptExecutionRouteVO
from src.modules.inventory.domain.stock_position.value_object.dimensions import StockDimensionsVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus

destination = StockDimensionsVO(
    inventory_item_id=item.id,
    location_id=location.id,
    owner_id=document.owner_id,
    lot_id=None,
    serial_id=None,
    stock_status=StockStatus.SELLABLE,
)
for index, amount in enumerate(("40", "35", "25")):
    actual = StockExecutionLine.create(
        identifier=StockExecutionLineIdVO(uuid4()),
        document_line_id=document.lines[0].id,
        inventory_item=item.execution_snapshot(),
        quantity=QuantityVO(Decimal(amount)),
        uom=item.base_uom,
        route=ReceiptExecutionRouteVO(destination),
    )
    execution = StockExecution.create(
        identifier=StockExecutionIdVO(uuid4()),
        document=document.execution_snapshot(),
        executed_at=datetime(2026, 11, 3, 9, 3 + index * 2, tzinfo=UTC),
        lines=(actual,),
        warehouse=warehouse.snapshot(),
        inventory_items=(item.execution_snapshot(),),
        locations=(location.snapshot(),),
    )
    document = document.register_execution(
        execution.snapshot_for_document(),
        updated_at=datetime(2026, 11, 3, 9, 4 + index * 2, tzinfo=UTC),
    )
# executed_qty: 40 → 75 → 100; remaining_qty: 60 → 25 → 0.
# Статусы: PARTIALLY_EXECUTED → PARTIALLY_EXECUTED → COMPLETED.
# Физические позиции и Ledger этот пример не изменяет.
```

### Граница проведения

Создание исполнения и регистрация прогресса пока существуют в Domain в памяти.
StockPosting.create_from_execution() строит журнал по физическим маршрутам
через StockExecutionPostingPolicy. Фабрика и её ограничения описаны ниже.
StockPosition.apply_posting_entry() применяет запись к одной позиции в памяти;
атомарное сохранение всех позиций с прогрессом документа пока не добавлено.

Будущий Application обязан сохранить исполнение, прогресс документа, проведение
и новые физические позиции одной транзакцией с проверкой версий и идемпотентности.
Компенсация StockPosting сама по себе не уменьшает executed_qty. Согласованный
откат исполнения и прогресса, частичное закрытие остатка плана, SQL, API и Outbox
остаются следующими срезами. Нельзя независимо записывать прогресс в production
как подтверждение физического проведения без этой координации.

## Построение журнала из исполнения

StockExecution.posting_snapshot() проверяет собственное состояние и возвращает
StockExecutionPostingSnapshot: id, operation_type, warehouse_id, owner_id,
executed_at в UTC и непустой tuple StockExecutionPostingLineSnapshot.
Каждый снимок строки содержит её ID, inventory_item_id, base_uom, quantity,
сохранённый conversion и route. Он не содержит чужих корней или Entity.
Существующий snapshot_for_document() остаётся отдельным контрактом итогов по плану.

Потребитель проверяет типы снимков, положительность и точность сохранённого
пересчёта, соответствие маршрута операции и товару/владельцу, уникальность ID
строк и серий. Исходные количества не пересчитываются заново по текущим
настройкам товара: это уже зафиксированный состав исполнения. Исторический
коэффициент остаётся частью его детализации.

StockPosting.create_from_execution() получает явно:

- identifier: StockPostingIdVO и posted_at: aware datetime;
- execution: StockExecutionPostingSnapshot;
- positions: tuple[StockPositionSnapshot, ...];
- locations: tuple[StockLocationSnapshot, ...] для всех трёх операций;
- entry_bindings: tuple[StockPostingEntryBindingVO, ...].

Основание PostingSourceVO(execution.id), вид операции и обычное проведение
с reversal_of_id=None выводятся фабрикой. Время нормализуется в UTC и не раньше
executed_at; нарушение даёт StockPostingExecutionTimeError.
ID не генерируются внутри Domain.

### Сопоставление и агрегация

StockExecutionPostingPolicy.build_entries() требует ровно участвующие позиции
по полному StockDimensionsVO и той же базовой единице. ID позиций и сочетания
измерений уникальны. Ровно участвующие локации должны принадлежать warehouse_id
исполнения; отсутствие, лишний или повторный снимок отклоняется.
Признак активности не переопределяет зафиксированный факт: Policy проверяет
неизменяемую принадлежность склада, а допустимость фактической операции и её
актуальный контекст остаются проверкам исполнения и будущего проведения.

Фабрика не ищет и не создаёт позицию. Если назначения ещё нет, внешний сценарий
сначала создаст нулевой StockPosition и передаст его снимок. Снимок без on_hand_qty
не подтверждает наличие товара для расхода.

StockPostingEntryBindingVO содержит position_id: StockPositionIdVO
и entry_id: StockLedgerEntryIdVO. Нужна ровно одна связь на итоговую позицию;
оба идентификатора не повторяются. Неполный или лишний набор даёт
InvalidStockPostingEntryBindingError, повторы — DuplicateStockLedgerEntryError.

Маршруты преобразуются в направленные движения:

| Маршрут | Записи |
| --- | --- |
| ReceiptExecutionRouteVO | +quantity в destination |
| IssueExecutionRouteVO | −quantity из source |
| InternalMoveExecutionRouteVO | −quantity из source и +quantity в destination |

Количество одной позиции одного направления суммируется точно через
QuantityArithmeticPolicy. Например, A→B на 4 KG и A→C на 6 KG дают
A:-10, B:+4, C:+6. Один серийный экземпляр остаётся отдельной позицией с ±1 PCS.
Выходные записи упорядочены по числовому UUID позиции; перестановка фактических
строк, снимков или связей ID не меняет состав и идентичность результата.
Сохраняются существующие проверки StockPostingPolicy и StockMovementBalancePolicy.

Если одна позиция участвует и в приходе, и в расходе, фабрика даёт
OpposingStockPositionMovementsError. Например, A→B и B→C требуют отдельных
исполнений/проведений. Нулевой или остаточный итог для B не скрывает оборот:
встречное сальдирование в этом срезе не поддерживается. Старый инвариант
одной записи на позицию внутри проведения сохраняется.

### Исходные единицы и итог Ledger

Для новой фабрики единое правило: conversion каждой итоговой записи выражается
в её базовой единице с factor_to_base=1, включая случай одного источника.

```text
StockExecutionLine #1: 2000 G × 0.001 = 2 KG
StockExecutionLine #2:    3 KG × 1     = 3 KG

StockLedgerEntry: +5 KG
conversion: quantity=5, uom=KG, factor_to_base=1
```

Исходные количества и коэффициенты остаются в immutable StockExecution,
на который ссылается posting.source.execution_id. Усреднённый коэффициент
или искусственная исходная единица не вычисляются. Старые create/restore
и компенсация StockPosting сохраняют свои контракты; новый срез не переписывает
исторические записи. Компенсация агрегированной записи даёт противоположный итог.
Переполнение/непредставимый точный итог дают StockQuantityArithmeticError без округления.

Пример для execution с двумя строками 2000 G и 3 KG в одну position,
подготовленных position и StockLocation location:

```python
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import StockPostingEntryBindingVO
from src.modules.inventory.domain.stock_posting.value_object.identifier import StockPostingIdVO
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import StockLedgerEntryIdVO

posting = StockPosting.create_from_execution(
    identifier=StockPostingIdVO(uuid4()),
    execution=execution.posting_snapshot(),
    posted_at=datetime(2026, 11, 4, 9, 1, tzinfo=UTC),
    positions=(position.snapshot(),),
    locations=(location.snapshot(),),
    entry_bindings=(
        StockPostingEntryBindingVO(
            position_id=position.id,
            entry_id=StockLedgerEntryIdVO(uuid4()),
        ),
    ),
)
# Одна запись +5 KG; posting.source.execution_id == execution.id.
# Исходные 2000 G и 3 KG сохранены в execution.lines.
# Документ и физическая position этим вызовом не изменяются.
```

Применение записи к конкретной позиции выполняется через StockPosition.apply_posting_entry(),
который делегирует проверки количества и шага существующему apply_delta().
Регистрация прогресса StockDocument, исполнение, журнал и новые состояния позиций
должны сохраняться будущим Application-сценарием одним UoW с проверкой версий,
глобальной дедупликацией и Outbox. SQL, write API прямого остатка, согласованный
откат исполнения/прогресса и глобальная защита присутствия серии не добавлены.

## Применение записи Ledger к позиции

StockLedgerEntry.snapshot() проверяет полное собственное состояние Entity,
включая сохранённое равенство исходного пересчёта, и возвращает immutable
StockLedgerEntrySnapshot. Он содержит только:

| Поле | Тип |
| --- | --- |
| id | StockLedgerEntryIdVO |
| position_id | StockPositionIdVO |
| quantity_delta | Ненулевой StockDeltaVO |
| base_uom | Известный UomCodeVO |

Потребитель повторно проверяет снимок. Сырые UUID/числа/единицы, Entity или
произвольные объекты вместо него дают InvalidStockLedgerEntrySnapshotError.
Нулевая дельта, включая -0.000, запрещена с ZeroStockLedgerDeltaError.
Источник, исходный коэффициент и полная Entity в позицию не передаются:
это уже рассчитанное изменение в базовой единице. Исторический пересчёт записи
при получении снимка не заменяется текущим коэффициентом.

StockPosition.apply_posting_entry() выполняет проверки перед изменением:

1. Проверяет собственное состояние и типизированный ненулевой снимок записи.
2. Требует expected_version как целое неотрицательное число без bool.
3. Сравнивает expected_version с текущей version; несовпадение даёт
   StockPositionVersionConflictError, некорректный тип — InvalidStockPositionValueError.
4. Сверяет entry.position_id с self.id; другая позиция даёт
   StockPostingPositionMismatchError, даже если её товар и измерения совпадают.
5. Сверяет базовую единицу записи с позицией без неявного пересчёта;
   несовпадение даёт StockPositionUomMismatchError.
6. Вызывает существующий apply_delta(), повторно проверяя снимки товара,
   локации/склада, партии/серии, текущую единицу товара, шаг, неотрицательный
   результат и ограничение конкретной серии 0–1 PCS.

При успехе возвращается новый экземпляр с version +1. ID, измерения и базовая
единица сохраняются. Исходные позиция, запись и снимок не меняются ни при успехе,
ни при ошибке. Компенсирующие записи применяются этим же методом и проходят
обычные проверки доступного физического количества.
Низкоуровневый apply_delta() продолжает принимать ноль; ограничение ненулевой
дельты относится к журналу и новому пути применения его записей.

Пример: position содержит 10 KG версии 7, а posting.entries[0] — её запись −4 KG.
context содержит существующие снимки inventory_item, location, warehouse
и при необходимости lot/serial:

```python
expected_version = position.version
entry_snapshot = posting.entries[0].snapshot()
changed = position.apply_posting_entry(
    entry=entry_snapshot,
    expected_version=expected_version,
    **context,
)
# changed: 6 KG, version=8; исходная position: 10 KG, version=7.
# Повторный вызов для changed с expected_version=7 даст конфликт версии.
```

Для перемещения A:10 KG/v7 → B:0 KG/v2 записи −4/+4 применяются к своим
позициям с ожидаемыми версиями 7 и 2. Получаются A:6 KG/v8 и B:4 KG/v3.
Если одна сторона отклоняется, уже вычисленный кандидат другой стороны
остаётся только объектом в памяти; исходные позиции не изменены.
Все кандидаты и журнал необходимо сохранять одной будущей транзакцией.

Проверка expected_version — Domain-проверка переданного состояния. Она не
выполняет compare-and-set в БД и не заменяет блокировки. Позиция не хранит
историю применённых ID записей: повтор той же записи с новой актуальной версией
не запрещается локальным агрегатом. Глобальная идемпотентность проведения,
проверка присутствия серии в других позициях, регистрация прогресса документа,
общий commit/rollback и Outbox относятся к будущему Application/SQL-срезу.

## Физический запас, пригодный к резервированию

StockAvailabilityPolicy.calculate_eligible_quantity() — чистый расчёт для одного
сочетания InventoryItem + Warehouse + Owner. Возвращает eligible_qty: QuantityVO
в базовой единице товара. Это физический запас, удовлетворяющий текущим правилам
пригодности; действующие резервы ещё не вычитаются. Физический on_hand_qty,
пригодный eligible_qty и будущий свободный остаток после резервов имеют разный смысл.
Расчёт не создаёт новых Aggregate Roots, Entity, резервов или движений.

Контракт получает один InventoryItemAvailabilitySnapshot, WarehouseSnapshot,
явные owner_id: StockOwnerIdVO и as_of: date, tuple позиций и ровно участвующие
снимки локаций, партий и экземпляров. datetime, строки и системное время
не используются вместо календарной даты. Выбор календарного дня склада относится
к вызывающему сценарию. Пустые positions/locations/lots/serials дают QuantityVO(0).

Три специализированных immutable-снимка получаются через availability_snapshot():

| Снимок | Поля |
| --- | --- |
| InventoryItemAvailabilitySnapshot | inventory_item_id, base_uom, quantity_rules, tracking_mode, expiration_mode |
| StockPositionAvailabilitySnapshot | id, dimensions, base_uom, on_hand_qty |
| StockSerialAvailabilitySnapshot | id, inventory_item_id, lot_id, dates |

Геттеры проверяют исходный агрегат; Policy повторно проверяет снимки через
ensure_valid(). Полные корни, учётный StockPositionSnapshot без количества и
снимки исполнения вместо специализированных снимков не принимаются.
StockPositionSnapshot для журнала остаётся без количества и версии.
Контракты не подтверждают согласованность чтения или актуальную версию в БД.

В первом правиле пригодности суммируются только позиции со StockStatus.SELLABLE
в локально активных локациях STORAGE активного склада. RECEIVING, SHIPPING,
QUARANTINE и TRANSIT исключены. Неактивность или другое состояние дают нулевой
вклад, сохраняя физический остаток. Обход активности родителей дерева не добавлен.
Расширение допустимых зон и правила отдельных операций остаются самостоятельными.

Товар, владелец, склад через локацию, базовая единица и матрица LOT/SERIAL должны
совпадать с областью расчёта. Количество каждой позиции проверяется по текущему
шагу товара, включая исключаемые позиции. Другой UOM не пересчитывается молча.
Неверные ссылки и настройки вызывают доменную ошибку, а не дают нулевой вклад.
Повтор ID позиции или полного ключа измерений запрещён. Повторные, отсутствующие
и лишние снимки контекста запрещены с InvalidStockAvailabilityContextError либо
соответствующей существующей ошибкой измерений/снимка. Некорректные новые снимки
товара и позиции дают InvalidInventoryItemAvailabilitySnapshotError и
InvalidStockPositionAvailabilitySnapshotError.

Срок проверяется только при REQUIRED: expires_on >= as_of разрешено,
expires_on < as_of исключает позицию. Последний день считается допустимым.
LOT и LOT_AND_SERIAL используют даты партии, SERIAL — собственные даты экземпляра
без копии партийных дат. Отсутствующий срок у положительного остатка даёт
ExpirationDateRequiredError даже при DAMAGED или неактивном адресе/складе.
Нулевая позиция может иметь неполную карточку, но её ссылки всё равно обязательны.
OPTIONAL не фильтрует по сроку, включая прошедшие даты-заметки. NONE не оценивает
дату производства, сохраняя существующий запрет заполненного expires_on.
Расчёт доступности не меняет допустимость приёмки просрочки, отгрузки или FEFO.

Количество конкретного экземпляра остаётся 0 или 1 PCS. Положительный остаток
одного serial_id в нескольких переданных позициях даёт DuplicatePositiveSerialStockError,
включая исключаемые по состоянию/активности позиции. Нулевые позиции той же серии
не создают повторного физического присутствия. Это проверка только данного набора,
не глобальная гарантия уникальности серии в tenant-хранении.

Сложение использует QuantityArithmeticPolicy без округления и влияния внешнего
Decimal context. Позиции суммируются в порядке UUID; перестановка входных данных
не меняет результат. Сохраняется контролируемый предел точной арифметики и
StockQuantityArithmeticError. Все исходные объекты остаются неизменными при успехе
и при ошибке.

Пример для одного LOT-товара в KG с REQUIRED, одного склада и владельца:

| Физический остаток | Условия | Вклад в eligible_qty |
| --- | --- | --- |
| 10 KG | STORAGE, SELLABLE, срок действителен | 10 KG |
| 3 KG | STORAGE, DAMAGED | 0 |
| 2 KG | SHIPPING, SELLABLE | 0 |
| 5 KG | STORAGE, SELLABLE, срок истёк | 0 |

Физически 20 KG, пригодно 10 KG; при OPTIONAL с теми же датами — 15 KG.
В следующем примере item — карточка такого товара, positions — tuple четырёх
StockPosition из таблицы, locations — снимки двух адресов, lots — карточки
участвующих партий. warehouse и owner_id задают общую область расчёта:

```python
from datetime import date

from src.modules.inventory.domain.policy.stock_availability import StockAvailabilityPolicy

eligible_qty = StockAvailabilityPolicy.calculate_eligible_quantity(
    inventory_item=item.availability_snapshot(),
    warehouse=warehouse,
    owner_id=owner_id,
    as_of=date(2026, 11, 4),
    positions=tuple(position.availability_snapshot() for position in positions),
    locations=locations,
    lots=tuple(lot.snapshot() for lot in lots),
)
# eligible_qty.value == Decimal("10"); исходные позиции не изменяются.
```

Полноту выборки и согласованный момент чтения должен обеспечить будущий Application
и слой хранения. Policy сама не ведёт резерв: общий счётчик реализован отдельным
AvailabilityPool ниже. Обязательство реализовано в отдельном StockReservation.
Защита от двойной продажи в хранении, SQL, блокировки, идемпотентность и Outbox
этим расчётом не реализуются.
Изменение пригодности по календарной дате при REQUIRED не создаёт движения Ledger.

## Общий пул доступности и мягких резервов

AvailabilityPool — самостоятельный immutable Aggregate Root без дочерних Entity,
коллекций позиций, партий, серий и резервов. Он хранит общий резерв для одного
товара, склада и владельца. Принадлежность конкретного обязательства заказу
и его жизненный цикл реализованы отдельно в StockReservation.

| Поле | Тип и назначение |
| --- | --- |
| id | AvailabilityPoolIdVO |
| key | AvailabilityPoolKeyVO: inventory_item_id, warehouse_id, owner_id |
| base_uom | Неизменяемый известный UomCodeVO |
| eligible_qty | QuantityVO, последний рассчитанный пригодный физический запас |
| reserved_qty | QuantityVO, общий действующий резерв |
| assessed_on | date, календарный день оценки пригодности |
| version | Целое неотрицательное число без bool |

AvailabilityPoolKeyVO проверяет собственные типы ссылок, не включая локацию,
партию или серию в ключ. Уникальность этого ключа в tenant-схеме относится
к будущему ограничению БД; Domain не проверяет другие экземпляры пула.

available_qty и deficit_qty — вычисляемые QuantityVO без самостоятельного хранения:
available_qty = max(eligible_qty − reserved_qty, 0),
deficit_qty = max(reserved_qty − eligible_qty, 0).
Сравнение выполняется до вычитания, отрицательный QuantityVO не создаётся.
Арифметика использует QuantityArithmeticPolicy с прежней защитой точности.

reserved_qty может превышать eligible_qty: после просрочки, блокировки или
уменьшения физического запаса существующие обязательства сохраняются.
Тогда свободное количество равно нулю и видна величина дефицита. Пригодность
не определяет автоматически, какой конкретный резерв отменять.
Свойства показывают сохранённую оценку на assessed_on, не читают системные часы
и не пересчитываются при обращении.

- create получает явные ID, ключ, as_of и полный контекст StockAvailabilityPolicy.
  Проверяет соответствие снимков товара/склада ключу, выводит base_uom из товара,
  рассчитывает eligible_qty, устанавливает reserved_qty=0 и version=0.
  Пустая область и неактивный склад допустимы с нулевым пригодным запасом.
  Сырые eligible_qty вместо расчёта фабрика не принимает.
- restore получает полный исторический состав без текущих снимков. Проверяет
  собственные типы, известную единицу, календарную дату и версию; допускает
  дефицит и не переписывает старые значения по текущему шагу товара.
- refresh_eligible_quantity получает expected_version, as_of и текущий физический
  контекст. Повторно рассчитывает eligible_qty, сохраняет reserved_qty и обновляет
  assessed_on. День оценки не убывает, datetime/строки не принимаются.
  Новое количество в том же дне допустимо. Если дата и числовой результат прежние,
  возвращает исходный объект после всех проверок. Новый день с прежним количеством
  является изменением и увеличивает версию.
- reserve(quantity, ...) также получает expected_version и полный текущий контекст.
  Заново рассчитывает пригодность перед проверкой количества. quantity — строго
  положительный QuantityVO, кратный шагу товара. Требуется quantity <= available_qty
  по новой оценке; иначе InsufficientAvailableStockError без частичного резерва.
  Успех сохраняет новую оценку, дату и увеличенный общий резерв одной следующей
  версии, даже если одновременно изменилось пригодное количество.
- release(quantity, expected_version=..., inventory_item=...) получает только
  InventoryItemStockSnapshot, не снимок доступности или исполнения. Проверяет
  тот же товар, базовую единицу, текущий шаг и quantity <= reserved_qty, затем
  уменьшает общий резерв. Превышение даёт ExcessiveReservationReleaseError.
  Активность склада, свежая дата и физический контекст не требуются: освобождение
  доступно при исторической оценке и дефиците. eligible_qty и assessed_on сохраняются.

Все переходы повторно проверяют собственное состояние и expected_version до
расчёта. Несовпадение версии даёт AvailabilityPoolVersionConflictError;
нецелая/отрицательная версия или bool — InvalidAvailabilityPoolValueError.
Неверные собственные значения restore/create также дают InvalidAvailabilityPoolValueError.
Чужой товар или склад даёт AvailabilityPoolContextMismatchError, смена базовой
единицы — AvailabilityPoolUomMismatchError без неявного пересчёта. Некалендарная
или убывающая дата пересчёта даёт AvailabilityAssessmentDateError.
Ноль и отрицательный ноль в reserve/release запрещены с InvalidReservationQuantityError;
сырые количества и нарушение шага отклоняются существующими доменными ошибками.
При текущем использовании reserved_qty также проверяется по текущему шагу товара.
Изменение правил количества остаётся отдельной контролируемой задачей.

Каждое изменение возвращает новый объект версии +1 с прежними ID, ключом и
единицей. Исходный пул и физические позиции неизменны при успехе и при ошибке.
При отказе reserve новая оценка тоже не сохраняется; для отдельного обновления
оценки служит refresh_eligible_quantity. SERIAL/LOT_AND_SERIAL требуют PCS и
шаг 1, но общий пул может содержать 12 разных экземпляров: ограничение 0–1
относится к физической позиции конкретной серии, не к общему резерву.

Пример для KG/шага 0.05 и TrackingMode.NONE. item — карточка товара, warehouse
и storage — снимки активного склада и STORAGE, owner_id и pool_id — явные
типизированные ID. position содержит 10 KG, updated_position содержит 5 KG после
отдельной учётной операции; пул не изменяет эти позиции самостоятельно:

```python
from datetime import date
from decimal import Decimal

from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.value_object.key import AvailabilityPoolKeyVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO

context = dict(
    inventory_item=item.availability_snapshot(),
    warehouse=warehouse,
    as_of=date(2026, 11, 4),
    positions=(position.availability_snapshot(),),
    locations=(storage,),
)
pool = AvailabilityPool.create(
    identifier=pool_id,
    key=AvailabilityPoolKeyVO(item.id, warehouse.id, owner_id),
    **context,
)
reserved = pool.reserve(QuantityVO(Decimal("7")), expected_version=0, **context)
deficit = reserved.refresh_eligible_quantity(
    expected_version=1,
    **(context | {"positions": (updated_position.availability_snapshot(),)}),
)
released = deficit.release(
    QuantityVO(Decimal("3")),
    expected_version=2,
    inventory_item=item.stock_snapshot(),
)
```

| Состояние | eligible_qty | reserved_qty | available_qty | deficit_qty | version |
| --- | --- | --- | --- | --- | --- |
| pool | 10 | 0 | 10 | 0 | 0 |
| reserved | 10 | 7 | 3 | 0 | 1 |
| deficit | 5 | 7 | 0 | 2 | 2 |
| released | 5 | 4 | 1 | 0 | 3 |

expected_version — проверка переданного Domain-состояния, не блокировка в БД.
Два вызова от одного исходного объекта могут подготовить две ветви версии +1;
конфликт их сохранения обязан обнаружить будущий Application/SQL. Счётчик пула
не хранит историю команд и не гарантирует идемпотентность повторного reserve/release.
Полнота и согласованность физической выборки тоже остаются обязанностью внешнего
сценария. В будущем пул и конкретный StockReservation изменяются одним UoW.
Погашение при отгрузке, SQL, Outbox, жёсткие привязки к позициям и планировщик
истечения резервов в текущий срез не входят. StockReservation поддерживает явное
истечение, описанное ниже. StockPosition и Ledger не изменяются.

## Мягкий резерв под конкретное обязательство

StockReservation — самостоятельный immutable Aggregate Root, относящийся к одной
строке внешнего обязательства. Он не владеет пулом, физическими позициями или
дочерними ReservationAllocation. Привязка к конкретным партиям, сериям и адресам
остаётся будущим жёстким резервированием; пустой коллекции под него сейчас нет.

| Поле | Тип и назначение |
| --- | --- |
| id | StockReservationIdVO |
| source_ref | Обязательный ReservationSourceVO(system, reference) строки обязательства |
| pool_id | AvailabilityPoolIdVO |
| key | AvailabilityPoolKeyVO товара, склада и владельца |
| base_uom | Неизменяемый известный UomCodeVO |
| requested_qty | Положительный QuantityVO, неизменяемый лимит текущего удержания |
| reserved_qty | QuantityVO текущего удерживаемого количества |
| status | StockReservationStatus |
| expires_at | Необязательный aware datetime срока действия резерва |
| created_at, updated_at | aware datetime в UTC |
| version | Целое неотрицательное число без bool |

ReservationSourceVO обрезает края строк, сохраняет регистр/ведущие нули и запрещает
пустые или нетекстовые значения и управляющие символы Cc/Cf. Ошибка —
InvalidReservationSourceError. Ссылка не подтверждает существование заказа,
его лимит или глобальную идемпотентность; несколько объектов с одной ссылкой
не обнаруживаются локальным агрегатом.

AvailabilityPool.reservation_snapshot() проверяет исходный пул и возвращает
AvailabilityPoolReservationSnapshot(id, key, base_uom). Потребитель повторно
проверяет снимок. В нём нет доступного количества, версии и разрешения на резерв;
типовые ошибки дают InvalidAvailabilityPoolReservationSnapshotError.

create получает явный ID, этот снимок пула, InventoryItemStockSnapshot, основание,
requested_qty, created_at и необязательный expires_at. Выводит pool_id/key/единицу
из снимка, сверяет товар и единицу, проверяет шаг запроса, создаёт PENDING с нулём
удержания и версией 0. created_at=updated_at; срок, если задан, строго позже создания.
Создание не проверяет вместимость пула и не меняет его счётчик.

restore получает полный собственный состав без текущих снимков и системных часов.
Сохраняет исторические количества и ссылки, нормализует aware-время в UTC,
проверяет 0 <= reserved_qty <= requested_qty, положительность запроса, версию,
хронологию и соответствие статуса количеству. Исторический коэффициент пересчёта
не требуется: оба количества уже выражены в фиксированной базовой единице.

| Статус | Собственный инвариант |
| --- | --- |
| PENDING | reserved_qty=0, удержание ещё не получено |
| PARTIALLY_RESERVED | 0 < reserved_qty < requested_qty |
| RESERVED | reserved_qty=requested_qty |
| RELEASED | Терминальный статус, reserved_qty=0 |
| EXPIRED | Терминальный статус, reserved_qty=0, срок задан и updated_at >= expires_at |

- add_reserved(quantity, expected_version=..., inventory_item=..., updated_at=...)
  регистрирует положительное увеличение, кратное текущему шагу. Тот же товар,
  прежняя единица, текущая кратность запроса и удержания обязательны.
  Предел requested_qty не превышается. Получается PARTIALLY_RESERVED или RESERVED.
  При updated_at >= expires_at увеличение запрещено с StockReservationExpiredError.
- release(quantity, ...) проверяет текущий учётный снимок и положительное кратное
  количество не больше собственного reserved_qty. Уменьшает удержание; при нуле
  закрывает в RELEASED, иначе получает PARTIALLY_RESERVED. Разрешено и после срока.
  Открытое частично освобождённое обязательство можно пополнить до прежнего запроса.
- release_all(expected_version=..., updated_at=...) закрывает всё в RELEASED,
  включая PENDING без удержания. Текущие снимки товара/пула не требуются.
- expire(expected_version=..., updated_at=...) закрывает всё в EXPIRED только
  при заданном сроке и времени операции не раньше него. На точной границе закрытие
  разрешено. Без срока или раньше него — StockReservationExpirationError.
  Операция также доступна для PENDING с нулевым удержанием.

Все переходы повторно валидируют собственное состояние, требуют строгого совпадения
expected_version и открытого статуса. Закрытые состояния не меняются и повторно
не закрываются. Время изменения передаётся явно, нормализуется в UTC и не убывает;
равные моменты допустимы. Каждое изменение возвращает новый объект версии +1,
сохраняя ID, основание, привязку, единицу, запрос, срок и момент создания.
Полное закрытие/истечение проверяют собственное историческое состояние без
повторного применения текущих правил товара. При успехе и отказе источники неизменны.

Типовые ошибки: InvalidStockReservationValueError для типов и версии,
StockReservationVersionConflictError для конфликта версии, StockReservationStatusError
для матрицы/терминального статуса, StockReservationTimeError для времени,
InvalidStockReservationQuantityError для нуля запроса/изменения,
StockReservationLimitExceededError для превышения запроса,
StockReservationReleaseExceededError для превышения удержания,
StockReservationItemMismatchError и StockReservationUomMismatchError для контекста.
Сырые количества и нарушение шага отклоняются существующими ошибками количества.
Арифметика выполняется QuantityArithmeticPolicy с прежним пределом точности,
без внешнего Decimal context, округления и assert. SERIAL допускает резерв многих
экземпляров в PCS/шаге 1, не требуя выбора каждого serial_id для мягкого удержания.

expires_at — срок обязательства, независимый от годности товара; допустим даже
при ExpirationMode.NONE. Течение времени или чтение статуса не обнуляет удержание.
После срока активный исторический статус может сохраняться до явного expire/release;
новое удержание по такому объекту уже запрещено.

Общий запас проверяет только AvailabilityPool.reserve(). add_reserved() проверяет
собственный лимит и не вызывает пул. Будущий Application должен подготовить оба
новых состояния и сохранить их одним UoW с проверкой версий. При освобождении,
release_all или expire в пул возвращается именно уменьшение собственного удержания.
Если прежнее удержание нулевое, pool.release(0) вызывать не нужно.

Пример подготовки согласованных состояний в памяти. pool — пул версии 0 с 10 KG,
item — товар KG/шага 0.05, context — его текущий физический контекст из примера выше,
reservation_id — явный StockReservationIdVO. Каждое действие ниже в будущем
требует атомарного сохранения пары состояний; сейчас сохранения нет:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
from src.modules.inventory.domain.stock_reservation.value_object.source import ReservationSourceVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO

created_at = datetime(2026, 11, 4, 10, tzinfo=UTC)
deadline = created_at + timedelta(hours=1)
reservation = StockReservation.create(
    identifier=reservation_id,
    pool=pool.reservation_snapshot(),
    inventory_item=item.stock_snapshot(),
    source_ref=ReservationSourceVO("sales_order_line", "ORDER-1/1"),
    requested_qty=QuantityVO(Decimal("7")),
    created_at=created_at,
    expires_at=deadline,
)
current, current_pool = reservation, pool
for amount in ("4", "3"):
    quantity = QuantityVO(Decimal(amount))
    current_pool = current_pool.reserve(
        quantity, expected_version=current_pool.version, **context
    )
    current = current.add_reserved(
        quantity, expected_version=current.version,
        inventory_item=item.stock_snapshot(), updated_at=created_at,
    )
current_pool = current_pool.release(
    QuantityVO(Decimal("2")), expected_version=current_pool.version,
    inventory_item=item.stock_snapshot(),
)
current = current.release(
    QuantityVO(Decimal("2")), expected_version=current.version,
    inventory_item=item.stock_snapshot(), updated_at=created_at,
)
to_release = current.reserved_qty  # 5 KG этого обязательства.
expired = current.expire(expected_version=current.version, updated_at=deadline)
final_pool = current_pool.release(
    to_release, expected_version=current_pool.version,
    inventory_item=item.stock_snapshot(),
)
# reserved_qty: 0 → 4 → 7 → 5 → 0; итог EXPIRED/version=4.
# final_pool.reserved_qty=0; исходные pool/reservation и физические позиции прежние.
```

Domain-версия не выполняет блокировки и не дедуплицирует команды. Повтор с новой
актуальной версией может увеличить удержание ещё раз в пределах запроса; две ветви
одного исходного объекта тоже допустимы в памяти. SQL, глобальная идемпотентность,
планировщик истечения и Outbox остаются внешним слоям. Погашение при отгрузке,
связь со StockExecution и жёсткие allocation — следующие Domain-срезы.

## Изменения, восстановление и проверки

Агрегаты и Entity имеют явные фабрики `create/restore`.
`restore` принимает полный состав, проверяет инварианты и сохраняет ID.
Публичные доменные методы возвращают новый корректный экземпляр;
при успехе и при отказе исходное состояние остаётся неизменным.

Базовая единица, правила количества и режимы прослеживаемости задаются при создании.
Их изменение и защита использованных упаковок относятся к будущим контролируемым
сценариям. Ledger хранит пересчёт своей записи; при построении из исполнения
исходные количества и коэффициенты сохраняются в StockExecution, а итог — в базовой единице;
снимок пользовательской упаковки появится при расширении ввода строк исполнения.
У дочерних Entity нет самостоятельных write repositories.

Тесты находятся в `test/test_inventory_domain.py`,
`test/test_inventory_packaging_domain.py`, `test/test_inventory_uom_domain.py`,
`test/test_inventory_quantity_domain.py`, `test/test_inventory_stock_lot_domain.py`,
`test/test_inventory_stock_serial_domain.py`, `test/test_inventory_warehouse_domain.py`,
`test/test_inventory_stock_location_domain.py`, `test/test_inventory_stock_position_domain.py`,
`test/test_inventory_stock_quantity_domain.py`, `test/test_inventory_ledger_conversion_domain.py`,
`test/test_inventory_stock_posting_domain.py`, `test/test_inventory_stock_document_domain.py`,
`test/test_inventory_stock_execution_domain.py`, `test/test_inventory_execution_posting_domain.py`,
`test/test_inventory_posting_application_domain.py`, `test/test_inventory_availability_domain.py`,
`test/test_inventory_availability_pool_domain.py` и `test/test_inventory_stock_reservation_domain.py`.
Application, SQL-хранение, миграции, API и интеграционные события в этот срез не входят.
