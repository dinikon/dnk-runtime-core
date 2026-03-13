from src.modules.shared import ClockProtocol
from src.modules.shorter.application.redirect.command import UpdateRedirectCommand
from src.modules.shorter.application.redirect.dto import RedirectDTO
from src.modules.shorter.domain.errors import RedirectNotFoundError
from src.modules.shorter.domain.redirect import (
    RedirectIdVO,
    RedirectRepositoryPort,
    RedirectTargetUrlVO,
    RedirectUtmParametersVO,
)


class UpdateRedirectUseCase:
    def __init__(
        self,
        *,
        clock: ClockProtocol,
        redirect_repository: RedirectRepositoryPort,
    ):
        self._clock = clock
        self._redirect_repository = redirect_repository

    async def execute(self, command: UpdateRedirectCommand) -> RedirectDTO:
        redirect_id = RedirectIdVO.from_value(command.redirect_id)
        redirect = await self._redirect_repository.get_by_id(redirect_id=redirect_id)
        if redirect is None:
            raise RedirectNotFoundError(redirect_id=str(command.redirect_id))

        redirect.update(
            target_url=RedirectTargetUrlVO(command.target_url),
            utm_parameters=RedirectUtmParametersVO(
                utm_source=command.utm_source,
                utm_medium=command.utm_medium,
                utm_campaign=command.utm_campaign,
                utm_id=command.utm_id,
                utm_term=command.utm_term,
                utm_content=command.utm_content,
            ),
            is_override=command.is_override,
            is_append=command.is_append,
            updated_at=self._clock.now(),
        )
        await self._redirect_repository.save(redirect)
        return RedirectDTO.from_entity(redirect)


__all__ = ["UpdateRedirectUseCase"]
