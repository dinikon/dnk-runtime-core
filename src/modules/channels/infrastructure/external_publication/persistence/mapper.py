from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from dataclasses import fields
from typing import Any
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)


class ExternalPublicationMapper:
    """Отделяет observed агрегат от persistence representation."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ExternalPublication:
        """Восстанавливает core и технические отметки без нормализации источника."""
        values = dict(row)
        values["payload"] = PublicationPayloadVO.from_document(values["payload"])
        values["meta"] = PublicationMetaVO.from_document(values["meta"])
        values["identifier"] = EntityIdVO(values.pop("id"))
        if values["connection_id"] is not None:
            values["connection_id"] = EntityIdVO(values["connection_id"])
        if values["last_import_run_id"] is not None:
            values["last_import_run_id"] = EntityIdVO(values["last_import_run_id"])
        return ExternalPublication.restore(**values)

    @staticmethod
    def to_values(publication: ExternalPublication) -> dict[str, Any]:
        """Извлекает уже проверенные доменные значения для INSERT/UPDATE."""
        values = {
            item.name: (
                getattr(publication, item.name).uuid
                if isinstance(getattr(publication, item.name), EntityIdVO)
                else getattr(publication, item.name)
            )
            for item in fields(publication)
            if item.name not in ("payload", "meta")
        }
        values["payload"] = publication.payload.to_document()
        values["meta"] = publication.meta.to_document()
        return values
