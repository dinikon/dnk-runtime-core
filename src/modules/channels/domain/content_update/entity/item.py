from dataclasses import dataclass
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.value_object.texts import ContentTextsVO
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from src.modules.channels.domain.error import ChannelsConflictError


@dataclass(slots=True)
class ContentUpdateItem:
    """Принадлежит операции и хранит подтверждённую цель вместе с результатом."""

    publication_id: EntityIdVO
    catalog_item_id: EntityIdVO
    binding_id: EntityIdVO
    binding_revision: int
    resource_type: str
    external_id: str
    provider_context: dict[str, JsonValue]
    desired: ContentTextsVO
    observed: ContentTextsVO | None
    status: str
    issues: tuple[str, ...]
    attempts: int

    @classmethod
    def create(
        cls,
        publication_id: EntityIdVO,
        catalog_item_id: EntityIdVO,
        binding_id: EntityIdVO,
        binding_revision: int,
        resource_type: str,
        external_id: str,
        provider_context: dict[str, JsonValue],
        desired: ContentTextsVO,
    ) -> Self:
        """Создаёт позицию, ожидающую только чтения внешнего источника."""
        return cls.restore(
            publication_id,
            catalog_item_id,
            binding_id,
            binding_revision,
            resource_type,
            external_id,
            provider_context,
            desired,
            None,
            "preview_pending",
            (),
            0,
        )

    @classmethod
    def restore(
        cls,
        publication_id: EntityIdVO,
        catalog_item_id: EntityIdVO,
        binding_id: EntityIdVO,
        binding_revision: int,
        resource_type: str,
        external_id: str,
        provider_context: dict[str, JsonValue],
        desired: ContentTextsVO,
        observed: ContentTextsVO | None,
        status: str,
        issues: tuple[str, ...],
        attempts: int,
    ) -> Self:
        """Восстанавливает внутреннюю позицию с проверкой допустимых состояний."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (publication_id, catalog_item_id, binding_id)
            )
            or binding_revision < 1
            or attempts < 0
            or not external_id
            or not resource_type
            or status
            not in {
                "preview_pending",
                "ready",
                "blocked",
                "unchanged",
                "pending",
                "sending",
                "verifying",
                "succeeded",
                "failed",
                "unknown",
                "stale",
                "reconciling",
            }
        ):
            raise ChannelsConflictError("invalid_content_update_item")
        if (
            not isinstance(desired, ContentTextsVO)
            or (observed is not None and not isinstance(observed, ContentTextsVO))
            or (
                status
                in {
                    "ready",
                    "unchanged",
                    "pending",
                    "sending",
                    "verifying",
                    "succeeded",
                    "unknown",
                    "reconciling",
                }
                and (observed is None or desired.missing_content())
            )
            or (status == "preview_pending" and observed is not None)
        ):
            raise ChannelsConflictError("invalid_content_update_item")
        return cls(
            publication_id,
            catalog_item_id,
            binding_id,
            binding_revision,
            resource_type,
            external_id,
            dict(provider_context),
            desired,
            observed,
            status,
            issues,
            attempts,
        )

    def preview(self, observed: ContentTextsVO | None, issues: tuple[str, ...]) -> None:
        """Сохраняет сравнение и не включает неполные тексты в отправку."""
        if self.status != "preview_pending":
            raise ChannelsConflictError("content_update_step_changed")
        self.observed = observed
        self.issues = tuple(
            dict.fromkeys(
                (
                    *issues,
                    *(
                        ("catalog_content_missing",)
                        if self.desired.missing_content()
                        else ()
                    ),
                )
            )
        )
        self.status = (
            "blocked"
            if self.issues or observed is None
            else (
                "unchanged" if observed.digest() == self.desired.digest() else "ready"
            )
        )

    def queue(self) -> None:
        """Разрешает отправку только подготовленной позиции."""
        if self.status != "ready":
            raise ChannelsConflictError("content_update_not_ready")
        self.status = "pending"

    def dispatch(self) -> str:
        """Перед HTTP сохраняет намерение; повтор шага выполняет сверку."""
        if self.status == "preview_pending":
            return "preview"
        if self.status in ("sending", "verifying", "unknown", "reconciling"):
            self.status = "verifying"
            return "verify"
        if self.status != "pending":
            raise ChannelsConflictError("content_update_step_changed")
        self.status = "sending"
        self.attempts += 1
        return "send"

    def sent(self) -> None:
        """Ответ API означает переход к проверке, а не подтверждённый успех."""
        if self.status != "sending":
            raise ChannelsConflictError("content_update_step_changed")
        self.status = "verifying"

    def verified(self, observed: ContentTextsVO) -> None:
        """Подтверждает результат по реально прочитанным текстам всех локалей."""
        if self.status != "verifying":
            raise ChannelsConflictError("content_update_step_changed")
        if observed.digest() == self.desired.digest():
            self.status, self.issues = "succeeded", ()
        else:
            self.status, self.issues = "failed", (
                "content_update_verification_mismatch",
            )

    def fail(self, code: str, *, uncertain: bool = False, stale: bool = False) -> None:
        """Сохраняет безопасную причину и отдельно отмечает неопределённую отправку."""
        self.status = "unknown" if uncertain else "stale" if stale else "failed"
        self.issues = (code,)

    def retry(self) -> None:
        """Не повторяет неизвестную запись: сначала требуется контрольное чтение."""
        if self.status not in ("failed", "unknown"):
            raise ChannelsConflictError("content_update_retry_unavailable")
        self.status, self.issues = "reconciling", ()
