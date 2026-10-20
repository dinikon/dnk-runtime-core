from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationImportResultDTO:
    """Возвращает адрес устойчивого процесса подготовки."""

    preparation_id: UUID
