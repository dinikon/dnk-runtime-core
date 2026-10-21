from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RepresentationExportRefDTO:
    """Передаёт конкретную версию разрешения связанного товара."""

    representation_id: UUID
    expected_revision: int


@dataclass(frozen=True, slots=True)
class SetPublicationExportCommand:
    """Описывает атомарное включение или выключение выбранных связей канала."""

    channel_id: UUID
    enabled: bool
    items: tuple[RepresentationExportRefDTO, ...]
