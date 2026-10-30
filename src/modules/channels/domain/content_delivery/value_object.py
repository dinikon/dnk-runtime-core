from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from enum import StrEnum
import re

from src.modules.channels.domain.content_delivery.error import ContentDeliveryError


class DeliveryStatus(StrEnum):
    """Состояние текущей попытки, независимо от ожидающего поколения."""

    QUEUED = "queued"
    IN_FLIGHT = "in_flight"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DeliveryFieldIssueVO:
    """Безопасная причина неподтверждённого поля без копии внешнего контента."""

    field: str
    code: str

    def __post_init__(self) -> None:
        """Проверяет закрытый набор полей и формат кода причины."""
        if (
            self.field not in {"title", "body", "gallery"}
            or not isinstance(self.code, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", self.code) is None
        ):
            raise ContentDeliveryError("content_result_invalid")


@dataclass(frozen=True, slots=True)
class DeliveryContextVO:
    """Подтверждённое пользователем намерение без секретов и копии Catalog."""

    channel_id: EntityIdVO
    group_id: EntityIdVO
    connection_id: EntityIdVO
    actor_id: EntityIdVO
    representation_revision: int
    binding_revision: int
    config_revision: int
    content_fingerprint: str
    identity_namespace: str
    identity_key: str
    external_id: str
    parent_external_id: str | None
    publication_kind: str
    locale: str
    role: str

    def __post_init__(self) -> None:
        """Отклоняет неполный контекст до создания или изменения агрегата."""
        if (
            any(
                not isinstance(v, EntityIdVO)
                for v in (
                    self.channel_id,
                    self.group_id,
                    self.connection_id,
                    self.actor_id,
                )
            )
            or any(
                type(v) is not int or v < 1
                for v in (
                    self.representation_revision,
                    self.binding_revision,
                    self.config_revision,
                )
            )
            or not isinstance(self.content_fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.content_fingerprint) is None
            or any(
                not isinstance(v, str) or not v.strip()
                for v in (
                    self.identity_namespace,
                    self.identity_key,
                    self.external_id,
                    self.publication_kind,
                    self.locale,
                )
            )
            or (
                self.parent_external_id is not None
                and (
                    not isinstance(self.parent_external_id, str)
                    or not self.parent_external_id.strip()
                )
            )
            or self.role not in {"container", "position"}
        ):
            raise ContentDeliveryError("content_context_invalid")


@dataclass(frozen=True, slots=True)
class DeliveryMediaVO:
    """Ревизия зарезервированного media для атомарной фиксации результата."""

    media_id: EntityIdVO
    revision: int
    operation_id: EntityIdVO

    def __post_init__(self) -> None:
        """Не допускает фиксацию media без идентификатора и положительной версии."""
        if (
            not isinstance(self.media_id, EntityIdVO)
            or not isinstance(self.operation_id, EntityIdVO)
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise ContentDeliveryError("content_media_invalid")
