"""Database, rate-limit cache and mail transport configuration."""

from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class InfrastructureSettings(BaseSettings):
    """Declare independent connection settings using the existing CORE names."""

    db_name: str = Field(
        "dniko", min_length=1, description="Shared PostgreSQL database."
    )
    db_user: str = Field("postgres", min_length=1, description="PostgreSQL user.")
    db_password: SecretStr = Field(SecretStr(""), description="PostgreSQL password.")
    db_host: str = Field("127.0.0.1", description="PostgreSQL hostname or socket path.")
    db_port: int = Field(5432, ge=1, le=65535, description="PostgreSQL TCP port.")
    redis_url: SecretStr = Field(
        SecretStr(""), description="Full redis/rediss URL, overriding separate fields."
    )
    redis_host: str = Field(
        "", description="Redis host; empty permits debug local cache."
    )
    redis_port: int = Field(6379, ge=1, le=65535, description="Redis TCP port.")
    redis_password: SecretStr = Field(SecretStr(""), description="Redis password.")
    redis_db: int = Field(2, ge=0, description="Redis logical database index.")
    email_backend: str | None = Field(
        None,
        description="Django mail backend; debug defaults to console, production SMTP.",
    )
    email_host: str = Field("localhost", description="SMTP hostname.")
    email_port: int = Field(587, ge=1, le=65535, description="SMTP TCP port.")
    email_host_user: str = Field("", description="SMTP authentication username.")
    email_host_password: SecretStr = Field(SecretStr(""), description="SMTP password.")
    email_use_tls: bool | None = Field(
        None, description="Use STARTTLS; defaults to enabled outside debug."
    )
    email_use_ssl: bool = Field(
        False, description="Use implicit TLS, normally port 465."
    )
    email_verify_certificate: bool = Field(
        True, description="Verify SMTP certificates; disabling is debug-only."
    )
    email_file_path: str | None = Field(
        None, description="Outbox directory for the optional filebased mail backend."
    )
    email_timeout: float = Field(10, gt=0, description="SMTP network timeout, seconds.")
    default_from_email: str = Field(
        "dNiko Alpha <noreply@localhost>", description="Default message sender address."
    )
    email_subject_prefix: str = Field(
        "[dNiko Alpha] ", description="Prefix of account email subjects."
    )
    email_notifications: bool = Field(
        True, description="Send account security notification emails."
    )

    @property
    def effective_redis_url(self) -> str:
        """Resolve Redis URL precedence and escape a separately configured password."""
        explicit = self.redis_url.get_secret_value()
        if explicit or not self.redis_host:
            return explicit
        password = self.redis_password.get_secret_value()
        auth = f":{quote(password, safe='')}@" if password else ""
        host = self.redis_host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"redis://{auth}{host}:{self.redis_port}/{self.redis_db}"

    @property
    def effective_email_backend(self) -> str:
        """Keep console delivery in debug and SMTP in production by default."""
        if self.email_backend is not None:
            return self.email_backend
        backend = "console" if self.debug else "smtp"
        return f"django.core.mail.backends.{backend}.EmailBackend"

    @property
    def effective_email_use_tls(self) -> bool:
        """Preserve the original environment-dependent STARTTLS default."""
        return not self.debug if self.email_use_tls is None else self.email_use_tls
