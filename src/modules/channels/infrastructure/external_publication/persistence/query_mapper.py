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
        """Возвращает версии extensions и доступный core."""
        values = dict(row)
        values["publication_id"] = values.pop("id")
        values.pop("fingerprint")
        values["warnings"] = tuple(values["warnings"])
        return GetExternalPublicationResultDTO(**values)

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> ListExternalPublicationsItemDTO:
        """Не разбирает платформенный JSON для построения списка."""
        values = dict(row)
        values["publication_id"] = values.pop("id")
        values["warnings"] = tuple(values["warnings"])
        return ListExternalPublicationsItemDTO(**values)
