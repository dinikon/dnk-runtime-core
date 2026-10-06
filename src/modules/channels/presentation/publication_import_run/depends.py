from typing import Annotated
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.publication_import_run.command.start_publication_import.handler import (
    StartPublicationImportHandler,
)
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.handler import (
    GetPublicationImportRunHandler,
)
from src.modules.channels.application.publication_import_run.service import (
    PublicationImportStarter,
)
from src.modules.channels.application.publication_import_run.worker_state import (
    PublicationImportState,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourcePort,
)
from src.modules.channels.application.publication_import_run.command.prepare_publication_import.command import (
    PreparePublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.command.prepare_publication_import.handler import (
    PreparePublicationImportHandler,
)
from src.modules.channels.application.publication_import_run.command.import_publication_page.command import (
    ImportPublicationPageCommand,
)
from src.modules.channels.application.publication_import_run.command.import_publication_page.handler import (
    ImportPublicationPageHandler,
)
from src.modules.channels.application.publication_import_run.command.complete_publication_import.command import (
    CompletePublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.command.complete_publication_import.handler import (
    CompletePublicationImportHandler,
)
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.channel.port.secret_cipher import SecretCipherPort
from src.modules.channels.application.channel.error import (
    ChannelSecretsUnavailableError,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.channel.definitions.registry import (
    CodeChannelRegistry,
)
from src.modules.channels.infrastructure.channel.crypto.cipher import (
    ChannelSecretCipher,
)
from src.modules.channels.infrastructure.external_publication.persistence.repository import (
    SqlAlchemyPublicationRepository,
)
from src.modules.channels.infrastructure.external_publication.content.html_sanitizer import (
    PublicationHtmlSanitizer,
)
from src.modules.channels.infrastructure.publication_import_run.persistence.repository import (
    SqlAlchemyPublicationImportRunRepository,
)
from src.modules.channels.infrastructure.publication_import_run.persistence.query_repository import (
    SqlAlchemyPublicationImportQueryRepository,
)
from src.modules.channels.infrastructure.publication_import_run.source.http_client import (
    PublicationJsonClient,
)
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    PublicationNormalizer,
)
from src.modules.channels.infrastructure.publication_import_run.source.prom import (
    PromPublicationSource,
)
from src.modules.channels.infrastructure.publication_import_run.source.woocommerce import (
    WooPublicationSource,
)
from src.modules.channels.infrastructure.publication_import_run.source.registry import (
    PublicationSourceRegistry,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.presentation.jobs import build_scheduled_job_repository
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)


def get_import_starter(uow: UoWDep, uuids: UuidDep) -> PublicationImportStarter:
    """Собирает общий запуск с run repository и jobs на одной сессии UoW."""
    return PublicationImportStarter(
        SqlAlchemyPublicationImportRunRepository(uow.session),
        build_scheduled_job_repository(uow.session),
        uuids,
    )


ImportStarterDep = Annotated[PublicationImportStarter, Depends(get_import_starter)]


def get_start_publication_import_handler(
    uow: UoWDep, starter: ImportStarterDep, clock: ClockDep
) -> StartPublicationImportHandler:
    """Собирает HTTP запуск из абстрактных портов общей транзакции."""
    return StartPublicationImportHandler(
        SqlAlchemyChannelRepository(uow.session), starter, clock
    )


StartPublicationImportHandlerDep = Annotated[
    StartPublicationImportHandler, Depends(get_start_publication_import_handler)
]


def get_get_publication_import_run_handler(
    uow: UoWDep,
) -> GetPublicationImportRunHandler:
    """Подключает проекции прогресса и безопасное чтение канала."""
    return GetPublicationImportRunHandler(
        SqlAlchemyPublicationImportQueryRepository(
            uow.session, build_scheduled_job_repository(uow.session)
        ),
        SqlAlchemyChannelQueryRepository(uow.session, CodeChannelRegistry()),
    )


GetPublicationImportRunHandlerDep = Annotated[
    GetPublicationImportRunHandler, Depends(get_get_publication_import_run_handler)
]


def build_publication_source() -> PublicationSourcePort:
    """Собирает HTTP адаптеры и очистку HTML без открытия транзакции."""
    client = PublicationJsonClient()
    normalizer = PublicationNormalizer(PublicationHtmlSanitizer())
    return PublicationSourceRegistry(
        {
            "prom": PromPublicationSource(client, normalizer),
            "woocommerce": WooPublicationSource(client, normalizer),
        }
    )


class PublicationImportJobRuntime:
    """Внешняя сборка фоновых шагов с отдельными короткими UoW и сетевым чтением между ними."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        source: PublicationSourcePort | None = None,
        cipher: SecretCipherPort | None = None,
    ) -> None:
        """Сохраняет зависимости worker, не переиспользуя request-scoped сессии."""
        self._sessions, self._source = sessions, source or build_publication_source()
        self._cipher = cipher or ChannelSecretCipher(
            dnk_config.CHANNELS.secret_encryption_key
        )
        self._clock, self._uuids = UtcClock(), UUID7Generator()
        self._naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)

    def _state(self, session: AsyncSession) -> PublicationImportState:
        """Подключает все порты состояния к одной tenant-сессии текущего шага."""
        return PublicationImportState(
            SqlAlchemyChannelRepository(session),
            SqlAlchemyPublicationImportRunRepository(session),
            build_scheduled_job_repository(session),
            self._clock,
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Собирает шаги worker, коммитит подготовку до HTTP и запись после HTTP."""
        if job.tenant_id is None or not job.lock_token:
            raise ValueError("Invalid publication import job envelope.")
        channel_id, run_id = UUID(job.payload["channel_id"]), UUID(
            job.payload["run_id"]
        )
        args = dict(
            tenant_id=job.tenant_id,
            channel_id=channel_id,
            run_id=run_id,
            job_id=job.id,
            lock_token=job.lock_token,
        )
        try:
            async with self._sessions.kw["bind"].connect() as connection:
                await bind_tenant_schema(connection, job.tenant_id, self._naming)
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(sessions) as uow:
                    prepared = await PreparePublicationImportHandler(
                        self._state(uow.session),
                        self._cipher,
                    ).execute(PreparePublicationImportCommand(**args))
            if prepared is None:
                return
            # No SQL connection or transaction is held while the source is read.
            page = await self._source.read_page(
                prepared.connection, prepared.checkpoint
            )
            async with self._sessions.kw["bind"].connect() as connection:
                await bind_tenant_schema(connection, job.tenant_id, self._naming)
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(sessions) as uow:
                    await ImportPublicationPageHandler(
                        self._state(uow.session),
                        SqlAlchemyPublicationRepository(uow.session),
                        self._uuids,
                    ).execute(
                        ImportPublicationPageCommand(
                            **args, page=page, expected_pages=prepared.pages
                        )
                    )
        except (PublicationSourceError, ChannelSecretsUnavailableError) as exc:
            if (
                isinstance(exc, PublicationSourceError)
                and exc.retryable
                and job.attempts < dnk_config.SCHEDULED_JOBS.max_attempts
            ):
                raise
            code = (
                exc.code
                if isinstance(exc, PublicationSourceError)
                else "secrets_unavailable"
            )
            await self._finish(args, code)
        except Exception:
            if job.attempts >= dnk_config.SCHEDULED_JOBS.max_attempts:
                await self._finish(args, "worker_exhausted")
            raise

    async def _finish(self, args: dict[str, UUID | str], code: str) -> None:
        """Фиксирует безопасную окончательную ошибку отдельным коротким шагом."""
        async with self._sessions.kw["bind"].connect() as connection:
            await bind_tenant_schema(connection, args["tenant_id"], self._naming)
            sessions = async_sessionmaker(connection, expire_on_commit=False)
            async with UnitOfWork(sessions) as uow:
                await CompletePublicationImportHandler(
                    self._state(uow.session)
                ).execute(CompletePublicationImportCommand(**args, error_code=code))
