from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FulfillmentSupplierIdVO(EntityIdVO):
    """Ссылка плана исполнения на поставщика."""


class FulfillmentSupplierSourceIdVO(EntityIdVO):
    """Ссылка плана исполнения на источник поставщика."""


class FulfillmentSupplierOfferIdVO(EntityIdVO):
    """Ссылка плана исполнения на коммерческое предложение поставщика."""


class FulfillmentSupplierOrderIdVO(EntityIdVO):
    """Ссылка плана исполнения на внешний заказ поставщику."""


class FulfillmentSupplierOrderLineIdVO(EntityIdVO):
    """Ссылка распределения на строку внешнего заказа."""


class FulfillmentSupplierShipmentIdVO(EntityIdVO):
    """Ссылка плана исполнения на внешнюю отправку поставщика."""
