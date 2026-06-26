from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import EntityDescriptionVO
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


@dataclass(slots=True)
class WorkflowApplicationEntity:
    id: EntityIdVO

    created_at: datetime
    updated_at: datetime

    created_by: EntityIdVO
    updated_by: EntityIdVO

    kind: str

    status: str

    title: EntityTitleVO
    description: EntityDescriptionVO

    icon: str
    icon_background: str