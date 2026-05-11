from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from src.modules.communication.application.ports import ProviderHttpResponse
from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    SecretCodec,
    TemplateRenderService,
)
from src.modules.communication.application.use_cases import (
    HandleProviderWebhookCommand,
    HandleProviderWebhookUseCase,
    ProcessOutboundMessageUseCase,
    ProcessQueuedMessagesCommand,
    SendCommunicationCommand,
    SendCommunicationUseCase,
)
from src.modules.communication.domain import OutboundMessageStatus
from src.modules.communication.infrastructure.provider_senders import (
    ProviderSenderRegistry,
    YamlHttpProviderSender,
    YamlSmtpProviderSender,
)


class _HttpClientStub:
    def __init__(self) -> None:
        self.requests = []

    async def request(self, *, method, url, headers, json_body, basic_auth=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json_body": json_body,
                "basic_auth": basic_auth,
            }
        )
        return ProviderHttpResponse(
            status_code=200,
            payload={"message_id": "ext-123", "status": "23033"},
        )


class _ProcessRepositoryStub:
    def __init__(self) -> None:
        self.secret_codec = SecretCodec()
        self.outbound = SimpleNamespace(
            outbound_message_id=uuid4(),
            communication_request_id=uuid4(),
            provider_connection_id=uuid4(),
            recipient_address="380671112233",
            rendered_payload={},
            provider_request_payload={},
            external_message_id=None,
            external_status=None,
            internal_status="QUEUED",
            error_code=None,
            error_message=None,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
        )
        self.request = SimpleNamespace(
            communication_request_id=self.outbound.communication_request_id,
            variables={"amount": 15000},
            recipient_snapshot={},
            initiator_ref_id="deal:123",
            status="QUEUED",
        )
        self.template = SimpleNamespace(provider_message_type_id=uuid4())
        self.message_type = SimpleNamespace(
            provider_message_type_id=self.template.provider_message_type_id,
            message_type_code="viber_text",
        )
        self.version = SimpleNamespace(
            template_payload={
                "text": "Approved {{ amount }}",
                "ttl": "{{ 60 }}",
            },
        )
        self.connection = SimpleNamespace(
            provider_connection_id=self.outbound.provider_connection_id,
            connection_code="gms_viber",
            channel_code="VIBER",
            config={"client_id": "abc"},
            secrets_b64=self.secret_codec.encode(
                {"username": "user", "password": "secret"}
            ),
        )
        self.connector = SimpleNamespace(
            yaml_spec={
                "auth": {
                    "type": "basic",
                    "username_secret_key": "username",
                    "password_secret_key": "password",
                },
                "message_types": [
                    {
                        "code": "viber_text",
                        "send": {
                            "transport": "http",
                            "method": "POST",
                            "url": "https://example.test/{{ config.client_id }}",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "phone_number": "{{ recipient.address }}",
                                "text": "{{ template.text }}",
                                "ttl": "{{ template.ttl }}",
                            },
                            "response_mapping": {
                                "external_message_id": "$.message_id",
                                "external_status": "$.status",
                            },
                        },
                    },
                ],
                "status_mapping": {"23033": "DELIVERED"},
            }
        )
        self.attempt = SimpleNamespace(
            status="STARTED",
            request_payload=None,
            response_payload=None,
            http_status_code=None,
            external_message_id=None,
            error_code=None,
            error_message=None,
            finished_at=None,
        )

    async def claim_queued_messages(self, limit: int):
        return [self.outbound]

    async def load_processing_context(self, outbound_message_id):
        return (
            self.outbound,
            self.request,
            self.template,
            self.version,
            self.connection,
            self.connector,
            self.message_type,
        )

    async def create_delivery_attempt(self, **_kwargs):
        self.attempt.request_payload = _kwargs["request_payload"]
        return self.attempt


class _SmtpTransportStub:
    instances: list["_SmtpTransportStub"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.sent_messages = []
        self.__class__.instances.append(self)

    async def send(self, message) -> None:
        self.sent_messages.append(message)


class _SmtpProcessRepositoryStub(_ProcessRepositoryStub):

    def __init__(self) -> None:
        super().__init__()
        self.outbound.recipient_address = "john@example.com"
        self.request.variables = {"name": "John"}
        self.version.template_payload = {
            "subject": "Hello {{ name }}",
            "text_body": "Plain {{ name }}",
            "html_body": "<p>Hello {{ name }}</p>",
        }
        self.message_type.message_type_code = "email_html"
        self.connection.connection_code = "dnk_smtp"
        self.connection.channel_code = "EMAIL"
        self.connection.config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "from_address": "no-reply@example.com",
            "from_name": "DNK Runtime",
            "use_tls": True,
            "use_starttls": False,
            "timeout_seconds": 10,
        }
        self.connection.secrets_b64 = self.secret_codec.encode(
            {"username": "user@example.com", "password": "secret"}
        )
        self.connector.yaml_spec = {
            "auth": {
                "type": "smtp_login",
                "username_secret_key": "username",
                "password_secret_key": "password",
            },
            "message_types": [
                {
                    "code": "email_text",
                    "send": {
                        "transport": "smtp",
                        "host": "{{ config.smtp_host }}",
                        "port": "{{ config.smtp_port }}",
                        "username": "{{ secrets.username }}",
                        "password": "{{ secrets.password }}",
                        "use_tls": "{{ config.use_tls }}",
                        "use_starttls": "{{ config.use_starttls }}",
                        "timeout_seconds": "{{ config.timeout_seconds }}",
                        "from_address": "{{ config.from_address }}",
                        "from_name": "{{ config.from_name }}",
                        "to_address": "{{ recipient.address }}",
                        "subject": "{{ template.subject }}",
                        "text_body": "{{ template.text_body }}",
                    },
                },
                {
                    "code": "email_html",
                    "send": {
                        "transport": "smtp",
                        "host": "{{ config.smtp_host }}",
                        "port": "{{ config.smtp_port }}",
                        "username": "{{ secrets.username }}",
                        "password": "{{ secrets.password }}",
                        "use_tls": "{{ config.use_tls }}",
                        "use_starttls": "{{ config.use_starttls }}",
                        "timeout_seconds": "{{ config.timeout_seconds }}",
                        "from_address": "{{ config.from_address }}",
                        "from_name": "{{ config.from_name }}",
                        "to_address": "{{ recipient.address }}",
                        "subject": "{{ template.subject }}",
                        "text_body": "{{ template.text_body | default('') }}",
                        "html_body": "{{ template.html_body }}",
                    },
                },
            ],
            "status_mapping": {"sent": "SENT"},
        }


class _IdempotencyRepositoryStub:
    def __init__(self) -> None:
        self.request = SimpleNamespace(
            communication_request_id=uuid4(),
            status="QUEUED",
        )
        self.outbound = SimpleNamespace(
            outbound_message_id=uuid4(),
            internal_status="QUEUED",
        )
        self.created = False

    async def get_existing_send_by_idempotency(self, **_kwargs):
        return self.request, self.outbound

    async def create_send_request(self, **_kwargs):
        self.created = True
        raise AssertionError("idempotent send must not create a new request")


class _WebhookRepositoryStub:
    def __init__(self, *, matched: bool) -> None:
        self.connector = SimpleNamespace(
            yaml_spec={
                "webhook": {
                    "external_message_id_path": "$.message_id",
                    "external_status_path": "$.status",
                    "event_time_path": "$.timestamp",
                },
                "status_mapping": {"Delivered": "DELIVERED"},
            }
        )
        self.outbound = (
            SimpleNamespace(
                tenant_id=uuid4(),
                outbound_message_id=uuid4(),
                provider_connection_id=uuid4(),
                external_status=None,
                internal_status="SENT",
                sent_at=None,
                delivered_at=None,
                failed_at=None,
            )
            if matched
            else None
        )
        self.events = []

    async def get_active_connector_by_code(self, provider_code: str):
        return self.connector

    async def find_outbound_by_external_message_id(self, external_message_id: str):
        return self.outbound

    async def add_delivery_event(self, **kwargs):
        self.events.append(kwargs)
        return SimpleNamespace(**kwargs)


class CommunicationUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_queued_message_renders_payload_and_maps_status(self) -> None:
        repository = _ProcessRepositoryStub()
        http_client = _HttpClientStub()
        use_case = ProcessOutboundMessageUseCase(
            repository=repository,
            sender_registry=ProviderSenderRegistry(
                [
                    YamlHttpProviderSender(
                        http_client=http_client,
                        payload_builder=ProviderPayloadBuildService(),
                        status_mapper=ProviderStatusMappingService(),
                        json_path=JsonPathService(),
                        secret_codec=SecretCodec(),
                    )
                ]
            ),
            template_renderer=TemplateRenderService(),
        )

        result = await use_case(ProcessQueuedMessagesCommand(limit=10))

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(repository.outbound.external_message_id, "ext-123")
        self.assertEqual(
            repository.outbound.internal_status,
            OutboundMessageStatus.DELIVERED.value,
        )
        self.assertEqual(http_client.requests[0]["basic_auth"], ("user", "secret"))
        self.assertEqual(http_client.requests[0]["json_body"]["ttl"], 60)

    async def test_process_queued_message_rejects_old_root_send_without_message_type_send(
        self,
    ) -> None:
        repository = _ProcessRepositoryStub()
        repository.connector.yaml_spec["send"] = {
            "transport": "http",
            "method": "POST",
            "url": "https://example.test/{{ config.client_id }}",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "phone_number": "{{ recipient.address }}",
                "text": "ROOT {{ template.text }}",
                "ttl": "{{ template.ttl }}",
            },
            "response_mapping": {
                "external_message_id": "$.message_id",
                "external_status": "$.status",
            },
        }
        repository.connector.yaml_spec["message_types"] = [
            {
                "code": "viber_text",
            }
        ]
        http_client = _HttpClientStub()
        use_case = ProcessOutboundMessageUseCase(
            repository=repository,
            sender_registry=ProviderSenderRegistry(
                [
                    YamlHttpProviderSender(
                        http_client=http_client,
                        payload_builder=ProviderPayloadBuildService(),
                        status_mapper=ProviderStatusMappingService(),
                        json_path=JsonPathService(),
                        secret_codec=SecretCodec(),
                    )
                ]
            ),
            template_renderer=TemplateRenderService(),
        )

        result = await use_case(ProcessQueuedMessagesCommand(limit=10))

        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(http_client.requests, [])
        self.assertEqual(repository.outbound.internal_status, "FAILED")
        self.assertIn("Send spec is missing", repository.outbound.error_message)

    async def test_process_queued_smtp_message_sends_email_and_redacts_secrets(
        self,
    ) -> None:
        _SmtpTransportStub.instances.clear()
        repository = _SmtpProcessRepositoryStub()
        use_case = ProcessOutboundMessageUseCase(
            repository=repository,
            sender_registry=ProviderSenderRegistry(
                [
                    YamlSmtpProviderSender(
                        payload_builder=ProviderPayloadBuildService(),
                        secret_codec=SecretCodec(),
                        transport_factory=_SmtpTransportStub,
                    )
                ]
            ),
            template_renderer=TemplateRenderService(),
        )

        result = await use_case(ProcessQueuedMessagesCommand(limit=10))

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(repository.outbound.internal_status, "SENT")
        self.assertEqual(
            repository.outbound.external_message_id,
            str(repository.outbound.outbound_message_id),
        )
        transport = _SmtpTransportStub.instances[0]
        self.assertEqual(transport.kwargs["username"], "user@example.com")
        self.assertEqual(transport.kwargs["password"], "secret")
        self.assertEqual(transport.sent_messages[0].recipient_email, "john@example.com")
        self.assertEqual(transport.sent_messages[0].subject, "Hello John")
        self.assertEqual(transport.sent_messages[0].html_body, "<p>Hello John</p>")
        snapshot = repository.outbound.provider_request_payload
        attempt_snapshot = repository.attempt.request_payload
        self.assertTrue(snapshot["has_password"])
        self.assertNotIn("secret", str(snapshot))
        self.assertNotIn("secret", str(attempt_snapshot))

    async def test_process_queued_smtp_text_message_does_not_render_html_body(
        self,
    ) -> None:
        _SmtpTransportStub.instances.clear()
        repository = _SmtpProcessRepositoryStub()
        repository.message_type.message_type_code = "email_text"
        repository.version.template_payload = {
            "subject": "Text {{ name }}",
            "text_body": "Plain {{ name }}",
        }
        use_case = ProcessOutboundMessageUseCase(
            repository=repository,
            sender_registry=ProviderSenderRegistry(
                [
                    YamlSmtpProviderSender(
                        payload_builder=ProviderPayloadBuildService(),
                        secret_codec=SecretCodec(),
                        transport_factory=_SmtpTransportStub,
                    )
                ]
            ),
            template_renderer=TemplateRenderService(),
        )

        result = await use_case(ProcessQueuedMessagesCommand(limit=10))

        self.assertEqual(result.succeeded, 1)
        message = _SmtpTransportStub.instances[0].sent_messages[0]
        self.assertEqual(message.text_body, "Plain John")
        self.assertIsNone(message.html_body)

    async def test_send_communication_returns_existing_idempotent_message(self) -> None:
        repository = _IdempotencyRepositoryStub()
        use_case = SendCommunicationUseCase(
            repository, schema_validator=SimpleNamespace()
        )

        result = await use_case(
            SendCommunicationCommand(
                tenant_id=uuid4(),
                initiator_type="CRM",
                message_class="TRANSACTIONAL",
                channel_code="VIBER",
                recipient_address="380671112233",
                template_code="loan_approved_viber",
                idempotency_key="idem-1",
            )
        )

        self.assertTrue(result.idempotent)
        self.assertFalse(repository.created)
        self.assertEqual(
            result.outbound_message_id, repository.outbound.outbound_message_id
        )

    async def test_webhook_updates_outbound_and_creates_delivery_event(self) -> None:
        repository = _WebhookRepositoryStub(matched=True)
        use_case = HandleProviderWebhookUseCase(
            repository,
            JsonPathService(),
            ProviderStatusMappingService(),
        )

        result = await use_case(
            HandleProviderWebhookCommand(
                provider_code="gms",
                raw_payload={
                    "message_id": "ext-123",
                    "status": "Delivered",
                    "timestamp": "2026-05-11T12:00:00Z",
                },
            )
        )

        self.assertTrue(result.matched)
        self.assertEqual(repository.outbound.internal_status, "DELIVERED")
        self.assertEqual(len(repository.events), 1)
        self.assertEqual(repository.events[0]["external_message_id"], "ext-123")

    async def test_webhook_accepts_unknown_external_message_without_event(self) -> None:
        repository = _WebhookRepositoryStub(matched=False)
        use_case = HandleProviderWebhookUseCase(
            repository,
            JsonPathService(),
            ProviderStatusMappingService(),
        )

        result = await use_case(
            HandleProviderWebhookCommand(
                provider_code="gms",
                raw_payload={"message_id": "missing", "status": "Delivered"},
            )
        )

        self.assertTrue(result.accepted)
        self.assertFalse(result.matched)
        self.assertEqual(repository.events, [])


__all__ = ["CommunicationUseCaseTests"]
