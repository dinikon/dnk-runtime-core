"""Application identity, HTTP boundary and session configuration."""

import base64
import hashlib
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class ApplicationSettings(BaseSettings):
    """Declare application settings without accessing services or Django."""

    secret_key: SecretStr = Field(description="Persistent Django signing secret.")
    debug: bool = Field(False, description="Enable local development behavior.")
    public_origin: str = Field("", description="Canonical browser origin, with port.")
    allowed_hosts: str | None = Field(
        None, description="Comma-separated allowed hosts; defaults to origin hostname."
    )
    trust_proxy: bool = Field(False, description="Trust the configured HTTPS proxy.")
    trusted_proxy_count: int = Field(
        0, ge=0, description="Number of trusted reverse proxy hops."
    )
    mfa_encryption_key: SecretStr = Field(
        SecretStr(""), description="Independent persistent Fernet key for MFA secrets."
    )
    session_cookie_age: int = Field(
        1209600, gt=0, description="Persistent session lifetime, in seconds."
    )
    session_remember: bool | None = Field(
        None, description="Remember sessions: true, false or auto for user choice."
    )
    language_code: str = Field(
        "ru", min_length=2, description="Django interface locale."
    )
    time_zone: str = Field(
        "UTC", min_length=1, description="IANA application time zone."
    )

    @field_validator("session_remember", mode="before")
    @classmethod
    def parse_remember_choice(cls, value):
        """Use auto or an empty value for the existing user-controlled choice."""
        if isinstance(value, str) and value.strip().lower() in {"", "auto"}:
            return None
        return value

    @property
    def effective_public_origin(self) -> str:
        """Apply the established local development origin fallback."""
        return (
            self.public_origin or ("http://localhost:8000" if self.debug else "")
        ).rstrip("/")

    @property
    def effective_allowed_hosts(self) -> list[str]:
        """Parse the backward-compatible comma-separated host list."""
        value = self.allowed_hosts
        if value is None:
            value = urlsplit(self.effective_public_origin).hostname or ""
        return [host.strip() for host in value.split(",") if host.strip()]

    @property
    def effective_mfa_encryption_key(self) -> str:
        """Keep the existing development derivation for stored MFA compatibility."""
        explicit = self.mfa_encryption_key.get_secret_value()
        if explicit:
            return explicit
        source = "dnk-core-development-mfa:" + self.secret_key.get_secret_value()
        return base64.urlsafe_b64encode(
            hashlib.sha256(source.encode()).digest()
        ).decode()
