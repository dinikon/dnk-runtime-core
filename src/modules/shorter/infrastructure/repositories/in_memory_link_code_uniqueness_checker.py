from __future__ import annotations

from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.link.port import LinkCodeUniquenessCheckerPort


class InMemoryLinkCodeUniquenessChecker(LinkCodeUniquenessCheckerPort):
    def __init__(self, taken_codes: set[tuple[str, str]] | None = None):
        self._taken_codes = taken_codes or set()

    def exists_by_domain_and_code(
        self,
        *,
        domain_id: EntityIdVO,
        code: str,
    ) -> bool:
        return (str(domain_id), code) in self._taken_codes


__all__ = ["InMemoryLinkCodeUniquenessChecker"]
