# Supplier Sourcing

`SupplierSource` описывает один внешний источник поставки, например склад или
канал отгрузки. Один контрагент может иметь несколько источников с разными
режимами, сроками и настройками актуальности. Карточкой контрагента владеет CRM.
`SupplierIdVO` хранит его идентичность как ссылку в Supplier Sourcing. Проверка
существования контрагента относится к будущему Application-сценарию создания.

## Карточка источника

| Поле | Тип и правило |
| --- | --- |
| `id` | `SupplierSourceIdVO`, постоянный идентификатор источника |
| `supplier_id` | `SupplierIdVO`, постоянная принадлежность поставщику |
| `name` | `SupplierSourceNameVO`, непустое отображаемое название |
| `external_warehouse_code` | `ExternalWarehouseCodeVO` или `None`, код в системе поставщика |
| `fulfillment_modes` | Непустой `frozenset[SupplierFulfillmentMode]` |
| `is_active` | Административная активность |
| `default_lead_time` | `SupplierLeadTimeVO` с неотрицательным `timedelta`; ноль означает немедленную поставку |
| `stock_update_policy` | `SupplierStockUpdatePolicyVO` с положительным TTL и двумя правилами обработки данных |

Название и внешний код обрезаются по краям. Значения сохраняют регистр.
Для внешнего кода сохраняются и ведущие нули. Отсутствие кода задаётся через `None`.

`create()` создаёт активный источник, `restore()` восстанавливает сохранённое
состояние. `rename()`, `change_external_warehouse_code()`, `configure_fulfillment()`
и `change_stock_update_policy()` возвращают новую версию карточки с теми же ID
источника и поставщика. `activate()` и `deactivate()` допускают повторный вызов.
`ensure_supports(mode)` проверяет активность и разрешённый режим. `DROPSHIP`
означает прямую поставку покупателю, `PURCHASE_TO_WAREHOUSE` — поставку на наш
склад.

## Настройки актуальности

TTL определяет длительность актуальности наблюдения. `StaleStockBehavior.MARK_UNKNOWN`
означает эффективное неизвестное наличие после устаревания. `BLOCK_AUTOMATIC_SALE`
блокирует автоматическую продажу по устаревшим данным. `MissingSkuBehavior.KEEP_LAST`
сохраняет последнее наблюдение, а `MARK_UNKNOWN` задаёт неизвестное наличие для SKU,
который отсутствует в успешно полученном полном снимке. Настройки хранятся на
источнике, а их применение относится к будущим срезам SupplierAvailability и импорта.

## Пример двух источников

Один поставщик отправляет заказы покупателям из Киева за день и привозит товар
на наш склад из Львова за три дня.

```python
from datetime import timedelta
from uuid import UUID

from src.modules.supplier_sourcing.domain.supplier_source.aggregate import SupplierSource
from src.modules.supplier_sourcing.domain.supplier_source.value_object.external_warehouse_code import (
    ExternalWarehouseCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import SupplierSourceIdVO
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import SupplierSourceNameVO
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    MissingSkuBehavior,
    StaleStockBehavior,
    SupplierStockUpdatePolicyVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import SupplierLeadTimeVO
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO

supplier = SupplierIdVO(UUID(int=100))
kyiv = SupplierSource.create(
    identifier=SupplierSourceIdVO(UUID(int=101)),
    supplier_id=supplier,
    name=SupplierSourceNameVO("Склад Киев"),
    external_warehouse_code=ExternalWarehouseCodeVO("001-Kyiv"),
    fulfillment_modes=frozenset({SupplierFulfillmentMode.DROPSHIP}),
    default_lead_time=SupplierLeadTimeVO(timedelta(days=1)),
    stock_update_policy=SupplierStockUpdatePolicyVO(
        ttl=timedelta(hours=2),
        stale_behavior=StaleStockBehavior.BLOCK_AUTOMATIC_SALE,
        missing_sku_behavior=MissingSkuBehavior.KEEP_LAST,
    ),
)
lviv = SupplierSource.create(
    identifier=SupplierSourceIdVO(UUID(int=102)),
    supplier_id=supplier,
    name=SupplierSourceNameVO("Склад Львов"),
    fulfillment_modes=frozenset({SupplierFulfillmentMode.PURCHASE_TO_WAREHOUSE}),
    default_lead_time=SupplierLeadTimeVO(timedelta(days=3)),
    stock_update_policy=SupplierStockUpdatePolicyVO(
        ttl=timedelta(hours=6),
        stale_behavior=StaleStockBehavior.MARK_UNKNOWN,
        missing_sku_behavior=MissingSkuBehavior.MARK_UNKNOWN,
    ),
)
kyiv.ensure_supports(SupplierFulfillmentMode.DROPSHIP)
lviv.ensure_supports(SupplierFulfillmentMode.PURCHASE_TO_WAREHOUSE)
kyiv_inactive = kyiv.deactivate()
```

Региональные правила `SourceDeliveryRule`, импорт, хранение и API добавляются по
[плану Inventory и внешних поставок](../plan/inventory.md).

Тесты находятся в `test/test_supplier_source_domain.py`.

## Коммерческое предложение SupplierOffer

`SupplierOffer` связывает внешний SKU с одним `InventoryItem`. Несколько
предложений на товар могут различаться поставщиками, источниками, прайс-листами,
ценами и коммерческими условиями.

| Поле | Назначение |
| --- | --- |
| `id`, `supplier_id`, `inventory_item_id` | Идентичность предложения и ссылки на поставщика и товар |
| `supplier_sku` | Внешний SKU с сохранением регистра и ведущих нулей |
| `base_uom` | Базовая единица товара из снимка создания |
| `price_list_id`, `source_id` | Опциональные ссылки на прайс-лист и конкретный источник |
| `purchase_price` | Неотрицательный `MoneyVO` за одну базовую единицу |
| `min_order_qty`, `order_multiple` | Положительные коммерческие количества в базовой единице |
| `lead_time`, `priority`, `is_active` | Срок поставки, целый приоритет от нуля и административная активность |

Фабрика принимает снимок товара и, при ограничении конкретным источником,
его `SupplierSourceIdentitySnapshot`. Источник должен принадлежать поставщику
предложения. Активация источника и выбор его режима проверяются при использовании
самого источника. `restore()` проверяет сохранённые поля предложения.

`change_purchase_price()` и `configure_order_terms()` возвращают предложение
с обновлёнными условиями и прежними ссылками. `ensure_order_quantity(quantity, uom=...)`
принимает количество в базовой единице активного предложения и проверяет минимум
и точную кратность от нуля. При минимуме 10 PCS и кратности 6 PCS первый допустимый
заказ равен 12 PCS. Складской шаг товара проверяется отдельно в Inventory.

### Два предложения на один товар

Для первого предложения используем поставщика и источник `kyiv` из предыдущего
примера. Снимок на границе модуля передаёт идентификатор и единицу из Inventory.

```python
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import InventoryItemIdVO
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.supplier_sourcing.domain.supplier_offer.aggregate import SupplierOffer
from src.modules.supplier_sourcing.domain.supplier_offer.item_snapshot import SupplierOfferItemSnapshot
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.identifier import SupplierOfferIdVO
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.order_quantity import SupplierOrderQuantityVO
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.supplier_sku import SupplierSkuVO
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import SupplierOfferUomCodeVO
from src.modules.supplier_sourcing.domain.value_object.inventory_item_id import SupplierInventoryItemIdVO

oil = InventoryItem.create(
    identifier=InventoryItemIdVO(UUID(int=200)),
    sku=SkuVO("oil-1l"),
    base_uom=UomCodeVO("PCS"),
    quantity_rules=QuantityRulesVO(Decimal(1)),
)
stock = oil.stock_snapshot()
item = SupplierOfferItemSnapshot(
    inventory_item_id=SupplierInventoryItemIdVO(stock.inventory_item_id.uuid),
    base_uom=SupplierOfferUomCodeVO(stock.base_uom.value),
)
first = SupplierOffer.create(
    identifier=SupplierOfferIdVO(UUID(int=201)),
    supplier_id=supplier,
    item=item,
    source=kyiv.identity_snapshot(),
    supplier_sku=SupplierSkuVO("001-Oil"),
    purchase_price=MoneyVO(Decimal("120.05"), CurrencyVO("UAH")),
    min_order_qty=SupplierOrderQuantityVO(Decimal(10)),
    order_multiple=SupplierOrderQuantityVO(Decimal(6)),
    lead_time=SupplierLeadTimeVO(timedelta(days=1)),
    priority=0,
)
second = SupplierOffer.create(
    identifier=SupplierOfferIdVO(UUID(int=202)),
    supplier_id=SupplierIdVO(UUID(int=203)),
    item=item,
    supplier_sku=SupplierSkuVO("OIL-1L-X"),
    purchase_price=MoneyVO(Decimal("3.25"), CurrencyVO("USD")),
    min_order_qty=SupplierOrderQuantityVO(Decimal(4)),
    order_multiple=SupplierOrderQuantityVO(Decimal(2)),
    lead_time=SupplierLeadTimeVO(timedelta(days=3)),
    priority=1,
)
first.ensure_order_quantity(SupplierOrderQuantityVO(Decimal(12)), uom=item.base_uom)
second.ensure_order_quantity(SupplierOrderQuantityVO(Decimal(4)), uom=item.base_uom)
```

Этот срез хранит текущую цену. `OfferPriceTier` и `SupplierOfferPriceRevision`
добавляются отдельными срезами. Тесты находятся в `test/test_supplier_offer_domain.py`.

## Текущее наблюдение SupplierAvailability

`SupplierAvailability` хранит последнее принятое наблюдение для одной пары
«предложение + источник». Фабрика принимает `SupplierOfferAvailabilitySnapshot`
и `SupplierSourceAvailabilitySnapshot`, проверяет общего поставщика, ограничение
предложения по источнику и совпадение единицы наблюдения с базовой единицей товара.
ID пары и единица фиксируются при создании.

| Тип наблюдения | Количество | Статус |
| --- | --- | --- |
| `EXACT_QUANTITY` | Положительное | `IN_STOCK` |
| `EXACT_QUANTITY` | Ноль | `OUT_OF_STOCK` или `BACKORDER` |
| `LOWER_BOUND` | Положительное | `IN_STOCK` |
| `LOWER_BOUND` | Ноль | `UNKNOWN` |
| `STATUS_ONLY` | `None` | `IN_STOCK`, `OUT_OF_STOCK` или `BACKORDER` |
| `UNKNOWN` | `None` | `UNKNOWN` |

Количества хранятся как конечный `Decimal` без округления. Точный ноль сообщает
об отсутствии наличия, нулевая нижняя граница оставляет фактическое количество
неизвестным. Статус `BACKORDER` сообщает о возможности заказа с ожиданием.
Данные отражают сообщение поставщика. Подтверждение прямой поставки относится
к будущему сценарию External Fulfillment.

`create()` устанавливает версию 0. `record_observation()` требует актуальную
версию и время получения позже текущего. При двух известных отметках поставщика
метка должна быть монотонной. Одинаковая метка допускается для тех же данных,
поэтому новый опрос с прежним содержимым может обновить срок. Точный повтор
наблюдения и обоих времён с актуальной версией сохраняет прежнее состояние.
При отсутствии одной из отметок поставщика порядок определяется по `received_at`.

`expires_at` рассчитывается при приёме как `received_at + TTL`. Все моменты
нормализуются в UTC, а `restore()` сохраняет зафиксированный срок. Оценка
`evaluate(as_of=..., source=...)` принимает явно заданное время начиная с момента
получения. При `as_of >= expires_at` она возвращает эффективный `UNKNOWN`.
С политикой `BLOCK_AUTOMATIC_SALE` результат также содержит
`automatic_sale_blocked=True`. Исходное наблюдение остаётся в агрегате.

### Наблюдение до и после TTL

Используем предложение `first` и источник `kyiv` из предыдущих примеров.
Источник сообщает о 15 PCS. Наблюдение получено в 12:00 UTC, срок истекает в
14:00 UTC. На этой границе результат оценки становится неизвестным и включает
признак блокировки автоматической продажи из политики источника.

```python
from datetime import UTC, datetime

from src.modules.supplier_sourcing.domain.supplier_availability.aggregate import SupplierAvailability
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.identifier import (
    SupplierAvailabilityIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.observation import (
    AvailabilityStatus,
    AvailabilityType,
    SupplierAvailabilityObservationVO,
)

received = datetime(2026, 11, 7, 12, tzinfo=UTC)
availability = SupplierAvailability.create(
    identifier=SupplierAvailabilityIdVO(UUID(int=204)),
    offer=first.availability_snapshot(),
    source=kyiv.availability_snapshot(),
    observation=SupplierAvailabilityObservationVO(
        AvailabilityType.EXACT_QUANTITY, AvailabilityStatus.IN_STOCK, Decimal(15)
    ),
    uom=item.base_uom,
    received_at=received,
    source_updated_at=received - timedelta(minutes=10),
)
fresh = availability.evaluate(
    as_of=received + timedelta(hours=1), source=kyiv.availability_snapshot()
)
stale = availability.evaluate(
    as_of=availability.expires_at, source=kyiv.availability_snapshot()
)
# fresh.observation.quantity == Decimal(15)
# stale.observation.quantity is None; stale.automatic_sale_blocked == True
# availability.observation.quantity == Decimal(15)
```

История наблюдений, дедупликация пакетов, обработка пропущенного SKU и
ограничение уникальности пары в хранилище относятся к последующим срезам.
Тесты находятся в `test/test_supplier_availability_domain.py`.
