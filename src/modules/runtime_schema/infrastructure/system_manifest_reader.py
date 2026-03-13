from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from src.modules.runtime_schema.infrastructure.contracts import (
    SystemModelRegistryReaderProtocol,
)
from src.modules.runtime_schema.infrastructure.ddl_models import (
    LoadedSystemManifest,
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.shared.domain.errors import ValidationError

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required for runtime_schema system manifest reader") from exc


class YamlSystemModelRegistryReader(SystemModelRegistryReaderProtocol):
    def __init__(self, manifest_path: Path):
        self._manifest_path = manifest_path

    async def load_system_manifest(self) -> LoadedSystemManifest:
        if not self._manifest_path.exists():
            raise ValidationError(
                f"system manifest file was not found: {self._manifest_path}"
            )

        raw_text = self._manifest_path.read_text(encoding="utf-8")
        payload = yaml.safe_load(raw_text) or {}

        if not isinstance(payload, dict):
            raise ValidationError("system manifest root must be mapping")

        version = str(payload.get("version", "")).strip()
        if not version:
            raise ValidationError("system manifest version is required")

        module_raw = payload.get("module")
        module = str(module_raw).strip() if module_raw is not None else None
        if module == "":
            module = None

        objects_payload = payload.get("objects", [])
        if not isinstance(objects_payload, list):
            raise ValidationError("system manifest objects must be a list")

        objects = tuple(self._parse_object(item) for item in objects_payload)
        seen_object_keys: set[str] = set()
        duplicate_object_keys: set[str] = set()
        for object_definition in objects:
            if object_definition.key in seen_object_keys:
                duplicate_object_keys.add(object_definition.key)
            else:
                seen_object_keys.add(object_definition.key)
        if duplicate_object_keys:
            ordered_keys = ", ".join(sorted(duplicate_object_keys))
            raise ValidationError(
                f"system manifest contains duplicate object keys: {ordered_keys}"
            )
        manifest_hash = sha256(raw_text.encode("utf-8")).hexdigest()
        return LoadedSystemManifest(
            version=version,
            manifest_hash=manifest_hash,
            module=module,
            objects=objects,
        )

    @staticmethod
    def _parse_object(payload: object) -> SystemObjectDefinition:
        if not isinstance(payload, dict):
            raise ValidationError("object entry must be mapping")

        key = str(payload.get("key", "")).strip()
        if not key:
            raise ValidationError("object key is required")

        name = payload.get("name")
        label = payload.get("label")
        if not isinstance(name, dict):
            raise ValidationError(f"object '{key}' must contain name mapping")
        if not isinstance(label, dict):
            raise ValidationError(f"object '{key}' must contain label mapping")

        name_singular = str(name.get("singular", "")).strip()
        name_plural = str(name.get("plural", "")).strip()
        label_singular = str(label.get("singular", "")).strip()
        label_plural = str(label.get("plural", "")).strip()
        if not name_singular or not name_plural:
            raise ValidationError(f"object '{key}' name singular/plural are required")
        if not label_singular or not label_plural:
            raise ValidationError(f"object '{key}' label singular/plural are required")

        fields_payload = payload.get("fields", [])
        if not isinstance(fields_payload, list):
            raise ValidationError(f"object '{key}' fields must be a list")
        fields = tuple(YamlSystemModelRegistryReader._parse_field(item) for item in fields_payload)
        seen_field_names: set[str] = set()
        duplicate_field_names: set[str] = set()
        for field in fields:
            normalized_field_name = field.name.strip().lower()
            if normalized_field_name in seen_field_names:
                duplicate_field_names.add(normalized_field_name)
            else:
                seen_field_names.add(normalized_field_name)
        if duplicate_field_names:
            ordered_field_names = ", ".join(sorted(duplicate_field_names))
            raise ValidationError(
                f"object '{key}' contains duplicate field names: {ordered_field_names}"
            )

        description_raw = payload.get("description")
        icon_raw = payload.get("icon")
        shortcut_raw = payload.get("shortcut")

        return SystemObjectDefinition(
            key=key,
            name_singular=name_singular,
            name_plural=name_plural,
            label_singular=label_singular,
            label_plural=label_plural,
            description=(
                str(description_raw).strip() if description_raw is not None else None
            ),
            icon=str(icon_raw).strip() if icon_raw is not None else None,
            shortcut=str(shortcut_raw).strip() if shortcut_raw is not None else None,
            duplicate_criteria=(
                dict(payload.get("duplicate_criteria"))
                if isinstance(payload.get("duplicate_criteria"), dict)
                else None
            ),
            fields=fields,
        )

    @staticmethod
    def _parse_field(payload: object) -> SystemFieldDefinition:
        if not isinstance(payload, dict):
            raise ValidationError("field entry must be mapping")

        name = str(payload.get("name", "")).strip()
        field_type = str(payload.get("type", "")).strip()
        label = str(payload.get("label", "")).strip()
        if not name:
            raise ValidationError("field name is required")
        if not field_type:
            raise ValidationError(f"field '{name}' type is required")
        if not label:
            raise ValidationError(f"field '{name}' label is required")

        description_raw = payload.get("description")
        icon_raw = payload.get("icon")
        options = payload.get("options")
        settings = payload.get("settings")
        default_value = payload.get("default_value")
        if default_value is None and "default_values" in payload:
            default_value = payload.get("default_values")

        return SystemFieldDefinition(
            name=name,
            field_type=field_type,
            label=label,
            description=(
                str(description_raw).strip() if description_raw is not None else None
            ),
            icon=str(icon_raw).strip() if icon_raw is not None else None,
            is_unique=bool(payload.get("is_unique", False)),
            is_index=bool(payload.get("is_index", False)),
            is_nullable=bool(payload.get("is_nullable", True)),
            is_ui_read_only=bool(payload.get("is_ui_read_only", False)),
            is_searchable=bool(payload.get("is_searchable", False)),
            options=dict(options) if isinstance(options, dict) else None,
            settings=dict(settings) if isinstance(settings, dict) else None,
            default_value=YamlSystemModelRegistryReader._normalize_default_value(
                default_value
            ),
            relation_target_object=(
                str(payload.get("relation_target_object")).strip()
                if payload.get("relation_target_object") is not None
                else None
            ),
            relation_target_field=(
                str(payload.get("relation_target_field")).strip()
                if payload.get("relation_target_field") is not None
                else None
            ),
        )

    @staticmethod
    def _normalize_default_value(value: object) -> dict[str, object] | None:
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized == "":
                return None
            return {"value": normalized}
        return None


__all__ = ["YamlSystemModelRegistryReader"]
