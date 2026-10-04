from typing import Annotated

from fastapi import Depends

from src.modules.contact_points.application.binding.command.remove_target_contact_points.handler import (
    RemoveTargetContactPointsHandler,
)
from src.modules.contact_points.application.binding.command.sync_target_contact_points.handler import (
    SyncTargetContactPointsHandler,
)
from src.modules.contact_points.application.binding.query.get_targets_contact_points.handler import (
    GetTargetsContactPointsHandler,
)
from src.modules.contact_points.domain.binding.service import ContactPointBindingService
from src.modules.contact_points.infrastructure.binding.persistence.repository import (
    SqlAlchemyContactPointBindingRepository,
)
from src.modules.contact_points.presentation.contact_point.depends import (
    ContactPointResolverDep,
)
from src.modules.contact_points.presentation.depends.naming import TenantNamingDep
from src.modules.contact_points.presentation.label.depends import (
    ContactPointLabelRepositoryDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_binding_repository(
    uow: UoWDep, naming: TenantNamingDep
) -> SqlAlchemyContactPointBindingRepository:
    """Собирает repository связей на общей сессии."""
    return SqlAlchemyContactPointBindingRepository(uow.session, naming)


ContactPointBindingRepositoryDep = Annotated[
    SqlAlchemyContactPointBindingRepository, Depends(get_binding_repository)
]


def get_sync_target_contact_points_handler(
    resolver: ContactPointResolverDep,
    bindings: ContactPointBindingRepositoryDep,
    labels: ContactPointLabelRepositoryDep,
    clock: ClockDep,
) -> SyncTargetContactPointsHandler:
    """Собирает обработчик синхронизации связей."""
    return SyncTargetContactPointsHandler(
        ContactPointBindingService(resolver, bindings, labels, clock)
    )


SyncTargetContactPointsHandlerDep = Annotated[
    SyncTargetContactPointsHandler,
    Depends(get_sync_target_contact_points_handler),
]


def get_targets_contact_points_handler(
    repository: ContactPointBindingRepositoryDep,
) -> GetTargetsContactPointsHandler:
    """Собирает пакетное чтение владельцев."""
    return GetTargetsContactPointsHandler(repository)


GetTargetsContactPointsHandlerDep = Annotated[
    GetTargetsContactPointsHandler, Depends(get_targets_contact_points_handler)
]


def get_remove_target_contact_points_handler(
    repository: ContactPointBindingRepositoryDep,
) -> RemoveTargetContactPointsHandler:
    """Собирает очистку связей владельца."""
    return RemoveTargetContactPointsHandler(repository)


RemoveTargetContactPointsHandlerDep = Annotated[
    RemoveTargetContactPointsHandler,
    Depends(get_remove_target_contact_points_handler),
]
