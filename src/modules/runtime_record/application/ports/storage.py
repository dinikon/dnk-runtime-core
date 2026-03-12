from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.runtime_record.domain.entities import RuntimeRecord


class RuntimeRecordReaderPort(Protocol):
    async def get_record(
        self,
        *,
        tenant_id: UUID,
        object_name_singular: str,
        record_id: UUID,
    ) -> RuntimeRecord | None: ...

