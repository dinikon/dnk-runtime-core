from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)
from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryMediaVO,
    DeliveryStatus,
    DeliveryFieldIssueVO,
)
from src.modules.channels.infrastructure.content_delivery.document import (
    context_from_document,
    context_to_document,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentDeliveryMapper:
    """Преобразует хранение и конкретные модели без I/O и бизнес-переходов."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContentDelivery:
        """Передаёт сохранённое состояние в явную фабрику восстановления."""
        prepared = row["prepared_context"]
        result = row["result"]
        if result["schema"] != "content_result.v1":
            raise ValueError("Unsupported content result schema")
        return ContentDelivery.restore(
            representation_id=EntityIdVO(row["representation_id"]),
            publication_id=EntityIdVO(row["publication_id"]),
            revision=row["revision"],
            requested_generation=row["requested_generation"],
            sending_generation=row["sending_generation"],
            applied_generation=row["applied_generation"],
            status=DeliveryStatus(row["status"]),
            current_job_id=EntityIdVO(row["current_job_id"]),
            requested_context=context_from_document(row["requested_context"]),
            prepared_context=(
                context_from_document(prepared["context"]) if prepared else None
            ),
            prepared_media=(
                tuple(
                    DeliveryMediaVO(
                        EntityIdVO(UUID(v["id"])),
                        v["revision"],
                        EntityIdVO(UUID(v["operation_id"])),
                    )
                    for v in prepared["media"]
                )
                if prepared
                else ()
            ),
            prepared_schema=row["prepared_schema"],
            prepared_request_encrypted=row["prepared_request_encrypted"],
            prepared_hash=row["prepared_hash"],
            last_applied_hash=row["last_applied_hash"],
            confirmed_fields=tuple(result["confirmed_fields"]),
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=(
                datetime.fromisoformat(result["completed_at"])
                if result["completed_at"]
                else None
            ),
            field_issues=tuple(
                DeliveryFieldIssueVO(v["field"], v["code"])
                for v in result.get("field_issues", ())
            ),
            initial_error_code=result.get("initial_error_code", row["error_code"]),
            last_success_at=(
                datetime.fromisoformat(result["last_success_at"])
                if result.get("last_success_at")
                else None
            ),
            applied_content_fingerprint=result.get("applied_content_fingerprint"),
        )

    @staticmethod
    def to_values(value: ContentDelivery) -> dict[str, Any]:
        """Сериализует явные поля; ciphertext никогда не расшифровывается mapper."""
        return {
            "representation_id": value.representation_id.uuid,
            "publication_id": value.publication_id.uuid,
            "revision": value.revision,
            "requested_generation": value.requested_generation,
            "sending_generation": value.sending_generation,
            "applied_generation": value.applied_generation,
            "status": value.status.value,
            "current_job_id": value.current_job_id.uuid,
            "requested_context": context_to_document(value.requested_context),
            "prepared_context": (
                {
                    "context": context_to_document(value.prepared_context),
                    "media": [
                        {
                            "id": str(v.media_id.uuid),
                            "revision": v.revision,
                            "operation_id": str(v.operation_id.uuid),
                        }
                        for v in value.prepared_media
                    ],
                }
                if value.prepared_context
                else None
            ),
            "prepared_schema": value.prepared_schema,
            "prepared_request_encrypted": value.prepared_request_encrypted,
            "prepared_hash": value.prepared_hash,
            "last_applied_hash": value.last_applied_hash,
            "result": {
                "schema": "content_result.v1",
                "confirmed_fields": list(value.confirmed_fields),
                "field_issues": [
                    {"field": v.field, "code": v.code} for v in value.field_issues
                ],
                "initial_error_code": value.initial_error_code,
                "last_success_at": (
                    value.last_success_at.isoformat() if value.last_success_at else None
                ),
                "applied_content_fingerprint": value.applied_content_fingerprint,
                "completed_at": (
                    value.completed_at.isoformat() if value.completed_at else None
                ),
            },
            "error_code": value.error_code,
            "created_at": value.created_at,
            "updated_at": value.updated_at,
        }

    @staticmethod
    def to_projection(row: Mapping[str, Any]) -> ContentDeliveryRow:
        """Выбирает только публичные поля без восстановления агрегата."""
        context, result = row["requested_context"], row["result"]
        prepared = row["prepared_context"]
        return ContentDeliveryRow(
            publication_id=row["publication_id"],
            external_id=context["external_id"],
            role=context["role"],
            publication_kind=context["publication_kind"],
            revision=row["revision"],
            requested_generation=row["requested_generation"],
            sending_generation=row["sending_generation"],
            applied_generation=row["applied_generation"],
            status=row["status"],
            confirmed_fields=tuple(result["confirmed_fields"]),
            error_code=row["error_code"],
            updated_at=row["updated_at"],
            completed_at=(
                datetime.fromisoformat(result["completed_at"])
                if result["completed_at"]
                else None
            ),
            content_fingerprint=(
                prepared["context"]["content_fingerprint"]
                if prepared
                else context["content_fingerprint"]
            ),
            current_job_id=row["current_job_id"],
            field_issues=tuple(
                DeliveryFieldIssueVO(v["field"], v["code"])
                for v in result.get("field_issues", ())
            ),
            initial_error_code=result.get("initial_error_code", row["error_code"]),
            last_success_at=(
                datetime.fromisoformat(result["last_success_at"])
                if result.get("last_success_at")
                else None
            ),
            applied_content_fingerprint=result.get("applied_content_fingerprint"),
        )
