# Inventory: Domain-модель товара, складов и физического журнала

Модуль `inventory` содержит самостоятельные корни `InventoryItem`,
`PackagingType`, `StockLot`, `StockSerial`, `Warehouse`, `StockLocation`, `StockPosition`
и `StockPosting`
в `domain/inventory_item/`, `domain/packaging_type/`, `domain/stock_lot/`,
`domain/stock_serial/`, `domain/warehouse/`, `domain/stock_location/`, `domain/stock_position/`
и `domain/stock_posting/`. В `domain/stock_execution/` пока существует только
StockExecutionIdVO для типизированной ссылки на будущее исполнение, без самого агрегата.
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
Правила приёмки просроченного товара, FEFO и расчёт доступности реализуются
в последующих складских сценариях; дата операции для них должна передаваться явно.

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
проверки дат поступления и доступность для продажи относятся к последующим Policy
операций. on_hand_qty не уменьшается при резервировании; доступное количество
будет отдельным расчётом. Изменение version в Domain не заменяет идемпотентность
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
StockPosting и новое состояние позиции в одной транзакции. SQL, API и исполнение
документов пока отсутствуют; Domain-модель журнала описана ниже.
SupplierAvailability остаётся внешним наблюдением и не создаёт физические позиции.

## Неизменяемый журнал физических движений

StockPosting — самостоятельный Aggregate Root завершённого проведения. Он владеет
неизменяемыми дочерними StockLedgerEntry; собственных репозиториев у записей нет.
Черновик, согласование и редактирование строк будут ответственностью StockDocument
и StockExecution. У StockPosting нет методов редактирования, удаления и установки статуса.

| Поле StockPosting | Тип |
| --- | --- |
| id | StockPostingIdVO |
| source | PostingSourceVO с execution_id: StockExecutionIdVO |
| operation_type | StockOperationType |
| posted_at | datetime с часовым поясом, нормализованный в UTC |
| entries | Непустой tuple[StockLedgerEntry, ...] |
| reversal_of_id | StockPostingIdVO или None |

ID и время передаются явно; Domain не генерирует их и не вызывает часы.
StockExecutionIdVO — только контракт идентичности. Существование исполнения,
принадлежность tenant и запрет повторного проведения проверит будущий сценарий.

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
Её содержимое и идентичность потребуют отдельного снимка в будущем StockExecution.

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

## Изменения, восстановление и проверки

Агрегаты и Entity имеют явные фабрики `create/restore`.
`restore` принимает полный состав, проверяет инварианты и сохраняет ID.
Публичные доменные методы возвращают новый корректный экземпляр;
при успехе и при отказе исходное состояние остаётся неизменным.

Базовая единица, правила количества и режимы прослеживаемости задаются при создании.
Их изменение и защита использованных упаковок относятся к будущим контролируемым
сценариям. Ledger уже сохраняет снимок исходного количества и системного пересчёта;
снимок пользовательской упаковки появится вместе со строками исполнения.
У дочерних Entity нет самостоятельных write repositories.

Тесты находятся в `test/test_inventory_domain.py`,
`test/test_inventory_packaging_domain.py`, `test/test_inventory_uom_domain.py`,
`test/test_inventory_quantity_domain.py`, `test/test_inventory_stock_lot_domain.py`,
`test/test_inventory_stock_serial_domain.py`, `test/test_inventory_warehouse_domain.py`,
`test/test_inventory_stock_location_domain.py`, `test/test_inventory_stock_position_domain.py`,
`test/test_inventory_stock_quantity_domain.py`, `test/test_inventory_ledger_conversion_domain.py`
и `test/test_inventory_stock_posting_domain.py`.
Application, SQL-хранение, миграции, API и интеграционные события в этот срез не входят.
