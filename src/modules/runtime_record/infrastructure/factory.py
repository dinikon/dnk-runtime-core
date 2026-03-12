from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_record.application.ports.storage import (
    RuntimeRecordReaderPort,
)
from src.modules.runtime_record.infrastructure.reader import (
    SqlAlchemyRuntimeRecordReader,
)


def build_runtime_record_reader(
    *,
    session: AsyncSession,
) -> RuntimeRecordReaderPort:
    return SqlAlchemyRuntimeRecordReader(session=session)


__all__ = ["build_runtime_record_reader"]
