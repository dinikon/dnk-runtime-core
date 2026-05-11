from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.modules.communication.application.ports import (
    HttpClientProtocol,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderProtocol,
)
from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    SecretCodec,
)
from src.modules.communication.domain import (
    CommunicationValidationError,
    OutboundMessageStatus,
)
from src.modules.shared.infrastructure.email.models import RenderedEmailMessage
from src.modules.shared.infrastructure.email.smtp_email_transport import (
    SmtpEmailTransport,
)


class ProviderSenderRegistry:
    """Transport-name keyed provider sender registry."""

    def __init__(self, senders: list[ProviderSenderProtocol]) -> None:
        self._senders = {sender.transport: sender for sender in senders}

    def get(self, transport: str) -> ProviderSenderProtocol:
        """Return sender for transport or raise a validation error."""
        sender = self._senders.get(transport)
        if sender is None:
            raise CommunicationValidationError(
                f"Unsupported provider transport '{transport}'."
            )
        return sender


class YamlHttpProviderSender:
    """YAML_HTTP sender using the existing HTTP client port."""

    transport = "http"

    def __init__(
        self,
        *,
        http_client: HttpClientProtocol,
        payload_builder: ProviderPayloadBuildService,
        status_mapper: ProviderStatusMappingService,
        json_path: JsonPathService,
        secret_codec: SecretCodec,
    ) -> None:
        self._http_client = http_client
        self._payload_builder = payload_builder
        self._status_mapper = status_mapper
        self._json_path = json_path
        self._secret_codec = secret_codec

    def build(self, context: ProviderSendContext) -> ProviderPreparedSend:
        """Build HTTP request details and persistable request snapshot."""
        send_spec = context.connector_spec["send"]
        method, url, headers, body = self._payload_builder.build(
            send_spec=send_spec,
            context=_render_context(context, secrets={}),
        )
        request_payload = {
            "transport": self.transport,
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
        }
        transport_payload = {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "basic_auth": self._build_basic_auth(
                context.connector_spec,
                context.secrets_b64,
            ),
        }
        return ProviderPreparedSend(
            request_payload=request_payload,
            transport_payload=transport_payload,
        )

    async def send(
        self,
        context: ProviderSendContext,
        prepared: ProviderPreparedSend,
    ) -> ProviderSendResult:
        """Send HTTP provider request and normalize response mapping."""
        payload = prepared.transport_payload
        response = await self._http_client.request(
            method=payload["method"],
            url=payload["url"],
            headers=payload["headers"],
            json_body=payload["body"],
            basic_auth=payload["basic_auth"],
        )
        send_spec = context.connector_spec["send"]
        response_mapping = send_spec.get("response_mapping") or {}
        external_message_id = self._json_path.extract_one(
            response.payload,
            response_mapping.get("external_message_id"),
        )
        external_status = self._json_path.extract_one(
            response.payload,
            response_mapping.get("external_status"),
        )
        internal_status = self._status_mapper.map_status(
            context.connector_spec.get("status_mapping"),
            external_status,
        )
        success = 200 <= response.status_code < 300
        if success and internal_status == OutboundMessageStatus.UNKNOWN.value:
            internal_status = OutboundMessageStatus.SENT.value

        return ProviderSendResult(
            success=success,
            response_payload=(
                response.payload
                if isinstance(response.payload, dict)
                else {"body": response.payload}
            ),
            http_status_code=response.status_code,
            external_message_id=(
                str(external_message_id) if external_message_id is not None else None
            ),
            external_status=(
                str(external_status) if external_status is not None else None
            ),
            internal_status=internal_status,
            error_code=None if success else f"HTTP_{response.status_code}",
            error_message=(
                None if success else "Provider returned non-success HTTP status."
            ),
        )

    def _build_basic_auth(
        self,
        yaml_spec: dict[str, Any],
        secrets_b64: str | None,
    ) -> tuple[str, str] | None:
        auth = yaml_spec.get("auth") or {}
        if auth.get("type") != "basic":
            return None
        secrets = self._secret_codec.decode(secrets_b64)
        username_key = auth.get("username_secret_key")
        password_key = auth.get("password_secret_key")
        if username_key not in secrets or password_key not in secrets:
            raise CommunicationValidationError(
                "Provider connection secrets are missing basic auth credentials."
            )
        return str(secrets[username_key]), str(secrets[password_key])


class YamlSmtpProviderSender:
    """YAML_SMTP sender using shared SMTP transport."""

    transport = "smtp"

    def __init__(
        self,
        *,
        payload_builder: ProviderPayloadBuildService,
        secret_codec: SecretCodec,
        transport_factory: Callable[..., SmtpEmailTransport] = SmtpEmailTransport,
    ) -> None:
        self._payload_builder = payload_builder
        self._secret_codec = secret_codec
        self._transport_factory = transport_factory

    def build(self, context: ProviderSendContext) -> ProviderPreparedSend:
        """Build SMTP transport settings and a redacted request snapshot."""
        secrets = self._secret_codec.decode(context.secrets_b64)
        rendered_send = self._payload_builder.render_value(
            context.connector_spec["send"],
            _render_context(
                _smtp_context_with_default_bodies(context),
                secrets=secrets,
            ),
        )
        if not isinstance(rendered_send, dict):
            raise CommunicationValidationError("SMTP send spec must render to object.")

        text_body = str(rendered_send.get("text_body") or "")
        html_body = rendered_send.get("html_body")
        html_body_value = str(html_body) if html_body not in (None, "") else None
        message = RenderedEmailMessage(
            recipient_email=str(rendered_send["to_address"]),
            subject=str(rendered_send["subject"]),
            text_body=text_body,
            html_body=html_body_value,
        )
        transport_kwargs = {
            "from_address": str(rendered_send["from_address"]),
            "from_name": str(rendered_send.get("from_name") or ""),
            "host": str(rendered_send["host"]),
            "port": int(rendered_send["port"]),
            "username": str(rendered_send.get("username") or ""),
            "password": str(rendered_send.get("password") or ""),
            "use_tls": _as_bool(rendered_send["use_tls"]),
            "use_starttls": _as_bool(rendered_send["use_starttls"]),
            "timeout_seconds": float(rendered_send["timeout_seconds"]),
        }
        request_payload = {
            "transport": self.transport,
            "host": transport_kwargs["host"],
            "port": transport_kwargs["port"],
            "from_address": transport_kwargs["from_address"],
            "from_name": transport_kwargs["from_name"],
            "to_address": message.recipient_email,
            "subject": message.subject,
            "use_tls": transport_kwargs["use_tls"],
            "use_starttls": transport_kwargs["use_starttls"],
            "timeout_seconds": transport_kwargs["timeout_seconds"],
            "has_username": bool(transport_kwargs["username"]),
            "has_password": bool(transport_kwargs["password"]),
            "has_html_body": message.html_body is not None,
        }
        return ProviderPreparedSend(
            request_payload=request_payload,
            transport_payload={
                "transport_kwargs": transport_kwargs,
                "message": message,
            },
        )

    async def send(
        self,
        context: ProviderSendContext,
        prepared: ProviderPreparedSend,
    ) -> ProviderSendResult:
        """Send SMTP message and synthesize a provider response snapshot."""
        payload = prepared.transport_payload
        transport = self._transport_factory(**payload["transport_kwargs"])
        await transport.send(payload["message"])
        external_message_id = str(context.outbound_message_id)
        external_status = "sent"
        return ProviderSendResult(
            success=True,
            response_payload={
                "message_id": external_message_id,
                "status": external_status,
            },
            http_status_code=None,
            external_message_id=external_message_id,
            external_status=external_status,
            internal_status=OutboundMessageStatus.SENT.value,
        )


def _render_context(
    context: ProviderSendContext,
    *,
    secrets: dict[str, Any],
) -> dict[str, Any]:
    return {
        "recipient": {
            "address": context.recipient_address,
            "snapshot": context.recipient_snapshot,
        },
        "template": context.rendered_payload,
        "variables": context.variables,
        "config": context.config,
        "secrets": secrets,
        "message": {
            "outbound_message_id": str(context.outbound_message_id),
            "communication_request_id": str(context.communication_request_id),
            "initiator_ref_id": context.initiator_ref_id,
        },
        "connection": {
            "connection_code": context.connection_code,
            "channel_code": context.channel_code,
        },
    }


def _smtp_context_with_default_bodies(
    context: ProviderSendContext,
) -> ProviderSendContext:
    rendered_payload = {
        "text_body": "",
        "html_body": "",
        **context.rendered_payload,
    }
    return ProviderSendContext(
        outbound_message_id=context.outbound_message_id,
        communication_request_id=context.communication_request_id,
        initiator_ref_id=context.initiator_ref_id,
        recipient_address=context.recipient_address,
        recipient_snapshot=context.recipient_snapshot,
        variables=context.variables,
        connection_code=context.connection_code,
        channel_code=context.channel_code,
        config=context.config,
        secrets_b64=context.secrets_b64,
        connector_spec=context.connector_spec,
        rendered_payload=rendered_payload,
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


__all__ = [
    "ProviderSenderRegistry",
    "YamlHttpProviderSender",
    "YamlSmtpProviderSender",
]
