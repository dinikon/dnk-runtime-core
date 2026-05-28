"""Segment static member use case package."""

__all__: list[str] = []
from src.modules.segmentation.application.segment_static_member.use_case.add_static_member import (
    AddStaticMemberUseCase,
    AddStaticMemberUseCaseProtocol,
)
from src.modules.segmentation.application.segment_static_member.use_case.list_static_members import (
    ListStaticMembersUseCase,
    ListStaticMembersUseCaseProtocol,
)
from src.modules.segmentation.application.segment_static_member.use_case.remove_static_member import (
    RemoveStaticMemberUseCase,
    RemoveStaticMemberUseCaseProtocol,
)

__all__ = [
    "AddStaticMemberUseCase",
    "AddStaticMemberUseCaseProtocol",
    "ListStaticMembersUseCase",
    "ListStaticMembersUseCaseProtocol",
    "RemoveStaticMemberUseCase",
    "RemoveStaticMemberUseCaseProtocol",
]
