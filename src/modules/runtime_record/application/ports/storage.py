from __future__ import annotations

from typing import Protocol

from src.modules.runtime_record.application.contracts import (
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
)


class RuntimeRecordReaderPort(Protocol):
    async def get_record(
        self,
        query: GetRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None: ...
