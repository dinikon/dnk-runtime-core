from __future__ import annotations

from src.modules.custom_object.application.dto import GetCustomObjectRecordResultDTO
from src.modules.custom_object.application.ports import (
    CustomObjectRecordRepositoryPort,
    GetCustomObjectRecordQuery,
)
from src.modules.custom_object.application.queries import GetCustomObjectRecordQueryDTO
from src.modules.custom_object.domain import (
    CustomObjectNameVO,
    CustomObjectRecordNotFoundError,
)


class GetCustomObjectRecordUseCase:
    def __init__(self, repository: CustomObjectRecordRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        dto: GetCustomObjectRecordQueryDTO,
    ) -> GetCustomObjectRecordResultDTO:
        object_name = CustomObjectNameVO(dto.object_name_singular)
        record = await self._repository.get_by_id(
            GetCustomObjectRecordQuery(
                tenant_id=dto.tenant_id,
                object_name_singular=object_name.value,
                record_id=dto.record_id,
            )
        )
        if record is None:
            raise CustomObjectRecordNotFoundError(
                object_name_singular=object_name.value,
                record_id=str(dto.record_id),
            )
        return GetCustomObjectRecordResultDTO(
            object_name_singular=record.record.object_name.value,
            record_id=record.record.record_id,
            values=dict(record.record.values),
        )


__all__ = ["GetCustomObjectRecordUseCase"]
