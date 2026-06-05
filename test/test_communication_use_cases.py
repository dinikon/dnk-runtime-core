from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from src.modules.communication.application.outbound_message.provider_send import (
    ProviderHttpResponse,
)
from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    SecretCodec,
    TemplateRenderService,
)
from src.modules.communication.application.outbound_message import (
    ProcessOutboundMessageByIdCommand,
    ProcessOutboundMessageByIdUseCase,
    ProcessOutboundMessageUseCase,
    ProcessQueuedMessagesCommand,
    SendCommunicationCommand,
    SendCommunicationUseCase,
)
from src.modules.communication.application.delivery import (
    DeliveryAttemptDTO,
    DeliveryEventDTO,
    HandleProviderWebhookCommand,
    HandleProviderWebhookUseCase,
    ListDeliveryAttemptsQuery,
    ListDeliveryAttemptsUseCase,
    ListDeliveryEventsQuery,
    ListDeliveryEventsUseCase,
)
from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.delivery import (
    DeliveryEventIdVO,
    DeliveryService,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    InvalidIdempotencyKeyError,
    InvalidInitiatorTypeError,
    OutboundMessageService,
    OutboundMessageIdVO,
    OutboundMessageStatus,
)
from src.modules.communication.domain.provider_connection import ProviderConnectionIdVO
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
)
from src.modules.communication.infrastructure.provider_senders import (
    ProviderSenderRegistry,
    YamlHttpProviderSender,
    YamlSmtpProviderSender,
)
from src.modules.shared import EntityIdVO


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


class _TurboSmsHttpClientStub(_HttpClientStub):
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
            payload={
                "response_code": 0,
                "response_status": "OK",
                "response_result": [
                    {
                        "phone": "380671112233",
                        "message_id": "turbo-123",
                        "response_status": "OK",
                    }
                ],
            },
        )


class _FailingHttpClientStub(_HttpClientStub):
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
            status_code=500,
            payload={"error": "temporary"},
        )


class _ProcessRepositoryStub:
    def __init__(self) -> None:
        self.secret_codec = SecretCodec()
        self.outbound = SimpleNamespace(
            outbound_message_id=uuid4(),
            communication_request_id=uuid4(),
            provider_connection_id=uuid4(),
            recipient_identifier_type="PHONE",
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
            processing_token=uuid4(),
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
        self.connection.ensure_active = lambda: None
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
                "retry_policy": {
                    "max_attempts": 3,
                    "backoff": {"initial_seconds": 30, "max_seconds": 600},
                },
            }
        )
        self.connector.ensure_active = lambda: None
        self.attempt = SimpleNamespace(
            delivery_attempt_id=uuid4(),
            attempt_no=1,
            status="STARTED",
            request_payload=None,
            response_payload=None,
            http_status_code=None,
            external_message_id=None,
            error_code=None,
            error_message=None,
            finished_at=None,
        )

    async def claim_queued_messages(self, tenant_id, limit: int):
        return [self.outbound]

    async def load_processing_context(self, tenant_id, outbound_message_id):
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

    async def complete_outbound_processing(self, **kwargs):
        self.outbound.rendered_payload = kwargs["rendered_payload"]
        self.outbound.provider_request_payload = kwargs["provider_request_payload"]
        self.outbound.external_message_id = kwargs["external_message_id"]
        self.outbound.external_status = kwargs["external_status"]
        self.outbound.internal_status = kwargs["internal_status"]
        return True

    async def fail_outbound_processing(self, **kwargs):
        self.outbound.internal_status = "FAILED"
        self.outbound.error_code = kwargs["error_code"]
        self.outbound.error_message = kwargs["error_message"]
        return True


class _ByIdRepositoryStub(_ProcessRepositoryStub):
    def __init__(self, *, claimable: bool = True) -> None:
        super().__init__()
        self.claimable = claimable
        self.completed = False
        self.failed_processing = False
        self.last_failure_kwargs = None
        self.claim_tokens = []

    async def claim_outbound_for_processing(self, **kwargs):
        self.claim_tokens.append(kwargs["processing_token"])
        if not self.claimable:
            self.outbound.internal_status = "SENT"
            return None
        self.outbound.internal_status = "SENDING"
        self.outbound.processing_token = kwargs["processing_token"]
        return self.outbound

    async def get_outbound_by_id(self, _tenant_id, _outbound_message_id):
        return self.outbound

    async def complete_outbound_processing(self, **kwargs):
        self.completed = True
        self.outbound.internal_status = kwargs["internal_status"]
        self.outbound.external_message_id = kwargs["external_message_id"]
        return True

    async def fail_outbound_processing(self, **kwargs):
        self.last_failure_kwargs = kwargs
        self.failed_processing = True
        self.outbound.internal_status = (
            "QUEUED" if kwargs.get("retry_at") is not None else "FAILED"
        )
        return True


class _UnitOfWorkStub:
    def __init__(self, _session_factory):
        self.session = object()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _RepositoryContextFactoryStub:
    def __init__(self, repository) -> None:
        self.repository = repository

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.repository

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _ClockStub:
    def now(self):
        return datetime.now(UTC)


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
        self.outbound.recipient_identifier_type = "EMAIL"
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


class _TurboSmsProcessRepositoryStub(_ProcessRepositoryStub):
    def __init__(self) -> None:
        super().__init__()
        self.message_type.message_type_code = "sms_text"
        self.connection.connection_code = "turbosms_sms"
        self.connection.channel_code = "SMS"
        self.connection.config = {"sender": "TurboSMS"}
        self.connection.secrets_b64 = self.secret_codec.encode(
            {"api_key": "turbo-secret-token"}
        )
        self.connector.yaml_spec = {
            "auth": {
                "type": "bearer",
                "token_secret_key": "api_key",
            },
            "message_types": [
                {
                    "code": "sms_text",
                    "send": {
                        "transport": "http",
                        "method": "POST",
                        "url": "https://api.turbosms.ua/message/send.json",
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "sequence_id": "{{ message.outbound_message_id }}",
                            "recipients": ["{{ recipient.address }}"],
                            "sms": {
                                "sender": "{{ config.sender }}",
                                "text": "{{ template.text }}",
                            },
                        },
                        "response_mapping": {
                            "external_message_id": "$.response_result[0].message_id",
                            "external_status": "$.response_result[0].response_status",
                        },
                    },
                },
            ],
            "status_mapping": {"OK": "SENT"},
        }


class _IdempotencyRepositoryStub:
    def __init__(self) -> None:
        self.request = SimpleNamespace(
            communication_request_id=CommunicationRequestIdVO.from_value(uuid4()),
            status="QUEUED",
        )
        self.outbound = SimpleNamespace(
            outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
            internal_status="QUEUED",
        )
        self.created = False

    async def get_existing_send_by_idempotency(self, **_kwargs):
        return self.request, self.outbound

    async def create_send_request(self, **_kwargs):
        self.created = True
        raise AssertionError("idempotent send must not create a new request")


class _SendRepositoryStub:
    def __init__(self, *, channel_code: str = "SMS") -> None:
        self.template = SimpleNamespace(
            template_id=MessageTemplateIdVO.from_value(uuid4()),
            channel_code=SimpleNamespace(value=channel_code),
            message_class=SimpleNamespace(value="TRANSACTIONAL"),
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
        )
        self.version = SimpleNamespace(
            template_version_id=TemplateVersionIdVO.from_value(uuid4()),
            variables_schema={},
        )
        self.connection = SimpleNamespace(
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
        )
        self.created_kwargs = None
        self.get_existing_calls = []
        self.template_calls = 0
        self.version_calls = 0
        self.connection_calls = 0

    async def get_existing_send_by_idempotency(self, **kwargs):
        self.get_existing_calls.append(kwargs)
        return None

    async def get_template(self, **_kwargs):
        self.template_calls += 1
        return self.template

    async def get_template_by_code(self, **_kwargs):
        return self.template

    async def get_active_template_version(self, *_args, **_kwargs):
        self.version_calls += 1
        return self.version

    async def find_active_connection(self, **_kwargs):
        self.connection_calls += 1
        return self.connection

    async def create_send_request(self, **kwargs):
        self.created_kwargs = kwargs
        return (
            SimpleNamespace(
                communication_request_id=kwargs["communication_request_id"],
                status="QUEUED",
            ),
            SimpleNamespace(
                outbound_message_id=kwargs["outbound_message_id"],
                internal_status="QUEUED",
            ),
        )


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
                tenant_id=EntityIdVO.from_value(uuid4()),
                outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
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

    async def get_active_connector_by_code(self, *, tenant_id, provider_code):
        return self.connector

    async def find_outbound_by_external_message_id(
        self,
        *,
        tenant_id,
        external_message_id: str,
    ):
        return self.outbound

    async def add_delivery_event(self, *, tenant_id, event):
        self.events.append(event)
        return event

    async def update_outbound_status_from_event(self, **kwargs):
        self.outbound.internal_status = kwargs["internal_status"]
        return self.outbound


class _DeliveryQueryRepositoryStub:
    def __init__(self) -> None:
        self.attempt_calls = []
        self.event_calls = []
        self.now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        self.outbound_id = OutboundMessageIdVO.from_value(uuid4())

    async def list_delivery_attempts(self, **kwargs):
        self.attempt_calls.append(kwargs)
        return [
            DeliveryAttemptDTO(
                delivery_attempt_id=uuid4(),
                tenant_id=kwargs["tenant_id"].uuid,
                outbound_message_id=self.outbound_id.uuid,
                provider_connection_id=uuid4(),
                attempt_no=1,
                status="SUCCESS",
                request_payload={"body": "hello"},
                response_payload={"status": "sent"},
                http_status_code=200,
                external_message_id="ext-1",
                error_code=None,
                error_message=None,
                started_at=self.now,
                finished_at=self.now,
            )
        ]

    async def list_delivery_events(self, **kwargs):
        self.event_calls.append(kwargs)
        return [
            DeliveryEventDTO(
                delivery_event_id=uuid4(),
                tenant_id=kwargs["tenant_id"].uuid,
                outbound_message_id=self.outbound_id.uuid,
                provider_connection_id=uuid4(),
                external_message_id="ext-1",
                external_status="Delivered",
                internal_status="DELIVERED",
                event_type="WEBHOOK_RECEIVED",
                event_at=self.now,
                raw_payload={"message_id": "ext-1"},
                created_at=self.now,
            )
        ]


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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(repository.outbound.external_message_id, "ext-123")
        self.assertEqual(
            repository.outbound.internal_status,
            OutboundMessageStatus.DELIVERED.value,
        )
        self.assertEqual(http_client.requests[0]["basic_auth"], ("user", "secret"))
        self.assertEqual(http_client.requests[0]["json_body"]["ttl"], 60)

    async def test_process_queued_message_fails_when_connection_disabled(self) -> None:
        repository = _ProcessRepositoryStub()

        def _raise_disabled() -> None:
            raise CommunicationValidationError("Provider connection is not active.")

        repository.connection.ensure_active = _raise_disabled
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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(repository.outbound.internal_status, "FAILED")
        self.assertEqual(repository.outbound.error_code, "CommunicationValidationError")
        self.assertEqual(http_client.requests, [])
        self.assertIsNone(repository.attempt.request_payload)

    async def test_process_queued_http_bearer_auth_uses_secret_without_persisting_it(
        self,
    ) -> None:
        repository = _TurboSmsProcessRepositoryStub()
        http_client = _TurboSmsHttpClientStub()
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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

        self.assertEqual(result.succeeded, 1)
        self.assertEqual(repository.outbound.external_message_id, "turbo-123")
        self.assertEqual(repository.outbound.internal_status, "SENT")
        self.assertEqual(
            http_client.requests[0]["headers"]["Authorization"],
            "Bearer turbo-secret-token",
        )
        self.assertIsNone(http_client.requests[0]["basic_auth"])
        self.assertEqual(
            http_client.requests[0]["json_body"]["sequence_id"],
            str(repository.outbound.outbound_message_id),
        )
        snapshot = repository.outbound.provider_request_payload
        attempt_snapshot = repository.attempt.request_payload
        self.assertEqual(snapshot["headers"]["Authorization"], "[REDACTED]")
        self.assertNotIn("turbo-secret-token", str(snapshot))
        self.assertNotIn("turbo-secret-token", str(attempt_snapshot))

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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(http_client.requests, [])
        self.assertEqual(repository.outbound.internal_status, "FAILED")
        self.assertIn("Send spec is missing", repository.outbound.error_message)

    async def test_process_outbound_by_id_claims_sends_and_persists_success(
        self,
    ) -> None:
        repository = _ByIdRepositoryStub()
        http_client = _HttpClientStub()
        use_case = ProcessOutboundMessageByIdUseCase(
            repository_context_factory=_RepositoryContextFactoryStub(repository),
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
            processing_lease_seconds=300,
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessOutboundMessageByIdCommand(
                tenant_id=uuid4(),
                outbound_message_id=repository.outbound.outbound_message_id,
            )
        )

        self.assertTrue(result.processed)
        self.assertTrue(result.succeeded)
        self.assertTrue(repository.completed)
        self.assertEqual(repository.outbound.external_message_id, "ext-123")
        self.assertEqual(http_client.requests[0]["json_body"]["text"], "Approved 15000")

    async def test_process_outbound_by_id_requeues_retryable_provider_failure(
        self,
    ) -> None:
        repository = _ByIdRepositoryStub()
        http_client = _FailingHttpClientStub()
        use_case = ProcessOutboundMessageByIdUseCase(
            repository_context_factory=_RepositoryContextFactoryStub(repository),
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
            processing_lease_seconds=300,
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessOutboundMessageByIdCommand(
                tenant_id=uuid4(),
                outbound_message_id=repository.outbound.outbound_message_id,
            )
        )

        self.assertTrue(result.processed)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.status, OutboundMessageStatus.QUEUED.value)
        self.assertIsNotNone(repository.last_failure_kwargs["retry_at"])
        self.assertEqual(repository.outbound.internal_status, "QUEUED")

    async def test_process_outbound_by_id_skips_duplicate_non_queued_message(
        self,
    ) -> None:
        repository = _ByIdRepositoryStub(claimable=False)
        http_client = _HttpClientStub()
        use_case = ProcessOutboundMessageByIdUseCase(
            repository_context_factory=_RepositoryContextFactoryStub(repository),
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
            processing_lease_seconds=300,
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessOutboundMessageByIdCommand(
                tenant_id=uuid4(),
                outbound_message_id=repository.outbound.outbound_message_id,
            )
        )

        self.assertFalse(result.processed)
        self.assertTrue(result.skipped)
        self.assertEqual(result.status, "SENT")
        self.assertEqual(http_client.requests, [])

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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

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
            clock=_ClockStub(),
        )

        result = await use_case(
            ProcessQueuedMessagesCommand(tenant_id=uuid4(), limit=10)
        )

        self.assertEqual(result.succeeded, 1)
        message = _SmtpTransportStub.instances[0].sent_messages[0]
        self.assertEqual(message.text_body, "Plain John")
        self.assertIsNone(message.html_body)

    async def test_send_communication_returns_existing_idempotent_message(self) -> None:
        repository = _IdempotencyRepositoryStub()
        use_case = SendCommunicationUseCase(
            repository=repository,
            service=OutboundMessageService(repository=repository, clock=_ClockStub()),
            template_lookup=repository,
            schema_validator=SimpleNamespace(),
            provider_connection_lookup=repository,
        )

        result = await use_case(
            SendCommunicationCommand(
                tenant_id=uuid4(),
                initiator_type="CRM",
                initiator_ref_id="deal:1",
                correlation_id=uuid4(),
                idempotency_key="idem-1",
                channel_code="VIBER",
                template_id=MessageTemplateIdVO.from_value(uuid4()),
                recipient_identifier_type="PHONE",
                recipient_address="380671112233",
                recipient_snapshot={"source_kind": "RAW_VALUE"},
            )
        )

        self.assertTrue(result.idempotent)
        self.assertFalse(repository.created)
        self.assertEqual(
            result.outbound_message_id,
            repository.outbound.outbound_message_id.uuid,
        )

    async def test_send_communication_rejects_blank_idempotency_key_first(self) -> None:
        repository = _SendRepositoryStub()
        use_case = SendCommunicationUseCase(
            repository=repository,
            service=OutboundMessageService(repository=repository, clock=_ClockStub()),
            template_lookup=repository,
            schema_validator=SimpleNamespace(validate=lambda *_args: None),
            provider_connection_lookup=repository,
        )

        with self.assertRaises(InvalidIdempotencyKeyError):
            await use_case(
                SendCommunicationCommand(
                    tenant_id=uuid4(),
                    initiator_type="CRM",
                    initiator_ref_id="manual:1",
                    correlation_id=uuid4(),
                    idempotency_key=" ",
                    channel_code="SMS",
                    template_id=MessageTemplateIdVO.from_value(uuid4()),
                    recipient_identifier_type="PHONE",
                    recipient_address="+380671112233",
                    recipient_snapshot={"manual": True},
                )
            )

        self.assertIsNone(repository.created_kwargs)

    async def test_send_communication_rejects_invalid_initiator_after_idempotency_miss(
        self,
    ) -> None:
        repository = _SendRepositoryStub()
        use_case = SendCommunicationUseCase(
            repository=repository,
            service=OutboundMessageService(repository=repository, clock=_ClockStub()),
            template_lookup=repository,
            schema_validator=SimpleNamespace(validate=lambda *_args: None),
            provider_connection_lookup=repository,
        )

        with self.assertRaises(InvalidInitiatorTypeError):
            await use_case(
                SendCommunicationCommand(
                    tenant_id=uuid4(),
                    initiator_type="manual",
                    initiator_ref_id="manual:1",
                    correlation_id=uuid4(),
                    idempotency_key="idem-send-invalid-initiator",
                    channel_code="SMS",
                    template_id=MessageTemplateIdVO.from_value(uuid4()),
                    recipient_identifier_type="PHONE",
                    recipient_address="+380671112233",
                    recipient_snapshot={"manual": True},
                )
            )

        self.assertEqual(len(repository.get_existing_calls), 1)
        self.assertEqual(repository.template_calls, 0)
        self.assertEqual(repository.version_calls, 0)
        self.assertEqual(repository.connection_calls, 0)
        self.assertIsNone(repository.created_kwargs)

    async def test_send_communication_uses_prepared_recipient_address(self) -> None:
        repository = _SendRepositoryStub()
        use_case = SendCommunicationUseCase(
            repository=repository,
            service=OutboundMessageService(repository=repository, clock=_ClockStub()),
            template_lookup=repository,
            schema_validator=SimpleNamespace(validate=lambda *_args: None),
            provider_connection_lookup=repository,
        )

        result = await use_case(
            SendCommunicationCommand(
                tenant_id=uuid4(),
                initiator_type=" crm ",
                initiator_ref_id="manual:1",
                correlation_id=uuid4(),
                idempotency_key="idem-send-1",
                channel_code="SMS",
                template_id=MessageTemplateIdVO.from_value(uuid4()),
                recipient_identifier_type="PHONE",
                recipient_address="+380671112233",
                recipient_snapshot={"manual": True},
            )
        )

        self.assertFalse(result.idempotent)
        assert repository.created_kwargs is not None
        self.assertEqual(
            repository.created_kwargs["recipient_address"],
            "+380671112233",
        )
        self.assertEqual(
            repository.created_kwargs["recipient_snapshot"],
            {"manual": True},
        )
        self.assertEqual(
            repository.created_kwargs["recipient_identifier_type"],
            "PHONE",
        )
        self.assertEqual(repository.created_kwargs["initiator_type"], "CRM")

    async def test_list_delivery_attempts_use_case_delegates_filters(self) -> None:
        repository = _DeliveryQueryRepositoryStub()
        use_case = ListDeliveryAttemptsUseCase(repository)
        tenant_id = EntityIdVO.from_value(uuid4())

        result = await use_case(
            ListDeliveryAttemptsQuery(
                tenant_id=tenant_id,
                outbound_message_id=repository.outbound_id,
                status="SUCCESS",
                limit=25,
                offset=50,
            )
        )

        self.assertEqual(result[0].status, "SUCCESS")
        self.assertEqual(repository.attempt_calls[0]["tenant_id"], tenant_id)
        self.assertEqual(
            repository.attempt_calls[0]["outbound_message_id"],
            repository.outbound_id,
        )
        self.assertEqual(repository.attempt_calls[0]["status"], "SUCCESS")
        self.assertEqual(repository.attempt_calls[0]["limit"], 25)
        self.assertEqual(repository.attempt_calls[0]["offset"], 50)

    async def test_list_delivery_events_use_case_delegates_filters(self) -> None:
        repository = _DeliveryQueryRepositoryStub()
        use_case = ListDeliveryEventsUseCase(repository)
        tenant_id = EntityIdVO.from_value(uuid4())

        result = await use_case(
            ListDeliveryEventsQuery(
                tenant_id=tenant_id,
                outbound_message_id=repository.outbound_id,
                external_message_id="ext-1",
                internal_status="DELIVERED",
                event_type="WEBHOOK_RECEIVED",
                limit=10,
                offset=20,
            )
        )

        self.assertEqual(result[0].event_type, "WEBHOOK_RECEIVED")
        self.assertEqual(repository.event_calls[0]["tenant_id"], tenant_id)
        self.assertEqual(
            repository.event_calls[0]["outbound_message_id"],
            repository.outbound_id,
        )
        self.assertEqual(repository.event_calls[0]["external_message_id"], "ext-1")
        self.assertEqual(repository.event_calls[0]["internal_status"], "DELIVERED")
        self.assertEqual(repository.event_calls[0]["event_type"], "WEBHOOK_RECEIVED")
        self.assertEqual(repository.event_calls[0]["limit"], 10)
        self.assertEqual(repository.event_calls[0]["offset"], 20)

    async def test_webhook_updates_outbound_and_creates_delivery_event(self) -> None:
        repository = _WebhookRepositoryStub(matched=True)
        use_case = HandleProviderWebhookUseCase(
            repository=repository,
            service=DeliveryService(repository=repository, clock=_ClockStub()),
            json_path=JsonPathService(),
            status_mapper=ProviderStatusMappingService(),
        )
        tenant_id = EntityIdVO.from_value(uuid4())

        result = await use_case(
            HandleProviderWebhookCommand(
                tenant_id=tenant_id,
                delivery_event_id=DeliveryEventIdVO.from_value(uuid4()),
                provider_code=ProviderConnectorCodeVO("gms"),
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
        self.assertEqual(repository.events[0].external_message_id, "ext-123")

    async def test_webhook_accepts_unknown_external_message_without_event(self) -> None:
        repository = _WebhookRepositoryStub(matched=False)
        use_case = HandleProviderWebhookUseCase(
            repository=repository,
            service=DeliveryService(repository=repository, clock=_ClockStub()),
            json_path=JsonPathService(),
            status_mapper=ProviderStatusMappingService(),
        )
        tenant_id = EntityIdVO.from_value(uuid4())

        result = await use_case(
            HandleProviderWebhookCommand(
                tenant_id=tenant_id,
                delivery_event_id=DeliveryEventIdVO.from_value(uuid4()),
                provider_code=ProviderConnectorCodeVO("gms"),
                raw_payload={"message_id": "missing", "status": "Delivered"},
            )
        )

        self.assertTrue(result.accepted)
        self.assertFalse(result.matched)
        self.assertEqual(repository.events, [])


__all__ = ["CommunicationUseCaseTests"]
