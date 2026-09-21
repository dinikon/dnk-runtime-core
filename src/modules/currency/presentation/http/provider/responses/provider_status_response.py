from datetime import date, datetime
from pydantic import BaseModel
from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)


class RateImportResponse(BaseModel):
    """Validated HTTP output for rate import response."""

    id: str
    provider_code: str
    started_at: datetime
    finished_at: datetime | None
    requested_date_from: date
    requested_date_to: date
    status: str
    received_count: int
    created_count: int
    updated_count: int
    error_count: int
    error_message: str | None


class ProviderStatusResponse(BaseModel):
    """Validated HTTP output for provider status response."""

    last_import: RateImportResponse | None
    last_available_rate_date: date | None

    @classmethod
    def from_dto(cls, status: ProviderStatusDTO):
        i = status.last_import
        return cls(
            last_available_rate_date=status.last_available_rate_date,
            last_import=(
                RateImportResponse(
                    id=str(i.id),
                    provider_code=str(i.provider_code),
                    started_at=i.started_at,
                    finished_at=i.finished_at,
                    requested_date_from=i.requested_date_from,
                    requested_date_to=i.requested_date_to,
                    status=i.status,
                    received_count=i.received_count,
                    created_count=i.created_count,
                    updated_count=i.updated_count,
                    error_count=i.error_count,
                    error_message=i.error_message,
                )
                if i
                else None
            ),
        )


__all__ = ["RateImportResponse", "ProviderStatusResponse"]
