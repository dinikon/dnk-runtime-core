from modules.shared.domain.value_object.entity_id import EntityIdVO


class ObjectIdVO(EntityIdVO): ...


class ObjectNameVO:
    name_singular: str
    name_plural: str


class ObjectLabelVO:
    name_singular: str
    name_plural: str
