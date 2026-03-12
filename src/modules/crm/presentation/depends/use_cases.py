from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.use_case.contact.get_contact_use_case import (
    GetContactUseCase,
)
from src.modules.runtime_record.infrastructure.factory import (
    build_runtime_record_reader,
)
from src.modules.shared.depends.uow import UoWDep


def get_get_contact_use_case(
    uow: UoWDep,
) -> GetContactUseCase:
    runtime_record_reader = build_runtime_record_reader(session=uow.session)
    return GetContactUseCase(runtime_record_reader=runtime_record_reader)


GetContactUseCaseDep = Annotated[
    GetContactUseCase,
    Depends(get_get_contact_use_case),
]


__all__ = [
    "GetContactUseCaseDep",
    "get_get_contact_use_case",
]
