from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class IdentityAuthSettings(BaseModel):
    otp_code_length: int = Field(
        default=6,
        ge=4,
        description="Number of digits in email OTP code.",
    )
    otp_token_ttl_seconds: int = Field(
        default=300,
        ge=1,
        description="OTP challenge lifetime in seconds.",
    )
    session_ttl_seconds: int = Field(
        default=432000,
        ge=1,
        description="Session lifetime in seconds.",
    )
    session_cookie_name: str = Field(
        default="dnk_session",
        min_length=1,
        description="Cookie name used for console auth session.",
    )


class IdentityAuthConfig(BaseSettings):
    AUTH: IdentityAuthSettings = Field(
        default_factory=IdentityAuthSettings,
        description="Identity auth settings.",
    )
