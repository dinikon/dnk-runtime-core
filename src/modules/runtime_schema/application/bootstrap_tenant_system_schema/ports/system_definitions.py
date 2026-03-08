from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.modules.runtime_schema.domain.entities import SystemObjectDefinition


class SystemObjectDefinitionsProviderProtocol(Protocol):
    def get_system_objects(self) -> Sequence[SystemObjectDefinition]: ...
