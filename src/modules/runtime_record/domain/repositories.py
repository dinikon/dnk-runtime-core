from __future__ import annotations

from typing import Protocol
from uuid import UUID


class RuntimeValueRepositoryProtocol(Protocol):
    async def write_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        values: dict[str, object | None],
    ) -> None: ...

    async def read_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        field_names: tuple[str, ...],
    ) -> dict[str, object | None]: ...


__all__ = ["RuntimeValueRepositoryProtocol"]
