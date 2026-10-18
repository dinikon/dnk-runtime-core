from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import asdict
from hashlib import sha256
import json
from src.modules.channels.application.sync_run.command.apply_publication_initialization.command import (
    ApplyPublicationInitializationCommand,
)
from src.modules.channels.application.sync_run.command.apply_publication_initialization.dto import (
    ApplyPublicationInitializationResultDTO,
)
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.domain.external_publication.repository import (
    ExternalPublicationRepositoryProtocol,
)
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.domain.external_publication.value_object.core import (
    PublicationCoreVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsUnavailableError,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class ApplyPublicationInitializationHandler:
    """Атомарно сохраняет observed, прогресс и следующий job."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        runs: SyncRunRepositoryProtocol,
        publications: ExternalPublicationRepositoryProtocol,
        initialization: InitializationService,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает repositories одной сессии, без доступа к Catalog."""
        self.channels, self.runs, self.publications = (channels, runs, publications)
        self.initialization, self.clock, self.identifiers = (
            initialization,
            clock,
            identifiers,
        )

    async def execute(
        self, command: ApplyPublicationInitializationCommand
    ) -> ApplyPublicationInitializationResultDTO:
        """Отбрасывает stale результат; повтор страницы не меняет счётчики."""
        owner_id = await self.runs.channel_id(EntityIdVO.from_value(command.run_id))
        channel = await self.channels.get(EntityIdVO.from_value(owner_id))
        run = await self.runs.get(EntityIdVO.from_value(command.run_id))
        try:
            run.ensure_step(command.sequence)
            channel.ensure_network(run.generation)
        except (ChannelsConflictError, ChannelsUnavailableError):
            return ApplyPublicationInitializationResultDTO(False, False, run.sequence)
        if command.outcome is None:
            retry = run.fail(
                command.error_code or "read_failed", self.clock.now(), command.retryable
            )
            await self.runs.save(run)
            if retry:
                await self.initialization.schedule(
                    command.tenant_id, run, min(60, 2**run.failures)
                )
            return ApplyPublicationInitializationResultDTO(True, False, run.sequence)
        outcome = command.outcome
        if not outcome.complete and outcome.checkpoint == run.checkpoint:
            run.fail("cursor_did_not_advance", self.clock.now())
            await self.runs.save(run)
            return ApplyPublicationInitializationResultDTO(True, False, run.sequence)
        processed = 0
        for row in outcome.publications:
            core = PublicationCoreVO(**asdict(row.core))
            fingerprint = sha256(
                json.dumps(
                    {
                        "core": asdict(row.core),
                        "version": row.extension_version,
                        "extensions": row.extensions,
                    },
                    sort_keys=True,
                    default=str,
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
            publication = await self.publications.find(
                run.connection_id, core.resource_type, core.external_id
            )
            if publication is None:
                publication = ExternalPublication.create(
                    EntityIdVO.from_value(self.identifiers.new()),
                    run.connection_id,
                    core,
                    row.extension_version,
                    row.extensions,
                    fingerprint,
                    run.id,
                    self.clock.now(),
                )
                await self.publications.add(publication)
                processed += 1
            else:
                processed += int(publication.last_import_run_id != run.id)
                publication.observe(
                    core,
                    row.extension_version,
                    row.extensions,
                    fingerprint,
                    run.id,
                    self.clock.now(),
                )
                await self.publications.save(publication)
        run.advance(
            outcome.checkpoint,
            processed,
            outcome.invalid,
            outcome.complete,
            self.clock.now(),
        )
        await self.runs.save(run)
        if not outcome.complete:
            await self.initialization.schedule(command.tenant_id, run)
        return ApplyPublicationInitializationResultDTO(
            True, outcome.complete, run.sequence
        )
