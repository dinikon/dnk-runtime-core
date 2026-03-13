from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_record.application.ports.storage import (
    RuntimeRecordReaderPort,
    RuntimeRecordStoragePort,
)
from src.modules.runtime_record.infrastructure.reader import (
    SqlAlchemyRuntimeRecordReader,
)


def build_runtime_record_reader(
    *,
    session: AsyncSession,
) -> RuntimeRecordReaderPort:
    return SqlAlchemyRuntimeRecordReader(session=session)


def build_runtime_record_storage(
    *,
    session: AsyncSession,
) -> RuntimeRecordStoragePort:
    return SqlAlchemyRuntimeRecordReader(session=session)


__all__ = [
    "build_runtime_record_reader",
    "build_runtime_record_storage",
]
