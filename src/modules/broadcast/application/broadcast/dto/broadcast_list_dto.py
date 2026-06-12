from dataclasses import dataclass

from src.modules.broadcast.application.broadcast.dto.broadcast_dto import BroadcastDTO


@dataclass(slots=True, frozen=True)
class BroadcastListDTO:
    """Страница broadcast definitions для query API."""

    items: tuple[BroadcastDTO, ...]
    total: int
    limit: int
    offset: int
