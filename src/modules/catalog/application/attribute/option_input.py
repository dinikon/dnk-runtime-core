from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)


@dataclass(frozen=True, slots=True)
class AttributeOptionInput:
    """Явное намерение добавить или сохранить option при замене списка."""

    label: str | None
    option_id: AttributeOptionIdVO | None = None
