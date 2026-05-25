from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.contact_point.application.use_case import (
    AttachContactPointUseCase,
    AttachContactPointUseCaseProtocol,
    DetachContactPointUseCase,
    DetachContactPointUseCaseProtocol,
    GetContactPointUseCase,
    GetContactPointUseCaseProtocol,
    ListContactPointBindingsUseCase,
    ListContactPointBindingsUseCaseProtocol,
    ListContactPointsUseCase,
    ListContactPointsUseCaseProtocol,
    ListOwnerContactPointsUseCase,
    ListOwnerContactPointsUseCaseProtocol,
)
from src.modules.contact_point.presentation.depends.infrastructure import (
    ContactPointHashServiceDep,
    ContactPointNormalizerDep,
    ContactPointObjectFeatureGateDep,
    ContactPointRuntimeRepositoryDep,
    OwnerResolverDep,
)
from src.modules.shared.presentation import ClockDep, UuidDep


def get_attach_contact_point_use_case(
    repository: ContactPointRuntimeRepositoryDep,
    owner_resolver: OwnerResolverDep,
    feature_gate: ContactPointObjectFeatureGateDep,
    normalizer: ContactPointNormalizerDep,
    hash_service: ContactPointHashServiceDep,
    clock: ClockDep,
    uuid_generator: UuidDep,
) -> AttachContactPointUseCaseProtocol:
    return AttachContactPointUseCase(
        contact_points=repository,
        bindings=repository,
        owner_resolver=owner_resolver,
        feature_gate=feature_gate,
        normalizer=normalizer,
        hash_service=hash_service,
        uuid_generator=uuid_generator,
        clock=clock,
    )


AttachContactPointUseCaseDep = Annotated[
    AttachContactPointUseCaseProtocol,
    Depends(get_attach_contact_point_use_case),
]


def get_detach_contact_point_use_case(
    repository: ContactPointRuntimeRepositoryDep,
    clock: ClockDep,
) -> DetachContactPointUseCaseProtocol:
    return DetachContactPointUseCase(
        bindings=repository,
        clock=clock,
    )


DetachContactPointUseCaseDep = Annotated[
    DetachContactPointUseCaseProtocol,
    Depends(get_detach_contact_point_use_case),
]


def get_list_owner_contact_points_use_case(
    repository: ContactPointRuntimeRepositoryDep,
    owner_resolver: OwnerResolverDep,
    feature_gate: ContactPointObjectFeatureGateDep,
) -> ListOwnerContactPointsUseCaseProtocol:
    return ListOwnerContactPointsUseCase(
        query_repository=repository,
        owner_resolver=owner_resolver,
        feature_gate=feature_gate,
    )


ListOwnerContactPointsUseCaseDep = Annotated[
    ListOwnerContactPointsUseCaseProtocol,
    Depends(get_list_owner_contact_points_use_case),
]


def get_get_contact_point_use_case(
    repository: ContactPointRuntimeRepositoryDep,
) -> GetContactPointUseCaseProtocol:
    return GetContactPointUseCase(query_repository=repository)


GetContactPointUseCaseDep = Annotated[
    GetContactPointUseCaseProtocol,
    Depends(get_get_contact_point_use_case),
]


def get_list_contact_points_use_case(
    repository: ContactPointRuntimeRepositoryDep,
) -> ListContactPointsUseCaseProtocol:
    return ListContactPointsUseCase(query_repository=repository)


ListContactPointsUseCaseDep = Annotated[
    ListContactPointsUseCaseProtocol,
    Depends(get_list_contact_points_use_case),
]


def get_list_contact_point_bindings_use_case(
    repository: ContactPointRuntimeRepositoryDep,
) -> ListContactPointBindingsUseCaseProtocol:
    return ListContactPointBindingsUseCase(query_repository=repository)


ListContactPointBindingsUseCaseDep = Annotated[
    ListContactPointBindingsUseCaseProtocol,
    Depends(get_list_contact_point_bindings_use_case),
]


__all__ = [
    "AttachContactPointUseCaseDep",
    "DetachContactPointUseCaseDep",
    "GetContactPointUseCaseDep",
    "ListContactPointBindingsUseCaseDep",
    "ListContactPointsUseCaseDep",
    "ListOwnerContactPointsUseCaseDep",
    "get_attach_contact_point_use_case",
    "get_detach_contact_point_use_case",
    "get_get_contact_point_use_case",
    "get_list_contact_point_bindings_use_case",
    "get_list_contact_points_use_case",
    "get_list_owner_contact_points_use_case",
]
