from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Any, Mapping
from uuid import UUID

from src.modules.channels.domain.content_delivery.value_object import DeliveryContextVO
from src.modules.channels.domain.types import JsonObject


def context_to_document(value: DeliveryContextVO) -> JsonObject:
    """Явно кодирует подтверждённый контекст без секретов."""
    return {
        "schema": "content_context.v1",
        "channel_id": str(value.channel_id.uuid),
        "group_id": str(value.group_id.uuid),
        "connection_id": str(value.connection_id.uuid),
        "actor_id": str(value.actor_id.uuid),
        "representation_revision": value.representation_revision,
        "binding_revision": value.binding_revision,
        "config_revision": value.config_revision,
        "content_fingerprint": value.content_fingerprint,
        "identity_namespace": value.identity_namespace,
        "identity_key": value.identity_key,
        "external_id": value.external_id,
        "parent_external_id": value.parent_external_id,
        "publication_kind": value.publication_kind,
        "locale": value.locale,
        "role": value.role,
    }


def context_from_document(value: Mapping[str, Any]) -> DeliveryContextVO:
    """Восстанавливает конкретный VO, оставляя инварианты его фабрике."""
    if value["schema"] != "content_context.v1":
        raise ValueError("Unsupported content context schema")
    return DeliveryContextVO(
        channel_id=EntityIdVO(UUID(value["channel_id"])),
        group_id=EntityIdVO(UUID(value["group_id"])),
        connection_id=EntityIdVO(UUID(value["connection_id"])),
        actor_id=EntityIdVO(UUID(value["actor_id"])),
        representation_revision=value["representation_revision"],
        binding_revision=value["binding_revision"],
        config_revision=value["config_revision"],
        content_fingerprint=value["content_fingerprint"],
        identity_namespace=value["identity_namespace"],
        identity_key=value["identity_key"],
        external_id=value["external_id"],
        parent_external_id=value["parent_external_id"],
        publication_kind=value["publication_kind"],
        locale=value["locale"],
        role=value["role"],
    )
