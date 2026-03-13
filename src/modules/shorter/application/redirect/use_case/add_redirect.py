from src.modules.shared import ClockProtocol
from src.modules.shorter.application.redirect.command import AddRedirectCommand
from src.modules.shorter.application.redirect.dto import RedirectDTO
from src.modules.shorter.domain.redirect import (
    RedirectEntity,
    RedirectRepositoryPort,
    RedirectTargetUrlVO,
    RedirectUtmParametersVO,
)


class AddRedirectUseCase:
    def __init__(
        self,
        *,
        clock: ClockProtocol,
        redirect_repository: RedirectRepositoryPort,
    ):
        self._clock = clock
        self._redirect_repository = redirect_repository

    async def execute(self, command: AddRedirectCommand) -> RedirectDTO:
        redirect = RedirectEntity.create(
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
            created_at=self._clock.now(),
        )
        await self._redirect_repository.save(redirect)
        return RedirectDTO.from_entity(redirect)


__all__ = ["AddRedirectUseCase"]
