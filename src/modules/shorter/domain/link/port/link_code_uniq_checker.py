from __future__ import annotations

from typing import Protocol

from modules.shared import EntityIdVO


class LinkCodeUniquenessCheckerPort(Protocol):
    def exists_by_domain_and_code(
        self,
        domain_id: EntityIdVO,
        code: str,
    ) -> bool: ...
