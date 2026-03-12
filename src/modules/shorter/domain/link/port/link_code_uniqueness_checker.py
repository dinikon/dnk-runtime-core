from typing import Protocol

from src.modules.shared import EntityIdVO


class LinkCodeUniquenessCheckerPort(Protocol):
    def exists_by_domain_and_code(
        self,
        *,
        domain_id: EntityIdVO,
        code: str,
    ) -> bool: ...
