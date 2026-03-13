from typing import Protocol

from src.modules.shorter.domain.redirect.entity import RedirectEntity
from src.modules.shorter.domain.redirect.value_object import RedirectIdVO


class RedirectRepositoryPort(Protocol):
    async def save(self, redirect: RedirectEntity) -> None: ...

    async def get_by_id(
        self,
        *,
        redirect_id: RedirectIdVO,
    ) -> RedirectEntity | None: ...

    async def list(self) -> tuple[RedirectEntity, ...]: ...

    async def delete_by_id(
        self,
        *,
        redirect_id: RedirectIdVO,
    ) -> bool: ...


__all__ = ["RedirectRepositoryPort"]
