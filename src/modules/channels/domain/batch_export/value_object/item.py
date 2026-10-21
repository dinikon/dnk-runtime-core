from dataclasses import dataclass, replace
from uuid import UUID
from src.modules.channels.domain.content_update.value_object.texts import ContentTextsVO
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from src.modules.channels.domain.error import ChannelsValidationError


@dataclass(frozen=True, slots=True)
class ExportItemVO:
    """Фиксирует одну цель; изменение связи не меняет уже собранный пакет."""

    publication_id: UUID
    catalog_item_id: UUID
    binding_id: UUID
    binding_revision: int
    representation_id: UUID
    external_id: str
    provider_context: dict[str, JsonValue]
    desired: ContentTextsVO | None = None
    baseline: dict[str, JsonValue] | None = None
    status: str = "pending"
    issues: tuple[str, ...] = ()
    identity_key: str | None = None
    identity_count: int = 0
    identity_native_ok: bool = True

    def __post_init__(self) -> None:
        """Не допускает некорректную цель или неопределённое состояние позиции."""
        if (
            not self.external_id
            or self.binding_revision < 1
            or self.status
            not in ("pending", "ready", "skipped", "verified", "failed", "unknown")
        ):
            raise ChannelsValidationError("invalid_export_item")

    def prepared(
        self,
        texts: ContentTextsVO | None,
        baseline: dict[str, JsonValue] | None,
        issues: tuple[str, ...],
        identity_key: str | None = None,
    ) -> "ExportItemVO":
        """Исключает неполные тексты и неподдержанную внешнюю карточку до создания файла."""
        if texts is None or texts.missing_content():
            issues = tuple(dict.fromkeys((*issues, "catalog_content_missing")))
        return replace(
            self,
            desired=texts,
            baseline=baseline,
            status="skipped" if issues else "ready",
            issues=issues,
            identity_key=identity_key,
        )

    def verified(
        self, issues: tuple[str, ...], *, uncertain: bool = False
    ) -> "ExportItemVO":
        """Фиксирует независимый результат чтения после принятого импорта."""
        return replace(
            self,
            status="unknown" if uncertain else "failed" if issues else "verified",
            issues=issues,
        )

    def scanned(self, count: int, native_ok: bool) -> "ExportItemVO":
        """Накапливает глобальные совпадения ключа, не заменяя исходный native ID."""
        return replace(
            self,
            identity_count=min(2, self.identity_count + count),
            identity_native_ok=self.identity_native_ok and native_ok,
        )

    def exclude(self, issue: str) -> "ExportItemVO":
        """Исключает цель из будущего файла, сохраняя зафиксированные связи и тексты."""
        if self.status not in ("pending", "ready") or not issue:
            raise ChannelsValidationError("invalid_export_exclusion")
        return replace(self, status="skipped", issues=(issue,))
