from uuid import UUID
from pydantic import Field, model_validator
from src.modules.crm.presentation.sales.http_values import (
    StrictRequest,
    BasketRequest,
    PointRequest,
)


class PatchLeadRequest(StrictRequest):
    """Отдельный транспортный контракт patch lead."""

    title: str | None = Field(default=None, max_length=255)
    basket: BasketRequest | None = None
    phones: tuple[PointRequest, ...] | None = None
    emails: tuple[PointRequest, ...] | None = None
    locale: str = Field(default="uk", max_length=64)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    middle_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    contact_id: UUID | None = None
    company_id: UUID | None = None

    @model_validator(mode="after")
    def ensure_patch(self) -> "PatchLeadRequest":
        """Различает отсутствие блока и запрещённый null; отклоняет пустой PATCH."""
        if not self.model_fields_set - {"locale"}:
            raise ValueError("Нет изменений.")
        for key in ("basket", "phones", "emails", "contact_ids", "company_ids"):
            if key in self.model_fields_set and getattr(self, key, None) is None:
                raise ValueError(f"{key} не может быть null.")
        return self
