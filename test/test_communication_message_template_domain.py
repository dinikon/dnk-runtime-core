from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.message_template import (
    InvalidMessageTemplateNameError,
    InvalidTemplateVersionTimestampError,
    MessageTemplateEntity,
    MessageTemplateIdVO,
    MessageTemplateNameVO,
    MessageTemplateService,
    TemplateStatusVO,
    TemplateVersionEntity,
    TemplateVersionIdVO,
    TemplateVersionNotFoundError,
    TemplateVersionStatusVO,
    TemplateVersionTimestampVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderConnectorNotFoundError,
    ProviderMessageType,
    ProviderMessageTypeIdVO,
    ProviderMessageTypeNotFoundError,
)
from src.modules.shared import EntityIdVO

NOW = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class _ClockStub:
    def __init__(self, now: datetime = NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _SchemaValidatorStub:
    def __init__(self) -> None:
        self.template_payload_calls = []
        self.variables_schema_calls = []

    def validate_template_payload(self, payload, field_schema) -> None:
        self.template_payload_calls.append((payload, field_schema))

    def validate_variables_schema(self, schema) -> None:
        self.variables_schema_calls.append(schema)


class _RepositoryStub:
    def __init__(self) -> None:
        self.templates: dict[MessageTemplateIdVO, MessageTemplateEntity] = {}
        self.versions: dict[TemplateVersionIdVO, TemplateVersionEntity] = {}
        self.saved_templates = []
        self.saved_version_batches = []

    async def load_template(self, *, tenant_id, template_id):
        return self.templates.get(template_id)

    async def save_template(self, *, tenant_id, template):
        self.templates[template.template_id] = template
        self.saved_templates.append(template)
        return template

    async def list_templates(self, *, tenant_id):
        return list(self.templates.values())

    async def load_template_version(self, *, tenant_id, template_version_id):
        return self.versions.get(template_version_id)

    async def load_active_template_version(self, *, tenant_id, template_id):
        for version in self.versions.values():
            if version.template_id == template_id and version.is_active:
                return version
        return None

    async def list_template_versions(self, *, tenant_id, template_id):
        return [
            version
            for version in self.versions.values()
            if version.template_id == template_id
        ]

    async def save_template_version(self, *, tenant_id, version):
        self.versions[version.template_version_id] = version
        return version

    async def save_template_versions(self, *, tenant_id, versions):
        self.saved_version_batches.append(list(versions))
        for version in versions:
            self.versions[version.template_version_id] = version
        return list(versions)


class _ProviderLookupStub:
    def __init__(
        self,
        *,
        connector: ProviderConnector | None,
        message_type: ProviderMessageType | None,
    ) -> None:
        self.connector = connector
        self.message_type = message_type

    async def load_provider_connector(self, *, tenant_id, provider_connector_id):
        if (
            self.connector is not None
            and self.connector.provider_connector_id == provider_connector_id
        ):
            return self.connector
        return None

    async def load_provider_message_type(self, *, tenant_id, provider_message_type_id):
        if (
            self.message_type is not None
            and self.message_type.provider_message_type_id == provider_message_type_id
        ):
            return self.message_type
        return None


class MessageTemplateDomainTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = EntityIdVO.from_value(uuid4())
        self.connector_id = ProviderConnectorIdVO.from_value(uuid4())
        self.message_type_id = ProviderMessageTypeIdVO.from_value(uuid4())
        self.template_id = MessageTemplateIdVO.from_value(uuid4())
        self.version_id = TemplateVersionIdVO.from_value(uuid4())
        self.connector = ProviderConnector(
            provider_connector_id=self.connector_id,
            provider_code="turbosms",
            provider_name="TurboSMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={},
            yaml_checksum="checksum",
            status="ACTIVE",
            created_at=NOW,
            updated_at=NOW,
        )
        self.message_type = ProviderMessageType(
            provider_message_type_id=self.message_type_id,
            provider_connector_id=self.connector_id,
            message_type_code="sms_text",
            channel_code="SMS",
            name="SMS Text",
            field_schema={"type": "object"},
            ui_schema={},
            is_active=True,
        )

    def test_message_template_create_sets_draft_status_and_timestamps(self) -> None:
        template = self._template()

        self.assertEqual(template.status, TemplateStatusVO.DRAFT)
        self.assertEqual(template.name, MessageTemplateNameVO("OTP SMS"))
        self.assertEqual(template.created_at, NOW)
        self.assertEqual(template.updated_at, NOW)

    def test_message_template_name_rejects_blank_value(self) -> None:
        with self.assertRaises(InvalidMessageTemplateNameError):
            MessageTemplateNameVO("")

    def test_template_version_timestamp_normalizes_to_utc_seconds(self) -> None:
        timestamp = TemplateVersionTimestampVO(datetime(2026, 5, 13, 15, 0, 5, 123456))

        self.assertEqual(timestamp.value, datetime(2026, 5, 13, 15, 0, 5, tzinfo=UTC))

    def test_template_version_timestamp_rejects_non_datetime(self) -> None:
        with self.assertRaises(InvalidTemplateVersionTimestampError):
            TemplateVersionTimestampVO("2026-05-13")  # type: ignore[arg-type]

    def test_message_template_binding_rejects_connector_mismatch(self) -> None:
        template = self._template()
        message_type = ProviderMessageType(
            provider_message_type_id=self.message_type_id,
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            message_type_code="sms_text",
            channel_code="SMS",
            name="SMS Text",
            field_schema={},
            ui_schema={},
            is_active=True,
        )

        with self.assertRaises(CommunicationValidationError):
            template.ensure_message_type_binding(message_type)

    def test_message_template_binding_rejects_channel_mismatch(self) -> None:
        template = self._template(channel_code="EMAIL")

        with self.assertRaises(CommunicationValidationError):
            template.ensure_message_type_binding(self.message_type)

    def test_template_version_state_methods(self) -> None:
        template = self._template()
        version = TemplateVersionEntity.create(
            template_version_id=self.version_id,
            template_id=template.template_id,
            version=NOW,
            template_payload={"text": "Hello"},
            variables_schema={},
            now=NOW,
        )

        self.assertEqual(version.status, TemplateVersionStatusVO.DRAFT)
        self.assertEqual(version.version.value, NOW)
        self.assertIsNone(version.activated_at)
        self.assertFalse(version.is_active)

        activated_at = NOW + timedelta(minutes=5)
        version.activate(now=activated_at)

        self.assertTrue(version.is_active)
        self.assertEqual(version.activated_at, activated_at)

        version.deprecate()

        self.assertEqual(version.status, TemplateVersionStatusVO.DEPRECATED)

    def test_template_version_ensure_belongs_to_rejects_other_template(self) -> None:
        version = TemplateVersionEntity.create(
            template_version_id=self.version_id,
            template_id=MessageTemplateIdVO.from_value(uuid4()),
            version=NOW,
            template_payload={},
            variables_schema={},
            now=NOW,
        )

        with self.assertRaises(TemplateVersionNotFoundError):
            version.ensure_belongs_to(self._template())

    async def test_service_create_template_happy_path(self) -> None:
        repository = _RepositoryStub()
        service = self._service(repository=repository)

        template = await service.create_template(
            tenant_id=self.tenant_id,
            template_id=self.template_id,
            name="OTP SMS",
            description=None,
            provider_connector_id=self.connector_id,
            provider_message_type_id=self.message_type_id,
            channel_code="SMS",
        )

        self.assertEqual(template.template_id, self.template_id)
        self.assertEqual(template.status, TemplateStatusVO.DRAFT)
        self.assertEqual(repository.saved_templates, [template])

    async def test_service_create_template_rejects_missing_connector(self) -> None:
        service = self._service(
            provider_lookup=_ProviderLookupStub(
                connector=None,
                message_type=self.message_type,
            )
        )

        with self.assertRaises(ProviderConnectorNotFoundError):
            await service.create_template(
                tenant_id=self.tenant_id,
                template_id=self.template_id,
                name="OTP SMS",
                description=None,
                provider_connector_id=self.connector_id,
                provider_message_type_id=self.message_type_id,
                channel_code="SMS",
            )

    async def test_service_create_template_rejects_disabled_connector(self) -> None:
        self.connector.status = "DISABLED"
        service = self._service(
            provider_lookup=_ProviderLookupStub(
                connector=self.connector,
                message_type=self.message_type,
            )
        )

        with self.assertRaises(CommunicationValidationError):
            await service.create_template(
                tenant_id=self.tenant_id,
                template_id=self.template_id,
                name="OTP SMS",
                description=None,
                provider_connector_id=self.connector_id,
                provider_message_type_id=self.message_type_id,
                channel_code="SMS",
            )

    async def test_service_create_template_rejects_missing_message_type(self) -> None:
        service = self._service(
            provider_lookup=_ProviderLookupStub(
                connector=self.connector,
                message_type=None,
            )
        )

        with self.assertRaises(ProviderMessageTypeNotFoundError):
            await service.create_template(
                tenant_id=self.tenant_id,
                template_id=self.template_id,
                name="OTP SMS",
                description=None,
                provider_connector_id=self.connector_id,
                provider_message_type_id=self.message_type_id,
                channel_code="SMS",
            )

    async def test_service_create_template_version_validates_and_sets_utc_version(
        self,
    ) -> None:
        repository = _RepositoryStub()
        validator = _SchemaValidatorStub()
        template = self._template()
        repository.templates[template.template_id] = template
        repository.versions[TemplateVersionIdVO.from_value(uuid4())] = (
            TemplateVersionEntity.create(
                template_version_id=TemplateVersionIdVO.from_value(uuid4()),
                template_id=template.template_id,
                version=NOW - timedelta(minutes=5),
                template_payload={"text": "Old"},
                variables_schema={},
                now=NOW,
            )
        )
        service = self._service(repository=repository, validator=validator)

        version = await service.create_template_version(
            tenant_id=self.tenant_id,
            template_id=template.template_id,
            template_version_id=self.version_id,
            template_payload={"text": "Hello"},
            variables_schema={"type": "object"},
        )

        self.assertEqual(version.template_version_id, self.version_id)
        self.assertEqual(version.version.value, NOW)
        self.assertEqual(
            validator.template_payload_calls,
            [({"text": "Hello"}, self.message_type.field_schema)],
        )
        self.assertEqual(validator.variables_schema_calls, [{"type": "object"}])

    async def test_service_activate_version_deprecates_previous_active(self) -> None:
        repository = _RepositoryStub()
        template = self._template()
        previous = TemplateVersionEntity.create(
            template_version_id=TemplateVersionIdVO.from_value(uuid4()),
            template_id=template.template_id,
            version=NOW - timedelta(minutes=5),
            template_payload={"text": "Old"},
            variables_schema={},
            now=NOW,
        )
        previous.activate(now=NOW)
        selected = TemplateVersionEntity.create(
            template_version_id=self.version_id,
            template_id=template.template_id,
            version=NOW,
            template_payload={"text": "New"},
            variables_schema={},
            now=NOW,
        )
        repository.templates[template.template_id] = template
        repository.versions[previous.template_version_id] = previous
        repository.versions[selected.template_version_id] = selected
        service = self._service(repository=repository)

        activated = await service.activate_template_version(
            tenant_id=self.tenant_id,
            template_id=template.template_id,
            template_version_id=selected.template_version_id,
        )

        self.assertEqual(activated.status, TemplateVersionStatusVO.ACTIVE)
        self.assertEqual(previous.status, TemplateVersionStatusVO.DEPRECATED)
        self.assertEqual(template.status, TemplateStatusVO.ACTIVE)
        self.assertEqual(repository.saved_templates[-1], template)
        self.assertEqual(len(repository.saved_version_batches[-1]), 2)

    def _template(self, *, channel_code: str = "SMS") -> MessageTemplateEntity:
        return MessageTemplateEntity.create(
            template_id=self.template_id,
            tenant_id=self.tenant_id,
            name="OTP SMS",
            description=None,
            provider_connector_id=self.connector_id,
            provider_message_type_id=self.message_type_id,
            channel_code=channel_code,
            now=NOW,
        )

    def _service(
        self,
        *,
        repository: _RepositoryStub | None = None,
        provider_lookup: _ProviderLookupStub | None = None,
        validator: _SchemaValidatorStub | None = None,
    ) -> MessageTemplateService:
        return MessageTemplateService(
            command_repository=repository or _RepositoryStub(),
            provider_lookup=provider_lookup
            or _ProviderLookupStub(
                connector=self.connector,
                message_type=self.message_type,
            ),
            schema_validator=validator or _SchemaValidatorStub(),
            clock=_ClockStub(),
        )


__all__ = ["MessageTemplateDomainTests"]
