from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

import yaml
from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment
from jsonpath_ng import parse as parse_jsonpath
from jsonschema import Draft202012Validator, ValidationError
from jsonschema.exceptions import SchemaError

from src.modules.communication.domain import (
    CommunicationValidationError,
    OutboundMessageStatus,
)

_JSON_SCHEMA_META_SCHEMA = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True, slots=True)
class ParsedConnector:
    """Validated provider connector YAML spec."""

    spec: dict[str, Any]
    checksum: str


class ProviderYamlLoader:
    """Loads and validates provider connector YAML files."""

    _REQUIRED_ROOT_FIELDS = (
        "provider_code",
        "provider_name",
        "version",
        "connector_type",
        "channels",
        "message_types",
    )

    def load(self, yaml_content: str) -> ParsedConnector:
        """Parse provider YAML, validate its contract, and return canonical data."""
        try:
            raw_spec = yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            raise CommunicationValidationError(f"Invalid YAML: {exc}") from exc

        if not isinstance(raw_spec, dict):
            raise CommunicationValidationError("Provider YAML root must be an object.")

        spec = dict(raw_spec)
        self._validate_root(spec)
        canonical_json = json.dumps(
            spec,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        checksum = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return ParsedConnector(spec=spec, checksum=checksum)

    def _validate_root(self, spec: Mapping[str, Any]) -> None:
        missing = [field for field in self._REQUIRED_ROOT_FIELDS if field not in spec]
        if missing:
            raise CommunicationValidationError(
                "Provider YAML is missing required fields: " + ", ".join(missing)
            )

        channels = spec.get("channels")
        if not isinstance(channels, list) or not all(
            isinstance(item, str) for item in channels
        ):
            raise CommunicationValidationError("channels must be a list of strings.")

        for schema_key in ("config_schema", "secrets_schema"):
            schema = spec.get(schema_key)
            if schema is not None:
                self._validate_json_schema(schema, schema_key)

        message_types = spec.get("message_types")
        if not isinstance(message_types, list) or not message_types:
            raise CommunicationValidationError(
                "message_types must be a non-empty list."
            )

        connector_type = str(spec["connector_type"])
        if "send" in spec:
            raise CommunicationValidationError(
                "Root-level send is not supported. Define send inside each message type."
            )

        for index, message_type in enumerate(message_types):
            self._validate_message_type(
                message_type,
                index,
                connector_type=connector_type,
            )

    def _validate_send_spec(
        self,
        connector_type: str,
        send: Mapping[str, Any],
        label: str,
    ) -> None:
        if "transport" not in send:
            raise CommunicationValidationError(
                f"{label}.transport is required in provider YAML."
            )

        if connector_type == "YAML_HTTP":
            if send.get("transport") != "http":
                raise CommunicationValidationError(
                    f"YAML_HTTP provider YAML must use {label}.transport=http."
                )
            for field in ("method", "url", "body", "response_mapping"):
                if field not in send:
                    raise CommunicationValidationError(
                        f"{label}.{field} is required in YAML_HTTP provider YAML."
                    )
            return

        if connector_type == "YAML_SMTP":
            if send.get("transport") != "smtp":
                raise CommunicationValidationError(
                    f"YAML_SMTP provider YAML must use {label}.transport=smtp."
                )
            for field in (
                "host",
                "port",
                "username",
                "password",
                "use_tls",
                "use_starttls",
                "timeout_seconds",
                "from_address",
                "from_name",
                "to_address",
                "subject",
            ):
                if field not in send:
                    raise CommunicationValidationError(
                        f"{label}.{field} is required in YAML_SMTP provider YAML."
                    )
            return

        if connector_type == "CUSTOM_ADAPTER":
            raise CommunicationValidationError(
                "CUSTOM_ADAPTER connector_type is not supported by YAML loader."
            )
        raise CommunicationValidationError(
            f"Unsupported connector_type '{connector_type}'."
        )

    def _validate_message_type(
        self,
        message_type: Any,
        index: int,
        *,
        connector_type: str,
    ) -> None:
        if not isinstance(message_type, dict):
            raise CommunicationValidationError(
                f"message_types[{index}] must be an object."
            )
        for field in ("code", "channel", "name", "field_schema"):
            if field not in message_type:
                raise CommunicationValidationError(
                    f"message_types[{index}].{field} is required."
                )
        self._validate_json_schema(
            message_type["field_schema"],
            f"message_types[{index}].field_schema",
        )
        ui_schema = message_type.get("ui_schema")
        if ui_schema is not None and not isinstance(ui_schema, dict):
            raise CommunicationValidationError(
                f"message_types[{index}].ui_schema must be an object."
            )
        send = message_type.get("send")
        if send is None:
            raise CommunicationValidationError(
                f"message_types[{index}].send is required."
            )
        if not isinstance(send, dict):
            raise CommunicationValidationError(
                f"message_types[{index}].send must be an object."
            )
        self._validate_send_spec(
            connector_type,
            send,
            f"message_types[{index}].send",
        )

    @staticmethod
    def _validate_json_schema(schema: Any, label: str) -> None:
        if not isinstance(schema, dict):
            raise CommunicationValidationError(f"{label} must be an object.")
        schema.setdefault("$schema", _JSON_SCHEMA_META_SCHEMA)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise CommunicationValidationError(
                f"{label} is not a valid JSON Schema: {exc.message}"
            ) from exc


class JsonSchemaValidationService:
    """Validates JSON payloads against JSON Schema."""

    def check_schema(self, schema: Mapping[str, Any] | None, label: str) -> None:
        """Validate a JSON Schema document without validating an instance."""
        if not schema:
            return
        try:
            Draft202012Validator.check_schema(dict(schema))
        except SchemaError as exc:
            raise CommunicationValidationError(
                f"{label} is not a valid JSON Schema: {exc.message}"
            ) from exc

    def validate(
        self, payload: Any, schema: Mapping[str, Any] | None, label: str
    ) -> None:
        """Validate payload or raise CommunicationValidationError."""
        if not schema:
            return
        try:
            Draft202012Validator(dict(schema)).validate(payload)
        except ValidationError as exc:
            path = ".".join(str(item) for item in exc.path)
            suffix = f" at {path}" if path else ""
            raise CommunicationValidationError(
                f"{label} does not match schema{suffix}: {exc.message}"
            ) from exc


class TemplateRenderService:
    """Renders template payload objects with Jinja2 StrictUndefined."""

    def __init__(self) -> None:
        self._environment = NativeEnvironment(undefined=StrictUndefined)

    def render(self, payload: Any, variables: Mapping[str, Any]) -> Any:
        """Render all string leaves in a JSON-like payload."""
        return self._render_value(payload, dict(variables))

    def _render_value(self, value: Any, variables: Mapping[str, Any]) -> Any:
        if isinstance(value, str):
            try:
                return self._environment.from_string(value).render(**variables)
            except Exception as exc:
                raise CommunicationValidationError(
                    f"Template rendering failed: {exc}"
                ) from exc
        if isinstance(value, list):
            return [self._render_value(item, variables) for item in value]
        if isinstance(value, dict):
            return {
                key: self._render_value(item, variables) for key, item in value.items()
            }
        return value


class ProviderPayloadBuildService:
    """Builds provider HTTP request payloads from connector YAML templates."""

    def __init__(self) -> None:
        self._environment = NativeEnvironment(undefined=StrictUndefined)

    def render_value(self, value: Any, context: Mapping[str, Any]) -> Any:
        """Render all string leaves in a JSON-like provider value."""
        if isinstance(value, str):
            try:
                return self._environment.from_string(value).render(**context)
            except Exception as exc:
                raise CommunicationValidationError(
                    f"Provider payload rendering failed: {exc}"
                ) from exc
        if isinstance(value, list):
            return [self.render_value(item, context) for item in value]
        if isinstance(value, dict):
            return {
                key: self.render_value(item, context) for key, item in value.items()
            }
        return value

    def build(
        self,
        *,
        send_spec: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[str, str, dict[str, str], Any]:
        """Return rendered HTTP method, URL, headers and JSON body."""
        method = str(send_spec["method"]).upper()
        url = self.render_value(send_spec["url"], context)
        headers = self.render_value(send_spec.get("headers", {}), context)
        body = self.render_value(send_spec.get("body", {}), context)
        if not isinstance(headers, dict):
            raise CommunicationValidationError("send.headers must render to an object.")
        return method, str(url), {str(k): str(v) for k, v in headers.items()}, body


class ProviderStatusMappingService:
    """Maps provider statuses to DNK internal message statuses."""

    def map_status(
        self,
        status_mapping: Mapping[str, Any] | None,
        external_status: Any,
    ) -> str:
        """Map external status with UNKNOWN fallback."""
        if external_status is None:
            return OutboundMessageStatus.UNKNOWN.value
        raw = str(external_status)
        mapped = (status_mapping or {}).get(raw)
        if mapped is None:
            return OutboundMessageStatus.UNKNOWN.value
        try:
            return OutboundMessageStatus(str(mapped)).value
        except ValueError:
            return OutboundMessageStatus.UNKNOWN.value


class JsonPathService:
    """Small JSONPath extraction wrapper."""

    def extract_one(self, payload: Any, expression: str | None) -> Any:
        """Extract the first match or None when the expression is empty/unmatched."""
        if not expression:
            return None
        try:
            matches = parse_jsonpath(expression).find(payload)
        except Exception as exc:
            raise CommunicationValidationError(
                f"Invalid JSONPath expression '{expression}': {exc}"
            ) from exc
        if not matches:
            return None
        return matches[0].value


class SecretCodec:
    """Encodes provider connection secrets as base64 JSON."""

    def encode(self, secrets: Mapping[str, Any] | None) -> str | None:
        """Encode secrets for DB storage."""
        if not secrets:
            return None
        raw = json.dumps(
            dict(secrets),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return base64.b64encode(raw).decode("ascii")

    def decode(self, secrets_b64: str | None) -> dict[str, Any]:
        """Decode secrets from DB storage."""
        if not secrets_b64:
            return {}
        try:
            raw = base64.b64decode(secrets_b64.encode("ascii"))
            decoded = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise CommunicationValidationError(
                "Provider connection secrets are not valid base64 JSON."
            ) from exc
        if not isinstance(decoded, dict):
            raise CommunicationValidationError(
                "Provider connection secrets must decode to an object."
            )
        return decoded


__all__ = [
    "JsonPathService",
    "JsonSchemaValidationService",
    "ParsedConnector",
    "ProviderPayloadBuildService",
    "ProviderStatusMappingService",
    "ProviderYamlLoader",
    "SecretCodec",
    "TemplateRenderService",
]
