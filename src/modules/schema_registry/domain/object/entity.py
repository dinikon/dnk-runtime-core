from dataclasses import dataclass
from datetime import datetime


from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ObjectEntity:
    id: EntityIdVO
    created_at: datetime
    updated_at: datetime

    tenant_id: EntityIdVO

    singular_name: str
    plural_name: str

    label_singular: str
    label_plural: str

    description: str

    @classmethod
    def create(
        cls,
        id_: EntityIdVO,
        tenant_id: EntityIdVO,
        now: datetime,
        singular_name: str,
        plural_name: str,
        label_singular: str,
        label_plural: str,
        description: str,
    ):
        return cls(
            id=id_,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            singular_name=singular_name,
            plural_name=plural_name,
            label_singular=label_singular,
            label_plural=label_plural,
            description=description,
        )
