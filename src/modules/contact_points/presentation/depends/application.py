from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.contact_points.presentation.depends.infrastructure import (
    ContactPointRepositoryDep,
    ContactPointBindingRepositoryDep,
    ContactPointLabelRepositoryDep,
    ContactPointNormalizersDep,
)
from src.modules.contact_points.domain.contact_point.service import ContactPointResolver
from src.modules.contact_points.domain.binding.service import ContactPointBindingService
from src.modules.contact_points.application.api import (
    SyncTargetContactPointsUseCase,
    GetTargetsContactPointsUseCase,
    RemoveTargetContactPointsUseCase,
    ResolveContactPointTargetsUseCase,
)
from src.modules.contact_points.application.label.use_case.create_label import (
    CreateContactPointLabelUseCase,
)
from src.modules.contact_points.application.label.use_case.update_label import (
    UpdateContactPointLabelUseCase,
)
from src.modules.contact_points.application.label.use_case.list_labels import (
    ListContactPointLabelsUseCase,
)


def get_contact_point_resolver(
    repository: ContactPointRepositoryDep,
    normalizers: ContactPointNormalizersDep,
    clock: ClockDep,
):
    """Собирает resolver без доступа к UoW из domain."""
    return ContactPointResolver(repository, normalizers, clock)


ContactPointResolverDep = Annotated[
    ContactPointResolver, Depends(get_contact_point_resolver)
]


def get_sync_target_contact_points_use_case(
    resolver: ContactPointResolverDep,
    bindings: ContactPointBindingRepositoryDep,
    labels: ContactPointLabelRepositoryDep,
    clock: ClockDep,
):
    """Собирает domain service и use case синхронизации."""
    return SyncTargetContactPointsUseCase(
        ContactPointBindingService(resolver, bindings, labels, clock)
    )


SyncTargetContactPointsUseCaseDep = Annotated[
    SyncTargetContactPointsUseCase, Depends(get_sync_target_contact_points_use_case)
]


def get_targets_contact_points_use_case(repository: ContactPointBindingRepositoryDep):
    """Собирает пакетное чтение для любых target."""
    return GetTargetsContactPointsUseCase(repository)


GetTargetsContactPointsUseCaseDep = Annotated[
    GetTargetsContactPointsUseCase, Depends(get_targets_contact_points_use_case)
]


def get_remove_target_contact_points_use_case(
    repository: ContactPointBindingRepositoryDep,
):
    """Собирает очистку связей владельца."""
    return RemoveTargetContactPointsUseCase(repository)


RemoveTargetContactPointsUseCaseDep = Annotated[
    RemoveTargetContactPointsUseCase, Depends(get_remove_target_contact_points_use_case)
]


def get_resolve_contact_point_targets_use_case(
    resolver: ContactPointResolverDep,
    points: ContactPointRepositoryDep,
    bindings: ContactPointBindingRepositoryDep,
):
    """Собирает read-only обратный поиск."""
    return ResolveContactPointTargetsUseCase(resolver, points, bindings)


ResolveContactPointTargetsUseCaseDep = Annotated[
    ResolveContactPointTargetsUseCase,
    Depends(get_resolve_contact_point_targets_use_case),
]


def get_create_label_use_case(
    repository: ContactPointLabelRepositoryDep, clock: ClockDep
):
    """Собирает создание настройки."""
    return CreateContactPointLabelUseCase(repository, clock)


CreateContactPointLabelUseCaseDep = Annotated[
    CreateContactPointLabelUseCase, Depends(get_create_label_use_case)
]


def get_update_label_use_case(
    repository: ContactPointLabelRepositoryDep, clock: ClockDep
):
    """Собирает редактирование настройки."""
    return UpdateContactPointLabelUseCase(repository, clock)


UpdateContactPointLabelUseCaseDep = Annotated[
    UpdateContactPointLabelUseCase, Depends(get_update_label_use_case)
]


def get_list_labels_use_case(repository: ContactPointLabelRepositoryDep):
    """Собирает чтение настроек."""
    return ListContactPointLabelsUseCase(repository)


ListContactPointLabelsUseCaseDep = Annotated[
    ListContactPointLabelsUseCase, Depends(get_list_labels_use_case)
]

__all__ = [
    "SyncTargetContactPointsUseCaseDep",
    "GetTargetsContactPointsUseCaseDep",
    "RemoveTargetContactPointsUseCaseDep",
    "ResolveContactPointTargetsUseCaseDep",
    "CreateContactPointLabelUseCaseDep",
    "UpdateContactPointLabelUseCaseDep",
    "ListContactPointLabelsUseCaseDep",
    "get_contact_point_resolver",
    "get_sync_target_contact_points_use_case",
    "get_targets_contact_points_use_case",
    "get_remove_target_contact_points_use_case",
    "get_resolve_contact_point_targets_use_case",
    "get_create_label_use_case",
    "get_update_label_use_case",
    "get_list_labels_use_case",
]
