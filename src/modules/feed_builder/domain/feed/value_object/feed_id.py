from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FeedIdVO(EntityIdVO):
    """Типизированный идентификатор Feed без генерации нового UUID."""

    __slots__ = ()
