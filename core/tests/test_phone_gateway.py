"""Telegram delivery failures and verified phone ownership boundaries."""

import time
from unittest.mock import patch

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from accounts.adapters import AccountAdapter, MFAAdapter
from accounts.telegram import TelegramDeliveryError, TelegramGatewayClient
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import TOTP

from tests.helpers import AccountTestCase, LOGIN_CODE, PASSWORD, TOTP_SECRET


class TelegramGatewayTests(SimpleTestCase):
    @patch("accounts.integrations.telegram_gateway.requests.post")
    def test_exact_gateway_payload_and_timeout(self, post):
        post.return_value.json.return_value = {
            "ok": True,
            "result": {"request_id": "request-123"},
        }
        result = TelegramGatewayClient().send_verification_code(
            "+12025550123", LOGIN_CODE
        )
        self.assertEqual(result, "request-123")
        post.assert_called_once_with(
            "https://gatewayapi.telegram.org/sendVerificationMessage",
            headers={"Authorization": f"Bearer {settings.TELEGRAM_GATEWAY_TOKEN}"},
            json={"phone_number": "+12025550123", "code": LOGIN_CODE, "ttl": 300},
            timeout=settings.TELEGRAM_GATEWAY_TIMEOUT,
            allow_redirects=False,
        )

    @patch("accounts.integrations.telegram_gateway.requests.post")
    def test_provider_network_http_and_bad_json_fail_closed_without_secrets(self, post):
        failures = [
            requests.Timeout("secret-token +12025550123 834719"),
            requests.HTTPError("secret-token +12025550123 834719"),
            ValueError("secret-token +12025550123 834719"),
        ]
        for error in failures:
            with self.subTest(error=type(error).__name__):
                post.side_effect = error
                with self.assertRaises(TelegramDeliveryError) as caught:
                    TelegramGatewayClient().send_verification_code(
                        "+12025550123", LOGIN_CODE
                    )
                self.assertNotIn("secret-token", str(caught.exception))
                self.assertNotIn(LOGIN_CODE, str(caught.exception))
                self.assertNotIn("+12025550123", str(caught.exception))
        post.side_effect = None
        for payload in (
            {"ok": False},
            [],
            {"ok": True},
            {"ok": True, "result": {"request_id": 1}},
        ):
            with self.subTest(payload=payload):
                post.return_value.json.return_value = payload
                with self.assertRaises(TelegramDeliveryError):
                    TelegramGatewayClient().send_verification_code(
                        "+12025550123", LOGIN_CODE
                    )

    @patch("accounts.integrations.telegram_gateway.requests.post")
    def test_disabled_gateway_and_invalid_codes_do_not_send(self, post):
        with override_settings(PHONE_LOGIN_ENABLED=False):
            with self.assertRaises(TelegramDeliveryError):
                TelegramGatewayClient().send_verification_code(
                    "+12025550123", LOGIN_CODE
                )
        for code in ("", "12345", "1234567", "ABC123", "１２３４５６"):
            with self.subTest(code=code), self.assertRaises(TelegramDeliveryError):
                TelegramGatewayClient().send_verification_code("+12025550123", code)
        with self.assertRaises(TelegramDeliveryError):
            TelegramGatewayClient().send_verification_code("2025550123", LOGIN_CODE)
        post.assert_not_called()


class PhoneOwnershipTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.adapter = AccountAdapter()

    def test_e164_is_trimmed_and_ambiguous_or_invalid_numbers_are_rejected(self):
        self.assertEqual(self.adapter.clean_phone("  +12025550123  "), "+12025550123")
        for number in (
            "2025550123",
            "+02025550123",
            "+1 202 555 0123",
            "+123",
            "+" + "1" * 16,
        ):
            with self.subTest(number=number), self.assertRaises(ValidationError):
                self.adapter.clean_phone(number)

    def test_duplicate_phone_fails_without_overwriting_existing_owner(self):
        self.adapter.set_phone(self.user, "+12025550123", True)
        second = self.create_user(username="bob", email="bob@example.com")
        self.adapter.set_phone(second, "+12025550124", True)
        with self.assertRaises(ValidationError):
            self.adapter.set_phone(second, "+12025550123", True)
        self.user.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.assertEqual(second.phone, "+12025550124")
        self.assertTrue(second.phone_verified)
        with self.assertRaises(IntegrityError), transaction.atomic():
            type(self.user).objects.filter(pk=second.pk).update(phone=self.user.phone)

    def test_missing_phone_cannot_be_marked_verified_and_empty_is_not_stored(self):
        self.adapter.set_phone(self.user, "", True)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.phone)
        self.assertFalse(self.user.phone_verified)
        with self.assertRaises(IntegrityError), transaction.atomic():
            type(self.user).objects.filter(pk=self.user.pk).update(phone_verified=True)

    def test_signup_collision_after_form_check_rolls_back_partial_user(self):
        self.adapter.set_phone(self.user, "+12025550123", True)
        # Simulate the form's availability check finishing before another request
        # commits ownership; the real DB uniqueness constraint must stop the write.
        with patch(
            "accounts.adapters.AccountAdapter.get_user_by_phone", return_value=None
        ):
            response = self.client.post(
                reverse("account_signup"),
                {
                    "first_name": "Анна",
                    "last_name": "Иванова",
                    "username": "racing-signup",
                    "email": "race@example.com",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                    "phone": self.user.phone,
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_signup"))
        self.assertFalse(
            type(self.user).objects.filter(username="racing-signup").exists()
        )
        self.assertFalse(EmailAddress.objects.filter(email="race@example.com").exists())
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.assertTrue(self.user.phone_verified)
        self.assert_anonymous()

    def test_confirmation_collision_after_form_check_preserves_both_owners(self):
        self.adapter.set_phone(self.user, "+12025550123", True)
        self.password_login()
        with (
            patch(
                "accounts.adapters.AccountAdapter.generate_phone_verification_code",
                return_value=LOGIN_CODE,
            ),
            patch(
                "accounts.telegram.TelegramGatewayClient.send_verification_code",
                return_value="request-123",
            ),
        ):
            self.client.post(reverse("account_change_phone"), {"phone": "+12025550124"})
        winner = self.create_user(username="winner", email="winner@example.com")
        self.adapter.set_phone(winner, "+12025550124", True)
        with patch(
            "accounts.adapters.AccountAdapter.get_user_by_phone", return_value=None
        ):
            response = self.client.post(
                reverse("account_verify_phone"), {"code": LOGIN_CODE}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_change_phone"))
        self.assertNotIn("account_phone_verification", self.client.session)
        self.user.refresh_from_db()
        winner.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.assertEqual(winner.phone, "+12025550124")
        self.assertTrue(self.user.phone_verified)
        self.assertTrue(winner.phone_verified)

    @patch(
        "accounts.adapters.AccountAdapter.generate_phone_verification_code",
        return_value=LOGIN_CODE,
    )
    @patch(
        "accounts.telegram.TelegramGatewayClient.send_verification_code",
        return_value="request-123",
    )
    def test_phone_replacement_keeps_old_number_until_new_one_is_verified(
        self, send, generate
    ):
        self.adapter.set_phone(self.user, "+12025550123", True)
        self.password_login()
        response = self.client.post(
            reverse("account_change_phone"), {"phone": "+12025550124"}
        )
        self.assertEqual(response.status_code, 302)
        send.assert_called_once_with("+12025550124", LOGIN_CODE, ttl=300)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.client.post(reverse("account_verify_phone"), {"code": "000000"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.client.post(reverse("account_verify_phone"), {"code": LOGIN_CODE})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550124")
        self.assertTrue(self.user.phone_verified)


class PhoneLoginTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        AccountAdapter().set_phone(self.user, "+12025550123", True)

    def request_code(self, phone="+12025550123", failure=None):
        with (
            patch(
                "accounts.adapters.AccountAdapter.generate_phone_verification_code",
                return_value=LOGIN_CODE,
            ),
            patch(
                "accounts.telegram.TelegramGatewayClient.send_verification_code",
                return_value="request-123",
                side_effect=failure,
            ) as send,
        ):
            response = self.client.post(
                reverse("account_request_login_code"), {"phone": phone}
            )
        return response, send

    def confirm(self, code=LOGIN_CODE):
        return self.client.post(reverse("account_confirm_login_code"), {"code": code})

    def test_issued_code_cannot_restore_changed_or_removed_phone(self):
        from django.core.cache import cache

        for replacement in ("+12025550124", None):
            with self.subTest(replacement=replacement):
                cache.clear()
                self.client = Client()
                AccountAdapter().set_phone(self.user, "+12025550123", True)
                self.request_code()
                AccountAdapter().set_phone(self.user, replacement, bool(replacement))
                self.confirm()
                self.assert_anonymous()
                self.user.refresh_from_db()
                self.assertEqual(self.user.phone, replacement)

    def test_issued_code_cannot_reclaim_a_reassigned_phone(self):
        self.request_code()
        AccountAdapter().set_phone(self.user, "+12025550124", True)
        new_owner = self.create_user(
            username="new-owner", email="new-owner@example.com"
        )
        AccountAdapter().set_phone(new_owner, "+12025550123", True)
        self.confirm()
        self.assert_anonymous()
        self.user.refresh_from_db()
        new_owner.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550124")
        self.assertEqual(new_owner.phone, "+12025550123")

    def test_gateway_disabled_after_issuance_blocks_confirmation_and_resend(self):
        from django.core.cache import cache

        for action in ("verify", "resend"):
            with self.subTest(action=action):
                cache.clear()
                self.client = Client()
                self.request_code()
                with (
                    override_settings(PHONE_LOGIN_ENABLED=False),
                    patch(
                        "accounts.telegram.TelegramGatewayClient.send_verification_code"
                    ) as send,
                ):
                    payload = (
                        {"code": LOGIN_CODE}
                        if action == "verify"
                        else {"action": "resend"}
                    )
                    self.client.post(reverse("account_confirm_login_code"), payload)
                send.assert_not_called()
                self.assert_anonymous()
                self.user.refresh_from_db()
                self.assertEqual(self.user.phone, "+12025550123")

    def test_valid_phone_otp_enters_session_and_cannot_be_replayed(self):
        response, send = self.request_code()
        self.assertEqual(response.status_code, 302)
        send.assert_called_once_with(self.user.phone, LOGIN_CODE, ttl=300)
        self.assert_anonymous()
        self.confirm()
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))
        self.confirm()
        self.assert_anonymous()

    def test_empty_expired_and_exhausted_codes_cannot_authenticate(self):
        self.request_code()
        self.confirm("")
        self.assert_anonymous()
        with patch(
            "allauth.account.internal.flows.code_verification.time.time",
            return_value=time.time() + 301,
        ):
            self.confirm()
        self.assert_anonymous()
        self.request_code()
        for _ in range(3):
            self.confirm("000000")
        self.confirm()
        self.assert_anonymous()

    def test_unknown_unverified_and_inactive_numbers_are_not_sent_codes(self):
        for field, value in (
            (None, None),
            ("phone_verified", False),
            ("is_active", False),
        ):
            with self.subTest(field=field):
                self.user.is_active = True
                self.user.phone_verified = True
                if field:
                    setattr(self.user, field, value)
                self.user.save(update_fields=["is_active", "phone_verified"])
                response, send = self.request_code(
                    "+12025550999" if field is None else self.user.phone
                )
                self.assertEqual(response.status_code, 302)
                send.assert_not_called()
                self.confirm()
                self.assert_anonymous()

    def test_provider_failure_creates_no_successful_login_and_keeps_ownership(self):
        response, _ = self.request_code(
            failure=TelegramDeliveryError("transport_failure")
        )
        self.assertEqual(response.status_code, 302)
        self.confirm()
        self.assert_anonymous()
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+12025550123")
        self.assertTrue(self.user.phone_verified)

    def test_phone_otp_still_requires_email_verification_and_mfa(self):
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.request_code()
        self.confirm()
        self.assert_anonymous()
        self.client.session.flush()
        EmailAddress.objects.filter(user=self.user).update(verified=True)
        TOTP.activate(self.user, TOTP_SECRET)
        self.request_code()
        response = self.confirm()
        self.assertEqual(response.url, reverse("mfa_authenticate"))
        self.assert_anonymous()


class MFAEncryptionTests(SimpleTestCase):
    def test_wrong_key_or_cleartext_never_decrypts_as_valid_secret(self):
        from cryptography.fernet import Fernet

        adapter = MFAAdapter()
        encrypted = adapter.encrypt("test-authenticator-secret")
        with override_settings(MFA_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertRaises(ImproperlyConfigured):
                adapter.decrypt(encrypted)
        with self.assertRaises(ImproperlyConfigured):
            adapter.decrypt("test-authenticator-secret")
