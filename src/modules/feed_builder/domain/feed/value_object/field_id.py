from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FieldIdVO(EntityIdVO):
    """Типизированный идентификатор Field без генерации нового UUID."""

    __slots__ = ()
