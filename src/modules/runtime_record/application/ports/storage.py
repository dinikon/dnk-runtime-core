from __future__ import annotations

from typing import Protocol

from src.modules.runtime_record.application.contracts import (
    FindRuntimeRecordQuery,
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
    UpsertRuntimeRecordCommand,
)


class RuntimeRecordReaderPort(Protocol):
    async def get_record(
        self,
        query: GetRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None: ...


class RuntimeRecordFinderPort(Protocol):
    async def get_record_by_fields(
        self,
        query: FindRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None: ...


class RuntimeRecordWriterPort(Protocol):
    async def upsert_record(
        self,
        command: UpsertRuntimeRecordCommand,
    ) -> None: ...


class RuntimeRecordStoragePort(
    RuntimeRecordReaderPort,
    RuntimeRecordFinderPort,
    RuntimeRecordWriterPort,
    Protocol,
): ...
