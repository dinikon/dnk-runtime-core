from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.services import ContactRuntimeRecordMapper
from src.modules.crm.application.contact.use_case import (
    GetContactUseCase,
)
from src.modules.crm.infrastructure.contact.repositories import (
    RuntimeRecordContactRepository,
)
from src.modules.runtime_record.infrastructure.factory import build_runtime_record_reader
from src.modules.shared.depends.uow import UoWDep


def get_get_contact_use_case(
    uow: UoWDep,
) -> GetContactUseCase:
    runtime_record_reader = build_runtime_record_reader(session=uow.session)
    repository = RuntimeRecordContactRepository(
        runtime_record_reader=runtime_record_reader,
        mapper=ContactRuntimeRecordMapper(),
    )
    return GetContactUseCase(repository=repository)


GetContactUseCaseDep = Annotated[
    GetContactUseCase,
    Depends(get_get_contact_use_case),
]


__all__ = [
    "GetContactUseCaseDep",
    "get_get_contact_use_case",
]
