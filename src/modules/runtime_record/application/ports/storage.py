from __future__ import annotations

from typing import Protocol

from src.modules.runtime_record.application.contracts import (
    DeleteRuntimeRecordCommand,
    FindRuntimeRecordQuery,
    GetRuntimeRecordQuery,
    ListRuntimeRecordsQuery,
    RuntimeRecordPayload,
    UpsertRuntimeRecordCommand,
)


class RuntimeRecordReaderPort(Protocol):
    async def get_record(
        self,
        query: GetRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None: ...


class RuntimeRecordListerPort(Protocol):
    async def list_records(
        self,
        query: ListRuntimeRecordsQuery,
    ) -> tuple[RuntimeRecordPayload, ...]: ...


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


class RuntimeRecordDeleterPort(Protocol):
    async def delete_record(
        self,
        command: DeleteRuntimeRecordCommand,
    ) -> bool: ...


class RuntimeRecordStoragePort(
    RuntimeRecordReaderPort,
    RuntimeRecordListerPort,
    RuntimeRecordFinderPort,
    RuntimeRecordWriterPort,
    RuntimeRecordDeleterPort,
    Protocol,
): ...
