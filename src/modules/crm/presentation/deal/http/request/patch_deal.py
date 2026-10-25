from uuid import UUID
from pydantic import Field, model_validator
from src.modules.crm.presentation.sales.http_values import (
    StrictRequest,
    BasketRequest,
    PointRequest,
)


class PatchDealRequest(StrictRequest):
    """Отдельный транспортный контракт patch deal."""

    title: str | None = Field(default=None, max_length=255)
    basket: BasketRequest | None = None
    phones: tuple[PointRequest, ...] | None = None
    emails: tuple[PointRequest, ...] | None = None
    locale: str = Field(default="uk", max_length=64)
    contact_ids: tuple[UUID, ...] | None = None
    company_ids: tuple[UUID, ...] | None = None

    @model_validator(mode="after")
    def ensure_patch(self) -> "PatchDealRequest":
        """Различает отсутствие блока и запрещённый null; отклоняет пустой PATCH."""
        if not self.model_fields_set - {"locale"}:
            raise ValueError("Нет изменений.")
        for key in ("basket", "phones", "emails", "contact_ids", "company_ids"):
            if key in self.model_fields_set and getattr(self, key, None) is None:
                raise ValueError(f"{key} не может быть null.")
        return self
