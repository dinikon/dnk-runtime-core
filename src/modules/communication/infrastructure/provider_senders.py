from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.modules.communication.application.outbound_message.provider_send import (
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
from src.modules.communication.domain.error import (
    CommunicationValidationError,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageStatus,
    ProviderPayloadValidationError,
)
from src.modules.communication.domain.provider_connection import (
    ProviderSecretsValidationError,
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
        send_spec = context.send_spec
        secrets = self._secret_codec.decode(context.secrets_b64)
        method, url, headers, body = self._payload_builder.build(
            send_spec=send_spec,
            context=_render_context(context, secrets=secrets),
        )
        auth_headers = self._build_auth_headers(context.connector_spec, secrets)
        transport_headers = {**headers, **auth_headers}
        request_headers = _redact_headers(transport_headers, secrets)
        request_body = _redact_secret_values(body, secrets)
        request_payload = {
            "transport": self.transport,
            "method": method,
            "url": url,
            "headers": request_headers,
            "body": request_body,
        }
        transport_payload = {
            "method": method,
            "url": url,
            "headers": transport_headers,
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
        send_spec = context.send_spec
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
            raise ProviderSecretsValidationError(
                "Provider connection secrets are missing basic auth credentials."
            )
        return str(secrets[username_key]), str(secrets[password_key])

    def _build_auth_headers(
        self,
        yaml_spec: dict[str, Any],
        secrets: dict[str, Any],
    ) -> dict[str, str]:
        auth = yaml_spec.get("auth") or {}
        if auth.get("type") != "bearer":
            return {}
        token_key = auth.get("token_secret_key")
        if token_key not in secrets:
            raise ProviderSecretsValidationError(
                "Provider connection secrets are missing bearer auth token."
            )
        return {"Authorization": f"Bearer {secrets[token_key]}"}


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
            context.send_spec,
            _render_context(context, secrets=secrets),
        )
        if not isinstance(rendered_send, dict):
            raise ProviderPayloadValidationError(
                "SMTP send spec must render to object."
            )

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
        "provider_message_type": {
            "code": context.provider_message_type_code,
        },
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _redact_headers(headers: dict[str, str], secrets: dict[str, Any]) -> dict[str, str]:
    sensitive_names = {"authorization", "proxy-authorization", "x-api-key"}
    secret_values = {
        str(item) for item in secrets.values() if item is not None and str(item) != ""
    }
    return {
        name: (
            "[REDACTED]"
            if name.lower() in sensitive_names
            else _redact_text(value, secret_values)
        )
        for name, value in headers.items()
    }


def _redact_secret_values(value: Any, secrets: dict[str, Any]) -> Any:
    secret_values = {
        str(item) for item in secrets.values() if item is not None and str(item) != ""
    }
    if not secret_values:
        return value
    return _redact_value(value, secret_values)


def _redact_value(value: Any, secret_values: set[str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, secret_values)
    if isinstance(value, list):
        return [_redact_value(item, secret_values) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item, secret_values) for key, item in value.items()}
    return value


def _redact_text(value: str, secret_values: set[str]) -> str:
    redacted = value
    for secret in secret_values:
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


__all__ = [
    "ProviderSenderRegistry",
    "YamlHttpProviderSender",
    "YamlSmtpProviderSender",
]
