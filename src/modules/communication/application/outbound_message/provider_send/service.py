from __future__ import annotations

from typing import Any
from uuid import UUID

from src.modules.communication.application.outbound_message.provider_send.ports import (
    ProviderSendContext,
)
from src.modules.communication.domain.error import CommunicationValidationError


def build_provider_send_context(
    *,
    outbound,
    request,
    connection,
    connector_spec: dict[str, Any],
    send_spec: dict[str, Any],
    provider_message_type_code: str,
    rendered_payload: dict[str, Any],
) -> ProviderSendContext:
    """Собирает provider send context из processing context."""
    return ProviderSendContext(
        outbound_message_id=id_uuid(outbound.outbound_message_id),
        communication_request_id=id_uuid(request.communication_request_id),
        initiator_ref_id=request.initiator_ref_id,
        recipient_identifier_type=outbound.recipient_identifier_type,
        recipient_address=outbound.recipient_address,
        recipient_snapshot=request.recipient_snapshot,
        variables=request.variables,
        connection_code=connection.connection_code,
        channel_code=connection.channel_code,
        provider_message_type_code=provider_message_type_code,
        config=connection.config,
        secrets_b64=connection.secrets_b64,
        connector_spec=connector_spec,
        send_spec=send_spec,
        rendered_payload=rendered_payload,
    )


def resolve_send_spec(
    connector_spec: dict[str, Any],
    message_type_code: str,
) -> dict[str, Any]:
    """Находит send spec в YAML connector spec для message type."""
    for message_type in connector_spec.get("message_types") or []:
        if not isinstance(message_type, dict):
            continue
        if str(message_type.get("code")) != message_type_code:
            continue
        send_spec = message_type.get("send")
        if send_spec is None:
            raise CommunicationValidationError(
                f"Send spec is missing for provider message type '{message_type_code}'."
            )
        if not isinstance(send_spec, dict):
            raise CommunicationValidationError(
                f"message type '{message_type_code}' send spec must be an object."
            )
        return send_spec

    raise CommunicationValidationError(
        f"No send spec found for provider message type '{message_type_code}'."
    )


def id_uuid(value: Any) -> UUID:
    """Возвращает UUID из UUID или domain id value object."""
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


__all__ = [
    "build_provider_send_context",
    "id_uuid",
    "resolve_send_spec",
]
