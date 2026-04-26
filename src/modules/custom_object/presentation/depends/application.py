from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application import (
    AddCustomFieldUseCase,
    CreateCustomObjectUseCase,
    CreateCustomRecordUseCase,
    DeleteCustomFieldUseCase,
    DeleteCustomObjectUseCase,
    DeleteCustomRecordUseCase,
    DescribeCustomObjectUseCase,
    GetCustomRecordUseCase,
    ListCustomObjectsUseCase,
    ListCustomRecordsUseCase,
    UpdateCustomRecordUseCase,
)
from src.modules.custom_object.presentation.depends.infrastructure import (
    CustomObjectStoreDep,
    RuntimeGatewayDep,
)


def get_list_custom_objects_use_case(
    store: CustomObjectStoreDep,
) -> ListCustomObjectsUseCase:
    """Создает use case списка custom objects."""
    return ListCustomObjectsUseCase(store)


ListCustomObjectsUseCaseDep = Annotated[
    ListCustomObjectsUseCase,
    Depends(get_list_custom_objects_use_case),
]


def get_create_custom_object_use_case(
    store: CustomObjectStoreDep,
) -> CreateCustomObjectUseCase:
    """Создает use case создания custom object."""
    return CreateCustomObjectUseCase(store)


CreateCustomObjectUseCaseDep = Annotated[
    CreateCustomObjectUseCase,
    Depends(get_create_custom_object_use_case),
]


def get_describe_custom_object_use_case(
    store: CustomObjectStoreDep,
) -> DescribeCustomObjectUseCase:
    """Создает use case чтения схемы custom object."""
    return DescribeCustomObjectUseCase(store)


DescribeCustomObjectUseCaseDep = Annotated[
    DescribeCustomObjectUseCase,
    Depends(get_describe_custom_object_use_case),
]


def get_delete_custom_object_use_case(
    store: CustomObjectStoreDep,
) -> DeleteCustomObjectUseCase:
    """Создает use case удаления custom object."""
    return DeleteCustomObjectUseCase(store)


DeleteCustomObjectUseCaseDep = Annotated[
    DeleteCustomObjectUseCase,
    Depends(get_delete_custom_object_use_case),
]


def get_add_custom_field_use_case(
    store: CustomObjectStoreDep,
) -> AddCustomFieldUseCase:
    """Создает use case добавления custom field."""
    return AddCustomFieldUseCase(store)


AddCustomFieldUseCaseDep = Annotated[
    AddCustomFieldUseCase,
    Depends(get_add_custom_field_use_case),
]


def get_delete_custom_field_use_case(
    store: CustomObjectStoreDep,
) -> DeleteCustomFieldUseCase:
    """Создает use case удаления custom field."""
    return DeleteCustomFieldUseCase(store)


DeleteCustomFieldUseCaseDep = Annotated[
    DeleteCustomFieldUseCase,
    Depends(get_delete_custom_field_use_case),
]


def get_create_custom_record_use_case(
    store: CustomObjectStoreDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CreateCustomRecordUseCase:
    """Создает use case создания custom-object record."""
    return CreateCustomRecordUseCase(store, runtime_gateway)


CreateCustomRecordUseCaseDep = Annotated[
    CreateCustomRecordUseCase,
    Depends(get_create_custom_record_use_case),
]


def get_get_custom_record_use_case(
    store: CustomObjectStoreDep,
    runtime_gateway: RuntimeGatewayDep,
) -> GetCustomRecordUseCase:
    """Создает use case чтения custom-object record."""
    return GetCustomRecordUseCase(store, runtime_gateway)


GetCustomRecordUseCaseDep = Annotated[
    GetCustomRecordUseCase,
    Depends(get_get_custom_record_use_case),
]


def get_list_custom_records_use_case(
    store: CustomObjectStoreDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ListCustomRecordsUseCase:
    """Создает use case списка custom-object records."""
    return ListCustomRecordsUseCase(store, runtime_gateway)


ListCustomRecordsUseCaseDep = Annotated[
    ListCustomRecordsUseCase,
    Depends(get_list_custom_records_use_case),
]


def get_update_custom_record_use_case(
    store: CustomObjectStoreDep,
    runtime_gateway: RuntimeGatewayDep,
) -> UpdateCustomRecordUseCase:
    """Создает use case обновления custom-object record."""
    return UpdateCustomRecordUseCase(store, runtime_gateway)


UpdateCustomRecordUseCaseDep = Annotated[
    UpdateCustomRecordUseCase,
    Depends(get_update_custom_record_use_case),
]


def get_delete_custom_record_use_case(
    store: CustomObjectStoreDep,
    runtime_gateway: RuntimeGatewayDep,
) -> DeleteCustomRecordUseCase:
    """Создает use case удаления custom-object record."""
    return DeleteCustomRecordUseCase(store, runtime_gateway)


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
