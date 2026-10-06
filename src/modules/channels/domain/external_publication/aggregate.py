from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from src.modules.channels.domain.external_publication.value_object.identifier import (
    PublicationIdVO,
)
from src.modules.channels.domain.external_publication.error import (
    InvalidPublicationError,
)
from src.modules.channels.domain.external_publication.value_object.read_document import (
    PublicationReadDocumentVO,
)


@dataclass(frozen=True, slots=True)
class ExternalPublication:
    """Хранит наблюдаемую внешнюю карточку независимо от товаров Catalog."""

    id: PublicationIdVO
    channel_id: ChannelIdVO
    connection_revision: int
    resource_type: str
    external_id: str
    parent_external_id: str | None
    raw_payload: str = field(repr=False)
    document: PublicationReadDocumentVO
    revision: int
    last_run_id: PublicationImportRunIdVO
    created_at: datetime
    observed_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: PublicationIdVO,
        channel_id: ChannelIdVO,
        connection_revision: int,
        resource_type: str,
        external_id: str,
        parent_external_id: str | None,
        raw_payload: str,
        document: PublicationReadDocumentVO,
        run_id: PublicationImportRunIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт первую наблюдаемую ревизию внешнего ресурса."""
        return cls.restore(
            id=id,
            channel_id=channel_id,
            connection_revision=connection_revision,
            resource_type=resource_type,
            external_id=external_id,
            parent_external_id=parent_external_id,
            raw_payload=raw_payload,
            document=document,
            revision=1,
            last_run_id=run_id,
            created_at=now,
            observed_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: PublicationIdVO,
        channel_id: ChannelIdVO,
        connection_revision: int,
        resource_type: str,
        external_id: str,
        parent_external_id: str | None,
        raw_payload: str,
        document: PublicationReadDocumentVO,
        revision: int,
        last_run_id: PublicationImportRunIdVO,
        created_at: datetime,
        observed_at: datetime,
    ) -> Self:
        """Проверяет идентичность, версии и время сохранённого снимка."""
        if not (
            isinstance(id, PublicationIdVO)
            and isinstance(channel_id, ChannelIdVO)
            and isinstance(last_run_id, PublicationImportRunIdVO)
        ):
            raise InvalidPublicationError("Invalid publication identifiers.")
        if (
            type(connection_revision) is not int
            or type(revision) is not int
            or connection_revision < 1
            or revision < 1
            or resource_type not in ("product", "variation")
        ):
            raise InvalidPublicationError("Invalid publication revision or resource.")
        if (
            not isinstance(external_id, str)
            or not 1 <= len(external_id) <= 255
            or (
                parent_external_id is not None
                and (
                    not isinstance(parent_external_id, str)
                    or not 1 <= len(parent_external_id) <= 255
                )
            )
            or parent_external_id == external_id
            or not isinstance(raw_payload, str)
            or not raw_payload
        ):
            raise InvalidPublicationError("Invalid external identity or snapshot.")
        if (
            not isinstance(document, PublicationReadDocumentVO)
            or document.schema_version != 1
        ):
            raise InvalidPublicationError("Unsupported read document.")
        if (
            any(
                not isinstance(value, datetime) or value.utcoffset() is None
                for value in (created_at, observed_at)
            )
            or observed_at < created_at
        ):
            raise InvalidPublicationError("Invalid observation timestamp.")
        return cls(
            id,
            channel_id,
            connection_revision,
            resource_type,
            external_id,
            parent_external_id,
            raw_payload,
            document,
            revision,
            last_run_id,
            created_at,
            observed_at,
        )

    def observe(
        self,
        *,
        raw_payload: str,
        document: PublicationReadDocumentVO,
        parent_external_id: str | None,
        run_id: PublicationImportRunIdVO,
        now: datetime,
    ) -> Self:
        """Обновляет снимок, увеличивая ревизию только при изменении данных."""
        changed = (raw_payload, document, parent_external_id) != (
            self.raw_payload,
            self.document,
            self.parent_external_id,
        )
        return self.restore(
            id=self.id,
            channel_id=self.channel_id,
            connection_revision=self.connection_revision,
            resource_type=self.resource_type,
            external_id=self.external_id,
            parent_external_id=parent_external_id,
            raw_payload=raw_payload,
            document=document,
            revision=self.revision + int(changed),
            last_run_id=run_id,
            created_at=self.created_at,
            observed_at=now,
        )
