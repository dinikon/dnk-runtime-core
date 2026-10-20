from io import BytesIO
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportFilesPort,
)
from src.modules.channels.application.publication_import.command.apply_publication_import_step.command import (
    ApplyPublicationImportStepCommand,
)
from src.modules.channels.application.publication_import.command.apply_publication_import_step.dto import (
    ApplyPublicationImportStepResultDTO,
)
from src.modules.channels.application.publication_import.access import (
    PublicationImportAccess,
)
from src.modules.channels.application.publication_import.port.jobs import (
    PublicationImportJobsPort,
)
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    PreparedImageVO,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class ApplyPublicationImportStepHandler:
    """Сохраняет снимок или результат одного изображения и планирует следующий шаг."""

    def __init__(
        self,
        access: PublicationImportAccess,
        imports: PublicationImportRepositoryProtocol,
        channels: ChannelRepositoryProtocol,
        jobs: PublicationImportJobsPort,
        clock: ClockPort,
        files: PublicationImportFilesPort,
    ) -> None:
        """Получает зависимости единственной транзакции применения."""
        self.access, self.imports, self.channels, self.jobs, self.clock, self.files = (
            access,
            imports,
            channels,
            jobs,
            clock,
            files,
        )

    async def execute(
        self, command: ApplyPublicationImportStepCommand
    ) -> ApplyPublicationImportStepResultDTO:
        """Отбрасывает результаты отменённого, устаревшего или заменённого шага."""
        preparation, source = await self.access.locked(command.preparation_id)
        now = self.clock.now()
        if not preparation.begin(command.sequence, now):
            return ApplyPublicationImportStepResultDTO(False)
        channel = await self.channels.get(
            EntityIdVO(source.channel_id), for_update=False
        )
        connection = channel.require_connection()
        if (
            source.archived
            or connection.is_paused
            or connection.verification_status != "verified"
            or connection.generation != preparation.connection_generation
            or source.observed_revision != preparation.observed_revision
        ):
            preparation.fail("import_source_changed")
        elif command.image_id is not None:
            file_id = None
            if (
                command.error_code is None
                and command.image_data is not None
                and command.image_content_type is not None
            ):
                file_id = await self.files.upload(
                    command.tenant_id,
                    BytesIO(command.image_data),
                    len(command.image_data),
                    command.image_content_type,
                )
            preparation.receive_image(
                command.image_id,
                PreparedImageVO(
                    EntityIdVO(file_id) if file_id else None,
                    command.error_code or (None if file_id else "invalid_image_file"),
                ),
            )
        elif command.error_code:
            preparation.fail(command.error_code)
        elif command.snapshot is not None:
            preparation.receive_snapshot(command.snapshot)
        else:
            preparation.fail("invalid_provider_response")
        await self.imports.save(preparation)
        if preparation.status == "images":
            await self.jobs.prepare(
                command.tenant_id, preparation.id.uuid, preparation.sequence, now
            )
        return ApplyPublicationImportStepResultDTO(True)
