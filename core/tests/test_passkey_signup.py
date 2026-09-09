"""Signup stages use a virtual device but the actual allauth/FIDO2 validation."""

import json
import re
from copy import deepcopy
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from tests.helpers import AccountTestCase
from tests.test_passkeys import VirtualPasskey


class PasskeySignupTests(AccountTestCase):
    def begin(self, next_url="/app/?from=signup"):
        response = self.client.post(
            "/accounts/signup/passkey/",
            {
                "username": "new_passkey",
                "email": "newpasskey@example.com",
                "next": next_url,
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 302, response.content)
        self.new_user = get_user_model().objects.get(username="new_passkey")
        self.assertFalse(self.new_user.has_usable_password())
        self.assertFalse(EmailAddress.objects.get(user=self.new_user).verified)
        self.assert_anonymous()
        code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
        response = self.client.post(response.url, {"code": code}, secure=True)
        self.assertEqual(urlparse(response.url).path, "/accounts/2fa/webauthn/signup/")
        self.assert_anonymous()
        response = self.client.get(response.url, secure=True)
        options = response.context["js_data"]["creation_options"]["publicKey"]
        self.assertEqual(options["authenticatorSelection"]["residentKey"], "required")
        self.assertEqual(
            options["authenticatorSelection"]["userVerification"], "required"
        )
        return options

    def finish(self, options, **kwargs):
        self.device = VirtualPasskey()
        credential = self.device.register(options, **kwargs)
        return self.client.post(
            "/accounts/2fa/webauthn/signup/",
            {
                "name": "My device",
                "credential": json.dumps(credential),
            },
            secure=True,
        )

    def test_full_signup_recovery_codes_show_once_continue_and_login(self):
        response = self.finish(self.begin())
        self.assertEqual(response.url, "/accounts/2fa/recovery-codes/")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertEqual(Authenticator.objects.filter(user=self.new_user).count(), 2)
        response = self.client.get(response.url)
        self.assertTrue(response.context["can_view_codes"])
        codes = response.context["unused_codes"]
        self.assertTrue(codes)
        self.assertContains(response, "Продолжить")
        response = self.client.get("/accounts/2fa/recovery-codes/")
        self.assertFalse(response.context["can_view_codes"])
        response = self.client.post("/accounts/signup/passkey/continue/")
        self.assertEqual(response.url, "/app/?from=signup")
        self.client.post("/accounts/logout/")
        options = self.client.get(
            "/accounts/2fa/webauthn/login/", secure=True, HTTP_ACCEPT="application/json"
        ).json()["request_options"]["publicKey"]
        credential = self.device.assert_login(options, self.new_user)
        self.client.post(
            "/accounts/2fa/webauthn/login/",
            {"credential": json.dumps(credential)},
            secure=True,
        )
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_signup_rejects_missing_uv_bad_origin_and_challenge(self):
        options = self.begin()
        for change in (
            {"verified": False},
            {"origin": "https://attacker.invalid"},
            {"challenge": "wrong"},
        ):
            with self.subTest(change=change):
                modified = deepcopy(options)
                if "challenge" in change:
                    modified["challenge"] = change["challenge"]
                    response = self.finish(modified)
                else:
                    response = self.finish(modified, **change)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assert_anonymous()
                self.assertFalse(
                    Authenticator.objects.filter(user=self.new_user).exists()
                )
                # Each failed render issues a fresh challenge for a retry.
                options = response.context["js_data"]["creation_options"]["publicKey"]

    def test_cancel_keeps_account_anonymous_and_verified_email_can_recover(self):
        self.begin()
        self.client.post("/accounts/logout/", {"next": "/accounts/login/"})
        self.assert_anonymous()
        self.assertTrue(get_user_model().objects.filter(pk=self.new_user.pk).exists())
        self.assertTrue(EmailAddress.objects.get(user=self.new_user).verified)
        self.client.post(
            "/accounts/login/code/", {"email": self.new_user.email, "channel": "email"}
        )
        code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
        self.client.post("/accounts/login/code/confirm/", {"code": code})
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_foreign_next_is_discarded_and_stage_cannot_be_skipped(self):
        response = self.client.get("/accounts/2fa/webauthn/signup/")
        self.assertEqual(response.status_code, 302)
        self.finish(self.begin("https://attacker.invalid/"))
        response = self.client.post("/accounts/signup/passkey/continue/")
        self.assertEqual(response.url, "/app/")
