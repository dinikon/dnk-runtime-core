from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FeedExportIssueDTO:
    """Описывает предупреждение или ошибку конкретного экспортируемого товара."""

    publication_id: UUID
    severity: Literal["ERROR", "WARNING"]
    code: str
    message: str
    sku: str | None
    field_id: UUID | None
    rule_id: UUID | None
    path: tuple[str | int, ...]
