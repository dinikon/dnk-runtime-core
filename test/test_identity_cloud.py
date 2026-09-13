"""OIDC signature/claim isolation, key rotation and atomic browser state tests."""

import asyncio
import base64
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from urllib.parse import parse_qs

import httpx
from authlib.jose import JsonWebKey, JsonWebToken
from authlib.jose.errors import JoseError

from src.modules.identity.application.ports.cloud import CloudConnection
from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.infrastructure.adapter.oidc_client import OidcClient
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend


class OidcValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tenant = uuid4()
        self.subject = str(uuid4())
        self.connection = CloudConnection(
            self.tenant,
            f"https://core.example/oidc/tenants/{self.tenant}",
            "client-a",
            "secret",
            "https://one.example/api/auth/cloud/callback/",
        )
        self.key = JsonWebKey.generate_key(
            "RSA", 2048, is_private=True, options={"kid": "a"}
        )
        self.jwks = {"keys": [self.key.as_dict(is_private=False)]}
        self.jwks_reads = 0
        self.claims = {
            "iss": self.connection.issuer,
            "sub": self.subject,
            "aud": "client-a",
            "iat": int(time.time()),
            "exp": int(time.time()) + 120,
            "nonce": "nonce",
        }
        self.header = {"alg": "RS256", "kid": "a"}
        self.discovery = {
            "issuer": self.connection.issuer,
            "authorization_endpoint": self.connection.issuer + "/authorize/",
            "token_endpoint": self.connection.issuer + "/token/",
            "jwks_uri": "https://core.example/oidc/jwks/",
        }

        def handler(request):
            if request.url.path.endswith("openid-configuration"):
                return httpx.Response(200, json=self.discovery)
            if request.url.path.endswith("/jwks/"):
                self.jwks_reads += 1
                return httpx.Response(200, json=self.jwks)
            if request.url.path.endswith("/token/"):
                self.assertEqual(
                    request.headers["authorization"],
                    "Basic " + base64.b64encode(b"client-a:secret").decode(),
                )
                self.assertEqual(
                    parse_qs(request.content.decode())["code_verifier"], ["verifier"]
                )
                encoded = (
                    JsonWebToken(["RS256"])
                    .encode(self.header, self.claims, self.key)
                    .decode()
                )
                return httpx.Response(
                    200,
                    json={
                        "access_token": "access",
                        "token_type": "Bearer",
                        "id_token": encoded,
                    },
                )
            return httpx.Response(404)

        self.client = OidcClient(
            "https://core.example", transport=httpx.MockTransport(handler)
        )

    async def exchange(self):
        return await self.client.exchange(
            self.connection, code="code", nonce="nonce", verifier="verifier"
        )

    async def test_code_pkce_basic_and_strict_claims(self):
        self.assertEqual(await self.exchange(), self.subject)
        for field, value in [
            ("iss", "https://evil.example"),
            ("aud", "other-client"),
            ("nonce", "other"),
            ("azp", "other"),
            ("exp", int(time.time()) - 120),
            ("sub", "not-a-uuid"),
        ]:
            old = self.claims.copy()
            self.claims[field] = value
            with (
                self.subTest(field=field),
                self.assertRaises((JoseError, IdentityAccessError)),
            ):
                await self.exchange()
            self.claims = old
        self.claims.pop("iat")
        with self.assertRaises(JoseError):
            await self.exchange()

    async def test_rotation_refreshes_once_and_unknown_key_is_rate_limited(self):
        await self.exchange()
        self.key = JsonWebKey.generate_key(
            "RSA", 2048, is_private=True, options={"kid": "b"}
        )
        self.header["kid"] = "b"
        self.jwks = {"keys": [self.key.as_dict(is_private=False)]}
        self.assertEqual(await self.exchange(), self.subject)
        self.assertEqual(self.jwks_reads, 2)
        self.key = JsonWebKey.generate_key(
            "RSA", 2048, is_private=True, options={"kid": "unknown"}
        )
        self.header["kid"] = "unknown"
        for _ in range(2):
            with self.assertRaises(IdentityAccessError):
                await self.exchange()
        self.assertEqual(self.jwks_reads, 2)

    async def test_discovery_cannot_redirect_credentials_to_other_origin(self):
        self.discovery["token_endpoint"] = "https://evil.example/token"
        with self.assertRaises(IdentityAccessError):
            await self.exchange()

    async def test_invalid_access_token_hash_is_rejected(self):
        self.claims["at_hash"] = "wrong"
        with self.assertRaises(JoseError):
            await self.exchange()

    async def test_authorization_uses_pkce_and_query_profile(self):
        url = await self.client.authorization_url(
            self.connection, state="state", nonce="nonce", verifier="verifier"
        )
        query = parse_qs(httpx.URL(url).query.decode())
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["response_mode"], ["query"])
        self.assertEqual(query["scope"], ["openid profile email"])
        self.assertNotIn("prompt", query)


class AtomicTokenTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_consumption_has_one_winner(self):
        manager = TokenManager(InMemoryTokenBackend())
        await manager.set_token(
            prefix="state", suffix="tenant", token="one", body={"value": True}, ttl=60
        )
        results = await asyncio.gather(
            *[
                manager.consume_token(prefix="state", suffix="tenant", token="one")
                for _ in range(20)
            ]
        )
        self.assertEqual(sum(r is not None for r in results), 1)
