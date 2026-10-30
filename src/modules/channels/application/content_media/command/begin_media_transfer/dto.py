from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BeginMediaTransferResultDTO:
    """Результат begin_media_transfer без документов хранения."""

    media_ids: tuple[UUID, ...]
