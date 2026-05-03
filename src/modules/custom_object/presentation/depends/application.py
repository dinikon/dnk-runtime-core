from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application.record.use_case import (
    CreateCustomRecordUseCase,
    DeleteCustomRecordUseCase,
    GetCustomRecordUseCase,
    ListCustomRecordsUseCase,
    UpdateCustomRecordUseCase,
)
from src.modules.custom_object.presentation.depends.infrastructure import (
    CustomRecordRepositoryDep,
)


def get_create_custom_record_use_case(
    repository: CustomRecordRepositoryDep,
) -> CreateCustomRecordUseCase:
    """Создает use case создания custom-object record."""
    return CreateCustomRecordUseCase(repository)


CreateCustomRecordUseCaseDep = Annotated[
    CreateCustomRecordUseCase,
    Depends(get_create_custom_record_use_case),
]


def get_get_custom_record_use_case(
    repository: CustomRecordRepositoryDep,
) -> GetCustomRecordUseCase:
    """Создает use case чтения custom-object record."""
    return GetCustomRecordUseCase(repository)


GetCustomRecordUseCaseDep = Annotated[
    GetCustomRecordUseCase,
    Depends(get_get_custom_record_use_case),
]


def get_list_custom_records_use_case(
    repository: CustomRecordRepositoryDep,
) -> ListCustomRecordsUseCase:
    """Создает use case списка custom-object records."""
    return ListCustomRecordsUseCase(repository)


ListCustomRecordsUseCaseDep = Annotated[
    ListCustomRecordsUseCase,
    Depends(get_list_custom_records_use_case),
]


def get_update_custom_record_use_case(
    repository: CustomRecordRepositoryDep,
) -> UpdateCustomRecordUseCase:
    """Создает use case обновления custom-object record."""
    return UpdateCustomRecordUseCase(repository)


UpdateCustomRecordUseCaseDep = Annotated[
    UpdateCustomRecordUseCase,
    Depends(get_update_custom_record_use_case),
]


def get_delete_custom_record_use_case(
    repository: CustomRecordRepositoryDep,
) -> DeleteCustomRecordUseCase:
    """Создает use case удаления custom-object record."""
    return DeleteCustomRecordUseCase(repository)


DeleteCustomRecordUseCaseDep = Annotated[
    DeleteCustomRecordUseCase,
    Depends(get_delete_custom_record_use_case),
]


__all__ = [
    "CreateCustomRecordUseCaseDep",
    "DeleteCustomRecordUseCaseDep",
    "GetCustomRecordUseCaseDep",
    "ListCustomRecordsUseCaseDep",
    "UpdateCustomRecordUseCaseDep",
]
