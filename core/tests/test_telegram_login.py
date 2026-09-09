"""A real signed OIDC exchange over a mocked HTTP transport (no provider calls)."""

import base64
import hashlib
import json
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import TOTP
from allauth.socialaccount.models import SocialAccount, SocialToken
from tests.helpers import AccountTestCase, TOTP_SECRET

ISSUER = "https://oauth.telegram.org"
LOGIN = "/accounts/oidc/telegram/login/"
CALLBACK = LOGIN + "callback/"
CONFIG = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "telegram",
                "name": "Telegram",
                "client_id": "test-telegram-id",
                "secret": "test-telegram-secret",
                "settings": {
                    "server_url": ISSUER,
                    "scope": ["openid", "profile"],
                    "oauth_pkce_enabled": True,
                    "fetch_userinfo": False,
                    "token_auth_method": "client_secret_basic",
                },
            }
        ]
    }
}


@override_settings(TELEGRAM_LOGIN_ENABLED=True, SOCIALACCOUNT_PROVIDERS=CONFIG)
class TelegramLoginTests(AccountTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        super().setUp()
        self.claims = {
            "iss": ISSUER,
            "aud": "test-telegram-id",
            "sub": "123456",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "preferred_username": "telegram_user",
            "name": "Telegram User",
        }
        self.signing_key = self.key
        self.algorithm = "RS256"
        self.token_payload = None
        self.transport_failure = False
        self.requests = []
        self.mock = patch(
            "requests.sessions.Session.request", side_effect=self.transport
        )
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def recent_auth(self):
        session = self.client.session
        session["account_authentication_methods"] = [
            {"method": "code", "at": time.time(), "email": self.user.email}
        ]
        session.save()

    def transport(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        if self.transport_failure:
            raise requests.Timeout("simulated")
        if url.endswith("openid-configuration"):
            data = {
                "issuer": ISSUER,
                "authorization_endpoint": ISSUER + "/auth",
                "token_endpoint": ISSUER + "/token",
                "jwks_uri": ISSUER + "/.well-known/jwks.json",
            }
        elif url.endswith("jwks.json"):
            key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
            data = {"keys": [{**key, "kid": "qa-key", "alg": "RS256", "use": "sig"}]}
        elif url == ISSUER + "/token":
            data = (
                self.token_payload
                if self.token_payload is not None
                else {
                    "access_token": "mock-access-token",
                    "token_type": "Bearer",
                    "id_token": jwt.encode(
                        self.claims,
                        self.signing_key,
                        algorithm=self.algorithm,
                        headers={"kid": "qa-key"},
                    ),
                }
            )
        else:
            raise AssertionError(f"Unexpected external request: {url}")
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(data).encode()
        return response

    def start(self, **data):
        response = self.client.post(LOGIN, data, secure=True)
        self.assertEqual(response.status_code, 302, response.content)
        return parse_qs(urlparse(response.url).query)

    def callback(self, state):
        return self.client.get(
            CALLBACK, {"state": state, "code": "mock-code"}, secure=True
        )

    def link(self):
        return SocialAccount.objects.create(
            user=self.user, provider="telegram", uid=self.claims["sub"]
        )

    def test_post_csrf_pkce_scopes_and_signed_login(self):
        self.link()
        browser = Client(enforce_csrf_checks=True)
        self.assertEqual(browser.post(LOGIN).status_code, 403)
        self.assertEqual(self.client.get(LOGIN).status_code, 200)
        query = self.start()
        self.assertEqual(set(query["scope"][0].split()), {"openid", "profile"})
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["redirect_uri"], ["https://testserver" + CALLBACK])
        response = self.callback(query["state"][0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        exchange = next(
            kwargs for _, url, kwargs in self.requests if url.endswith("/token")
        )
        verifier = exchange["data"]["code_verifier"]
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        self.assertEqual(query["code_challenge"], [digest])
        self.assertEqual(exchange["auth"].username, "test-telegram-id")
        self.assertEqual(exchange["auth"].password, "test-telegram-secret")
        self.assertFalse(SocialToken.objects.exists())
        self.assertTrue(any(url.endswith("jwks.json") for _, url, _ in self.requests))

    def test_state_is_session_bound_and_single_use(self):
        self.link()
        state = self.start()["state"][0]
        stranger = Client()
        stranger.get(CALLBACK, {"state": state, "code": "mock-code"})
        self.assert_anonymous(stranger)
        self.callback("invalid")
        self.assert_anonymous()
        self.callback(state)
        self.client.post("/accounts/logout/")
        self.callback(state)
        self.assert_anonymous()

    def test_signed_tokens_require_claims_algorithm_signature_and_lifetime(self):
        self.link()
        original = self.claims.copy()
        cases = [
            {"iss": "https://attacker.invalid"},
            {"aud": "wrong"},
            {"exp": int(time.time()) - 1},
            {"sub": ""},
            {"sub": None},
            {"exp": None},
            {"iss": None},
            {"iat": None},
        ]
        for change in cases:
            with self.subTest(change=change):
                self.claims = {**original, **change}
                self.claims = {
                    key: value
                    for key, value in self.claims.items()
                    if value is not None
                }
                self.callback(self.start()["state"][0])
                self.assert_anonymous()
        self.claims = original
        self.signing_key = self.other_key
        self.callback(self.start()["state"][0])
        self.assert_anonymous()
        self.signing_key = "not-the-rsa-secret-at-least-32-bytes"
        self.algorithm = "HS256"
        self.callback(self.start()["state"][0])
        self.assert_anonymous()
        self.token_payload = {"access_token": "missing-id-token"}
        self.callback(self.start()["state"][0])
        self.assert_anonymous()

    @override_settings(
        AUTH_USERNAME_MODE="generated",
        ACCOUNT_SIGNUP_FIELDS=["email*"],
        ACCOUNT_LOGIN_METHODS={"email"},
    )
    def test_signup_asks_names_email_and_never_merges_by_claimed_email(self):
        self.claims.update(email=self.user.email, email_verified=True)
        response = self.callback(self.start()["state"][0])
        self.assertEqual(urlparse(response.url).path, "/accounts/3rdparty/signup/")
        form = self.client.get(response.url).context["form"]
        self.assertNotIn("password1", form.fields)
        self.assertTrue(form.fields["email"].required)
        self.assert_anonymous()
        self.assertFalse(SocialAccount.objects.exists())
        response = self.client.post(
            response.url,
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "new_telegram",
                "email": "newtelegram@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        new = get_user_model().objects.get(email="newtelegram@example.com")
        self.assertEqual(new.username, f"user_{new.pk.hex}")
        self.assertEqual(new.get_full_name(), "Иванова Анна")
        self.assertFalse(new.has_usable_password())
        self.assertFalse(EmailAddress.objects.get(user=new).verified)
        self.assertEqual(SocialAccount.objects.get(user=new).uid, self.claims["sub"])
        self.assert_anonymous()

    def test_mfa_is_required_after_telegram(self):
        self.link()
        TOTP.activate(self.user, TOTP_SECRET)
        response = self.callback(self.start()["state"][0])
        self.assertEqual(urlparse(response.url).path, "/accounts/2fa/authenticate/")
        self.assert_anonymous()

    def test_connect_conflict_and_disconnect_with_verified_email(self):
        self.password_login()
        response = self.callback(self.start(process="connect")["state"][0])
        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(provider="telegram")
        self.assertEqual(account.user, self.user)
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(
            self.user, backend="allauth.account.auth_backends.AuthenticationBackend"
        )
        self.recent_auth()
        response = self.client.post("/accounts/3rdparty/", {"account": account.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SocialAccount.objects.exists())
        other = self.create_user(username="bob", email="bob@example.com")
        SocialAccount.objects.create(
            user=other, provider="telegram", uid=self.claims["sub"]
        )
        self.callback(self.start(process="connect")["state"][0])
        self.assertFalse(SocialAccount.objects.filter(user=self.user).exists())

    def test_disabled_link_is_visible_and_removable_and_last_method_protected(self):
        account = self.link()
        self.password_login()
        with override_settings(TELEGRAM_LOGIN_ENABLED=False):
            self.assertContains(self.client.get("/accounts/3rdparty/"), "Telegram")
            self.assertEqual(self.client.post(LOGIN).status_code, 404)
            self.user.set_unusable_password()
            self.user.save()
            self.client.force_login(
                self.user, backend="allauth.account.auth_backends.AuthenticationBackend"
            )
            self.recent_auth()
            EmailAddress.objects.filter(user=self.user).update(verified=False)
            response = self.client.post("/accounts/3rdparty/", {"account": account.pk})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_transport_failure_and_cancel_show_retry(self):
        self.transport_failure = True
        self.assertContains(
            self.client.post(LOGIN), "Не удалось завершить вход", status_code=401
        )
        self.transport_failure = False
        state = self.start()["state"][0]
        self.client.get(CALLBACK, {"state": state, "error": "access_denied"})
        self.assert_anonymous()
        self.callback(state)
        self.assert_anonymous()
