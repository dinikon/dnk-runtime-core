from __future__ import annotations

from src.modules.custom_object.domain import CustomObjectNameVO, CustomObjectRecordEntity
from src.modules.runtime_record.application.contracts import RuntimeRecordPayload


class CustomObjectRuntimeRecordMapper:
    def map_payload(
        self,
        payload: RuntimeRecordPayload,
    ) -> CustomObjectRecordEntity:
        values: dict[str, object] = {}
        values.update(payload.system_values)
        values.update(payload.custom_values)
        return CustomObjectRecordEntity(
            object_name=CustomObjectNameVO(payload.object_name_singular),
            record_id=payload.record_id,
            values=values,
        )


__all__ = ["CustomObjectRuntimeRecordMapper"]
