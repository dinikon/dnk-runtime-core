"""WebAuthn ceremonies with an actual P-256 key and signed client assertions.

Only the hardware authenticator is simulated: the application and python-fido2
parse and cryptographically validate the same bytes a browser would submit.
"""

import base64
import hashlib
import json
import secrets
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.urls import reverse
from fido2 import cbor

from allauth.account.models import EmailAddress
from allauth.account.utils import user_pk_to_url_str
from allauth.mfa.models import Authenticator

from tests.helpers import AccountTestCase


def websafe(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


class VirtualPasskey:
    """A minimal discoverable ES256 credential, independent of server helpers."""

    def __init__(self):
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = secrets.token_bytes(32)

    def client_data(self, kind, challenge, origin):
        return json.dumps(
            {
                "type": kind,
                "challenge": challenge,
                "origin": origin,
                "crossOrigin": False,
            },
            separators=(",", ":"),
        ).encode()

    def register(self, options, origin="https://testserver", verified=True):
        public = self.private_key.public_key().public_numbers()
        cose_key = {
            1: 2,
            3: -7,
            -1: 1,
            -2: public.x.to_bytes(32, "big"),
            -3: public.y.to_bytes(32, "big"),
        }
        credential = (
            b"\0" * 16
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + cbor.encode(cose_key)
        )
        flags = 0x01 | 0x40 | (0x04 if verified else 0)
        auth_data = (
            hashlib.sha256(options["rp"]["id"].encode()).digest()
            + bytes([flags])
            + b"\0" * 4
            + credential
        )
        client_data = self.client_data("webauthn.create", options["challenge"], origin)
        return {
            "id": websafe(self.credential_id),
            "rawId": websafe(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": websafe(client_data),
                "attestationObject": websafe(
                    cbor.encode({"fmt": "none", "authData": auth_data, "attStmt": {}})
                ),
            },
            "clientExtensionResults": {"credProps": {"rk": True}},
        }

    def assert_login(
        self,
        options,
        user,
        *,
        origin="https://testserver",
        challenge=None,
        verified=True,
        signing_key=None,
        rp_id=None,
    ):
        flags = 0x01 | (0x04 if verified else 0)
        auth_data = (
            hashlib.sha256((rp_id or options["rpId"]).encode()).digest()
            + bytes([flags])
            + (1).to_bytes(4, "big")
        )
        client_data = self.client_data(
            "webauthn.get", challenge or options["challenge"], origin
        )
        signature = (signing_key or self.private_key).sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        return {
            "id": websafe(self.credential_id),
            "rawId": websafe(self.credential_id),
            "type": "public-key",
            "response": {
                "authenticatorData": websafe(auth_data),
                "clientDataJSON": websafe(client_data),
                "signature": websafe(signature),
                "userHandle": websafe(user_pk_to_url_str(user).encode()),
            },
            "clientExtensionResults": {},
        }


class PasskeyTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.device = VirtualPasskey()

    def register(self, **kwargs):
        self.password_login()
        response = self.client.get(reverse("mfa_add_webauthn"), secure=True)
        self.assertEqual(response.status_code, 200, response.content)
        options = response.context["js_data"]["creation_options"]["publicKey"]
        self.assertEqual(options["authenticatorSelection"]["residentKey"], "required")
        self.assertEqual(
            options["authenticatorSelection"]["userVerification"], "required"
        )
        credential = self.device.register(options, **kwargs)
        response = self.client.post(
            reverse("mfa_add_webauthn"),
            {"name": "Virtual security key", "credential": json.dumps(credential)},
            secure=True,
        )
        return response

    def begin_login(self):
        response = self.client.get(
            reverse("mfa_login_webauthn"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            secure=True,
        )
        self.assertEqual(response.status_code, 200, response.content)
        options = response.json()["request_options"]["publicKey"]
        self.assertEqual(options["userVerification"], "required")
        return options

    def submit(self, credential, **kwargs):
        return self.client.post(
            reverse("mfa_login_webauthn"),
            {"credential": json.dumps(credential), **kwargs},
            secure=True,
        )

    def ready_for_login(self):
        self.assertEqual(self.register().status_code, 302)
        self.assertEqual(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.WEBAUTHN
            ).count(),
            1,
        )
        self.client.post(reverse("account_logout"))

    def test_register_and_sign_in_with_verified_signed_assertion(self):
        self.ready_for_login()
        credential = self.device.assert_login(self.begin_login(), self.user)
        response = self.submit(credential, next="/app/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, "/app/")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_registration_without_user_verification_is_rejected(self):
        self.assertEqual(self.register(verified=False).status_code, 200)
        self.assertFalse(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.WEBAUTHN
            ).exists()
        )

    def test_signed_assertion_requires_uv_correct_origin_challenge_rp_and_key(self):
        self.ready_for_login()
        alterations = {
            "missing_uv": {"verified": False},
            "foreign_origin": {"origin": "https://attacker.example"},
            "wrong_challenge": {"challenge": websafe(b"wrong-challenge" * 3)},
            "wrong_rp": {"rp_id": "attacker.example"},
            "wrong_signature": {"signing_key": ec.generate_private_key(ec.SECP256R1())},
        }
        for label, change in alterations.items():
            with self.subTest(label=label):
                from django.core.cache import cache

                cache.clear()
                self.submit(
                    self.device.assert_login(self.begin_login(), self.user, **change)
                )
                self.assert_anonymous()

    def test_consumed_challenge_and_another_users_handle_are_rejected(self):
        self.ready_for_login()
        stranger = self.create_user(username="bob", email="bob@example.com")
        self.submit(self.device.assert_login(self.begin_login(), stranger))
        self.assert_anonymous()
        credential = self.device.assert_login(self.begin_login(), self.user)
        self.submit(credential)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))
        self.submit(credential)
        self.assert_anonymous()

    def test_malformed_payload_inactive_user_and_unverified_email_cannot_enter(self):
        self.ready_for_login()
        self.begin_login()
        self.submit({"response": {"userHandle": "invalid"}})
        self.assert_anonymous()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.submit(self.device.assert_login(self.begin_login(), self.user))
        self.assert_anonymous()
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.submit(self.device.assert_login(self.begin_login(), self.user))
        self.assert_anonymous()
