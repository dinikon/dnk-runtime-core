from typing import Protocol

from src.modules.broadcast.application.broadcast.dto.broadcast_dto import BroadcastDTO


class BroadcastRepositoryProtocol(Protocol):
    def load(self) -> BroadcastDTO: ...
    def save(self, broadcast: BroadcastDTO) -> None: ...
