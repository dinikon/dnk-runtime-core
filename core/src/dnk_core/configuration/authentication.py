"""Primary authentication modes, enrollment controls and provider credentials."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

ProviderSwitch = bool | Literal["auto"]
PasswordMode = Literal["required", "optional", "passwordless"]
UsernameMode = Literal["generated", "required"]
PhoneLoginMode = Literal["any_verified", "primary_only"]


class AuthenticationSettings(BaseSettings):
    """Expose supported product policies while preserving security invariants."""

    auth_phone_login_mode: PhoneLoginMode = Field(
        "any_verified",
        description="Allow all verified phones or only the primary phone to log in.",
    )
    auth_max_phone_numbers: int = Field(
        5, gt=0, description="Maximum owned phones, including unverified contacts."
    )

    auth_username_mode: UsernameMode = Field(
        "generated",
        description="Generate internal usernames or require a public login name.",
    )
    auth_password_mode: PasswordMode = Field(
        "passwordless",
        description="Password policy for primary login and ordinary signup.",
    )
    auth_signup_enabled: bool = Field(
        True, description="Allow creating public accounts."
    )
    auth_email_code_enabled: bool = Field(
        True, description="Allow primary email OTP login."
    )
    auth_passkey_login_enabled: bool = Field(
        True, description="Allow primary passkey login."
    )
    auth_passkey_signup_enabled: bool = Field(
        True, description="Offer passkey registration."
    )
    mfa_totp_enrollment_enabled: bool = Field(
        True, description="Allow new TOTP enrollment; existing factors remain required."
    )
    mfa_passkey_enrollment_enabled: bool = Field(
        True, description="Allow new passkeys; existing factors remain manageable."
    )
    mfa_totp_issuer: str = Field(
        "dNiko Alpha", min_length=1, description="TOTP issuer label."
    )
    auth_code_timeout: int = Field(
        300,
        ge=30,
        le=3600,
        description="Shared login/phone OTP and Gateway TTL, seconds.",
    )
    auth_code_max_attempts: int = Field(
        3, ge=1, le=10, description="Attempts per login/phone OTP."
    )
    auth_code_resend_enabled: bool = Field(
        True, description="Allow resending login/phone OTP."
    )
    email_verification_timeout: int = Field(
        900, gt=0, description="Email confirmation code lifetime, seconds."
    )
    email_verification_max_attempts: int = Field(
        3, ge=1, le=10, description="Attempts per email confirmation code."
    )
    email_verification_max_resends: int = Field(
        2,
        ge=0,
        description="Allowed email confirmation resends; zero disables resending.",
    )
    reauthentication_timeout: int = Field(
        300,
        gt=0,
        description="Recent-authentication window for sensitive changes, seconds.",
    )
    email_reauthentication_timeout: int = Field(
        300, gt=0, description="Fallback email reauthentication code lifetime, seconds."
    )
    email_reauthentication_max_attempts: int = Field(
        3, ge=1, le=10, description="Attempts per fallback email reauthentication code."
    )
    email_reauthentication_resend_wait_seconds: int = Field(
        30,
        gt=0,
        description="Minimum interval between email reauthentication deliveries.",
    )
    email_reauthentication_max_per_hour: int = Field(
        5,
        gt=0,
        description="Maximum email reauthentication deliveries per user per hour.",
    )
    google_login_enabled: ProviderSwitch = Field(
        "auto", description="Google: auto, true or false."
    )
    google_client_id: str = Field("", description="Google OAuth client identifier.")
    google_client_secret: SecretStr = Field(
        SecretStr(""), description="Google OAuth client secret."
    )
    github_login_enabled: ProviderSwitch = Field(
        "auto", description="GitHub: auto, true or false."
    )
    github_client_id: str = Field("", description="GitHub OAuth client identifier.")
    github_client_secret: SecretStr = Field(
        SecretStr(""), description="GitHub OAuth client secret."
    )
    telegram_login_enabled: ProviderSwitch = Field(
        "auto", description="Telegram Login: auto, true or false."
    )
    telegram_login_client_id: str = Field(
        "", description="Telegram OIDC client identifier."
    )
    telegram_login_client_secret: SecretStr = Field(
        SecretStr(""), description="Telegram OIDC client secret."
    )
    telegram_gateway_enabled: ProviderSwitch = Field(
        "auto", description="Telegram Gateway: auto, true or false."
    )
    telegram_gateway_token: SecretStr = Field(
        SecretStr(""), description="Telegram Gateway bearer token."
    )
    telegram_gateway_timeout: float = Field(
        5, gt=0, description="Telegram Gateway HTTP timeout, seconds."
    )

    @field_validator(
        "google_login_enabled",
        "github_login_enabled",
        "telegram_login_enabled",
        "telegram_gateway_enabled",
        mode="before",
    )
    @classmethod
    def parse_provider_switch(cls, value):
        """Treat an empty or case-insensitive auto setting as credential detection."""
        if isinstance(value, str) and value.strip().lower() in {"", "auto"}:
            return "auto"
        return value

    def provider_enabled(self, name: str) -> bool:
        """Resolve a provider switch from credentials without exposing secrets."""
        if name == "telegram_gateway":
            configured = bool(self.telegram_gateway_token.get_secret_value().strip())
            switch = self.telegram_gateway_enabled
        else:
            configured = bool(
                getattr(self, f"{name}_client_id").strip()
                and getattr(self, f"{name}_client_secret").get_secret_value().strip()
            )
            switch = getattr(
                self,
                (
                    f"{name}_enabled"
                    if name == "telegram_login"
                    else f"{name}_login_enabled"
                ),
            )
        return configured if switch == "auto" else switch

    def validate_provider(self, name: str) -> None:
        """Require credentials only when a provider is explicitly enabled."""
        if name == "telegram_gateway":
            explicit = self.telegram_gateway_enabled is True
            configured = bool(self.telegram_gateway_token.get_secret_value().strip())
            setting = "CORE_TELEGRAM_GATEWAY_ENABLED"
        else:
            attr = (
                f"{name}_enabled"
                if name == "telegram_login"
                else f"{name}_login_enabled"
            )
            explicit = getattr(self, attr) is True
            configured = bool(
                getattr(self, f"{name}_client_id").strip()
                and getattr(self, f"{name}_client_secret").get_secret_value().strip()
            )
            setting = f"CORE_{attr.upper()}"
        if explicit and not configured:
            raise ValueError(f"{setting}=true requires complete provider credentials.")
