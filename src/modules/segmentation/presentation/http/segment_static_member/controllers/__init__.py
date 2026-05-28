from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_static_member.controllers import (
    add_static_member,
    list_static_members,
    remove_static_member,
)

routers: tuple[APIRouter, ...] = (
    add_static_member.router,
    list_static_members.router,
    remove_static_member.router,
)

__all__ = ["routers"]
