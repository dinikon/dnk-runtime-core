from typing import Protocol

from src.modules.broadcast.application.broadcast.repository.command_repository import (
    BroadcastCommandRepositoryProtocol,
)
from src.modules.broadcast.application.broadcast.repository.query_repository import (
    BroadcastQueryRepositoryProtocol,
)


class BroadcastRepositoryProtocol(
    BroadcastCommandRepositoryProtocol,
    BroadcastQueryRepositoryProtocol,
    Protocol,
):
    """Полный порт хранения broadcast definitions."""

    pass


__all__ = [
    "BroadcastCommandRepositoryProtocol",
    "BroadcastQueryRepositoryProtocol",
    "BroadcastRepositoryProtocol",
]
