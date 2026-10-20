from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.content_update.value_object.texts import ContentTextsVO


@dataclass(frozen=True, slots=True)
class ApplyContentUpdateStepCommand:
    """Передаёт нормализованный факт одного внешнего шага."""

    tenant_id: UUID
    run_id: UUID
    sequence: int
    publication_id: UUID
    mode: str
    observed: ContentTextsVO | None = None
    issues: tuple[str, ...] = ()
    error_code: str | None = None
    uncertain: bool = False
