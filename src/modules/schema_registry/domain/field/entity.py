from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class FieldEntity:
    id: EntityIdVO
