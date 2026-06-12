from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.modules.broadcast.application.broadcast.dto import BroadcastListDTO
from src.modules.shared import EntityIdVO


class BroadcastQueryRepositoryProtocol(Protocol):
    """Порт query-чтения broadcast definitions."""

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        filter_dsl: Mapping[str, Any] | None,
        sort_dsl: Sequence[Mapping[str, Any]],
        limit: int,
        offset: int,
    ) -> BroadcastListDTO:
        """Возвращает страницу broadcast definitions tenant."""
        ...


__all__ = ["BroadcastQueryRepositoryProtocol"]
