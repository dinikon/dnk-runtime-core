from typing import Protocol

from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.application.contact.integration_events import contact_deleted_event
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.shared.application.events import OutboxRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class DeleteContactUseCaseProtocol(Protocol):
    """Порт use case удаления контакта."""

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Удаляет контакт tenant."""
        ...


class DeleteContactUseCase:
    """Use case удаления CRM-контакта."""

    def __init__(
        self,
        *,
        command_repository: ContactCommandRepositoryProtocol,
        outbox_repository: OutboxRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case командным репозиторием контактов."""
        self._command_repository = command_repository
        self._outbox_repository = outbox_repository
        self._clock = clock

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Выполняет команду удаления контакта."""
        contact = await self._command_repository.load(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(str(command.contact_id))

        await self._command_repository.delete(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
        await self._outbox_repository.add(
            contact_deleted_event(
                tenant_id=command.tenant_id.uuid,
                contact_id=command.contact_id.uuid,
                occurred_at=self._clock.now(),
                actor_id=command.actor_id,
                reason=None,
            )
        )
