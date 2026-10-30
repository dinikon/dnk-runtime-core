from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.import_contracts import (
    FeedImportDetails,
    FeedImportStep,
    PreparedFeedImport,
    FeedSubmissionResult,
    FeedPollResult,
    feed_content_fingerprint,
)
from src.modules.channels.application.content_feed.port.access import (
    FeedAccessPort,
    FeedAuthorizationPort,
)
from src.modules.channels.application.content_feed.port.importer import FeedImporterPort
from src.modules.channels.application.content_feed.port.jobs import FeedImportJobsPort
from src.modules.channels.application.content_feed.port.query_repository import (
    ContentFeedQueryRepositoryProtocol,
)
from src.modules.channels.application.content_feed.service.renderer import FeedRenderer
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.delivery import (
    FeedDeliveryPhase as Phase,
    FeedImportContextVO,
    FeedPublicationVerificationVO,
)
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.repository import (
    ContentFeedRepositoryProtocol,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FeedImports:
    """Координирует одну операцию ContentFeed и короткие этапы Shared Jobs."""

    def __init__(
        self,
        *,
        feeds: ContentFeedRepositoryProtocol,
        queries: ContentFeedQueryRepositoryProtocol,
        channels: ChannelRepositoryProtocol,
        platforms: PlatformRegistry,
        renderer: FeedRenderer,
        importer: FeedImporterPort,
        access: FeedAccessPort,
        authorization: FeedAuthorizationPort,
        jobs: FeedImportJobsPort,
        cipher: Cipher,
        uow: UnitOfWorkProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        tenant_id: UUID,
    ) -> None:
        """Принимает порты одной внешней сборки, не открывает собственный UoW."""
        self.feeds = feeds
        self.queries = queries
        self.channels = channels
        self.platforms = platforms
        self.renderer = renderer
        self.importer = importer
        self.access = access
        self.authorization = authorization
        self.jobs = jobs
        self.cipher = cipher
        self.uow = uow
        self.clock = clock
        self.uuid = uuid
        self.tenant_id = tenant_id

    async def details(self, *, channel_id: UUID, feed_id: UUID) -> FeedImportDetails:
        """Читает бизнес-состояние и доступные действия без секретного запроса."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        state = feed.delivery
        recovery = bool(
            state.phase
            in {Phase.QUEUED, Phase.SUBMITTING, Phase.PROCESSING, Phase.VERIFYING}
            and state.current_job_id is not None
            and not await self.jobs.active(
                tenant_id=self.tenant_id, job_id=state.current_job_id.uuid
            )
        )
        attach = (
            state.phase in {Phase.UNKNOWN, Phase.NEEDS_ATTENTION}
            and state.external_import_id is None
            and state.context is not None
        )
        return FeedImportDetails(
            state,
            recovery,
            feed.enabled and not state.busy,
            (recovery or state.phase == Phase.NEEDS_ATTENTION)
            and (
                state.external_import_id is not None
                or state.phase in {Phase.QUEUED, Phase.SUBMITTING}
            ),
            attach,
            state.phase in {Phase.UNKNOWN, Phase.NEEDS_ATTENTION}
            and state.external_import_id is None,
        )

    async def request(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        actor_id: UUID,
        request_id: UUID,
        expected_revision: int,
        expected_delivery_revision: int,
        force_update: bool,
    ) -> FeedImportDetails:
        """Сохраняет намерение и первое задание атомарно, без внешнего API."""
        channel = await self._channel(channel_id, for_update=True)
        if (
            "apply_content_feed"
            not in self.platforms.get(
                channel.platform_kind
            ).manifest.supported_capabilities
        ):
            raise FeedBuildError("feed_import_unsupported")
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        if feed.access_token_encrypted is None:
            raise ContentFeedError("feed_import_disabled")
        self.access.url(feed.id.uuid, feed.access_token_encrypted)
        previous = feed.delivery.revision
        started = feed.request_import(
            operation_id=EntityIdVO(request_id),
            actor_id=EntityIdVO(actor_id),
            job_id=EntityIdVO(self.uuid.new()),
            expected_revision=expected_revision,
            expected_delivery_revision=expected_delivery_revision,
            force_update=force_update,
            now=self.clock.now(),
        )
        if started:
            await self.feeds.save_delivery(
                feed,
                expected_revision=feed.revision,
                expected_delivery_revision=previous,
            )
            await self._schedule(feed, channel_id, delay=0)
        return await self.details(channel_id=channel_id, feed_id=feed_id)

    async def resume(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_delivery_revision: int,
    ) -> FeedImportDetails:
        """Возобновляет безопасное чтение либо подготовку, но никогда не повторяет submitting."""
        feed = await self._editable(
            channel_id, feed_id, expected_revision, expected_delivery_revision
        )
        if feed.delivery.current_job_id is not None and await self.jobs.active(
            tenant_id=self.tenant_id, job_id=feed.delivery.current_job_id.uuid
        ):
            raise ContentFeedError("feed_import_active", conflict=True)
        previous = feed.delivery.revision
        if feed.delivery.phase == Phase.SUBMITTING:
            feed.record_submission_failure(
                code="feed_import_acceptance_unknown",
                uncertain=True,
                now=self.clock.now(),
            )
        else:
            feed.resume_import(
                job_id=EntityIdVO(self.uuid.new()),
                actor_id=EntityIdVO(actor_id),
                now=self.clock.now(),
            )
            await self._schedule(feed, channel_id, delay=0)
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )
        return await self.details(channel_id=channel_id, feed_id=feed_id)

    async def attach(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_delivery_revision: int,
        external_id: str,
    ) -> FeedImportDetails:
        """Проверяет доступный итоговый отчёт и фиксирует ручную привязку ID с аудитом."""
        feed = await self._editable(
            channel_id, feed_id, expected_revision, expected_delivery_revision
        )
        if (
            feed.delivery.phase not in {Phase.UNKNOWN, Phase.NEEDS_ATTENTION}
            or feed.delivery.external_import_id is not None
        ):
            raise ContentFeedError("feed_import_attach_forbidden", conflict=True)
        channel = await self._channel(channel_id)
        self._identity_matches(feed, channel)
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=()
        )
        credentials = self.cipher.decrypt(channel.connection.encrypted_credentials)
        config = channel.connection.config
        await self.uow.commit()
        result = await self.importer.poll(
            config=config, credentials=credentials, external_id=external_id
        )
        if result.report is None:
            raise FeedBuildError("feed_import_id_not_verified")
        feed = await self._editable(
            channel_id, feed_id, expected_revision, expected_delivery_revision
        )
        previous = feed.delivery.revision
        job = EntityIdVO(self.uuid.new())
        feed.record_acceptance(
            external_id=external_id, job_id=job, now=self.clock.now(), manual=True
        )
        feed.record_report(report=result.report, job_id=job, now=self.clock.now())
        # Новый инициатор явно принимает ответственность за ручную привязку.
        feed.resume_import(
            job_id=job, actor_id=EntityIdVO(actor_id), now=self.clock.now()
        )
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )
        await self._schedule(feed, channel_id, delay=0)
        return await self.details(channel_id=channel_id, feed_id=feed_id)

    async def resolve(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_delivery_revision: int,
    ) -> FeedImportDetails:
        """Фиксирует отдельное ручное решение, не создавая повторного POST."""
        feed = await self._editable(
            channel_id, feed_id, expected_revision, expected_delivery_revision
        )
        previous = feed.delivery.revision
        feed.resolve_unknown_import(actor_id=EntityIdVO(actor_id), now=self.clock.now())
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )
        return await self.details(channel_id=channel_id, feed_id=feed_id)

    async def claim(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        operation_id: UUID,
        job_id: UUID,
        lock_token: str,
    ) -> FeedImportStep | None:
        """Проверяет lease, текущую операцию и фазу до любых внешних вызовов."""
        feed = await self._owned(channel_id, feed_id, operation_id, job_id, lock_token)
        if feed is None:
            return None
        previous = feed.delivery.revision
        if feed.delivery.phase == Phase.SUBMITTING:
            feed.record_submission_failure(
                code="feed_import_acceptance_unknown",
                uncertain=True,
                now=self.clock.now(),
            )
            await self.feeds.save_delivery(
                feed,
                expected_revision=feed.revision,
                expected_delivery_revision=previous,
            )
            return None
        if feed.delivery.phase not in {Phase.QUEUED, Phase.PROCESSING, Phase.VERIFYING}:
            return None
        if (
            feed.delivery.tracking_deadline is not None
            and self.clock.now() >= feed.delivery.tracking_deadline
        ):
            feed.require_attention(
                code="feed_import_tracking_expired", now=self.clock.now()
            )
            await self.feeds.save_delivery(
                feed,
                expected_revision=feed.revision,
                expected_delivery_revision=previous,
            )
            return None
        channel = await self._channel(channel_id)
        self._identity_matches(feed, channel)
        assert channel.connection.identity is not None
        assert feed.delivery.actor_id is not None
        await self.authorization.require(
            actor_id=feed.delivery.actor_id.uuid, channel_id=channel_id, file_ids=()
        )
        if feed.delivery.phase == Phase.QUEUED and not feed.enabled:
            feed.record_submission_failure(
                code="feed_import_disabled", uncertain=False, now=self.clock.now()
            )
            await self.feeds.save_delivery(
                feed,
                expected_revision=feed.revision,
                expected_delivery_revision=previous,
            )
            return None
        return FeedImportStep(
            feed_id,
            channel_id,
            operation_id,
            job_id,
            feed.delivery.actor_id.uuid,
            feed.delivery.phase.value,
            channel.connection.config,
            channel.connection.config_revision,
            channel.connection.identity.namespace,
            channel.connection.identity.key,
            channel.connection.encrypted_credentials,
            feed.delivery_request_encrypted,
            feed.delivery.external_import_id,
            feed.revision,
            feed.delivery.force_update,
        )

    async def prepare(self, step: FeedImportStep) -> PreparedFeedImport:
        """Формирует актуальный XML общим renderer и выполняет preflight вне SQL-транзакции."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(step.channel_id), feed_id=EntityIdVO(step.feed_id)
        )
        document = await self.renderer.render(
            feed=feed, channel_id=step.channel_id, actor_id=step.actor_id
        )
        if document.snapshot is None or feed.access_token_encrypted is None:
            raise FeedBuildError("feed_import_snapshot_missing")
        url = self.access.url(feed.id.uuid, feed.access_token_encrypted)
        credentials = self.cipher.decrypt(step.encrypted_credentials)
        await self.uow.commit()
        payload = await self.importer.prepare(
            config=step.config,
            credentials=credentials,
            document=document,
            feed_url=url,
            force_update=step.force_update,
        )
        context = FeedImportContextVO(
            step.feed_revision,
            step.connection_revision,
            step.identity_namespace,
            step.identity_key,
            feed_content_fingerprint(document.snapshot),
        )
        return PreparedFeedImport(payload, context)

    async def begin(
        self, step: FeedImportStep, prepared: PreparedFeedImport, *, lock_token: str
    ) -> bool:
        """Сохраняет submitting под барьером Channel, до POST и с действующей lease."""
        feed = await self._owned(
            step.channel_id, step.feed_id, step.operation_id, step.job_id, lock_token
        )
        if feed is None:
            return False
        channel = await self._channel(step.channel_id)
        self._identity_matches(feed, channel)
        if (
            channel.connection.config_revision != step.connection_revision
            or feed.revision != step.feed_revision
        ):
            raise FeedBuildError("feed_import_context_changed")
        snapshot = await self.renderer.representations.snapshot(
            channel_id=step.channel_id, connection_id=feed.connection_id.uuid
        )
        if feed_content_fingerprint(snapshot) != prepared.context.content_fingerprint:
            raise FeedBuildError("feed_import_context_changed")
        files = tuple(
            sorted(
                {
                    image.file_id.uuid
                    for group in snapshot.groups
                    for target in group.targets
                    for content in target.content
                    for image in content.gallery or ()
                }
            )
        )
        await self.authorization.require(
            actor_id=step.actor_id, channel_id=step.channel_id, file_ids=files
        )
        previous = feed.delivery.revision
        feed.begin_submission(
            context=prepared.context,
            encrypted_request=self.cipher.encrypt(prepared.payload),
            now=self.clock.now(),
        )
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )
        return True

    async def apply_submission(
        self, step: FeedImportStep, result: FeedSubmissionResult, *, lock_token: str
    ) -> None:
        """Закрепляет внешний факт по операции и lease даже после выключения фида."""
        feed = await self._owned(
            step.channel_id, step.feed_id, step.operation_id, step.job_id, lock_token
        )
        if feed is None:
            return
        previous = feed.delivery.revision
        if result.outcome == "accepted" and result.external_id is not None:
            feed.record_acceptance(
                external_id=result.external_id,
                job_id=EntityIdVO(self.uuid.new()),
                now=self.clock.now(),
            )
            await self._schedule(feed, step.channel_id, delay=10)
        else:
            feed.record_submission_failure(
                code=result.error_code or "feed_import_acceptance_unknown",
                uncertain=result.outcome != "rejected",
                now=self.clock.now(),
            )
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )

    async def apply_poll(
        self, step: FeedImportStep, result: FeedPollResult, *, lock_token: str
    ) -> None:
        """Сохраняет отчёт и следующее задание атомарно; без отчёта POST не повторяется."""
        feed = await self._owned(
            step.channel_id, step.feed_id, step.operation_id, step.job_id, lock_token
        )
        if feed is None:
            return
        previous = feed.delivery.revision
        if result.blocked:
            feed.require_attention(
                code=result.error_code or "feed_import_access_denied",
                now=self.clock.now(),
            )
        elif result.report is not None:
            feed.record_report(
                report=result.report,
                job_id=EntityIdVO(self.uuid.new()),
                now=self.clock.now(),
            )
            await self._schedule(feed, step.channel_id, delay=0)
        elif (
            feed.delivery.tracking_deadline is not None
            and self.clock.now() >= feed.delivery.tracking_deadline
        ):
            feed.require_attention(
                code="feed_import_tracking_expired", now=self.clock.now()
            )
        else:
            feed.wait_for_report(
                job_id=EntityIdVO(self.uuid.new()),
                now=self.clock.now(),
                code=result.error_code,
            )
            elapsed = (
                (self.clock.now() - feed.delivery.requested_at).total_seconds()
                if feed.delivery.requested_at
                else 0
            )
            await self._schedule(
                feed, step.channel_id, delay=min(60, max(10, int(elapsed)))
            )
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )

    async def apply_verification(
        self,
        step: FeedImportStep,
        results: tuple[FeedPublicationVerificationVO, ...],
        *,
        lock_token: str,
    ) -> None:
        """Отмечает устаревший снимок и сохраняет проверку каждого поля независимо от отчёта."""
        feed = await self._owned(
            step.channel_id, step.feed_id, step.operation_id, step.job_id, lock_token
        )
        if feed is None:
            return
        previous = feed.delivery.revision
        assert feed.delivery.context is not None
        changed = feed.revision != feed.delivery.context.feed_revision
        files = ()
        try:
            snapshot = await self.renderer.representations.snapshot(
                channel_id=step.channel_id, connection_id=feed.connection_id.uuid
            )
            changed = (
                changed
                or feed_content_fingerprint(snapshot)
                != feed.delivery.context.content_fingerprint
            )
            files = tuple(
                sorted(
                    {
                        image.file_id.uuid
                        for group in snapshot.groups
                        for target in group.targets
                        for content in target.content
                        for image in content.gallery or ()
                    }
                )
            )
        except FeedBuildError:
            changed = True
        await self.authorization.require(
            actor_id=step.actor_id, channel_id=step.channel_id, file_ids=files
        )
        if changed:
            results = tuple(
                replace(
                    value,
                    fields=tuple(
                        replace(field, status="obsolete") for field in value.fields
                    ),
                )
                for value in results
            )
        report = feed.delivery.report
        issue = (
            "feed_import_context_changed"
            if changed
            else (
                "feed_import_report_requires_attention"
                if report is None
                or report.status != "SUCCESS"
                or report.created != 0
                or report.with_errors_count != 0
                or report.issues
                else (
                    "feed_import_content_unconfirmed"
                    if not results
                    or any(
                        field.status != "confirmed"
                        for value in results
                        for field in value.fields
                    )
                    else None
                )
            )
        )
        feed.record_verification(results=results, now=self.clock.now(), code=issue)
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )

    async def fail(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        operation_id: UUID,
        job_id: UUID,
        lock_token: str,
        code: str,
    ) -> None:
        """Останавливает ожидаемый отказ, предотвращая бесконечные технические retries."""
        feed = await self._owned(channel_id, feed_id, operation_id, job_id, lock_token)
        if feed is None:
            return
        previous = feed.delivery.revision
        if feed.delivery.phase in {Phase.SUBMITTING, Phase.QUEUED}:
            feed.record_submission_failure(
                code=code,
                uncertain=feed.delivery.phase == Phase.SUBMITTING,
                now=self.clock.now(),
            )
        elif feed.delivery.busy:
            feed.require_attention(code=code, now=self.clock.now())
        else:
            return
        await self.feeds.save_delivery(
            feed, expected_revision=feed.revision, expected_delivery_revision=previous
        )

    async def _channel(self, channel_id: UUID, *, for_update: bool = False) -> Channel:
        """Требует актуальную верификацию до использования credentials."""
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=for_update)
        if channel is None:
            raise ContentFeedError("feed_channel_not_found")
        connection = channel.connection
        if (
            connection.identity is None
            or connection.verification.status != "verified"
            or connection.verification.config_revision != connection.config_revision
        ):
            raise FeedBuildError("feed_connection_unverified")
        return channel

    @staticmethod
    def _identity_matches(feed: ContentFeed, channel: Channel) -> None:
        """Известный импорт никогда не отслеживается в другом магазине."""
        context = feed.delivery.context
        identity = channel.connection.identity
        if context is not None and (
            identity is None
            or identity.namespace != context.identity_namespace
            or identity.key != context.identity_key
        ):
            raise FeedBuildError("feed_import_identity_changed")

    async def _editable(
        self, channel_id: UUID, feed_id: UUID, revision: int, delivery_revision: int
    ) -> ContentFeed:
        """Проверяет оба счётчика до ручного изменения состояния."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.require_revision(revision)
        feed.delivery.require_revision(delivery_revision)
        return feed

    async def _owned(
        self,
        channel_id: UUID,
        feed_id: UUID,
        operation_id: UUID,
        job_id: UUID,
        lock_token: str,
    ) -> ContentFeed | None:
        """Отсекает старые задания до чтения настроек и любых внешних вызовов."""
        if not await self.jobs.owns(
            tenant_id=self.tenant_id, job_id=job_id, lock_token=lock_token
        ):
            return None
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        if feed.delivery.operation_id != EntityIdVO(
            operation_id
        ) or feed.delivery.current_job_id != EntityIdVO(job_id):
            return None
        return feed

    async def _schedule(
        self, feed: ContentFeed, channel_id: UUID, *, delay: int
    ) -> None:
        """Ставит отдельный короткий этап без ожидания внутри worker."""
        assert (
            feed.delivery.operation_id is not None
            and feed.delivery.current_job_id is not None
        )
        await self.jobs.schedule(
            tenant_id=self.tenant_id,
            channel_id=channel_id,
            feed_id=feed.id.uuid,
            operation_id=feed.delivery.operation_id.uuid,
            job_id=feed.delivery.current_job_id.uuid,
            run_at=self.clock.now() + timedelta(seconds=delay),
        )
