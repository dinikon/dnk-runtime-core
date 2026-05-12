from __future__ import annotations

import unittest
from pathlib import Path

from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    ProviderYamlLoader,
    SecretCodec,
    TemplateRenderService,
)
from src.modules.communication.domain import (
    CommunicationValidationError,
    OutboundMessageStatus,
)
from src.modules.communication.infrastructure.persistence import ProviderConnectionModel
from src.modules.communication.infrastructure.repository import connection_to_dto

VALID_PROVIDER_YAML = """
provider_code: gms
provider_name: GMS
version: "1.0.0"
connector_type: YAML_HTTP
channels:
  - VIBER
auth:
  type: basic
  username_secret_key: username
  password_secret_key: password
config_schema:
  type: object
  required: [client_id]
  properties:
    client_id:
      type: string
secrets_schema:
  type: object
  required: [username, password]
  properties:
    username:
      type: string
    password:
      type: string
      format: password
message_types:
  - code: viber_text
    channel: VIBER
    name: Viber text
    field_schema:
      type: object
      required: [text]
      properties:
        text:
          type: string
        ttl:
          type: integer
          default: 60
    send:
      transport: http
      method: POST
      url: "https://example.test/{{ config.client_id }}"
      headers:
        Content-Type: application/json
      body:
        phone_number: "{{ recipient.address }}"
        text: "{{ template.text }}"
        ttl: "{{ template.ttl }}"
      response_mapping:
        external_message_id: "$.message_id"
        external_status: "$.status"
webhook:
  external_message_id_path: "$.message_id"
  external_status_path: "$.status"
status_mapping:
  "23033": DELIVERED
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CommunicationServicesTests(unittest.TestCase):
    def test_provider_yaml_loader_validates_and_checksums_contract(self) -> None:
        parsed = ProviderYamlLoader().load(VALID_PROVIDER_YAML)

        self.assertEqual(parsed.spec["provider_code"], "gms")
        self.assertEqual(len(parsed.checksum), 64)
        self.assertEqual(parsed.spec["message_types"][0]["code"], "viber_text")

    def test_provider_yaml_loader_rejects_missing_send_contract(self) -> None:
        with self.assertRaises(CommunicationValidationError):
            ProviderYamlLoader().load(
                VALID_PROVIDER_YAML.replace("response_mapping:", "response_map:")
            )

    def test_provider_yaml_loader_rejects_root_send_contract(self) -> None:
        yaml_content = VALID_PROVIDER_YAML.replace(
            """    send:
      transport: http
      method: POST
      url: "https://example.test/{{ config.client_id }}"
      headers:
        Content-Type: application/json
      body:
        phone_number: "{{ recipient.address }}"
        text: "{{ template.text }}"
        ttl: "{{ template.ttl }}"
      response_mapping:
        external_message_id: "$.message_id"
        external_status: "$.status"
""",
            """send:
  transport: http
  method: POST
  url: "https://example.test/{{ config.client_id }}"
  headers:
    Content-Type: application/json
  body:
    phone_number: "{{ recipient.address }}"
    text: "{{ template.text }}"
    ttl: "{{ template.ttl }}"
  response_mapping:
    external_message_id: "$.message_id"
    external_status: "$.status"
""",
        )

        with self.assertRaises(CommunicationValidationError):
            ProviderYamlLoader().load(yaml_content)

    def test_provider_yaml_loader_rejects_message_type_without_any_send(
        self,
    ) -> None:
        yaml_content = VALID_PROVIDER_YAML.replace(
            """    send:
      transport: http
      method: POST
      url: "https://example.test/{{ config.client_id }}"
      headers:
        Content-Type: application/json
      body:
        phone_number: "{{ recipient.address }}"
        text: "{{ template.text }}"
        ttl: "{{ template.ttl }}"
      response_mapping:
        external_message_id: "$.message_id"
        external_status: "$.status"
""",
            "",
        )

        with self.assertRaises(CommunicationValidationError):
            ProviderYamlLoader().load(yaml_content)

    def test_provider_yaml_loader_rejects_invalid_message_type_transport(
        self,
    ) -> None:
        yaml_content = VALID_PROVIDER_YAML.replace(
            "      transport: http",
            "      transport: smtp",
        )

        with self.assertRaises(CommunicationValidationError):
            ProviderYamlLoader().load(yaml_content)

    def test_provider_yaml_loader_accepts_yaml_smtp_contract(self) -> None:
        yaml_content = (
            PROJECT_ROOT / "docs/communication/providers/smtp_email.yaml"
        ).read_text(encoding="utf-8")

        parsed = ProviderYamlLoader().load(yaml_content)

        self.assertEqual(parsed.spec["connector_type"], "YAML_SMTP")
        self.assertNotIn("send", parsed.spec)
        self.assertEqual(parsed.spec["message_types"][0]["send"]["transport"], "smtp")
        self.assertEqual(parsed.spec["message_types"][0]["channel"], "EMAIL")

    def test_provider_yaml_loader_accepts_turbosms_sms_contract(self) -> None:
        yaml_content = (
            PROJECT_ROOT / "docs/communication/providers/turbosms_sms.yaml"
        ).read_text(encoding="utf-8")

        parsed = ProviderYamlLoader().load(yaml_content)

        self.assertEqual(parsed.spec["provider_code"], "turbosms")
        self.assertEqual(parsed.spec["connector_type"], "YAML_HTTP")
        self.assertEqual(parsed.spec["auth"]["type"], "bearer")
        self.assertEqual(parsed.spec["message_types"][0]["channel"], "SMS")
        self.assertEqual(
            parsed.spec["message_types"][0]["send"]["url"],
            "https://api.turbosms.ua/message/send.json",
        )

    def test_provider_yaml_loader_rejects_invalid_yaml_smtp_contract(self) -> None:
        yaml_content = (
            PROJECT_ROOT / "docs/communication/providers/smtp_email.yaml"
        ).read_text(encoding="utf-8")

        with self.assertRaises(CommunicationValidationError):
            ProviderYamlLoader().load(
                yaml_content.replace("      host:", "      smtp_host:")
            )

    def test_template_and_provider_payload_rendering_keep_native_types(self) -> None:
        rendered = TemplateRenderService().render(
            {"text": "Hello {{ name }}", "ttl": "{{ ttl }}"},
            {"name": "John", "ttl": 60},
        )

        self.assertEqual(rendered, {"text": "Hello John", "ttl": 60})

        method, url, headers, body = ProviderPayloadBuildService().build(
            send_spec={
                "method": "POST",
                "url": "https://example.test/{{ config.client_id }}",
                "headers": {"X-Provider": "{{ connection.connection_code }}"},
                "body": {
                    "phone_number": "{{ recipient.address }}",
                    "ttl": "{{ template.ttl }}",
                },
            },
            context={
                "config": {"client_id": "abc"},
                "connection": {"connection_code": "gms_viber"},
                "recipient": {"address": "380671112233"},
                "template": rendered,
            },
        )

        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://example.test/abc")
        self.assertEqual(headers["X-Provider"], "gms_viber")
        self.assertEqual(body["ttl"], 60)

    def test_status_mapping_and_jsonpath_extraction(self) -> None:
        payload = {"results": [{"message_id": "ext-1", "status": "23033"}]}

        external_status = JsonPathService().extract_one(payload, "$.results[0].status")
        internal_status = ProviderStatusMappingService().map_status(
            {"23033": "DELIVERED"},
            external_status,
        )

        self.assertEqual(external_status, "23033")
        self.assertEqual(internal_status, OutboundMessageStatus.DELIVERED.value)

    def test_secret_codec_stores_base64_and_connection_dto_hides_value(self) -> None:
        codec = SecretCodec()
        encoded = codec.encode({"username": "user", "password": "secret"})

        self.assertIsNotNone(encoded)
        self.assertNotIn("secret", encoded or "")
        self.assertEqual(codec.decode(encoded)["password"], "secret")

        model = ProviderConnectionModel(
            tenant_id="00000000-0000-0000-0000-000000000001",
            provider_connector_id="00000000-0000-0000-0000-000000000002",
            connection_code="gms_viber",
            connection_name="GMS Viber",
            channel_code="VIBER",
            config={"client_id": "abc"},
            secrets_b64=encoded,
            secret_ref=None,
            status="ACTIVE",
        )
        dto = connection_to_dto(model)

        self.assertTrue(dto.has_secrets)
        self.assertFalse(hasattr(dto, "secrets_b64"))


__all__ = ["CommunicationServicesTests", "VALID_PROVIDER_YAML"]
