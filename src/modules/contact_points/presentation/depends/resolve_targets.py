from typing import Annotated

from fastapi import Depends

from src.modules.contact_points.application.query.resolve_contact_point_targets.handler import (
    ResolveContactPointTargetsHandler,
)
from src.modules.contact_points.presentation.depends.binding import (
    ContactPointBindingRepositoryDep,
)
from src.modules.contact_points.presentation.depends.contact_point import (
    ContactPointRepositoryDep,
    ContactPointResolverDep,
)


def get_resolve_contact_point_targets_handler(
    resolver: ContactPointResolverDep,
    points: ContactPointRepositoryDep,
    bindings: ContactPointBindingRepositoryDep,
) -> ResolveContactPointTargetsHandler:
    """Собирает read-only обратный поиск владельцев."""
    return ResolveContactPointTargetsHandler(resolver, points, bindings)


ResolveContactPointTargetsHandlerDep = Annotated[
    ResolveContactPointTargetsHandler,
    Depends(get_resolve_contact_point_targets_handler),
]
