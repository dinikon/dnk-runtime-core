from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.value_object.core import (
    PublicationCoreVO,
)
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)
from src.modules.channels.domain.external_publication.value_object.fingerprint import (
    publication_fingerprint,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)


@dataclass(slots=True)
class ExternalPublication:
    """Владеет identity и последним наблюдаемым снимком внешней карточки."""

    id: EntityIdVO
    connection_id: EntityIdVO
    resource_type: str
    external_id: str
    payload: PublicationPayloadVO
    meta: PublicationMetaVO
    source_updated_at: datetime | None
    fingerprint: str
    observed_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_import_run_id: EntityIdVO

    @property
    def core(self) -> PublicationCoreVO:
        """Строит временную типизированную проекцию без дублирования хранения."""
        return self.payload.to_core(
            self.resource_type,
            self.external_id,
            self.source_updated_at,
            self.meta.read_issues,
        )

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        resource_type: str,
        external_id: str,
        payload: PublicationPayloadVO,
        meta: PublicationMetaVO,
        source_updated_at: datetime | None,
        run_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт наблюдение без записи в Catalog."""
        return cls.restore(
            identifier,
            connection_id,
            resource_type,
            external_id,
            payload,
            meta,
            source_updated_at,
            publication_fingerprint(payload, meta, source_updated_at),
            1,
            now,
            now,
            run_id,
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        resource_type: str,
        external_id: str,
        payload: PublicationPayloadVO,
        meta: PublicationMetaVO,
        source_updated_at: datetime | None,
        fingerprint: str,
        observed_revision: int,
        first_seen_at: datetime,
        last_seen_at: datetime,
        last_import_run_id: EntityIdVO,
    ) -> Self:
        """Восстанавливает снимок с прежними identity, связями и ревизией."""
        payload.to_core(resource_type, external_id, source_updated_at, meta.read_issues)
        if observed_revision < 1 or not fingerprint:
            raise ChannelsValidationError("invalid_publication_state")
        return cls(
            identifier,
            connection_id,
            resource_type,
            external_id,
            payload,
            meta,
            source_updated_at,
            fingerprint,
            observed_revision,
            first_seen_at,
            last_seen_at,
            last_import_run_id,
        )

    def observe(
        self,
        resource_type: str,
        external_id: str,
        payload: PublicationPayloadVO,
        meta: PublicationMetaVO,
        source_updated_at: datetime | None,
        run_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Обновляет снимок, сохраняя UUID и ревизию при неизменных данных."""
        if (self.resource_type, self.external_id) != (resource_type, external_id):
            raise ChannelsConflictError("publication_identity_changed")
        payload.to_core(resource_type, external_id, source_updated_at, meta.read_issues)
        fingerprint = publication_fingerprint(payload, meta, source_updated_at)
        if self.fingerprint != fingerprint:
            self.observed_revision += 1
        self.payload, self.meta, self.source_updated_at = (
            payload,
            meta,
            source_updated_at,
        )
        self.fingerprint, self.last_seen_at, self.last_import_run_id = (
            fingerprint,
            now,
            run_id,
        )
