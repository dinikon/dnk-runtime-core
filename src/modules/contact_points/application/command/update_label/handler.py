from src.modules.contact_points.application.command.update_label.command import (
    UpdateContactPointLabelCommand,
)
from src.modules.contact_points.application.command.update_label.dto import (
    UpdateContactPointLabelDTO,
    label_dto,
)
from src.modules.contact_points.domain.label_repository import (
    ContactPointLabelRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class UpdateContactPointLabelHandler:
    """Выполняет update подписи без изменения transaction boundary."""

    def __init__(
        self, repository: ContactPointLabelRepositoryProtocol, clock: ClockPort
    ):
        self.repository, self.clock = repository, clock

    async def execute(
        self, command: UpdateContactPointLabelCommand
    ) -> UpdateContactPointLabelDTO:
        """Сохраняет настройку и возвращает DTO."""
        label = await self.repository.get(
            command.tenant_id, command.label_id, for_update=True
        )
        if label.update(
            name=command.name,
            is_active=command.is_active,
            actor_id=command.actor_id,
            now=self.clock.now(),
        ):
            await self.repository.save(command.tenant_id, label)
        return label_dto(label)


__all__ = ["UpdateContactPointLabelHandler"]
