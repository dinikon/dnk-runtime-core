from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application.field.use_case import (
    AddCustomFieldUseCase,
    DeleteCustomFieldUseCase,
)
from src.modules.custom_object.application.object.use_case import (
    CreateCustomObjectUseCase,
    DeleteCustomObjectUseCase,
    DescribeCustomObjectUseCase,
    ListCustomObjectsUseCase,
)
from src.modules.custom_object.application.record.use_case import (
    CreateCustomRecordUseCase,
    DeleteCustomRecordUseCase,
    GetCustomRecordUseCase,
    ListCustomRecordsUseCase,
    UpdateCustomRecordUseCase,
)
from src.modules.custom_object.presentation.depends.infrastructure import (
    CustomFieldSchemaRepositoryDep,
    CustomObjectSchemaRepositoryDep,
    CustomRecordRepositoryDep,
)


def get_list_custom_objects_use_case(
    repository: CustomObjectSchemaRepositoryDep,
) -> ListCustomObjectsUseCase:
    """Создает use case списка custom objects."""
    return ListCustomObjectsUseCase(repository)


ListCustomObjectsUseCaseDep = Annotated[
    ListCustomObjectsUseCase,
    Depends(get_list_custom_objects_use_case),
]


def get_create_custom_object_use_case(
    repository: CustomObjectSchemaRepositoryDep,
) -> CreateCustomObjectUseCase:
    """Создает use case создания custom object."""
    return CreateCustomObjectUseCase(repository)


CreateCustomObjectUseCaseDep = Annotated[
    CreateCustomObjectUseCase,
    Depends(get_create_custom_object_use_case),
]


def get_describe_custom_object_use_case(
    repository: CustomObjectSchemaRepositoryDep,
) -> DescribeCustomObjectUseCase:
    """Создает use case чтения схемы custom object."""
    return DescribeCustomObjectUseCase(repository)


DescribeCustomObjectUseCaseDep = Annotated[
    DescribeCustomObjectUseCase,
    Depends(get_describe_custom_object_use_case),
]


def get_delete_custom_object_use_case(
    repository: CustomObjectSchemaRepositoryDep,
) -> DeleteCustomObjectUseCase:
    """Создает use case удаления custom object."""
    return DeleteCustomObjectUseCase(repository)


DeleteCustomObjectUseCaseDep = Annotated[
    DeleteCustomObjectUseCase,
    Depends(get_delete_custom_object_use_case),
]


def get_add_custom_field_use_case(
    repository: CustomFieldSchemaRepositoryDep,
) -> AddCustomFieldUseCase:
    """Создает use case добавления custom field."""
    return AddCustomFieldUseCase(repository)


AddCustomFieldUseCaseDep = Annotated[
    AddCustomFieldUseCase,
    Depends(get_add_custom_field_use_case),
]


def get_delete_custom_field_use_case(
    repository: CustomFieldSchemaRepositoryDep,
) -> DeleteCustomFieldUseCase:
    """Создает use case удаления custom field."""
    return DeleteCustomFieldUseCase(repository)


DeleteCustomFieldUseCaseDep = Annotated[
    DeleteCustomFieldUseCase,
    Depends(get_delete_custom_field_use_case),
]


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
    "AddCustomFieldUseCaseDep",
    "CreateCustomObjectUseCaseDep",
    "CreateCustomRecordUseCaseDep",
    "DeleteCustomFieldUseCaseDep",
    "DeleteCustomObjectUseCaseDep",
    "DeleteCustomRecordUseCaseDep",
    "DescribeCustomObjectUseCaseDep",
    "GetCustomRecordUseCaseDep",
    "ListCustomObjectsUseCaseDep",
    "ListCustomRecordsUseCaseDep",
    "UpdateCustomRecordUseCaseDep",
]
