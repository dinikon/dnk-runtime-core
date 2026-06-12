from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.modules.broadcast.application.broadcast.dto import BroadcastDTO
from src.modules.broadcast.application.broadcast.dto import BroadcastListDTO
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.shared import EntityIdVO


class BroadcastQueryRepositoryProtocol(Protocol):
    """Порт query-чтения broadcast definitions."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast_id: BroadcastIdVO,
    ) -> BroadcastDTO | None:
        """Возвращает одну broadcast definition tenant или None."""
        ...

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
