"""Optional real-Core interoperability; no sibling source or persistent state edits.

Run with CORE_REPOSITORY_PATH pointing to a Core checkout with its virtualenv,
and TEST_POSTGRES_URL pointing to a disposable Runtime PostgreSQL database.
The Core uses its tests.settings in-memory SQLite database in a child process.
Optional HTTPS mode also sets CORE_INTEROP_BIND (TLS proxy upstream address),
CORE_INTEROP_PUBLIC_ORIGIN and CORE_INTEROP_CA_FILE; the caller provides DNS and
a TLS reverse proxy for that origin. Its Core SQLite file is still temporary.
"""

import base64
import json
import os
from pathlib import Path
import selectors
import ssl
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx

from src.modules.identity.application.cloud_auth_service import CloudAuthService
from src.modules.identity.application.ports.cloud import CloudConnection
from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.infrastructure.adapter.oidc_client import OidcClient
from modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import UnitOfWork
from test import test_identity_access_postgres as access_fixtures


class CoreBridge:
    def __init__(self, repository: Path):
        self.stderr = tempfile.TemporaryFile()
        executable = repository / ".venv" / "bin" / "python"
        script = Path(__file__).parent / "integration_support" / "core_oidc_bridge.py"
        self.process = subprocess.Popen(
            [str(executable), str(script), str(repository)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
        )
        try:
            self.initial = self.read(timeout=45)
        except Exception:
            self.close()
            raise

    def read(self, *, timeout=20):
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout):
                raise RuntimeError("Core interoperability bridge timed out.")
            line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Core interoperability bridge exited before responding.")
        result = json.loads(line)
        if "bridge_error" in result:
            raise RuntimeError(
                f"Core interoperability request failed: {result['bridge_error']}"
            )
        return result

    def call(self, message):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        return self.read()

    def close(self):
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.process.stdout.close()
        self.stderr.close()


class CoreBridgeTransport(httpx.AsyncBaseTransport):
    def __init__(self, bridge):
        self.bridge = bridge

    async def handle_async_request(self, request):
        result = self.bridge.call(
            {
                "action": "http",
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": base64.b64encode(request.content).decode(),
            }
        )
        return httpx.Response(
            result["status"],
            headers=result["headers"],
            content=base64.b64decode(result["body"]),
            request=request,
        )


class CoreHttpsTransport(httpx.AsyncBaseTransport):
    """Use the caller's test CA; production client URL restrictions still apply."""

    async def handle_async_request(self, request):
        context = ssl.create_default_context(cafile=os.environ["CORE_INTEROP_CA_FILE"])
        async with httpx.AsyncClient(
            verify=context, trust_env=False, timeout=10, follow_redirects=False
        ) as client:
            response = await client.send(request)
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=await response.aread(),
                request=request,
            )


@unittest.skipUnless(
    os.environ.get("CORE_REPOSITORY_PATH") and os.environ.get("TEST_POSTGRES_URL"),
    "Set CORE_REPOSITORY_PATH and disposable TEST_POSTGRES_URL for real-Core interoperability.",
)
class RealCoreIdentityInteroperabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_rotation_invitation_link_and_local_revoke(self):
        bridge = CoreBridge(Path(os.environ["CORE_REPOSITORY_PATH"]))
        self.addCleanup(bridge.close)
        fixture = access_fixtures.IdentityAccessPostgresTests()
        await fixture.asyncSetUp()
        self.addAsyncCleanup(fixture.asyncTearDown)
        initial = bridge.initial
        credentials = initial["credentials"][0]
        fixture.context.host = urlsplit(credentials["redirect_uri"]).hostname
        host = fixture.context.host
        connection = CloudConnection(
            UUID(initial["tenant_ids"][0]),
            credentials["issuer"],
            credentials["client_id"],
            credentials["client_secret"],
            credentials["redirect_uri"],
        )
        reader = AsyncMock()
        reader.get.return_value = connection
        network = bool(os.environ.get("CORE_INTEROP_BIND"))
        transport = CoreHttpsTransport() if network else CoreBridgeTransport(bridge)
        origin = os.environ.get("CORE_INTEROP_PUBLIC_ORIGIN", "https://testserver")
        oidc = OidcClient(origin, transport=transport)
        async with UnitOfWork(fixture.sessions) as uow:
            local = fixture.service(uow)
            await local.access.lock(fixture.tenant.uuid)
            await local.access.bind(
                fixture.tenant.uuid,
                fixture.admin.id.uuid,
                connection.issuer,
                initial["owner"],
            )
            await uow.commit()
            cloud = CloudAuthService(local, reader, oidc)

            async def roundtrip(session, user, purpose):
                request = await cloud.start(host, session, "browser", purpose)
                if network:
                    cookies = bridge.call({"action": "login", "user": user})["cookies"]
                    async with httpx.AsyncClient(
                        transport=CoreHttpsTransport(),
                        cookies=cookies,
                        follow_redirects=False,
                    ) as browser:
                        reply = await browser.get(request["authorization_url"])
                    response = {
                        "status": reply.status_code,
                        "headers": {"Location": reply.headers.get("location", "")},
                    }
                else:
                    response = bridge.call(
                        {
                            "action": "authorize",
                            "url": request["authorization_url"],
                            "user": user,
                        }
                    )
                self.assertEqual(response["status"], 302)
                query = parse_qs(urlsplit(response["headers"]["Location"]).query)
                self.assertEqual(query["iss"], [connection.issuer])
                return await cloud.callback(
                    host,
                    session,
                    "browser",
                    state=query["state"][0],
                    code=query["code"][0],
                    issuer=query["iss"][0],
                )

            purpose, owner_session = await roundtrip(None, "owner", "login")
            self.assertEqual(purpose, "login")
            self.assertEqual(owner_session.user_id, fixture.admin.id.uuid)
            bridge.call({"action": "rotate"})
            _, rotated = await roundtrip(None, "owner", "login")
            self.assertEqual(rotated.user_id, fixture.admin.id.uuid)
            self.assertEqual(bridge.call({"action": "access_count"})["count"], 0)
            invitation = await local.invite(
                host, owner_session.token, "guest@example.net", "member"
            )
            secret = parse_qs(urlsplit(invitation["invitation_url"]).fragment)["token"][
                0
            ]
            otp = await local.request_invitation_otp(host, secret)
            _, guest, guest_session = await local.accept_invitation(
                host, secret, otp["token"], otp["code"], "Guest", "User"
            )
            purpose, _ = await roundtrip(guest_session.token, "guest", "link")
            self.assertEqual(purpose, "link")
            identity = await local.access.identity_for_user(
                fixture.tenant.uuid, guest.id.uuid
            )
            self.assertEqual(identity.subject, initial["guest"])
            self.assertEqual(bridge.call({"action": "access_count"})["count"], 0)
            _, login = await roundtrip(None, "guest", "login")
            self.assertEqual(login.user_id, guest.id.uuid)
            await local.change_user(
                host, owner_session.token, guest.id.uuid, status="revoked"
            )
            with self.assertRaises(IdentityAccessError):
                await roundtrip(None, "guest", "login")
