"""Fresh local facts and independent public-ingress observations."""

import asyncio
import json
import ssl
from urllib.parse import urlsplit

from sqlalchemy import select

from src.modules.control_plane.application.contracts import (
    DomainReadiness,
    StatusResponse,
)
from src.modules.control_plane.infrastructure.services import aware, now
from src.modules.control_plane.infrastructure.crypto import CredentialCipher
from src.modules.control_plane.infrastructure.models import (
    CloudConnectionModel,
    InstallationModel,
    ProvisioningAttemptModel,
    ReadinessObservationModel,
)
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter


def probe_hostname(settings, zone: str) -> str:
    return f"dnk-probe-{settings.instance_id.hex}.{zone}"


def heartbeat_key(settings) -> str:
    from src.config import dnk_config
    from src.modules.shared.infrastructure.persistence.tenant_migrations import (
        TenantMigrator,
    )
    from src.modules.shared.infrastructure.persistence.global_migrations import (
        GlobalMigrator,
    )

    # Release schema revisions prevent another generation's worker satisfying readiness.
    return f"worker:{settings.instance_id}:{dnk_config.project.version}:{GlobalMigrator().head()}:{TenantMigrator().head()}"


def auth_store_key(settings) -> str:
    return f"auth-store:{settings.instance_id}"


async def auth_store_ready(timeout_seconds: float = 5) -> bool:
    """Read-only local Redis probe; never creates sessions or contacts Core."""
    from redis.asyncio import Redis
    from src.config import dnk_config

    client = Redis(
        host=dnk_config.REDIS_HOST,
        port=dnk_config.REDIS_PORT,
        username=dnk_config.REDIS_USERNAME or None,
        password=dnk_config.REDIS_PASSWORD or None,
        ssl=dnk_config.REDIS_USE_SSL,
        db=dnk_config.REDIS_DB,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def save_observation(session, key: str, routing: bool, tls: bool) -> None:
    from src.modules.control_plane.infrastructure.services import serialize

    await serialize(session, f"cp:observation:{key}")
    record = await session.get(ReadinessObservationModel, key)
    if record is None:
        record = ReadinessObservationModel(key=key)
        session.add(record)
    record.routing_ready, record.tls_ready, record.observed_at = routing, tls, now()


async def instance_status(session, settings) -> StatusResponse:
    from src.modules.shared.infrastructure.persistence.global_migrations import (
        GlobalMigrator,
    )

    worker_key = heartbeat_key(settings)
    records = (
        await session.scalars(
            select(ReadinessObservationModel).where(
                ReadinessObservationModel.key.in_(
                    [worker_key, *settings.allowed_base_domains]
                )
            )
        )
    ).all()
    observations = {record.key: record for record in records}
    domains = []
    for zone in settings.allowed_base_domains:
        observation = observations.get(zone)
        fresh = bool(
            observation
            and (now() - aware(observation.observed_at)).total_seconds()
            <= settings.observation_ttl_seconds
        )
        domains.append(
            DomainReadiness(
                base_domain=zone,
                routing_ready=fresh and observation.routing_ready,
                tls_ready=fresh and observation.tls_ready,
            )
        )
    heartbeat = observations.get(worker_key)
    fresh_worker = bool(
        heartbeat
        and heartbeat.routing_ready
        and (now() - aware(heartbeat.observed_at)).total_seconds()
        <= settings.heartbeat_ttl_seconds
    )
    await GlobalMigrator().require_current(await session.connection())
    return StatusResponse(ready=settings.enabled and fresh_worker, domains=domains)


async def tenant_ready(session, settings, schema_prefix, hostname: str):
    installation = await session.scalar(
        select(InstallationModel).where(InstallationModel.hostname == hostname)
    )
    if installation is None:
        return None
    attempt = await session.get(
        ProvisioningAttemptModel, installation.current_attempt_id
    )
    if (
        attempt is None
        or attempt.state != "succeeded"
        or attempt.resources_state != "present"
    ):
        return False
    connection = await session.get(CloudConnectionModel, installation.runtime_tenant_id)
    if connection is None or not CredentialCipher(
        settings.secret_encryption_key
    ).decrypt(connection.encrypted_secret):
        return False
    if not await TenancyAdapter(session, schema_prefix).ready(
        installation,
        json.loads(
            CredentialCipher(settings.secret_encryption_key).decrypt(
                attempt.encrypted_command
            )
        ),
        require_active=True,
    ):
        return False
    return {
        "tenant_id": str(installation.core_tenant_id),
        "hostname": hostname,
        "ready": True,
    }


async def observe_zone(settings, zone: str) -> tuple[bool, bool]:
    """Connect to configured LB with the zone hostname as verified TLS SNI/Host."""
    hostname = probe_hostname(settings, zone)
    target = urlsplit("//" + settings.ingress_probe_address)
    routing, tls, writer = False, False, None
    try:
        async with asyncio.timeout(min(settings.request_timeout_seconds, 5)):
            reader, writer = await asyncio.open_connection(
                target.hostname,
                target.port or 443,
                ssl=ssl.create_default_context(),
                server_hostname=hostname,
                limit=16384,
            )
            tls = True
            writer.write(
                f"GET /.well-known/dnk/instance-routing HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n".encode(
                    "ascii"
                )
            )
            await writer.drain()
            head = await reader.readuntil(b"\r\n\r\n")
            if len(head) > 16384 or head.split(b"\r\n", 1)[0].split()[1] != b"200":
                return False, tls
            # A connection-close response has a bounded tiny JSON document.
            headers = dict(
                line.split(b":", 1) for line in head.split(b"\r\n")[1:] if b":" in line
            )
            lengths = [
                v.strip() for k, v in headers.items() if k.lower() == b"content-length"
            ]
            if lengths:
                length = int(lengths[0])
                if not 0 <= length <= 4096:
                    return False, tls
                body = await reader.readexactly(length)
            else:
                body = b""
                while len(body) <= 4096:
                    chunk = await reader.read(4097 - len(body))
                    if not chunk:
                        break
                    body += chunk
            if len(body) > 4096:
                return False, tls
            data = json.loads(body)
            routing = data == {
                "instance_id": str(settings.instance_id),
                "hostname": hostname,
            }
    except (
        OSError,
        ValueError,
        TimeoutError,
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        IndexError,
    ):
        pass
    finally:
        if writer is not None:
            writer.close()
    return routing, tls
