"""The exact unwrapped Runtime v1 wire contract."""

import re
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StrictBool,
    field_validator,
    model_validator,
)


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OwnerProfile(ProtocolModel):
    first_name: str = Field(default="", max_length=255)
    last_name: str = Field(default="", max_length=255)
    display_name: str = Field(default="", max_length=255)


class Owner(ProtocolModel):
    sub: UUID
    verified_email: EmailStr
    profile: OwnerProfile = Field(default_factory=OwnerProfile)


class OIDC(ProtocolModel):
    issuer: str = Field(max_length=2048)
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: SecretStr
    redirect_uri: str = Field(max_length=2048)

    @field_validator("client_secret")
    @classmethod
    def nonempty_secret(cls, value):
        if not value.get_secret_value():
            raise ValueError("Empty client credential")
        return value


def exact_hostname(value: str) -> str:
    if (
        len(value) > 253
        or value != value.lower()
        or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
            value,
        )
    ):
        raise ValueError("Invalid exact DNS hostname")
    return value


class ProvisioningCommand(ProtocolModel):
    tenant_id: UUID
    operation_id: UUID
    attempt_id: UUID
    hostname: str
    name: str = Field(min_length=1, max_length=255)
    owner: Owner
    oidc: OIDC

    _hostname = field_validator("hostname")(exact_hostname)

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tenant name is empty")
        return value.strip()

    def validate_placement(self, settings) -> None:
        if not any(
            self.hostname.endswith("." + zone) for zone in settings.allowed_base_domains
        ):
            raise ValueError("Hostname is outside configured zones")
        if self.hostname.split(".", 1)[0].startswith("dnk-probe-"):
            raise ValueError("Reserved diagnostic hostname")
        origin = settings.public_origin
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ValueError("Invalid trusted Core origin")
        if self.oidc.issuer != f"{origin}/oidc/tenants/{self.tenant_id}":
            raise ValueError("Issuer does not match trusted Core tenant")
        if (
            self.oidc.redirect_uri
            != f"https://{self.hostname}/api/auth/cloud/callback/"
        ):
            raise ValueError("Callback does not match hostname")


class AttemptResponse(ProtocolModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_serialization_defaults_required=True
    )
    tenant_id: UUID
    operation_id: UUID
    attempt_id: UUID
    state: Literal["queued", "running", "succeeded", "failed"]
    resources_state: Literal["absent", "present", "unknown"]
    runtime_tenant_id: str | None = Field(max_length=128)
    error_code: str | None = None


class DomainReadiness(ProtocolModel):
    base_domain: str
    routing_ready: bool
    tls_ready: bool


class StatusResponse(ProtocolModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_serialization_defaults_required=True
    )
    ready: bool
    protocol_version: Literal[1] = 1
    deletion_protocol_version: Literal[1] = 1
    domains: list[DomainReadiness]


class DeletionCommand(ProtocolModel):
    tenant_id: UUID
    operation_id: UUID
    hostname: str
    runtime_tenant_id: UUID | None = None
    initiator_id: UUID
    source: Literal["user", "operator"]

    _hostname = field_validator("hostname")(exact_hostname)


class DeletionResponse(ProtocolModel):
    tenant_id: UUID
    runtime_tenant_id: UUID | None
    operation_id: UUID
    state: Literal["deletion_pending", "blocked", "purging", "deleted"]
    version: int
    resources_state: Literal["present", "unknown", "absent"]
    creation_succeeded: StrictBool
    error_code: str | None = None


class DeletionCapability(ProtocolModel):
    can_delete: StrictBool
    reason: str | None = None


class PurgeCommand(ProtocolModel):
    tenant_id: UUID
    version: int = Field(strict=True, ge=1)


class AccessProjectionPayload(ProtocolModel):
    """Runtime's immutable PUT payload; version is a per-user sequence."""

    event_id: UUID
    version: int = Field(strict=True, ge=1, le=9223372036854775807)
    available: StrictBool


class AccessProjectionAcknowledgment(ProtocolModel):
    """Core may omit version only when acknowledging a duplicate/stale event."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"applied": {"const": True}},
                        "required": ["applied"],
                    },
                    "then": {"required": ["version"]},
                }
            ]
        },
    )
    applied: StrictBool
    # Omission has an internal None default; an explicitly provided JSON null is
    # invalid, matching Core's optional integer field and Runtime's decoder.
    version: int = Field(default=None, strict=True, ge=1, le=9223372036854775807)

    @model_validator(mode="after")
    def applied_has_version(self):
        if self.applied and self.version is None:
            raise ValueError("Applied acknowledgment must contain its version")
        return self


class AccessProjectionResponse(ProtocolModel):
    """Core's wrapped successful response, unlike Runtime's unwrapped API."""

    status: Literal[200]
    data: AccessProjectionAcknowledgment
