from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SupplierFulfillmentOrderIdVO(EntityIdVO):
    """Идентификатор заказа на прямую поставку."""


class SupplierFulfillmentLineIdVO(EntityIdVO):
    """Идентификатор строки внутри заказа на прямую поставку."""


class SupplierFulfillmentShipmentIdVO(EntityIdVO):
    """Идентификатор факта прямой отправки поставщиком."""
