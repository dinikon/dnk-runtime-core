"""Instance-local integration settings; no shared database or broker with Core."""

import base64
import ipaddress
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings


class ControlPlaneSettings(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    enabled: bool = False
    public_origin: str = ""
    management_origin: str = ""
    management_host: str = ""
    allowed_base_domains: list[str] = Field(default_factory=list)
    instance_id: UUID | None = None
    trusted_proxy_networks: list[str] = Field(default_factory=list)
    allowed_core_fingerprints: list[str] = Field(default_factory=list)
    secret_encryption_key: str = Field(default="", repr=False)
    encryption_key_path: str = ""
    client_cert_path: str = ""
    client_key_path: str = ""
    ca_bundle_path: str = ""
    ingress_probe_address: str = ""
    rabbitmq_url: str = Field(default="", repr=False)
    install_queue: str = "dnk.runtime.installation"
    access_queue: str = "dnk.runtime.access"
    lease_seconds: PositiveInt = 180
    step_timeout_seconds: PositiveInt = 120
    heartbeat_interval_seconds: PositiveInt = 10
    heartbeat_ttl_seconds: PositiveInt = 30
    observation_interval_seconds: PositiveInt = 30
    observation_ttl_seconds: PositiveInt = 60
    dispatch_interval_seconds: PositiveInt = 5
    reconcile_interval_seconds: PositiveInt = 30
    request_timeout_seconds: PositiveInt = Field(default=10, le=10)
    retry_base_seconds: PositiveInt = 5
    retry_max_seconds: PositiveInt = 300

    @field_validator("instance_id", mode="before")
    @classmethod
    def blank_instance_id(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_integration(self):
        if self.secret_encryption_key and self.encryption_key_path:
            raise ValueError("Use secret_encryption_key OR encryption_key_path")
        if self.encryption_key_path:
            try:
                self.secret_encryption_key = (
                    Path(self.encryption_key_path).read_text().strip()
                )
            except OSError:
                raise ValueError(
                    "Cannot read Control Plane encryption key file"
                ) from None
        if self.secret_encryption_key:
            try:
                valid_key = (
                    len(base64.urlsafe_b64decode(self.secret_encryption_key)) == 32
                )
            except (ValueError, TypeError):
                valid_key = False
            if not valid_key:
                raise ValueError("Control Plane encryption key must be a Fernet key")
        for field in ("public_origin", "management_origin"):
            value = getattr(self, field)
            if value:
                parsed = urlsplit(value)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValueError(f"{field} must be an exact HTTPS origin")
        hostname = re.compile(
            r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
        )
        for host in [self.management_host, *self.allowed_base_domains]:
            if host and not hostname.fullmatch(host):
                raise ValueError(
                    "Control Plane domains must be exact lowercase DNS names"
                )
        if len(set(self.allowed_base_domains)) != len(self.allowed_base_domains):
            raise ValueError("Duplicate Control Plane base domains")
        for network in self.trusted_proxy_networks:
            parsed = ipaddress.ip_network(network, strict=False)
            if parsed.prefixlen == 0:
                raise ValueError("Trusting all proxy addresses is prohibited")
        self.allowed_core_fingerprints = [
            value.replace(":", "").lower() for value in self.allowed_core_fingerprints
        ]
        if any(
            not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in self.allowed_core_fingerprints
        ):
            raise ValueError("Core certificate fingerprints must use SHA-256")
        if self.step_timeout_seconds >= self.lease_seconds:
            raise ValueError("Step timeout must be shorter than installation lease")
        if self.heartbeat_ttl_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("Heartbeat TTL must exceed its interval")
        if self.observation_ttl_seconds <= self.observation_interval_seconds:
            raise ValueError("Observation TTL must exceed its interval")
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("Maximum retry delay must exceed its base")
        if self.install_queue == self.access_queue:
            raise ValueError("Installation and access queues must be separate")
        if self.rabbitmq_url:
            broker = urlsplit(self.rabbitmq_url)
            if (
                broker.scheme not in {"amqp", "amqps"}
                or not broker.hostname
                or not broker.username
                or not broker.password
                or broker.path in {"", "/", "/%2F", "/%2f"}
            ):
                raise ValueError(
                    "Control Plane broker requires credentials and a dedicated vhost"
                )
        if self.enabled:
            required = (
                "public_origin",
                "management_origin",
                "management_host",
                "instance_id",
                "allowed_base_domains",
                "trusted_proxy_networks",
                "allowed_core_fingerprints",
                "secret_encryption_key",
                "client_cert_path",
                "client_key_path",
                "ca_bundle_path",
                "ingress_probe_address",
                "rabbitmq_url",
            )
            if any(not getattr(self, field) for field in required):
                raise ValueError(
                    "Enabled Control Plane integration requires all trust, identity, broker and routing settings"
                )
        return self


class ControlPlaneConfig(BaseSettings):
    CONTROL_PLANE: ControlPlaneSettings = Field(default_factory=ControlPlaneSettings)
