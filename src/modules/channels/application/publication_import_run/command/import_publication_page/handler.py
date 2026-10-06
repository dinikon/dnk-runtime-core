from uuid import uuid5
from src.modules.channels.domain.external_publication.value_object.identifier import (
    PublicationIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.publication_import_run.command.import_publication_page.command import (
    ImportPublicationPageCommand,
)
from src.modules.channels.application.publication_import_run.command.import_publication_page.dto import (
    ImportPublicationPageResultDTO,
)
from src.modules.channels.application.publication_import_run.worker_state import (
    PublicationImportState,
)
from src.modules.channels.application.publication_import_run.service import (
    schedule_import_page,
)
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.domain.external_publication.repository import (
    PublicationRepositoryProtocol,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class ImportPublicationPageHandler:
    """Сохраняет страницу и курсор вместе с заданием продолжения."""

    def __init__(
        self,
        state: PublicationImportState,
        publications: PublicationRepositoryProtocol,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты короткой общей транзакции сохранения страницы."""
        self._state, self._publications, self._uuids = state, publications, uuids

    async def execute(
        self, command: ImportPublicationPageCommand
    ) -> ImportPublicationPageResultDTO:
        """Повторно проверяет lease и ревизию, затем применяет наблюдаемые снимки."""
        loaded = await self._state.load(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            run_id=command.run_id,
            job_id=command.job_id,
            lock_token=command.lock_token,
        )
        if loaded is None or loaded[1].pages != command.expected_pages:
            return ImportPublicationPageResultDTO(False, False)
        channel, run = loaded
        now = self._state.clock.now()
        for resource in command.page.resources:
            current = await self._publications.find(
                channel.id,
                channel.connection_revision,
                resource.resource_type,
                resource.external_id,
            )
            if current is None:
                publication = ExternalPublication.create(
                    id=PublicationIdVO.from_value(self._uuids.new()),
                    channel_id=channel.id,
                    connection_revision=channel.connection_revision,
                    resource_type=resource.resource_type,
                    external_id=resource.external_id,
                    parent_external_id=resource.parent_external_id,
                    raw_payload=resource.raw_payload,
                    document=resource.document,
                    run_id=run.id,
                    now=now,
                )
            else:
                publication = current.observe(
                    raw_payload=resource.raw_payload,
                    document=resource.document,
                    parent_external_id=resource.parent_external_id,
                    run_id=run.id,
                    now=now,
                )
            await self._publications.save(publication)
        completed = command.page.next_checkpoint is None
        run = run.record_page(
            resources=len(command.page.resources),
            checkpoint=command.page.next_checkpoint or run.checkpoint,
            job_id=EntityIdVO.from_value(uuid5(run.id.uuid, str(run.pages + 1))),
            now=now,
        )
        if completed:
            run = run.finish(error_code=None, now=now)
        else:
            await schedule_import_page(self._state.jobs, run, command.tenant_id, now)
        await self._state.runs.save(run)
        return ImportPublicationPageResultDTO(True, completed)
