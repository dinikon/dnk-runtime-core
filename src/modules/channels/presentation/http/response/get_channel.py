from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.presentation.http.response.channel_fields import (
    ConfigResponse,
    IdentityResponse,
    VerificationResponse,
)
from src.modules.channels.application.query.get_channel.dto import GetChannelDTO


class GetChannelResponse(BaseModel):
    """Независимый HTTP-контракт карточки канала."""

    id: UUID
    name: str
    platform_kind: str
    revision: int
    config: ConfigResponse
    config_revision: int
    identity: IdentityResponse | None
    verification: VerificationResponse
    created_at: datetime
    updated_at: datetime
    recovery_required: bool
    available_capabilities: tuple[str, ...]

    @classmethod
    def from_dto(cls, value: GetChannelDTO) -> "GetChannelResponse":
        """Явно выбирает поля результата сценария для HTTP-ответа."""
        return cls(
            id=value.id,
            name=value.name,
            platform_kind=value.platform_kind,
            revision=value.revision,
            config=ConfigResponse.from_projection(value.config),
            config_revision=value.config_revision,
            identity=(
                IdentityResponse.from_projection(value.identity)
                if value.identity is not None
                else None
            ),
            verification=VerificationResponse.from_projection(value.verification),
            created_at=value.created_at,
            updated_at=value.updated_at,
            recovery_required=value.recovery_required,
            available_capabilities=value.available_capabilities,
        )
