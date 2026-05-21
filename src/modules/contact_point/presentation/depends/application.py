from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.contact_point.application.use_case import (
    AttachContactPointUseCase,
    AttachContactPointUseCaseProtocol,
    DetachContactPointUseCase,
    DetachContactPointUseCaseProtocol,
)
from src.modules.contact_point.presentation.depends.infrastructure import (
    ContactPointHashServiceDep,
    ContactPointNormalizerDep,
    ContactPointObjectFeatureGateDep,
    ContactPointRuntimeRepositoryDep,
    OwnerResolverDep,
)
from src.modules.shared.depends import ClockDep, UuidDep


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


__all__ = [
    "AttachContactPointUseCaseDep",
    "DetachContactPointUseCaseDep",
    "get_attach_contact_point_use_case",
    "get_detach_contact_point_use_case",
]
