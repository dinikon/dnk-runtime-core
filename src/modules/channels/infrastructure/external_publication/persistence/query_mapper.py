from src.modules.channels.application.external_publication.identity_contract import (
    PublicationIdentityDiagnosticDTO,
)
from dataclasses import asdict
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from collections.abc import Mapping
from typing import Any
from src.modules.channels.application.external_publication.query.get_external_publication.dto import (
    GetExternalPublicationResultDTO,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListExternalPublicationsItemDTO,
)


class ExternalPublicationQueryMapper:
    """Собирает core/detail DTO без восстановления observed агрегата."""

    @staticmethod
    def to_details(row: Mapping[str, Any]) -> GetExternalPublicationResultDTO:
        """Возвращает типизированные поля без приватных метаданных плагина."""
        values = dict(row)
        values["identity"] = PublicationIdentityDiagnosticDTO(
            values.pop("identity_state"),
            values.pop("identity_key"),
            values.pop("identity_conflict_count"),
        )
        values["publication_id"] = values.pop("id")
        values.pop("fingerprint")
        metadata = values.pop("meta")
        payload = PublicationPayloadVO.from_document(values.pop("payload"))
        values.update(
            asdict(
                payload.to_core(
                    values["resource_type"],
                    values["external_id"],
                    values["source_updated_at"],
                    tuple(metadata["read_issues"]),
                )
            )
        )
        return GetExternalPublicationResultDTO(**values)

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> ListExternalPublicationsItemDTO:
        """Проецирует общий payload без разбора provider JSON."""
        values = dict(row)
        values["identity"] = PublicationIdentityDiagnosticDTO(
            values.pop("identity_state"),
            values.pop("identity_key"),
            values.pop("identity_conflict_count"),
        )
        values["publication_id"] = values.pop("id")
        payload = PublicationPayloadVO.from_document(values.pop("payload"))
        values.update(
            asdict(
                payload.to_core(
                    values["resource_type"],
                    values["external_id"],
                    values["source_updated_at"],
                    tuple(values.pop("read_issues")),
                )
            )
        )
        return ListExternalPublicationsItemDTO(**values)
