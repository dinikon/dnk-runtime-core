from __future__ import annotations

from src.modules.crm.application.contact.ports import (
    ContactRecord,
    ContactRecordRepositoryPort,
    GetContactRecordQuery,
)
from src.modules.crm.application.contact.services import ContactRuntimeRecordMapper
from src.modules.runtime_record.application.contracts import GetRuntimeRecordQuery
from src.modules.runtime_record.application.ports import RuntimeRecordReaderPort


class RuntimeRecordContactRepository(ContactRecordRepositoryPort):
    def __init__(
        self,
        runtime_record_reader: RuntimeRecordReaderPort,
        mapper: ContactRuntimeRecordMapper,
    ):
        self._runtime_record_reader = runtime_record_reader
        self._mapper = mapper

    async def get_by_id(
        self,
        query: GetContactRecordQuery,
    ) -> ContactRecord | None:
        runtime_payload = await self._runtime_record_reader.get_record(
            GetRuntimeRecordQuery(
                tenant_id=query.tenant_id,
                object_name_singular="contact",
                record_id=query.contact_id,
            )
        )
        if runtime_payload is None:
            return None
        return self._mapper.map_payload(runtime_payload)


__all__ = ["RuntimeRecordContactRepository"]
