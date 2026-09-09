"""Authentication switches must change behavior without bypassing account security."""

import json
import re
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, hotp_value
from allauth.socialaccount.models import SocialAccount
from accounts.services.capabilities import has_primary_login
from accounts.services.phones import set_phone, remove_phone
from tests.helpers import AccountTestCase, PASSWORD, LOGIN_CODE, TOTP_SECRET
from tests import test_accounts
from tests.test_passkeys import VirtualPasskey

PASSWORDLESS = {
    "AUTH_PASSWORD_MODE": "passwordless",
    "ACCOUNT_SIGNUP_FIELDS": ["username*", "email*", "phone"],
    "ACCOUNT_LOGIN_METHODS": {"email", "phone"},
}


def emailed_code():
    """Extract the generated numeric proof from the isolated in-memory outbox."""
    return re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()


def totp_code():
    """Generate the real current TOTP for the shared isolated authenticator seed."""
    return format_hotp_value(hotp_value(TOTP_SECRET, int(time.time()) // 30))


class PasswordPolicyTests(AccountTestCase):
    """Exercise required, optional and passwordless forms through the HTTP stack."""

    @override_settings(**PASSWORDLESS)
    def test_passwordless_uses_email_code_and_rejects_stale_password_post(self):
        """A hidden password must never authenticate or trigger unsolicited delivery."""
        response = self.client.get(reverse("account_login"))
        self.assertNotIn("password", response.context["form"].fields)
        response = self.password_login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assert_anonymous()
        response = self.client.post(
            reverse("account_login"), {"login": self.user.username}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(
            reverse("account_login"),
            {"login": self.user.email, "next": "/app/?email=yes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assert_anonymous()
        response = self.client.post(response.url, {"code": emailed_code()})
        self.assertEqual(response.url, "/app/?email=yes")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    @override_settings(**PASSWORDLESS)
    def test_passwordless_signup_creates_no_password_and_keeps_mfa_for_code_login(self):
        """Registration creates an unusable password and an enrolled factor stays mandatory."""
        response = self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "new",
                "email": "new@example.com",
            },
        )
        user = get_user_model().objects.get(username="new")
        self.assertFalse(user.has_usable_password())
        self.client.post(response.url, {"code": emailed_code()})
        self.client.logout()
        TOTP.activate(self.user, TOTP_SECRET)
        response = self.client.post(
            reverse("account_login"), {"login": self.user.email}
        )
        response = self.client.post(response.url, {"code": emailed_code()})
        self.assertEqual(response.url, reverse("mfa_authenticate"))
        self.assert_anonymous()
        self.client.post(response.url, {"code": totp_code()})
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    @override_settings(
        AUTH_PASSWORD_MODE="optional",
        ACCOUNT_SIGNUP_FIELDS=["username*", "email*", "password1", "password2"],
    )
    def test_optional_signup_accepts_empty_or_matching_passwords(self):
        """Optional registration validates supplied passwords and permits both empty fields."""
        for suffix, fields in (
            ("none", {}),
            ("password", {"password1": PASSWORD, "password2": PASSWORD}),
        ):
            with self.subTest(suffix=suffix):
                response = self.client.post(
                    reverse("account_signup"),
                    {
                        "first_name": "Анна",
                        "last_name": "Иванова",
                        "username": suffix,
                        "email": f"{suffix}@example.com",
                        **fields,
                    },
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    get_user_model().objects.get(username=suffix).has_usable_password(),
                    bool(fields),
                )
                self.client.logout()
        response = self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "mismatch",
                "email": "bad@example.com",
                "password1": PASSWORD,
                "password2": "different",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="mismatch").exists())

    def test_required_signup_rejects_missing_password(self):
        """The explicit required mode retains normal mandatory password registration."""
        response = self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "missing",
                "email": "missing@example.com",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="missing").exists())

    @override_settings(**PASSWORDLESS)
    def test_password_remains_available_for_reauthentication_and_reset(self):
        """Disabling primary password login must not block account recovery or reauth."""
        self.client.force_login(self.user)
        methods = get_adapter().get_reauthentication_methods(self.user)
        self.assertTrue(any(method["id"] == "reauthenticate" for method in methods))
        response = self.client.post(
            reverse("account_reauthenticate"), {"password": PASSWORD}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.get(reverse("account_change_password")).status_code, 200
        )
        self.client.logout()
        response = self.client.post(
            reverse("account_reset_password"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mail.outbox)

    @override_settings(**PASSWORDLESS)
    def test_explicit_remember_policy_applies_to_passwordless_email_login(self):
        """Configured browser-only and persistent sessions apply beyond password login."""
        for remember in (False, True):
            with (
                self.subTest(remember=remember),
                override_settings(ACCOUNT_SESSION_REMEMBER=remember),
            ):
                self.client.logout()
                response = self.client.post(
                    reverse("account_login"), {"login": self.user.email}
                )
                self.client.post(response.url, {"code": emailed_code()})
                self.assertEqual(self.client.get("/api/me/").status_code, 200)
                self.assertEqual(
                    self.client.session.get_expire_at_browser_close(), not remember
                )

    @override_settings(ACCOUNT_SESSION_REMEMBER=None, **PASSWORDLESS)
    def test_passwordless_remember_checkbox_survives_email_code_stage(self):
        """The visible remember choice controls the final OTP-authenticated session."""
        for remember in (False, True):
            with self.subTest(remember=remember):
                self.client.logout()
                response = self.client.post(
                    reverse("account_login"),
                    {"login": self.user.email, "remember": "on" if remember else ""},
                )
                self.client.post(response.url, {"code": emailed_code()})
                self.assertEqual(self.client.get("/api/me/").status_code, 200)
                self.assertEqual(
                    self.client.session.get_expire_at_browser_close(), not remember
                )


class FeatureStageTests(AccountTestCase):
    """Configuration changes cannot complete a pending login using a disabled method."""

    def test_closed_signup_blocks_new_accounts_but_allows_existing_confirmation(self):
        """An account already awaiting confirmation survives closing new registrations."""
        response = self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "pending",
                "email": "pending@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        code = emailed_code()
        with override_settings(AUTH_SIGNUP_ENABLED=False):
            for path in (
                "/accounts/signup/",
                "/accounts/signup/passkey/",
                "/accounts/3rdparty/signup/",
            ):
                for method in (self.client.get, self.client.post):
                    self.assertEqual(method(path).status_code, 404)
            response = self.client.post(response.url, {"code": code})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_disabled_channels_reject_requests_and_an_issued_email_code(self):
        """Disabling delivery also invalidates codes issued while it was enabled."""
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=LOGIN_CODE,
        ):
            self.client.post(
                reverse("account_request_login_code"), {"email": self.user.email}
            )
        sent = len(mail.outbox)
        with override_settings(
            EMAIL_CODE_LOGIN_ENABLED=False, PHONE_LOGIN_ENABLED=False
        ):
            for channel in ("email", "telegram"):
                self.assertEqual(
                    self.client.get(
                        reverse("account_request_login_code"), {"channel": channel}
                    ).status_code,
                    404,
                )
                self.assertEqual(
                    self.client.post(
                        reverse("account_request_login_code"),
                        {"channel": channel, "email": self.user.email},
                    ).status_code,
                    404,
                )
            response = self.client.post(
                reverse("account_confirm_login_code"), {"code": LOGIN_CODE}
            )
            self.assertEqual(response.status_code, 302)
            self.assertNotIn("account_login", self.client.session)
            self.assert_anonymous()
            self.assertEqual(len(mail.outbox), sent)

    def test_password_disabled_between_primary_login_and_mfa_cannot_finish(self):
        """A password proof from the previous policy cannot finish its pending MFA stage."""
        TOTP.activate(self.user, TOTP_SECRET)
        self.assertEqual(self.password_login().url, reverse("mfa_authenticate"))
        with override_settings(**PASSWORDLESS):
            response = self.client.post(
                reverse("mfa_authenticate"), {"code": totp_code()}
            )
            self.assertEqual(response.url, reverse("account_login"))
            self.assertNotIn("account_login", self.client.session)
            self.assert_anonymous()

    def test_password_disabled_while_waiting_for_phone_verification_cannot_finish(self):
        """Phone verification cannot complete a password flow disabled after issuance."""
        set_phone(self.user, "+380501234567", False)
        with (
            patch("accounts.telegram.TelegramGatewayClient.send_verification_code"),
            patch(
                "accounts.adapters.AccountAdapter.generate_phone_verification_code",
                return_value=LOGIN_CODE,
            ),
        ):
            response = self.password_login()
        self.assertEqual(response.url, reverse("account_verify_phone"))
        with override_settings(**PASSWORDLESS):
            self.client.post(response.url, {"code": LOGIN_CODE})
            self.assertNotIn("account_login", self.client.session)
            self.assert_anonymous()

    @override_settings(ACCOUNT_PHONE_VERIFICATION_TIMEOUT=120)
    def test_direct_gateway_client_uses_configured_code_ttl(self):
        """Legacy direct client calls use the same timeout as allauth phone proofs."""
        from accounts.telegram import TelegramGatewayClient

        with patch("accounts.integrations.telegram_gateway.requests.post") as post:
            post.return_value.json.return_value = {
                "ok": True,
                "result": {"request_id": "test"},
            }
            TelegramGatewayClient().send_verification_code("+380501234567", LOGIN_CODE)
        self.assertEqual(post.call_args.kwargs["json"]["ttl"], 120)

    def test_email_disabled_between_code_and_mfa_cannot_finish(self):
        """An email code that passed verification cannot bypass a later feature switch."""
        TOTP.activate(self.user, TOTP_SECRET)
        response = self.client.post(
            reverse("account_request_login_code"), {"email": self.user.email}
        )
        self.client.post(response.url, {"code": emailed_code()})
        with override_settings(EMAIL_CODE_LOGIN_ENABLED=False):
            self.client.post(reverse("mfa_authenticate"), {"code": totp_code()})
            self.assertNotIn("account_login", self.client.session)
            self.assert_anonymous()

    def test_disabled_provider_cannot_finish_mfa_or_oauth_callback(self):
        """Existing provider proof and direct callbacks are both rejected after disabling it."""
        TOTP.activate(self.user, TOTP_SECRET)
        response = test_accounts.SocialLoginTests.callback(self)
        self.assertEqual(response.url, reverse("mfa_authenticate"))
        with override_settings(GOOGLE_LOGIN_ENABLED=False):
            self.client.post(reverse("mfa_authenticate"), {"code": totp_code()})
            self.assert_anonymous()
            self.assertNotIn("account_login", self.client.session)
            self.assertEqual(
                self.client.get(
                    reverse("google_callback"), {"code": "old", "state": "old"}
                ).status_code,
                404,
            )

    def test_passkey_signup_switch_during_email_verification_does_not_skip_key(self):
        """Removing the native optional stage must never authenticate a keyless signup."""
        response = self.client.post(
            "/accounts/signup/passkey/",
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "username": "pendingkey",
                "email": "pendingkey@example.com",
            },
        )
        code = emailed_code()
        with override_settings(MFA_PASSKEY_SIGNUP_ENABLED=False):
            response = self.client.post(response.url, {"code": code})
            self.assertEqual(response.url, reverse("mfa_signup_webauthn"))
            self.assertTrue(
                EmailAddress.objects.get(email="pendingkey@example.com").verified
            )
            self.assert_anonymous()
            self.assertEqual(self.client.get(response.url).status_code, 404)
            self.assertNotIn("account_login", self.client.session)

    def test_disabled_enrollment_keeps_existing_totp_authentication(self):
        """Enrollment switches do not remove validation or management of existing factors."""
        TOTP.activate(self.user, TOTP_SECRET)
        self.password_login()
        with override_settings(
            MFA_TOTP_ENROLLMENT_ENABLED=False, MFA_PASSKEY_ENROLLMENT_ENABLED=False
        ):
            self.client.post(reverse("mfa_authenticate"), {"code": totp_code()})
            self.assertEqual(self.client.get("/api/me/").status_code, 200)
            for path in (reverse("mfa_activate_totp"), reverse("mfa_add_webauthn")):
                self.assertEqual(self.client.get(path).status_code, 404)
                self.assertEqual(self.client.post(path).status_code, 404)
            self.assertEqual(
                self.client.get(reverse("mfa_list_webauthn")).status_code, 200
            )
            self.assertEqual(
                self.client.get(reverse("mfa_deactivate_totp")).status_code, 200
            )

    def test_disabled_provider_invalidates_pending_social_signup(self):
        """Provider availability is rechecked on the separate social signup form."""
        with override_settings(SOCIALACCOUNT_AUTO_SIGNUP=False):
            response = test_accounts.SocialLoginTests.callback(self, linked=False)
        self.assertIn("socialaccount_sociallogin", self.client.session)
        with override_settings(GOOGLE_LOGIN_ENABLED=False):
            response = self.client.post(
                response.url,
                {
                    "first_name": "Анна",
                    "last_name": "Иванова",
                    "username": "newgoogle",
                    "email": "newgoogle@example.com",
                },
            )
            self.assertEqual(response.url, reverse("account_login"))
            self.assertNotIn("socialaccount_sociallogin", self.client.session)
            self.assertFalse(
                get_user_model().objects.filter(username="newgoogle").exists()
            )
            self.assert_anonymous()

    def test_disabled_enrollment_invalidates_a_suspended_post_before_native_resume(
        self,
    ):
        """Native reauth must not replay a POST directly into a disabled enrollment view."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("mfa_add_webauthn"), {"name": "Pending", "credential": "{}"}
        )
        self.assertIn("account_reauthentication_state", self.client.session)
        with override_settings(MFA_PASSKEY_ENROLLMENT_ENABLED=False):
            with patch(
                "allauth.mfa.webauthn.forms.AddWebAuthnForm.clean",
                side_effect=AssertionError("Disabled enrollment must not validate"),
            ):
                response = self.client.post(response.url, {"password": PASSWORD})
            self.assertEqual(response.url, reverse("core_account_overview"))
            self.assertNotIn("account_reauthentication_state", self.client.session)
            self.assertFalse(Authenticator.objects.filter(user=self.user).exists())

    def test_disabled_provider_invalidates_delayed_connect_after_email_reauth(self):
        """The serialized native connect callback cannot outlive provider availability."""
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_login(self.user)
        session = self.client.session
        session["account_authentication_methods"] = [
            {"method": "code", "at": time.time(), "email": self.user.email}
        ]
        session.save()

        def age_authentication():
            """Simulate a callback arriving after the initial reauth window expired."""
            session = self.client.session
            session["account_authentication_methods"][-1]["at"] = time.time() - 301
            session.save()

        response = test_accounts.SocialLoginTests.callback(
            self,
            provider="github",
            linked=False,
            process="connect",
            before_callback=age_authentication,
        )
        self.assertIn("account_reauthentication_state", self.client.session)
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=LOGIN_CODE,
        ):
            self.client.post(response.url, {"action": "request"})
        with override_settings(GITHUB_LOGIN_ENABLED=False):
            response = self.client.post(
                response.url, {"action": "verify", "code": LOGIN_CODE}
            )
            self.assertEqual(response.url, reverse("core_account_overview"))
            self.assertNotIn("account_reauthentication_state", self.client.session)
            self.assertFalse(
                SocialAccount.objects.filter(user=self.user, provider="github").exists()
            )

    def test_closed_signup_still_allows_existing_login_and_authenticated_connect(self):
        """The registration switch applies only to creation of new identities."""
        with override_settings(AUTH_SIGNUP_ENABLED=False):
            self.assertEqual(
                test_accounts.SocialLoginTests.callback(self).status_code, 302
            )
            self.assertEqual(self.client.get("/api/me/").status_code, 200)
            self.assertEqual(
                test_accounts.SocialLoginTests.callback(
                    self, provider="github", linked=False, process="connect"
                ).status_code,
                302,
            )
            self.assertTrue(
                SocialAccount.objects.filter(user=self.user, provider="github").exists()
            )


class PrimaryMethodRemovalTests(AccountTestCase):
    """Account changes count enabled primary methods rather than installed credentials."""

    def test_disabled_email_and_password_reauth_do_not_allow_last_social_removal(self):
        """A stored password and enrolled TOTP are not substitutes for enabled primary login."""
        self.password_login()
        account = SocialAccount.objects.create(
            user=self.user, provider="google", uid="primary"
        )
        TOTP.activate(self.user, TOTP_SECRET)
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless", EMAIL_CODE_LOGIN_ENABLED=False
        ):
            response = self.client.post(
                reverse("socialaccount_connections"), {"account": account.pk}
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())
            self.assertFalse(has_primary_login(self.user, exclude_social=account.pk))
            self.assertTrue(has_primary_login(self.user))

    def test_disabled_provider_is_not_a_fallback_but_verified_email_is(self):
        """A disabled saved connection stays removable once a real fallback is available."""
        self.password_login()
        google = SocialAccount.objects.create(
            user=self.user, provider="google", uid="primary"
        )
        SocialAccount.objects.create(user=self.user, provider="github", uid="disabled")
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless",
            EMAIL_CODE_LOGIN_ENABLED=False,
            GITHUB_LOGIN_ENABLED=False,
        ):
            self.client.post(
                reverse("socialaccount_connections"), {"account": google.pk}
            )
            self.assertTrue(SocialAccount.objects.filter(pk=google.pk).exists())
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless", GITHUB_LOGIN_ENABLED=False
        ):
            self.client.post(
                reverse("socialaccount_connections"), {"account": google.pk}
            )
            self.assertFalse(SocialAccount.objects.filter(pk=google.pk).exists())

    def test_last_passkey_cannot_be_removed_until_another_primary_is_available(self):
        """Use a real enrolled key to verify removal guard and disabled-enrollment management."""
        self.password_login()
        device = VirtualPasskey()
        response = self.client.get(reverse("mfa_add_webauthn"), secure=True)
        options = response.context["js_data"]["creation_options"]["publicKey"]
        self.client.post(
            reverse("mfa_add_webauthn"),
            {"name": "Only key", "credential": json.dumps(device.register(options))},
            secure=True,
        )
        key = Authenticator.objects.get(
            user=self.user, type=Authenticator.Type.WEBAUTHN
        )
        url = reverse("mfa_remove_webauthn", kwargs={"pk": key.pk})
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless",
            EMAIL_CODE_LOGIN_ENABLED=False,
            MFA_PASSKEY_ENROLLMENT_ENABLED=False,
        ):
            self.client.post(url)
            self.assertTrue(Authenticator.objects.filter(pk=key.pk).exists())
        self.client.post(url)
        self.assertFalse(Authenticator.objects.filter(pk=key.pk).exists())

    def test_last_verified_email_and_phone_are_protected(self):
        """Removing an enabled final contact cannot strand a passwordless account."""
        with override_settings(AUTH_PASSWORD_MODE="passwordless"):
            address = EmailAddress.objects.get(user=self.user)
            self.assertFalse(get_adapter().can_delete_email(address))
        contact = set_phone(self.user, "+380501234567", True)
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless", EMAIL_CODE_LOGIN_ENABLED=False
        ):
            with self.assertRaises(ValidationError):
                remove_phone(self.user, contact.pk)
            self.user.refresh_from_db()
            self.assertTrue(self.user.phone_numbers.get(pk=contact.pk).verified)

    @override_settings(**PASSWORDLESS)
    def test_email_removal_uses_fresh_contact_state_after_waiting_for_account_lock(
        self,
    ):
        """A concurrent phone removal cannot leave the email guard using a stale user."""
        contact = set_phone(self.user, "+380501234567", True)
        self.client.force_login(self.user)
        session = self.client.session
        session["account_authentication_methods"] = [
            {"method": "password", "at": time.time(), "reauthenticated": True}
        ]
        session.save()
        user_model = get_user_model()
        select_for_update = user_model.objects.select_for_update

        def remove_phone_before_acquiring_lock(*args, **kwargs):
            """Model the committed phone removal while this request waits for its lock."""
            self.user.phone_numbers.all().delete()
            return select_for_update(*args, **kwargs)

        with patch.object(
            user_model.objects,
            "select_for_update",
            side_effect=remove_phone_before_acquiring_lock,
        ):
            self.client.post(
                reverse("account_email"),
                {"action_remove": "", "email": self.user.email},
            )
        self.assertTrue(
            EmailAddress.objects.filter(user=self.user, verified=True).exists()
        )
