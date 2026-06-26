from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import EntityDescriptionVO
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


@dataclass(slots=True)
class WorkflowEntityEntity:
    id: EntityIdVO

    created_at: datetime
    updated_at: datetime

    created_by: EntityIdVO
    updated_by: EntityIdVO

    app_id: EntityIdVO

    version: str
    graph: str

    features: str

    environment: str

    title: EntityTitleVO
    description: EntityDescriptionVO

