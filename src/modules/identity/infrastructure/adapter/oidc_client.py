"""Restricted OIDC relying party backed by Authlib, with per-issuer JWKS cache."""

import asyncio
import base64
import json
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebToken
from authlib.oidc.core import CodeIDToken

from src.modules.identity.domain.access import IdentityAccessError


class OidcClient:
    def __init__(self, public_origin: str, *, transport=None):
        self.public_origin = public_origin.rstrip("/")
        self.transport = transport
        self.metadata = {}
        self.keys = {}
        self.locks = {}
        self.unknown_refresh = {}
        self.jwt = JsonWebToken(["RS256"])

    def trusted_url(self, url):
        parsed = urlsplit(url)
        expected = urlsplit(self.public_origin)
        if (
            parsed.scheme != "https"
            or (parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc)
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise IdentityAccessError("Cloud endpoint is not trusted.", 503)
        return url

    def check_connection(self, connection):
        expected = f"{self.public_origin}/oidc/tenants/{connection.core_tenant_id}"
        if connection.issuer != expected:
            raise IdentityAccessError("Cloud issuer is not trusted.", 503)
        self.trusted_url(connection.issuer)

    async def fetch_json(self, url):
        self.trusted_url(url)
        async with httpx.AsyncClient(
            timeout=5, follow_redirects=False, trust_env=False, transport=self.transport
        ) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            if len(response.content) > 1024 * 1024:
                raise IdentityAccessError("Cloud metadata is too large.", 503)
            result = response.json()
            if not isinstance(result, dict):
                raise IdentityAccessError("Cloud metadata is invalid.", 503)
            return result

    async def discovery(self, connection):
        self.check_connection(connection)
        cached = self.metadata.get(connection.issuer)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        doc = await self.fetch_json(
            connection.issuer + "/.well-known/openid-configuration"
        )
        if doc.get("issuer") != connection.issuer:
            raise IdentityAccessError("Cloud discovery issuer does not match.", 503)
        for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            value = doc.get(field)
            if not isinstance(value, str):
                raise IdentityAccessError("Cloud metadata is incomplete.", 503)
            self.trusted_url(value)
        self.metadata[connection.issuer] = (time.monotonic() + 300, doc)
        return doc

    def oauth_client(self, connection):
        return AsyncOAuth2Client(
            client_id=connection.client_id,
            client_secret=connection.client_secret,
            token_endpoint_auth_method="client_secret_basic",
            scope="openid profile email",
            redirect_uri=connection.callback,
            code_challenge_method="S256",
            timeout=5,
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        )

    async def authorization_url(self, connection, *, state, nonce, verifier):
        metadata = await self.discovery(connection)
        async with self.oauth_client(connection) as client:
            url, _ = client.create_authorization_url(
                metadata["authorization_endpoint"],
                state=state,
                nonce=nonce,
                code_verifier=verifier,
                response_mode="query",
            )
        return url

    async def signing_key(self, connection, metadata, kid):
        if not isinstance(kid, str) or not kid or len(kid) > 256:
            raise IdentityAccessError("ID token has no valid key identifier.", 401)
        lock = self.locks.setdefault(connection.issuer, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            cached = self.keys.get(connection.issuer)
            # A known key uses a five-minute cache. An unknown key forces at most
            # one refresh per five seconds across all callers of this process.
            if cached and cached[0] + 300 > now and kid in cached[1]:
                return cached[1][kid]
            if cached and kid not in cached[1]:
                if self.unknown_refresh.get(connection.issuer, float("-inf")) + 5 > now:
                    raise IdentityAccessError(
                        "ID token signing key is not recognized.", 401
                    )
                self.unknown_refresh[connection.issuer] = now
            document = await self.fetch_json(metadata["jwks_uri"])
            selected = {}
            keys = document.get("keys", [])
            if not isinstance(keys, list) or len(keys) > 100:
                raise IdentityAccessError("Cloud signing keys are invalid.", 503)
            for key in keys:
                if (
                    not isinstance(key, dict)
                    or key.get("kty") != "RSA"
                    or key.get("use", "sig") != "sig"
                    or key.get("alg", "RS256") != "RS256"
                    or "verify" not in key.get("key_ops", ["verify"])
                ):
                    continue
                key_id = key.get("kid")
                if (
                    not isinstance(key_id, str)
                    or key_id in selected
                    or any(part in key for part in ("d", "p", "q"))
                ):
                    raise IdentityAccessError("Cloud signing keys are invalid.", 503)
                selected[key_id] = key
            self.keys[connection.issuer] = (now, selected)
            if kid not in selected:
                self.unknown_refresh[connection.issuer] = now
                raise IdentityAccessError(
                    "ID token signing key is not recognized.", 401
                )
            return selected[kid]

    async def exchange(self, connection, *, code, nonce, verifier):
        metadata = await self.discovery(connection)
        async with self.oauth_client(connection) as client:
            token = await client.fetch_token(
                metadata["token_endpoint"],
                grant_type="authorization_code",
                code=code,
                code_verifier=verifier,
            )
        encoded = token.get("id_token")
        if not isinstance(encoded, str) or len(encoded) > 65536:
            raise IdentityAccessError("Cloud response has no valid ID token.", 401)
        try:
            header_segment = encoded.split(".")[0]
            header = json.loads(
                base64.urlsafe_b64decode(
                    header_segment + "=" * (-len(header_segment) % 4)
                )
            )
        except (ValueError, TypeError):
            raise IdentityAccessError("ID token is malformed.", 401) from None
        if not isinstance(header, dict) or header.get("alg") != "RS256":
            raise IdentityAccessError("ID token algorithm is not allowed.", 401)
        key = await self.signing_key(connection, metadata, header.get("kid"))
        claims = self.jwt.decode(
            encoded,
            key,
            claims_cls=CodeIDToken,
            claims_options={
                "iss": {"essential": True, "value": connection.issuer},
                "aud": {"essential": True, "value": connection.client_id},
                "sub": {"essential": True},
                "exp": {"essential": True},
                "iat": {"essential": True},
            },
            claims_params={
                "client_id": connection.client_id,
                "nonce": nonce,
                "access_token": token.get("access_token"),
            },
        )
        claims.validate(leeway=30)
        if claims.get("at_hash") and not token.get("access_token"):
            raise IdentityAccessError(
                "ID token access token hash cannot be verified.", 401
            )
        subject = claims.get("sub")
        try:
            UUID(subject)
        except (TypeError, ValueError, AttributeError):
            raise IdentityAccessError(
                "Cloud subject is not a user UUID.", 401
            ) from None
        # Tokens are deliberately discarded after identity verification.
        return str(subject)
