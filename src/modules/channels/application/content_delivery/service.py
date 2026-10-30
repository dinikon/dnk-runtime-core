from dataclasses import dataclass, replace
from uuid import UUID

from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryResult,
    ContentReconciliationResult,
    ContentDeliveryRow,
    ContentWorkSnapshot,
    ContentWriteOutcome,
    PreparedContentRequest,
    ContentMediaResult,
    ContentMediaSource,
)
from src.modules.channels.application.content_delivery.planning import (
    content_fingerprint,
)
from src.modules.channels.application.content_delivery.port.access import (
    ContentDeliveryAuthorizationPort,
)
from src.modules.channels.application.content_delivery.port.jobs import (
    ContentDeliveryJobsPort,
)
from src.modules.channels.application.content_delivery.port.query_repository import (
    ContentDeliveryQueryRepositoryProtocol,
)
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationContext,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.content_delivery.repository import (
    ContentDeliveryRepositoryProtocol,
)
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryContextVO,
    DeliveryMediaVO,
    DeliveryStatus,
    DeliveryFieldIssueVO,
)
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.domain.product_representation.value_object import (
    PreparedPublicationContent,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import CiphertextUnreadable
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentDeliveryDeferred(Exception):
    """Ожидает независимую цель или media без расходования попыток записи."""


@dataclass(frozen=True, slots=True)
class DeliveryFilesAuthorization:
    """Связывает сохранённого инициатора с существующим портом медиаподготовки."""

    access: ContentDeliveryAuthorizationPort
    actor_id: UUID
    channel_id: UUID

    async def require_files(self, file_ids: tuple[UUID, ...]) -> None:
        """Повторно проверяет актуальные права перед выдачей внешнего URL."""
        await self.access.require(
            actor_id=self.actor_id, channel_id=self.channel_id, file_ids=file_ids
        )


class ContentDeliveries:
    """Координирует подготовку и запись; сетевой вызов выполняет внешний Worker."""

    def __init__(
        self,
        *,
        galleries: MediaGalleries,
        transfers: MediaTransfers,
        channels: ChannelRepositoryProtocol,
        deliveries: ContentDeliveryRepositoryProtocol,
        queries: ContentDeliveryQueryRepositoryProtocol,
        jobs: ContentDeliveryJobsPort,
        authorization: ContentDeliveryAuthorizationPort,
        platforms: PlatformRegistry,
        cipher: Cipher,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает порты одной сессии UoW и готовые сервисы representation/media."""
        self.galleries, self.transfers, self.channels = galleries, transfers, channels
        self.deliveries, self.queries, self.jobs = deliveries, queries, jobs
        self.authorization, self.platforms, self.cipher = (
            authorization,
            platforms,
            cipher,
        )
        self.clock, self.uuid = clock, uuid

    async def request(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
        fingerprint: str,
    ) -> tuple[ContentDeliveryRow, ...]:
        """Принимает только проверенный снимок; Jobs и поколения сохраняются атомарно."""
        context, _ = await self.galleries.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self.galleries.reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        draft = await self.galleries.drafts.prepare(
            context=context,
            overrides=context.state.overrides,
            as_of=self.clock.now(),
            for_update=True,
        )
        self._require_export(context, draft.export_blockers)
        platform = self.platforms.get(context.channel.platform_kind)
        issues = platform.content_issues(draft.prepared.preparation.targets)
        if issues:
            raise ContentDeliveryError(issues[0].code)
        if fingerprint != content_fingerprint(draft.prepared):
            raise ContentDeliveryError("content_preview_changed", conflict=True)
        file_ids = tuple(
            sorted(
                {
                    image.file_id.uuid
                    for target in draft.prepared.preparation.targets
                    for content in target.content
                    for image in content.gallery or ()
                }
            )
        )
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=file_ids
        )
        self.cipher.require_configured()
        assert context.state.id is not None
        for target in sorted(
            draft.prepared.preparation.targets,
            key=lambda v: (
                v.parent_publication_id is not None,
                str(v.publication_id.uuid),
            ),
        ):
            wanted = self._target_context(
                context,
                target,
                draft.prepared.preparation.targets,
                actor_id,
                fingerprint,
            )
            delivery = await self.deliveries.get(
                EntityIdVO(context.state.id), target.publication_id
            )
            if delivery is None:
                delivery = ContentDelivery.create(
                    representation_id=EntityIdVO(context.state.id),
                    publication_id=target.publication_id,
                    context=wanted,
                    job_id=EntityIdVO(self.uuid.new()),
                    now=self.clock.now(),
                )
            else:
                changed = delivery.request_update(
                    context=wanted,
                    job_id=EntityIdVO(self.uuid.new()),
                    now=self.clock.now(),
                )
                if (
                    not changed
                    and delivery.status is DeliveryStatus.QUEUED
                    and not await self.jobs.active(
                        tenant_id=tenant_id, job_id=delivery.current_job_id.uuid
                    )
                ):
                    delivery.recover_queued(
                        job_id=EntityIdVO(self.uuid.new()), now=self.clock.now()
                    )
            await self.deliveries.save(delivery)
            if delivery.status is DeliveryStatus.QUEUED:
                await self.jobs.schedule(
                    tenant_id=tenant_id, delivery=delivery, now=self.clock.now()
                )
        return await self.read(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )

    async def read(
        self, *, tenant_id: UUID, channel_id: UUID, group_id: UUID
    ) -> tuple[ContentDeliveryRow, ...]:
        """Возвращает безопасные проекции, включая утраченное задание."""
        context = await self.galleries.reader.load(
            channel_id=channel_id, group_id=group_id
        )
        if context.state.id is None:
            return ()
        rows = await self.queries.for_representation(context.state.id)
        result: list[ContentDeliveryRow] = []
        for row in rows:
            recovery = row.status in {
                "queued",
                "in_flight",
                "unknown",
            } and not await self.jobs.active(
                tenant_id=tenant_id, job_id=row.current_job_id
            )
            result.append(replace(row, recovery_required=recovery))
        return tuple(
            sorted(result, key=lambda v: (v.role != "container", v.external_id))
        )

    async def reconcile(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        publication_id: UUID,
        expected_revision: int,
    ) -> tuple[ContentDeliveryRow, ...]:
        """Планирует только сверку; утраченный in_flight тоже считается неоднозначным."""
        context, _ = await self.galleries.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        if context.state.id is None:
            raise ContentDeliveryError("content_delivery_not_found")
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=()
        )
        delivery = await self.deliveries.get(
            EntityIdVO(context.state.id), EntityIdVO(publication_id)
        )
        if delivery is None:
            raise ContentDeliveryError("content_delivery_not_found")
        if delivery.revision != expected_revision:
            raise ContentDeliveryError("content_revision_conflict", conflict=True)
        if await self.jobs.active(
            tenant_id=tenant_id, job_id=delivery.current_job_id.uuid
        ):
            raise ContentDeliveryError("content_attempt_active", conflict=True)
        if delivery.status is DeliveryStatus.IN_FLIGHT:
            assert (
                delivery.sending_generation is not None
                and delivery.prepared_hash is not None
            )
            delivery.complete_attempt(
                job_id=delivery.current_job_id,
                generation=delivery.sending_generation,
                content_hash=delivery.prepared_hash,
                fields=(),
                error_code="content_worker_interrupted",
                uncertain=True,
                now=self.clock.now(),
            )
        delivery.request_reconciliation(
            expected_revision=delivery.revision,
            job_id=EntityIdVO(self.uuid.new()),
            now=self.clock.now(),
        )
        await self.deliveries.save(delivery)
        await self.jobs.schedule(
            tenant_id=tenant_id, delivery=delivery, now=self.clock.now()
        )
        return await self.read(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )

    async def resolve(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        publication_id: UUID,
        expected_revision: int,
        acknowledge_unconfirmed: bool,
    ) -> tuple[ContentDeliveryRow, ...]:
        """Завершает unknown по явному решению; media и последний успех не подменяются."""
        if acknowledge_unconfirmed is not True:
            raise ContentDeliveryError("content_resolution_confirmation_required")
        context, _ = await self.galleries.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        if context.state.id is None:
            raise ContentDeliveryError("content_delivery_not_found")
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=()
        )
        delivery = await self.deliveries.get(
            EntityIdVO(context.state.id), EntityIdVO(publication_id)
        )
        if delivery is None:
            raise ContentDeliveryError("content_delivery_not_found")
        if await self.jobs.active(
            tenant_id=tenant_id, job_id=delivery.current_job_id.uuid
        ):
            raise ContentDeliveryError("content_attempt_active", conflict=True)
        delivery.resolve_uncertainty(
            expected_revision=expected_revision, now=self.clock.now()
        )
        await self.deliveries.save(delivery)
        return await self.read(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )

    async def prepare(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        representation_id: UUID,
        publication_id: UUID,
        job_id: UUID,
        lock_token: str,
    ) -> ContentWorkSnapshot | None:
        """Готовит запрос под обычным порядком locks; storage проверяется вне SQL."""
        if not await self.jobs.owns(
            tenant_id=tenant_id, job_id=job_id, lock_token=lock_token
        ):
            return None
        await self.galleries.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        delivery = await self.deliveries.get(
            EntityIdVO(representation_id), EntityIdVO(publication_id)
        )
        if (
            delivery is None
            or delivery.current_job_id.uuid != job_id
            or delivery.requested_context.channel_id.uuid != channel_id
            or delivery.requested_context.group_id.uuid != group_id
        ):
            return None
        if delivery.status in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}:
            return await self._snapshot(delivery, reconcile=True)
        if delivery.status is not DeliveryStatus.QUEUED:
            return None
        expected = delivery.requested_context
        reserved = False
        try:
            context, _ = await self.galleries.writes.lock_context(
                tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
            )
            draft = await self.galleries.drafts.prepare(
                context=context,
                overrides=context.state.overrides,
                as_of=self.clock.now(),
            )
            self._require_export(context, draft.export_blockers)
            target = next(
                (
                    v
                    for v in draft.prepared.preparation.targets
                    if v.publication_id.uuid == publication_id
                ),
                None,
            )
            if (
                target is None
                or self._target_context(
                    context,
                    target,
                    draft.prepared.preparation.targets,
                    expected.actor_id.uuid,
                    content_fingerprint(draft.prepared),
                )
                != expected
            ):
                raise ContentDeliveryError("content_preview_changed", conflict=True)
            if target.parent_publication_id is not None:
                parent = await self.deliveries.get(
                    EntityIdVO(representation_id), target.parent_publication_id
                )
                if parent is not None and parent.status in {
                    DeliveryStatus.QUEUED,
                    DeliveryStatus.IN_FLIGHT,
                    DeliveryStatus.UNKNOWN,
                }:
                    raise ContentDeliveryDeferred()
                if (
                    parent is not None
                    and parent.status is DeliveryStatus.FAILED
                    and parent.error_code
                    in {
                        "content_target_changed",
                        "content_target_invalid",
                        "provider_response_invalid",
                    }
                ):
                    raise ContentDeliveryError("content_parent_changed", conflict=True)
            galleries = await self.galleries.prepare(
                tenant_id=tenant_id,
                channel_id=channel_id,
                group_id=group_id,
                expected_revision=expected.representation_revision,
                expected_binding_revision=expected.binding_revision,
                expected_config_revision=expected.config_revision,
                authorization=DeliveryFilesAuthorization(
                    self.authorization, expected.actor_id.uuid, channel_id
                ),
            )
            delivery = await self.deliveries.get(
                EntityIdVO(representation_id), EntityIdVO(publication_id)
            )
            if (
                delivery is None
                or delivery.current_job_id.uuid != job_id
                or delivery.status is not DeliveryStatus.QUEUED
                or delivery.requested_context != expected
                or not await self.jobs.owns(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    lock_token=lock_token,
                    for_update=True,
                )
            ):
                return None
            gallery = next(
                (
                    v
                    for v in galleries
                    if v.publication_id == publication_id
                    and v.locale == expected.locale
                ),
                None,
            )
            images = {v.media_id: v for v in gallery.images} if gallery else {}
            if any(
                v.transfer_status is MediaTransferStatus.UNKNOWN
                for v in images.values()
            ):
                raise ContentDeliveryError(
                    "content_media_reconciliation_required", conflict=True
                )
            if any(
                v.transfer_status is MediaTransferStatus.IN_FLIGHT
                for v in images.values()
            ):
                raise ContentDeliveryDeferred()
            pending = tuple(
                (v.media_id, v.revision)
                for v in images.values()
                if v.remote_media_id is None
            )
            request = self.platforms.get(context.channel.platform_kind).prepare_content(
                context=expected,
                content=next(v for v in target.content if v.locale == expected.locale),
                gallery=gallery,
                reserved_media_ids=tuple(v[0] for v in pending),
            )
            encrypted = self.cipher.encrypt(request.payload)
            references: list[DeliveryMediaVO] = []
            if pending:
                started = await self.transfers.begin(
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    group_id=group_id,
                    expected_revision=expected.representation_revision,
                    expected_binding_revision=expected.binding_revision,
                    expected_config_revision=expected.config_revision,
                    media_revisions=pending,
                    operation_id=job_id,
                )
                reserved = bool(started)
                for identifier in started:
                    media = await self.galleries.media.get(EntityIdVO(identifier))
                    assert media is not None
                    references.append(
                        DeliveryMediaVO(
                            EntityIdVO(identifier), media.revision, EntityIdVO(job_id)
                        )
                    )
            delivery.begin_attempt(
                job_id=EntityIdVO(job_id),
                encrypted_request=encrypted,
                schema=request.schema,
                content_hash=request.content_hash,
                media=tuple(references),
                now=self.clock.now(),
            )
            await self.deliveries.save(delivery)
            return await self._snapshot(delivery, reconcile=False)
        except (
            ContentDeliveryError,
            ProductRepresentationError,
            ContentMediaError,
        ) as error:
            if reserved:
                # Ошибка после резервирования должна откатить и media, и попытку.
                raise
            current = await self.deliveries.get(
                EntityIdVO(representation_id), EntityIdVO(publication_id)
            )
            if (
                current is not None
                and current.current_job_id.uuid == job_id
                and current.status is DeliveryStatus.QUEUED
            ):
                current.block(code=error.code, now=self.clock.now())
                await self.deliveries.save(current)
            return None

    async def accepts_send(
        self, *, tenant_id: UUID, snapshot: ContentWorkSnapshot, lock_token: str
    ) -> bool:
        """Под сетевым барьером только читает Catalog, не захватывая его locks повторно."""
        if not await self.jobs.owns(
            tenant_id=tenant_id, job_id=snapshot.job_id, lock_token=lock_token
        ):
            return False
        delivery = await self.deliveries.get(
            EntityIdVO(snapshot.representation_id), EntityIdVO(snapshot.publication_id)
        )
        if (
            delivery is None
            or delivery.status not in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}
            or delivery.current_job_id.uuid != snapshot.job_id
            or delivery.sending_generation != snapshot.generation
            or delivery.prepared_hash != snapshot.request.content_hash
        ):
            return False
        try:
            if snapshot.reconcile:
                channel = await self.channels.get(
                    snapshot.context.channel_id, for_update=True
                )
                if channel is None:
                    return False
                identity = channel.connection.identity
                if (
                    channel.connection.id != snapshot.context.connection_id
                    or channel.connection.config_revision
                    != snapshot.context.config_revision
                    or identity is None
                    or (identity.namespace, identity.key)
                    != (
                        snapshot.context.identity_namespace,
                        snapshot.context.identity_key,
                    )
                ):
                    return False
                await self.authorization.require(
                    actor_id=snapshot.context.actor_id.uuid,
                    channel_id=snapshot.context.channel_id.uuid,
                    file_ids=tuple(
                        sorted({v.file.file_id for v in snapshot.media_sources})
                    ),
                )
                return True
            context = await self.galleries.reader.load(
                channel_id=snapshot.context.channel_id.uuid,
                group_id=snapshot.context.group_id.uuid,
            )
            draft = await self.galleries.drafts.prepare(
                context=context,
                overrides=context.state.overrides,
                as_of=self.clock.now(),
            )
            self._require_export(context, draft.export_blockers)
            target = next(
                (
                    v
                    for v in draft.prepared.preparation.targets
                    if v.publication_id.uuid == snapshot.publication_id
                ),
                None,
            )
            if (
                target is None
                or self._target_context(
                    context,
                    target,
                    draft.prepared.preparation.targets,
                    snapshot.context.actor_id.uuid,
                    content_fingerprint(draft.prepared),
                )
                != snapshot.context
            ):
                return False
            await self.authorization.require(
                actor_id=snapshot.context.actor_id.uuid,
                channel_id=snapshot.context.channel_id.uuid,
                file_ids=tuple(
                    sorted(
                        {
                            image.file_id.uuid
                            for content in target.content
                            for image in content.gallery or ()
                        }
                    )
                ),
            )
            for reference in delivery.prepared_media:
                media = await self.galleries.media.get(
                    EntityIdVO(reference.media_id.uuid)
                )
                if (
                    media is None
                    or media.revision != reference.revision
                    or media.access_revoked_at is not None
                ):
                    return False
            return True
        except (ContentDeliveryError, ProductRepresentationError, ContentMediaError):
            return False

    async def apply(
        self,
        *,
        tenant_id: UUID,
        snapshot: ContentWorkSnapshot,
        lock_token: str,
        result: ContentDeliveryResult | ContentReconciliationResult,
    ) -> bool:
        """Одним UoW фиксирует результат цели и media только при действующей lease."""
        channel = await self.channels.get(
            EntityIdVO(snapshot.context.channel_id.uuid), for_update=True
        )
        delivery = await self.deliveries.get(
            EntityIdVO(snapshot.representation_id), EntityIdVO(snapshot.publication_id)
        )
        if (
            channel is None
            or delivery is None
            or delivery.status not in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}
            or delivery.current_job_id.uuid != snapshot.job_id
            or delivery.sending_generation != snapshot.generation
            or delivery.prepared_hash != snapshot.request.content_hash
            or not await self.jobs.owns(
                tenant_id=tenant_id,
                job_id=snapshot.job_id,
                lock_token=lock_token,
                for_update=True,
            )
        ):
            return False
        identity = channel.connection.identity
        if (
            channel.connection.config_revision != snapshot.context.config_revision
            or identity is None
            or (identity.namespace, identity.key)
            != (snapshot.context.identity_namespace, snapshot.context.identity_key)
        ):
            result = ContentDeliveryResult(
                ContentWriteOutcome.UNKNOWN, error_code="content_connection_changed"
            )
        observed = {v.media_id: v.remote_id for v in result.media}
        uncertain = result.outcome is ContentWriteOutcome.UNKNOWN
        error = result.error_code or (
            "content_reconciliation_required" if uncertain else None
        )
        references: list[DeliveryMediaVO] = []
        for reference in delivery.prepared_media:
            identifier = observed.get(reference.media_id.uuid)
            existing = await self.galleries.media.get(reference.media_id)
            if (
                existing is not None
                and existing.revision == reference.revision
                and existing.transfer_status is MediaTransferStatus.READY
                and (identifier is None or identifier == existing.remote_media_id)
            ):
                references.append(reference)
                continue
            missing = (
                result.outcome
                in {ContentWriteOutcome.CONFIRMED, ContentWriteOutcome.PARTIAL}
                and identifier is None
            )
            applied = await self.transfers.record(
                channel_id=snapshot.context.channel_id.uuid,
                config_revision=snapshot.context.config_revision,
                identity_namespace=snapshot.context.identity_namespace,
                identity_key=snapshot.context.identity_key,
                operation_id=reference.operation_id.uuid,
                media_id=reference.media_id.uuid,
                expected_revision=reference.revision,
                remote_id=identifier,
                error=(
                    None
                    if identifier is not None
                    else ("content_media_unconfirmed" if missing else error)
                ),
                uncertain=identifier is None and (uncertain or missing),
            )
            media = await self.galleries.media.get(EntityIdVO(reference.media_id.uuid))
            if not applied or media is None:
                uncertain, error = True, "content_media_changed"
                references.append(reference)
            else:
                references.append(
                    DeliveryMediaVO(
                        reference.media_id, media.revision, reference.operation_id
                    )
                )
            if missing:
                uncertain, error = True, "content_media_unconfirmed"
        fields, issues = result.fields, result.issues
        if uncertain and error in {
            "content_media_unconfirmed",
            "content_media_changed",
        }:
            fields = tuple(v for v in fields if v != "gallery")
            issues = tuple(v for v in issues if v.field != "gallery") + (
                DeliveryFieldIssueVO("gallery", error),
            )
        accepted = delivery.complete_attempt(
            job_id=EntityIdVO(snapshot.job_id),
            generation=snapshot.generation,
            content_hash=snapshot.request.content_hash,
            fields=fields,
            error_code=error,
            uncertain=uncertain,
            media=tuple(references),
            issues=issues,
            now=self.clock.now(),
        )
        if not accepted:
            return False
        next_job = delivery.queue_next(
            job_id=EntityIdVO(self.uuid.new()), now=self.clock.now()
        )
        await self.deliveries.save(delivery)
        if next_job:
            await self.jobs.schedule(
                tenant_id=tenant_id, delivery=delivery, now=self.clock.now()
            )
        return True

    async def _snapshot(
        self, delivery: ContentDelivery, *, reconcile: bool
    ) -> ContentWorkSnapshot | None:
        """Выдаёт только сохранённый запрос и credentials той же identity/конфигурации."""
        context = delivery.prepared_context
        if (
            context is None
            or delivery.prepared_request_encrypted is None
            or delivery.prepared_schema is None
            or delivery.prepared_hash is None
            or delivery.sending_generation is None
        ):
            return None
        channel = await self.channels.get(context.channel_id)
        if channel is None:
            return None
        identity = channel.connection.identity
        if (
            channel.connection.config_revision != context.config_revision
            or identity is None
            or (identity.namespace, identity.key)
            != (context.identity_namespace, context.identity_key)
        ):
            delivery.complete_attempt(
                job_id=delivery.current_job_id,
                generation=delivery.sending_generation,
                content_hash=delivery.prepared_hash,
                fields=(),
                error_code="content_connection_changed",
                uncertain=True,
                now=self.clock.now(),
            )
            await self.deliveries.save(delivery)
            return None
        try:
            payload = self.cipher.decrypt(delivery.prepared_request_encrypted)
        except CiphertextUnreadable:
            delivery.complete_attempt(
                job_id=delivery.current_job_id,
                generation=delivery.sending_generation,
                content_hash=delivery.prepared_hash,
                fields=(),
                error_code="content_request_unreadable",
                uncertain=True,
                now=self.clock.now(),
            )
            await self.deliveries.save(delivery)
            return None
        known_media: list[ContentMediaResult] = []
        media_sources: list[ContentMediaSource] = []
        if reconcile:
            for reference in delivery.prepared_media:
                media = await self.galleries.media.get(reference.media_id)
                if (
                    media is None
                    or media.connection_id != context.connection_id
                    or media.revision != reference.revision
                    or media.access_revoked_at is not None
                ):
                    continue
                if media.remote_media_id is not None:
                    known_media.append(
                        ContentMediaResult(media.id.uuid, media.remote_media_id)
                    )
                else:
                    try:
                        files = await self.galleries.files.describe(
                            (media.file_id.uuid,)
                        )
                    except ContentMediaError:
                        continue
                    media_sources.append(ContentMediaSource(media.id.uuid, files[0]))
        return ContentWorkSnapshot(
            representation_id=delivery.representation_id.uuid,
            publication_id=delivery.publication_id.uuid,
            job_id=delivery.current_job_id.uuid,
            platform_kind=channel.platform_kind,
            generation=delivery.sending_generation,
            context=context,
            config=channel.connection.config,
            encrypted_credentials=channel.connection.encrypted_credentials,
            request=PreparedContentRequest(
                delivery.prepared_schema, payload, delivery.prepared_hash
            ),
            reconcile=reconcile,
            known_media=tuple(known_media),
            media_sources=tuple(media_sources),
        )

    def _require_export(
        self, context: RepresentationContext, blockers: tuple[str, ...]
    ) -> None:
        """Координирует доменную готовность и декларацию установленного пакета."""
        if not context.state.export_enabled or context.state.id is None:
            raise ContentDeliveryError("content_export_disabled", conflict=True)
        if blockers:
            raise ContentDeliveryError(blockers[0], conflict=True)
        if (
            "write_content"
            not in self.platforms.get(
                context.channel.platform_kind
            ).manifest.supported_capabilities
        ):
            raise ContentDeliveryError("content_platform_unsupported")

    @staticmethod
    def _target_context(
        context: RepresentationContext,
        target: PreparedPublicationContent,
        targets: tuple[PreparedPublicationContent, ...],
        actor_id: UUID,
        fingerprint: str,
    ) -> DeliveryContextVO:
        """Явно связывает существующую цель, локаль и подтверждённую identity."""
        identity = context.channel.identity
        if identity is None or len(context.locales) != 1 or target.external_id is None:
            raise ContentDeliveryError("content_context_invalid")
        parent = next(
            (
                v.external_id
                for v in targets
                if v.publication_id == target.parent_publication_id
            ),
            None,
        )
        return DeliveryContextVO(
            channel_id=EntityIdVO(context.channel.id),
            group_id=EntityIdVO(context.binding.id),
            connection_id=EntityIdVO(context.binding.connection_id),
            actor_id=EntityIdVO(actor_id),
            representation_revision=context.state.revision,
            binding_revision=context.binding.revision,
            config_revision=context.channel.config_revision,
            content_fingerprint=fingerprint,
            identity_namespace=identity.namespace,
            identity_key=identity.key,
            external_id=target.external_id,
            parent_external_id=parent,
            publication_kind=target.publication_kind or "",
            locale=context.locales[0],
            role=target.role.value,
        )
