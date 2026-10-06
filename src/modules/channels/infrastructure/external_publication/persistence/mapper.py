import json
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from src.modules.channels.domain.external_publication.value_object.identifier import (
    PublicationIdVO,
)
from typing import Any, Mapping
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.infrastructure.external_publication.persistence.document_mapper import (
    PublicationDocumentMapper,
)


class PublicationMapper:
    """Преобразует публикацию и представление хранения без сетевых или SQL вызовов."""

    @staticmethod
    def to_values(publication: ExternalPublication) -> dict[str, Any]:
        """Извлекает поля агрегата для записи в JSONB и обычные столбцы."""
        return dict(
            id=publication.id.uuid,
            channel_id=publication.channel_id.uuid,
            connection_revision=publication.connection_revision,
            resource_type=publication.resource_type,
            external_id=publication.external_id,
            parent_external_id=publication.parent_external_id,
            raw_payload=json.loads(publication.raw_payload),
            document=PublicationDocumentMapper.to_values(publication.document),
            revision=publication.revision,
            last_run_id=publication.last_run_id.uuid,
            created_at=publication.created_at,
            observed_at=publication.observed_at,
        )

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ExternalPublication:
        """Восстанавливает доменную публикацию через её проверяемую фабрику."""
        values = dict(row)
        values["id"] = PublicationIdVO.from_value(values["id"])
        values["channel_id"] = ChannelIdVO.from_value(values["channel_id"])
        values["last_run_id"] = PublicationImportRunIdVO.from_value(
            values["last_run_id"]
        )
        values["raw_payload"] = json.dumps(
            values["raw_payload"], ensure_ascii=False, sort_keys=True
        )
        values["document"] = PublicationDocumentMapper.to_document(values["document"])
        return ExternalPublication.restore(**values)
