"""Segment static member command package."""

__all__: list[str] = []
from src.modules.segmentation.application.segment_static_member.command.add_static_member_command import (
    AddStaticMemberCommand,
)
from src.modules.segmentation.application.segment_static_member.command.remove_static_member_command import (
    RemoveStaticMemberCommand,
)

__all__ = [
    "AddStaticMemberCommand",
    "RemoveStaticMemberCommand",
]
