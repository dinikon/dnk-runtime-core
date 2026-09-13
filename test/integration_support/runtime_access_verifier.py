"""Opt-in real Runtime -> nginx mTLS -> Core access projection verifier.

Requires a disposable PostgreSQL database and caller-provided nginx/TLS fixture.
Starts a disposable real-Core bridge or uses an existing private metadata file.
Never prints control tokens, OIDC secrets, database URLs, or certificate material.
"""

import argparse
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import selectors
import socket
import ssl
import subprocess
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config.deploy.control_plane import ControlPlaneSettings
from src.modules.control_plane.application.contracts import ProvisioningCommand
from src.modules.control_plane.application.services import AcceptProvisioningCommand
from src.modules.control_plane.infrastructure.models import (
    AccessProjectionModel,
    CloudConnectionModel,
    DeliveryModel,
    InstallationModel,
    ProvisioningAttemptModel,
)
from src.modules.control_plane.infrastructure.services import (
    AccessProjectionWriter,
    ProvisioningRepository,
    now,
)
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter
from src.modules.control_plane.infrastructure.worker_engine import AccessDelivery
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)


@contextmanager
def resolve_test_hosts(hostnames, connect_address=None):
    """Optional fixture DNS override; original URL, Host and verified TLS SNI remain."""
    if not connect_address:
        yield
        return
    resolver = socket.getaddrinfo

    def resolve(host, port, *args, **kwargs):
        name = host.decode("ascii") if isinstance(host, bytes) else host
        return resolver(
            connect_address if name in hostnames else host, port, *args, **kwargs
        )

    with patch("socket.getaddrinfo", resolve):
        yield


@contextmanager
def bridge_metadata(arguments):
    if arguments.metadata_file:
        yield json.loads(arguments.metadata_file.read_text())
        return
    repository = arguments.core_repository.resolve()
    executable = repository / ".venv" / "bin" / "python"
    script = Path(__file__).with_name("core_oidc_bridge.py")
    environment = {
        **os.environ,
        "CORE_INTEROP_BIND": arguments.bridge_bind,
        "CORE_INTEROP_PUBLIC_ORIGIN": arguments.core_origin,
        "CORE_INTEROP_MANAGEMENT_ORIGIN": arguments.management_origin,
        "CORE_INTEROP_RUNTIME_CERT": str(arguments.tls_dir / "runtime.crt"),
    }
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [str(executable), str(script), str(repository)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            env=environment,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(45):
                    raise RuntimeError("Core fixture startup timed out")
                first_line = process.stdout.readline()
            if not first_line:
                raise RuntimeError("Core fixture failed to start")
            yield json.loads(first_line)
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            process.stdout.close()


async def verify(database_url, tls_dir, metadata, core_origin, management_origin):
    tls_dir = Path(tls_dir)
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tls = ssl.create_default_context(cafile=tls_dir / "ca.crt")
    core_id = None
    async with httpx.AsyncClient(
        verify=tls, trust_env=False, timeout=10, follow_redirects=False
    ) as observer:
        headers = {"X-Interop-Control-Token": metadata["control_token"]}

        async def control(action, values=None):
            reply = await observer.post(
                f"{core_origin}/__control__/{action}",
                json=values or {},
                headers=headers,
            )
            if reply.status_code != 200:
                raise AssertionError(
                    f"Core fixture control returned HTTP {reply.status_code}"
                )
            return reply.json()

        async def state():
            return await control(
                "access", {"tenant_id": str(core_id), "user_id": str(user_id)}
            )

        try:
            fixture = await control("access-fixture")
            core_id, user_id = UUID(fixture["tenant_id"]), UUID(fixture["user_id"])
            config = ControlPlaneSettings(
                public_origin=core_origin,
                management_origin=management_origin,
                allowed_base_domains=["one.example.test"],
                instance_id=UUID(fixture["instance_id"]),
                secret_encryption_key=Fernet.generate_key().decode(),
                ca_bundle_path=str(tls_dir / "ca.crt"),
                client_cert_path=str(tls_dir / "runtime.crt"),
                client_key_path=str(tls_dir / "runtime.key"),
            )
            hostname = f"access-{uuid4().hex}.one.example.test"
            payload = {
                "tenant_id": str(core_id),
                "operation_id": str(uuid4()),
                "attempt_id": str(uuid4()),
                "hostname": hostname,
                "name": "Real Core access interoperability",
                "owner": {
                    "sub": str(user_id),
                    "verified_email": "guest@example.com",
                    "profile": {},
                },
                "oidc": {
                    "issuer": f"{core_origin}/oidc/tenants/{core_id}",
                    "client_id": "access-fixture-unused-for-login",
                    "client_secret": Fernet.generate_key().decode(),
                    "redirect_uri": f"https://{hostname}/api/auth/cloud/callback/",
                },
            }
            async with engine.begin() as connection:
                await GlobalMigrator().upgrade(connection)
            async with sessions() as session, session.begin():
                repository = ProvisioningRepository(
                    session, config, TenancyAdapter(session, "dnk_")
                )
                await AcceptProvisioningCommand(repository, config)(
                    ProvisioningCommand.model_validate(payload), payload["attempt_id"]
                )
                installation = await session.get(InstallationModel, core_id)
                writer = AccessProjectionWriter(session)
                for available in (True, False, True):
                    await writer.set_available(
                        installation.runtime_tenant_id, user_id, available
                    )
            async with sessions() as session:
                events = list(
                    (
                        await session.scalars(
                            select(DeliveryModel)
                            .where(
                                DeliveryModel.core_tenant_id == core_id,
                                DeliveryModel.kind == "access",
                            )
                            .order_by(DeliveryModel.version)
                        )
                    ).all()
                )
            delivery = AccessDelivery(
                sessions, config
            )  # real HTTPS/mTLS; no mocked transport
            await delivery.run(events[1].event_id)
            revoked = await state()
            if revoked["available"] is not False or revoked["version"] != 2:
                raise AssertionError("Core did not apply revocation version 2")
            await delivery.run(events[0].event_id)
            stale = await state()
            if stale["available"] is not False or stale["version"] != 2:
                raise AssertionError("Stale grant restored access in Core")
            await delivery.run(events[2].event_id)
            restored = await state()
            if (
                restored["available"] is not True
                or restored["version"] != 3
                or restored["event_count"] != 3
            ):
                raise AssertionError(
                    "Core did not apply the expected versioned event history"
                )
            async with sessions() as session, session.begin():
                event = await session.get(DeliveryModel, events[2].event_id)
                event.state, event.next_attempt_at = "pending", now()
            await delivery.run(events[2].event_id)
            if await state() != restored:
                raise AssertionError(
                    "Duplicate delivery changed Core access or event history"
                )
            async with sessions() as session:
                statuses = [
                    (await session.get(DeliveryModel, event.event_id)).state
                    for event in events
                ]
            if statuses != ["delivered"] * 3:
                raise AssertionError(
                    "Runtime did not persist all delivery acknowledgments"
                )
            return {"version": 3, "event_count": 3, "runtime_delivered": 3}
        finally:
            try:
                if core_id is not None:
                    async with sessions() as session, session.begin():
                        for model in (
                            DeliveryModel,
                            AccessProjectionModel,
                            CloudConnectionModel,
                            ProvisioningAttemptModel,
                            InstallationModel,
                        ):
                            await session.execute(
                                delete(model).where(model.core_tenant_id == core_id)
                            )
                    await control("remove-access-fixture", {"tenant_id": str(core_id)})
            finally:
                await engine.dispose()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--core-repository",
        type=Path,
        help="Start a fresh disposable Core bridge using this checkout's virtualenv",
    )
    source.add_argument(
        "--metadata-file",
        type=Path,
        help="Private metadata JSON from an already running disposable bridge",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("TEST_CP_POSTGRES_URL"),
        help="Disposable Runtime PostgreSQL URL; defaults to TEST_CP_POSTGRES_URL",
    )
    parser.add_argument(
        "--tls-dir",
        type=Path,
        required=True,
        help="Directory containing ca.crt, runtime.crt and runtime.key",
    )
    parser.add_argument("--core-origin", default="https://core.example.test")
    parser.add_argument(
        "--management-origin", default="https://core-management.example.test"
    )
    parser.add_argument(
        "--bridge-bind",
        default="0.0.0.0:18090",
        help="HTTP upstream reached only through the fixture's TLS proxy",
    )
    parser.add_argument(
        "--connect-address",
        help="Optional fixture DNS override preserving verified Host/SNI, e.g. 127.0.0.1",
    )
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error(
            "Set TEST_CP_POSTGRES_URL or --database-url to a disposable PostgreSQL database"
        )
    return arguments


def main():
    arguments = parse_args()
    hosts = {
        urlsplit(arguments.core_origin).hostname,
        urlsplit(arguments.management_origin).hostname,
    }
    with (
        resolve_test_hosts(hosts, arguments.connect_address),
        bridge_metadata(arguments) as metadata,
    ):
        result = asyncio.run(
            verify(
                arguments.database_url,
                arguments.tls_dir,
                metadata,
                arguments.core_origin,
                arguments.management_origin,
            )
        )
    print(
        f"PASS: real Core mTLS projection; version={result['version']}, events={result['event_count']}, delivered={result['runtime_delivered']}"
    )


if __name__ == "__main__":
    main()
