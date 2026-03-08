from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.domain.entities import SystemObjectDefinition


class TenantSchemaManagerProtocol(Protocol):
    async def ensure_system_object(
        self,
        *,
        schema: str,
        object_definition: SystemObjectDefinition,
    ) -> None: ...
