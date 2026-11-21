from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ExternalSupplierIdVO(EntityIdVO):
    """UUID контрагента внутри локальной составной ссылки внешнего исполнения."""


class ExternalSupplierSourceIdVO(EntityIdVO):
    """Ссылка внешнего исполнения на источник поставщика."""


class ExternalSupplierOfferIdVO(EntityIdVO):
    """Ссылка внешнего исполнения на выбранное предложение."""


class ExternalInventoryItemIdVO(EntityIdVO):
    """Ссылка внешнего исполнения на учётный товар."""


class ExternalFulfillmentPlanIdVO(EntityIdVO):
    """Ссылка внешнего исполнения на план заказа."""


class ExternalFulfillmentAllocationIdVO(EntityIdVO):
    """Ссылка внешнего исполнения на распределение плана."""
