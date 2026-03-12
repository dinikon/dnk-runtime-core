from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application.services import CustomObjectRuntimeRecordMapper
from src.modules.custom_object.application.use_case import (
    CreateCustomObjectFieldUseCase,
    CreateCustomObjectUseCase,
    GetCustomObjectRecordUseCase,
)
from src.modules.custom_object.infrastructure.repositories import (
    RuntimeRecordCustomObjectRepository,
    RuntimeSchemaCustomObjectRepository,
)
from src.modules.runtime_record.infrastructure.factory import build_runtime_record_reader
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.shared.depends.uow import UoWDep


def get_get_custom_object_record_use_case(
    uow: UoWDep,
) -> GetCustomObjectRecordUseCase:
    runtime_record_reader = build_runtime_record_reader(session=uow.session)
    repository = RuntimeRecordCustomObjectRepository(
        session=uow.session,
        runtime_record_reader=runtime_record_reader,
        mapper=CustomObjectRuntimeRecordMapper(),
    )
    return GetCustomObjectRecordUseCase(repository=repository)


GetCustomObjectRecordUseCaseDep = Annotated[
    GetCustomObjectRecordUseCase,
    Depends(get_get_custom_object_record_use_case),
]


def get_create_custom_object_use_case(
    uow: UoWDep,
) -> CreateCustomObjectUseCase:
    orchestrator = build_ddl_orchestrator(session=uow.session)
    repository = RuntimeSchemaCustomObjectRepository(
        session=uow.session,
        orchestrator=orchestrator,
    )
    return CreateCustomObjectUseCase(repository=repository)


CreateCustomObjectUseCaseDep = Annotated[
    CreateCustomObjectUseCase,
    Depends(get_create_custom_object_use_case),
]


def get_create_custom_object_field_use_case(
    uow: UoWDep,
) -> CreateCustomObjectFieldUseCase:
    orchestrator = build_ddl_orchestrator(session=uow.session)
    repository = RuntimeSchemaCustomObjectRepository(
        session=uow.session,
        orchestrator=orchestrator,
    )
    return CreateCustomObjectFieldUseCase(repository=repository)


CreateCustomObjectFieldUseCaseDep = Annotated[
    CreateCustomObjectFieldUseCase,
    Depends(get_create_custom_object_field_use_case),
]


__all__ = [
    "CreateCustomObjectFieldUseCaseDep",
    "CreateCustomObjectUseCaseDep",
    "GetCustomObjectRecordUseCaseDep",
    "get_create_custom_object_field_use_case",
    "get_create_custom_object_use_case",
    "get_get_custom_object_record_use_case",
]
