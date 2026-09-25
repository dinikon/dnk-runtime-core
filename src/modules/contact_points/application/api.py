"""Публичные application-контракты для infrastructure adapters других модулей."""

from src.modules.contact_points.application.binding.command.sync_target_contact_points_command import (
    SyncTargetContactPointsCommand,
)
from src.modules.contact_points.application.binding.command.remove_target_contact_points_command import (
    RemoveTargetContactPointsCommand,
)
from src.modules.contact_points.application.binding.query.get_targets_contact_points_query import (
    GetTargetsContactPointsQuery,
)
from src.modules.contact_points.application.binding.dto.binding_dto import (
    ContactPointBindingDTO,
)
from src.modules.contact_points.application.binding.use_case.sync_target_contact_points import (
    SyncTargetContactPointsUseCase,
)
from src.modules.contact_points.application.binding.use_case.get_targets_contact_points import (
    GetTargetsContactPointsUseCase,
)
from src.modules.contact_points.application.binding.use_case.remove_target_contact_points import (
    RemoveTargetContactPointsUseCase,
)
from src.modules.contact_points.application.contact_point.query.resolve_contact_point_targets_query import (
    ResolveContactPointTargetsQuery,
)
from src.modules.contact_points.application.contact_point.use_case.resolve_contact_point_targets import (
    ResolveContactPointTargetsUseCase,
)

__all__ = [
    "SyncTargetContactPointsCommand",
    "RemoveTargetContactPointsCommand",
    "GetTargetsContactPointsQuery",
    "ContactPointBindingDTO",
    "SyncTargetContactPointsUseCase",
    "GetTargetsContactPointsUseCase",
    "RemoveTargetContactPointsUseCase",
    "ResolveContactPointTargetsQuery",
    "ResolveContactPointTargetsUseCase",
]
