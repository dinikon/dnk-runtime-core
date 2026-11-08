# External Fulfillment

`SupplierFulfillmentOrder` хранит черновик прямой поставки покупателю от одного
поставщика и источника. `SupplierFulfillmentLine` соответствует одному целому
распределению плана. Разные строки на один и тот же товар сохраняют отдельные
ссылки на свои распределения.

## Основание и создание черновика

`FulfillmentPlan.supplier_order_basis_snapshot(allocation_ids=...)` передаёт ID,
версию и время плана, а также выбранные плановые распределения
`SUPPLIER_DROPSHIP`. Источник, предложение, товар, базовая единица, количество
и цена передаются по каждой строке. Допустимы зафиксированный план и смешанный
план после подтверждения или исполнения складской части.

`SupplierFulfillmentOrder.create_from_plan()` принимает снимки принимающего
контекста. Политика создания проверяет активный источник с режимом DROPSHIP,
принадлежность предложений одному поставщику, совпадение источника, товара и
единицы каждой строки, а также точное покрытие выбранных распределений
привязками ID строк. Запрошенное количество и цена с валютой копируются из плана.
Текущая цена предложения может измениться после планирования.

Корень фиксирует статус `DRAFT`, версию `0`, основание плана, поставщика, источник,
адрес и время создания в UTC. Адрес хранит двухбуквенный код страны, город, строку
адреса и опциональный индекс. Restore проверяет собственные поля и уникальность
строк и распределений по сохранённым данным.

## Пример из смешанного плана

Продолжение [примера 3 + 4 PCS в Inventory](inventory.md#ручное-распределение-supplier_dropship).
Выбираем только внешние 4 PCS и переводим снимки в контракты External Fulfillment.

```python
from src.modules.external_fulfillment.domain.aggregate import SupplierFulfillmentOrder
from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot, SupplierFulfillmentOfferSnapshot,
    SupplierFulfillmentPlanBasisSnapshot, SupplierFulfillmentSourceSnapshot,
)
from src.modules.external_fulfillment.domain.value_object.delivery_address import SupplierDeliveryAddressVO
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO, SupplierFulfillmentOrderIdVO,
)
from src.modules.external_fulfillment.domain.value_object.line_binding import SupplierFulfillmentLineBindingVO
from src.modules.external_fulfillment.domain.value_object.plan_ref import SupplierFulfillmentPlanRefVO
from src.modules.external_fulfillment.domain.value_object.quantity import SupplierFulfillmentQuantityVO
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentAllocationIdVO, ExternalFulfillmentPlanIdVO, ExternalInventoryItemIdVO,
    ExternalSupplierIdVO, ExternalSupplierOfferIdVO, ExternalSupplierSourceIdVO,
)
from src.modules.external_fulfillment.domain.value_object.uom_code import SupplierFulfillmentUomCodeVO

exported = mixed_confirmed.supplier_order_basis_snapshot(allocation_ids=(external_id,))
(selected,) = exported.allocations
row = SupplierFulfillmentAllocationSnapshot(
    allocation_id=ExternalFulfillmentAllocationIdVO(selected.id.uuid),
    inventory_item_id=ExternalInventoryItemIdVO(selected.inventory_item_id.uuid),
    supplier_source_id=ExternalSupplierSourceIdVO(selected.source.supplier_source_id.uuid),
    supplier_offer_id=ExternalSupplierOfferIdVO(selected.source.supplier_offer_id.uuid),
    base_uom=SupplierFulfillmentUomCodeVO(selected.base_uom.value),
    quantity=SupplierFulfillmentQuantityVO(selected.quantity.value),
    quoted_price=selected.quoted_purchase_price,
)
basis = SupplierFulfillmentPlanBasisSnapshot(
    SupplierFulfillmentPlanRefVO(ExternalFulfillmentPlanIdVO(exported.plan_id.uuid), exported.plan_version),
    exported.plan_updated_at,
    (row,),
)
source = SupplierFulfillmentSourceSnapshot(
    row.supplier_source_id, ExternalSupplierIdVO(supplier_option.source_supplier_id.uuid),
    supplier_option.source_is_active, supplier_option.source_supports_dropship,
)
offer = SupplierFulfillmentOfferSnapshot(
    row.supplier_offer_id, ExternalSupplierIdVO(supplier_option.offer_supplier_id.uuid),
    ExternalSupplierSourceIdVO(supplier_option.offer_source_id.uuid),
    ExternalInventoryItemIdVO(supplier_option.inventory_item_id.uuid),
    SupplierFulfillmentUomCodeVO(supplier_option.base_uom.value), supplier_option.offer_is_active,
)
supplier_order = SupplierFulfillmentOrder.create_from_plan(
    identifier=SupplierFulfillmentOrderIdVO(UUID(int=725)),
    basis=basis, source=source, offers=(offer,),
    line_bindings=(SupplierFulfillmentLineBindingVO(row.allocation_id, SupplierFulfillmentLineIdVO(UUID(int=726))),),
    delivery_address=SupplierDeliveryAddressVO("UA", "Київ", "вул. Тестова, 1", "01001"),
    created_at=exported.plan_updated_at,
)
# DRAFT v0, одна строка на 4 PCS по 120.05 UAH за PCS.
```

Тесты находятся в `test/test_supplier_fulfillment_order_domain.py`.

## Закрепление и подготовка запроса поставщику

`draft_snapshot()` передаёт весь черновик для закрепления. План сверяет текущий
спрос и состояние выбранных распределений с черновиком. Он повторно проверяет
учётный шаг, активность и режим источника, принадлежность предложения, цену,
минимум и коммерческую кратность по актуальным снимкам.

`assign_supplier_order()` закрепляет все выбранные строки одной версией плана.
Закрепление фиксирует шаг, минимум и кратность и защищает строки от второго заказа и
обычной отмены. Если складская часть была исполнена после создания черновика,
можно использовать новую версию плана с теми же внешними строками. При смене
цены выбор пересматривается явно.

`request()` сверяет закреплённый состав, ID заказа и строк, поставщика и версии.
Заказ сохраняет правила количества по каждой строке.
Успешный переход даёт REQUESTED версии 1 с `requested_at` в UTC. Распределение
сохраняет PLANNED до подтверждения поставщика.

Продолжаем пример с черновиком на 4 PCS. Закрепляем его единственную строку,
переводим подтверждение закрепления на границе модулей и готовим запрос.

```python
from src.modules.external_fulfillment.domain.assignment_snapshot import SupplierFulfillmentAssignmentSnapshot
from src.modules.external_fulfillment.domain.value_object.quantity_terms import SupplierFulfillmentQuantityTermsVO
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderDraftLineSnapshot, SupplierOrderDraftSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOrderIdVO, FulfillmentSupplierOrderLineIdVO,
)

external_draft = supplier_order.draft_snapshot()
inventory_draft = SupplierOrderDraftSnapshot(
    order_id=FulfillmentSupplierOrderIdVO(external_draft.order_id.uuid),
    order_version=external_draft.order_version,
    supplier_id=FulfillmentSupplierIdVO(external_draft.supplier_id.uuid),
    plan_id=FulfillmentPlanIdVO(external_draft.plan_ref.plan_id.uuid),
    source_plan_version=external_draft.plan_ref.plan_version,
    created_at=external_draft.created_at,
    lines=(SupplierOrderDraftLineSnapshot(
        FulfillmentSupplierOrderLineIdVO(external_draft.line_bindings[0].line_id.uuid),
        selected,
    ),),
)
assigned_plan = mixed_confirmed.assign_supplier_order(
    inventory_draft, demand=demand, inventory_items=(item,), supplier_options=(supplier_option,),
    expected_version=mixed_confirmed.version, updated_at=confirmed_at,
)
assigned = assigned_plan.supplier_order_assignment_snapshot(order_id=inventory_draft.order_id)
(assigned_line,) = assigned.lines
selected_row = assigned_line.allocation
assigned_row = SupplierFulfillmentAllocationSnapshot(
    allocation_id=ExternalFulfillmentAllocationIdVO(selected_row.id.uuid),
    inventory_item_id=ExternalInventoryItemIdVO(selected_row.inventory_item_id.uuid),
    supplier_source_id=ExternalSupplierSourceIdVO(selected_row.source.supplier_source_id.uuid),
    supplier_offer_id=ExternalSupplierOfferIdVO(selected_row.source.supplier_offer_id.uuid),
    base_uom=SupplierFulfillmentUomCodeVO(selected_row.base_uom.value),
    quantity=SupplierFulfillmentQuantityVO(selected_row.quantity.value),
    quoted_price=selected_row.quoted_purchase_price,
)
proof = SupplierFulfillmentAssignmentSnapshot(
    order_id=SupplierFulfillmentOrderIdVO(assigned.order_id.uuid),
    order_version=assigned.order_version,
    supplier_id=ExternalSupplierIdVO(assigned.supplier_id.uuid),
    source_plan_version=assigned.source_plan_version,
    assigned_at=assigned.assigned_at,
    basis=SupplierFulfillmentPlanBasisSnapshot(
        SupplierFulfillmentPlanRefVO(ExternalFulfillmentPlanIdVO(assigned.plan_id.uuid), assigned.plan_version),
        assigned.plan_updated_at, (assigned_row,),
    ),
    line_bindings=(SupplierFulfillmentLineBindingVO(
        assigned_row.allocation_id, SupplierFulfillmentLineIdVO(assigned_line.line_id.uuid),
    ),),
    quantity_terms=tuple(
        (SupplierFulfillmentLineIdVO(line_id.uuid),
         SupplierFulfillmentQuantityTermsVO(rule.step, rule.minimum, rule.multiple))
        for line_id, rule in assigned.quantity_terms
    ),
)
requested = supplier_order.request(
    proof, expected_version=supplier_order.version, requested_at=confirmed_at,
)
# REQUESTED v1. Закреплённая внешняя строка плана остаётся PLANNED.
```

REQUESTED фиксирует локальную готовность запроса. Будущий Application-сценарий
сохранит план, внешний заказ и Outbox вместе, а адаптер отправит запрос после
commit. Снятие закрепления относится к следующим срезам.

Тесты находятся в `test/test_supplier_fulfillment_request_domain.py`.

## Полное подтверждение поставщиком

`confirm()` принимает все строки подготовленного запроса. Поставщик подтверждает
исходное количество и цену в исходной валюте по каждой строке. Заказ сохраняет
подтверждённые значения отдельно, переходит в CONFIRMED версии 2 и фиксирует
время подтверждения в UTC.

План регистрирует полную группу из снимка ответа одной версией. Точный повтор
с тем же временем ответа сохраняет состояние, даже если строки пришли в другом
порядке. Изменение состава, условий или времени уже сохранённого ответа
отклоняется.

Продолжаем пример с запросом на 4 PCS. Поставщик подтвердил полное количество
по 120.05 UAH за PCS.

```python
from src.modules.external_fulfillment.domain.value_object.line_confirmation import (
    SupplierFulfillmentLineConfirmationVO,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderConfirmationSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_basis_snapshot import (
    SupplierOrderAllocationSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_confirmation import (
    FulfillmentSupplierOrderConfirmationRefVO,
)

(requested_line,) = requested.lines
supplier_confirmed = requested.confirm(
    (SupplierFulfillmentLineConfirmationVO(
        requested_line.id, SupplierFulfillmentQuantityVO(Decimal("4")),
        MoneyVO(Decimal("120.05"), CurrencyVO("UAH")),
    ),),
    expected_version=requested.version,
    confirmed_at=confirmed_at,
)

def inventory_reply_lines(reply):
    bindings = {binding.allocation_id: binding.line_id for binding in reply.line_bindings}
    return tuple(
        SupplierOrderDraftLineSnapshot(
            FulfillmentSupplierOrderLineIdVO(bindings[row.allocation_id].uuid),
            SupplierOrderAllocationSnapshot(
                id=FulfillmentAllocationIdVO(row.allocation_id.uuid),
                source=SupplierDropshipSourceRefVO(
                    FulfillmentSupplierSourceIdVO(row.supplier_source_id.uuid),
                    FulfillmentSupplierOfferIdVO(row.supplier_offer_id.uuid),
                ),
                inventory_item_id=InventoryItemIdVO(row.inventory_item_id.uuid),
                base_uom=UomCodeVO(row.base_uom.value),
                quantity=QuantityVO(row.quantity.value),
                quoted_purchase_price=row.quoted_price,
            ),
        )
        for row in reply.allocations
    )


def inventory_confirmation(reply):
    return SupplierOrderConfirmationSnapshot(
        order_id=FulfillmentSupplierOrderIdVO(reply.order_id.uuid),
        supplier_id=FulfillmentSupplierIdVO(reply.supplier_id.uuid),
        plan_id=FulfillmentPlanIdVO(reply.plan_ref.plan_id.uuid),
        source_plan_version=reply.plan_ref.plan_version,
        confirmation=FulfillmentSupplierOrderConfirmationRefVO(
            reply.order_version, reply.requested_at, reply.confirmed_at,
        ),
        lines=inventory_reply_lines(reply),
        confirmed_quantities=tuple(
            (FulfillmentSupplierOrderLineIdVO(line.line_id.uuid), QuantityVO(line.quantity.value))
            for line in reply.line_confirmations
        ),
    )


confirmation = inventory_confirmation(supplier_confirmed.confirmation_snapshot())
fully_confirmed = assigned_plan.register_supplier_confirmation(
    confirmation, expected_version=assigned_plan.version, updated_at=confirmed_at,
)
# План CONFIRMED. Внешняя строка CONFIRMED с fulfilled_qty = 0 PCS.
```

Если склад уже отгрузил свои 3 PCS, регистрация ответа сохраняет
PARTIALLY_FULFILLED и подтверждает все действующие распределения.
Application сохранит оба агрегата и Outbox одной транзакцией.

## Частичное подтверждение поставщиком

В другом варианте того же примера поставщик принимает 2 из запрошенных 4 PCS.
Подтверждённое количество соответствует зафиксированным минимуму 2 и кратности 2.
Ответ охватывает все строки запроса, включая строки с нулевым количеством и
пустой ценой. При частичном ответе заказ хранит PARTIALLY_CONFIRMED версии 2.
Для сохранённого REQUESTED без правил количества доступно полное подтверждение.

```python
partial_order = requested.confirm(
    (SupplierFulfillmentLineConfirmationVO(
        requested_line.id, SupplierFulfillmentQuantityVO(Decimal("2")),
        requested_line.quoted_price,
    ),),
    expected_version=requested.version,
    confirmed_at=confirmed_at,
)
partial_plan = assigned_plan.register_supplier_confirmation(
    inventory_confirmation(partial_order.confirmation_snapshot()),
    expected_version=assigned_plan.version,
    updated_at=confirmed_at,
)
supplier_allocation = partial_plan.get_allocation(external_id)
# quantity = 4 PCS, supplier_confirmed_qty = 2 PCS, fulfilled_qty = 0 PCS.
free_quantity = partial_plan.remaining_to_allocate(row_ref, demand=demand)
# free_quantity = 2 PCS.
```

Положительное количество остаётся обязательством поставщика. Строка с нулём
остаётся в плане со статусом CANCELLED и ссылкой на окончательный ответ.
Неподтверждённое количество доступно для ручного допланирования. В примере все
действующие распределения подтверждены, и при этом 2 PCS спроса ещё свободны.

## Полный отказ поставщика

`reject()` регистрирует явный отказ по всему REQUESTED и сохраняет REJECTED
версии 2. Время отказа хранится в UTC. Переданная причина остаётся в заказе.
Исходные строки и цены доступны для аудита. Ожидание ответа сохраняет REQUESTED.

В третьем варианте поставщик отказал по запросу на 4 PCS.

```python
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderRejectionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_rejection import (
    FulfillmentSupplierOrderRejectionRefVO,
)

rejected_order = requested.reject(
    expected_version=requested.version,
    rejected_at=confirmed_at,
    reason="Товар недоступен",
)
rejection = rejected_order.rejection_snapshot()
inventory_rejection = SupplierOrderRejectionSnapshot(
    order_id=FulfillmentSupplierOrderIdVO(rejection.order_id.uuid),
    supplier_id=FulfillmentSupplierIdVO(rejection.supplier_id.uuid),
    plan_id=FulfillmentPlanIdVO(rejection.plan_ref.plan_id.uuid),
    source_plan_version=rejection.plan_ref.plan_version,
    rejection=FulfillmentSupplierOrderRejectionRefVO(
        rejection.order_version, rejection.requested_at, rejection.rejected_at,
    ),
    lines=inventory_reply_lines(rejection),
)
rejected_plan = assigned_plan.register_supplier_rejection(
    inventory_rejection,
    expected_version=assigned_plan.version,
    updated_at=confirmed_at,
)
free_after_rejection = rejected_plan.remaining_to_allocate(row_ref, demand=demand)
# План CONFIRMED по складским 3 PCS. Все 4 PCS поставщика свободны.
```

План закрывает всю закреплённую группу одной версией. Строки сохраняют
CANCELLED, исходные количества и ссылку на отказ. Если отказ закрывает
последнее распределение к исполнению, план переходит в AWAITING_ALLOCATION.
При допланировании требуется свежий снимок спроса. Если склад завершил
исполнение уже после отказа, FULFILLED с историей отказа также допускает
допланирование по актуальному спросу. Точный повтор отказа сохраняет состояние
и после добавления новых строк.

Application сохранит внешний заказ, план и Outbox одной транзакцией.

## Полная внешняя отгрузка

`SupplierFulfillmentOrder.register_shipment()` принимает один факт отправки.
В нём есть ID, время и опциональные перевозчик и ТТН. Строки факта содержат
ровно все положительно подтверждённые количества. После отправки заказ
становится SHIPPED версии 3. Исходные количества, подтверждение версии 2 и
фактически отгруженные количества сохраняются отдельно.

Продолжаем ветку полного подтверждения 4 PCS.

```python
from src.modules.external_fulfillment.domain.value_object.identifier import SupplierFulfillmentShipmentIdVO
from src.modules.external_fulfillment.domain.value_object.shipment import (
    SupplierFulfillmentShipmentLineVO, SupplierFulfillmentShipmentVO,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_shipment_snapshot import SupplierOrderShipmentSnapshot
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import FulfillmentSupplierShipmentIdVO
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_shipment import FulfillmentSupplierOrderShipmentRefVO

supplier_shipped = supplier_confirmed.register_shipment(
    SupplierFulfillmentShipmentVO(
        SupplierFulfillmentShipmentIdVO(UUID(int=727)), confirmed_at,
        carrier_id="carrier-a", tracking_number="TTN-123",
    ),
    (SupplierFulfillmentShipmentLineVO(
        requested_line.id, SupplierFulfillmentQuantityVO(Decimal("4")),
    ),),
    expected_version=supplier_confirmed.version,
)
fact = supplier_shipped.shipment_snapshot()
inventory_shipment = SupplierOrderShipmentSnapshot(
    confirmation=inventory_confirmation(fact.confirmation),
    shipment=FulfillmentSupplierOrderShipmentRefVO(
        FulfillmentSupplierShipmentIdVO(fact.shipment.id.uuid),
        fact.order_version, fact.shipment.shipped_at,
    ),
    shipped_quantities=tuple(
        (FulfillmentSupplierOrderLineIdVO(line.line_id.uuid), QuantityVO(line.quantity.value))
        for line in fact.lines
    ),
)
after_supplier_shipment = fully_confirmed.register_supplier_shipment(
    inventory_shipment, expected_version=fully_confirmed.version, updated_at=confirmed_at,
)
# Внешняя строка FULFILLED на 4 PCS, смешанный план PARTIALLY_FULFILLED.
```

После отгрузки складских 3 PCS смешанный план становится FULFILLED. Факты
можно зарегистрировать в любом порядке. Если поставщик подтвердил 2 из 4 PCS,
отправка 2 PCS закрывает его обязательство, а ещё 2 PCS остаются доступны
для допланирования по актуальному спросу.

Точный повтор факта сохраняет версии. Внешняя отправка обновляет исполнение
плана, а складские движения создаются в собственном маршруте через Shipment.
Отправка несколькими партиями и регистрация доставки относятся к следующим
срезам.
