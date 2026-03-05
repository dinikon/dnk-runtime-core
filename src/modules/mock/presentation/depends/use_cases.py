from typing import Annotated

from fastapi import Depends

from src.modules.mock.application.workplaces.use_cases import (
    GetMockCrmEntityUseCase,
    GetMockCrmWorkplaceUseCase,
    GetMockWorkplacesUseCase,
)


def get_mock_workplaces_use_case() -> GetMockWorkplacesUseCase:
    return GetMockWorkplacesUseCase()


MockWorkplacesUseCaseDep = Annotated[
    GetMockWorkplacesUseCase,
    Depends(get_mock_workplaces_use_case),
]


def get_mock_crm_workplace_use_case() -> GetMockCrmWorkplaceUseCase:
    return GetMockCrmWorkplaceUseCase()


MockCrmWorkplaceUseCaseDep = Annotated[
    GetMockCrmWorkplaceUseCase,
    Depends(get_mock_crm_workplace_use_case),
]


def get_mock_crm_entity_use_case() -> GetMockCrmEntityUseCase:
    return GetMockCrmEntityUseCase()


MockCrmEntityUseCaseDep = Annotated[
    GetMockCrmEntityUseCase,
    Depends(get_mock_crm_entity_use_case),
]

__all__ = [
    "MockCrmEntityUseCaseDep",
    "MockCrmWorkplaceUseCaseDep",
    "MockWorkplacesUseCaseDep",
    "get_mock_crm_entity_use_case",
    "get_mock_crm_workplace_use_case",
    "get_mock_workplaces_use_case",
]
