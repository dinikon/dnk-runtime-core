from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class EmailProvider(StrEnum):
    SMTP = "smtp"
    RESEND = "resend"


class EmailSmtpSettings(BaseModel):
    host: str = Field(
        default="localhost",
        min_length=1,
        description="SMTP server host.",
    )
    port: int = Field(
        default=25,
        ge=1,
        description="SMTP server port.",
    )
    username: str = Field(
        default="",
        description="SMTP username.",
    )
    password: str = Field(
        default="",
        description="SMTP password.",
    )
    use_tls: bool = Field(
        default=False,
        description="Use implicit TLS via SMTP_SSL.",
    )
    use_starttls: bool = Field(
        default=False,
        description="Upgrade a plain SMTP connection with STARTTLS.",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description="SMTP connection timeout in seconds.",
    )


class EmailSettings(BaseModel):
    provider: EmailProvider = Field(
        default=EmailProvider.SMTP,
        description="Email delivery provider.",
    )
    from_address: str = Field(
        default="no-reply@example.com",
        min_length=1,
        description="Default sender email address.",
    )
    from_name: str = Field(
        default="DNK Runtime",
        description="Default sender display name.",
    )
    smtp: EmailSmtpSettings = Field(
        default_factory=EmailSmtpSettings,
        description="SMTP transport settings.",
    )


class EmailConfig(BaseSettings):
    EMAIL: EmailSettings = Field(
        default_factory=EmailSettings,
        description="Email delivery settings.",
    )


__all__ = [
    "EmailConfig",
    "EmailProvider",
    "EmailSettings",
    "EmailSmtpSettings",
]
