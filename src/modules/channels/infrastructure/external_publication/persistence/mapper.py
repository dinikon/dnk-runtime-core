"""Преобразование SQL-документов в Domain и обратно."""

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)


def to_domain(row: ExternalPublicationModel) -> ExternalPublication:
    """Восстанавливает публикацию через фабрику с проверками Domain."""
    if row.normalized_schema != "publication.v1":
        raise InvalidExternalPublicationError("Версия снимка не поддерживается.")
    try:
        kind = PublicationKind(row.kind)
    except ValueError:
        raise InvalidExternalPublicationError(
            "Роль публикации не поддерживается."
        ) from None
    return ExternalPublication.restore(
        publication_id=EntityIdVO.from_value(row.id),
        connection_id=EntityIdVO.from_value(row.connection_id),
        resource_type=row.resource_type,
        external_id=row.external_id,
        kind=kind,
        parent_id=EntityIdVO.from_value(row.parent_id) if row.parent_id else None,
        revision=row.revision,
        raw_data=row.raw_data,
        data=PublicationData.from_document(row.normalized_data),
        platform_schema=row.platform_schema,
        platform_data=row.platform_data,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        run_id=EntityIdVO.from_value(row.last_sync_run_id),
    )


def to_values(publication: ExternalPublication) -> dict[str, object]:
    """Извлекает значения хранения без бизнес-решений."""
    return {
        "id": publication.id.uuid,
        "connection_id": publication.connection_id.uuid,
        "resource_type": publication.resource_type,
        "external_id": publication.external_id,
        "kind": publication.kind.value,
        "parent_id": publication.parent_id.uuid if publication.parent_id else None,
        "revision": publication.revision,
        "raw_data": publication.raw_data,
        "normalized_schema": "publication.v1",
        "normalized_data": publication.data.to_document(),
        "platform_schema": publication.platform_schema,
        "platform_data": publication.platform_data,
        "first_seen_at": publication.first_seen_at,
        "last_seen_at": publication.last_seen_at,
        "last_sync_run_id": publication.last_sync_run_id.uuid,
    }
