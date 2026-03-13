from src.modules.shorter.application.redirect.dto import (
    RedirectDTO,
    ResultListRedirectDTO,
)
from src.modules.shorter.application.redirect.query import ListRedirectQuery
from src.modules.shorter.domain.redirect import RedirectRepositoryPort


class ListRedirectUseCase:
    def __init__(self, *, redirect_repository: RedirectRepositoryPort):
        self._redirect_repository = redirect_repository

    async def execute(self, _query: ListRedirectQuery) -> ResultListRedirectDTO:
        items = await self._redirect_repository.list()
        ordered_items = tuple(
            sorted(items, key=lambda item: (item.created_at, str(item.id.value)))
        )
        return ResultListRedirectDTO(
            items=tuple(RedirectDTO.from_entity(item) for item in ordered_items)
        )


__all__ = ["ListRedirectUseCase"]
