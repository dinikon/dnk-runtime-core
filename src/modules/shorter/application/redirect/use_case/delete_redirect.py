from src.modules.shorter.application.redirect.command import DeleteRedirectCommand
from src.modules.shorter.application.redirect.dto import ResultDeleteRedirectDTO
from src.modules.shorter.domain.errors import RedirectNotFoundError
from src.modules.shorter.domain.redirect import RedirectIdVO, RedirectRepositoryPort


class DeleteRedirectUseCase:
    def __init__(self, *, redirect_repository: RedirectRepositoryPort):
        self._redirect_repository = redirect_repository

    async def execute(
        self,
        command: DeleteRedirectCommand,
    ) -> ResultDeleteRedirectDTO:
        redirect_id = RedirectIdVO.from_value(command.redirect_id)
        deleted = await self._redirect_repository.delete_by_id(redirect_id=redirect_id)
        if not deleted:
            raise RedirectNotFoundError(redirect_id=str(command.redirect_id))
        return ResultDeleteRedirectDTO(redirect_id=command.redirect_id)


__all__ = ["DeleteRedirectUseCase"]
