from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.application.uuid import UuidPort
from src.modules.shared.infrastructure.uuid import Uuid7Generator

default_uuid_generator: UuidPort = Uuid7Generator()


def get_uuid_generator(request: Request) -> UuidPort:
    """Возвращает UUID generator из app.state или default UUIDv7 generator."""

    from_state = getattr(request.app.state, "uuid_generator", None)
    if from_state is not None:
        return from_state
    return default_uuid_generator


UuidDep = Annotated[UuidPort, Depends(get_uuid_generator)]

__all__ = ["UuidDep", "default_uuid_generator", "get_uuid_generator"]
