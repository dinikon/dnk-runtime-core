from src.modules.shorter.application.redirect.dto import RedirectDTO
from src.modules.shorter.application.redirect.query import GetRedirectQuery
from src.modules.shorter.domain.errors import RedirectNotFoundError
from src.modules.shorter.domain.redirect import RedirectIdVO, RedirectRepositoryPort


class GetRedirectUseCase:
    def __init__(self, *, redirect_repository: RedirectRepositoryPort):
        self._redirect_repository = redirect_repository

    async def execute(self, query: GetRedirectQuery) -> RedirectDTO:
        redirect = await self._redirect_repository.get_by_id(
            redirect_id=RedirectIdVO.from_value(query.redirect_id)
        )
        if redirect is None:
            raise RedirectNotFoundError(redirect_id=str(query.redirect_id))
        return RedirectDTO.from_entity(redirect)


__all__ = ["GetRedirectUseCase"]
