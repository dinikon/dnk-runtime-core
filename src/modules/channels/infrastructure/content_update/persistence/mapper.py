from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun
from src.modules.channels.domain.content_update.entity.item import ContentUpdateItem
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)


class ContentUpdateMapper:
    """Преобразует сохранённый JSON снимка без I/O и доменных переходов."""

    @staticmethod
    def texts(value: Mapping[str, Any]) -> ContentTextsVO:
        """Читает ограниченную версионированную структуру текстов."""
        if value["version"] != 1:
            raise ValueError("unsupported_content_snapshot_version")
        return ContentTextsVO(
            tuple(
                LocalizedTextVO(text["locale"], text["title"], text["body"])
                for text in value["translations"]
            )
        )

    @staticmethod
    def text_values(value: ContentTextsVO) -> dict[str, Any]:
        """Сериализует только локаль, название и описание."""
        return {
            "version": 1,
            "translations": [
                {"locale": text.locale, "title": text.title, "body": text.body}
                for text in value.translations
            ],
        }

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], items: Sequence[Mapping[str, Any]]
    ) -> ContentUpdateRun:
        """Восстанавливает весь корень через явные фабрики Domain."""
        return ContentUpdateRun.restore(
            *(
                EntityIdVO(row[key])
                for key in ("id", "channel_id", "connection_id", "actor_id")
            ),
            row["generation"],
            row["sdk_version"],
            row["status"],
            row["revision"],
            row["sequence"],
            row["created_at"],
            row["expires_at"],
            row["confirmed_at"],
            row["preview_hash"],
            [
                ContentUpdateItem.restore(
                    *(
                        EntityIdVO(item[key])
                        for key in ("publication_id", "catalog_item_id", "binding_id")
                    ),
                    item["binding_revision"],
                    item["resource_type"],
                    item["external_id"],
                    item["provider_context"],
                    ContentUpdateMapper.texts(item["desired"]),
                    (
                        ContentUpdateMapper.texts(item["observed"])
                        if item["observed"]
                        else None
                    ),
                    item["status"],
                    tuple(item["issues"]),
                    item["attempts"],
                )
                for item in items
            ],
        )

    @staticmethod
    def to_values(run: ContentUpdateRun) -> dict[str, Any]:
        """Извлекает значения корня без самостоятельной записи."""
        return {
            "id": run.id.uuid,
            "channel_id": run.channel_id.uuid,
            "connection_id": run.connection_id.uuid,
            "actor_id": run.actor_id.uuid,
            "generation": run.generation,
            "sdk_version": run.sdk_version,
            "status": run.status,
            "revision": run.revision,
            "sequence": run.sequence,
            "created_at": run.created_at,
            "expires_at": run.expires_at,
            "confirmed_at": run.confirmed_at,
            "preview_hash": run.preview_hash_value,
        }

    @staticmethod
    def item_values(run: ContentUpdateRun, item: ContentUpdateItem) -> dict[str, Any]:
        """Извлекает snapshot и результат внутренней позиции."""
        return {
            "run_id": run.id.uuid,
            "publication_id": item.publication_id.uuid,
            "catalog_item_id": item.catalog_item_id.uuid,
            "binding_id": item.binding_id.uuid,
            "binding_revision": item.binding_revision,
            "resource_type": item.resource_type,
            "external_id": item.external_id,
            "provider_context": item.provider_context,
            "desired": ContentUpdateMapper.text_values(item.desired),
            "observed": (
                ContentUpdateMapper.text_values(item.observed)
                if item.observed
                else None
            ),
            "status": item.status,
            "issues": list(item.issues),
            "attempts": item.attempts,
        }
