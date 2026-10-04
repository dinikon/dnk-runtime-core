from src.modules.contact_points.application.label.command.create_label.command import (
    CreateContactPointLabelCommand,
)
from src.modules.contact_points.application.label.command.create_label.dto import (
    CreateContactPointLabelDTO,
    label_dto,
)
from src.modules.contact_points.domain.label.aggregate import ContactPointLabel
from src.modules.contact_points.domain.label.repository import (
    ContactPointLabelRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class CreateContactPointLabelHandler:
    """Выполняет create подписи без изменения transaction boundary."""

    def __init__(
        self, repository: ContactPointLabelRepositoryProtocol, clock: ClockPort
    ):
        self.repository, self.clock = repository, clock

    async def execute(
        self, command: CreateContactPointLabelCommand
    ) -> CreateContactPointLabelDTO:
        """Сохраняет настройку и возвращает DTO."""
        label = ContactPointLabel.create(
            label_id=command.label_id,
            point_type=command.type,
            name=command.name,
            actor_id=command.actor_id,
            now=self.clock.now(),
        )
        await self.repository.add(command.tenant_id, label)
        return label_dto(label)


__all__ = ["CreateContactPointLabelHandler"]
