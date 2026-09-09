"""Multi-phone ownership, native OTP flows and configuration-dependent login."""

import time
import re
from contextlib import contextmanager
from unittest.mock import patch
from uuid import UUID, uuid4

from django.core.cache import cache
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.urls import reverse
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, hotp_value

from accounts.adapters import AccountAdapter
from accounts.models import PhoneNumber, User
from accounts.services.capabilities import has_primary_login
from accounts.services.phones import (
    add_phone,
    confirm_phone,
    remove_phone,
    set_phone,
    set_primary_phone,
)
from accounts.telegram import TelegramDeliveryError
from tests.helpers import AccountTestCase, LOGIN_CODE, PASSWORD, TOTP_SECRET

FIRST = "+12025550123"
SECOND = "+12025550124"


@contextmanager
def gateway_codes(code=LOGIN_CODE, failure=None):
    """Keep all phone tests independent of network delivery and random OTP values."""
    with (
        patch(
            "accounts.adapters.AccountAdapter.generate_phone_verification_code",
            return_value=code,
        ),
        patch(
            "accounts.telegram.TelegramGatewayClient.send_verification_code",
            return_value="test-request",
            side_effect=failure,
        ) as send,
    ):
        yield send


class PhoneManagementTests(AccountTestCase):
    """Exercise contact management through the actual authenticated Django endpoints."""

    def setUp(self):
        """Authenticate recently so management tests exercise the intended action."""
        super().setUp()
        self.password_login()

    def add(self, phone=FIRST):
        """Submit the current server form with isolated Gateway delivery."""
        cache.clear()
        with gateway_codes() as send:
            response = self.client.post(
                reverse("account_change_phone"), {"phone": phone}
            )
        return response, send

    def verify(self, code=LOGIN_CODE):
        """Complete the currently bound native phone verification process."""
        return self.client.post(reverse("account_verify_phone"), {"code": code})

    def test_first_confirmation_becomes_primary_and_next_preserves_it(self):
        """Confirmation adds a contact; it never replaces the current primary."""
        response, send = self.add()
        self.assertEqual(response.url, reverse("account_verify_phone"))
        send.assert_called_once_with(FIRST, LOGIN_CODE, ttl=300)
        first = self.user.phone_numbers.get(phone=FIRST)
        self.assertIsInstance(first.pk, UUID)
        self.assertFalse(first.verified)
        self.verify("000000")
        first.refresh_from_db()
        self.assertFalse(first.verified)
        self.verify()
        first.refresh_from_db()
        self.assertTrue(first.primary and first.verified)
        self.add(SECOND)
        self.verify()
        second = self.user.phone_numbers.get(phone=SECOND)
        self.assertTrue(second.verified)
        self.assertFalse(second.primary)
        self.assertTrue(self.user.phone_numbers.get(pk=first.pk).primary)
        response = self.client.get(reverse("account_change_phone"))
        self.assertContains(response, FIRST)
        self.assertContains(response, SECOND)
        self.assertContains(response, "2 / 5")

    def test_primary_requires_verification_and_explicit_replacement_before_delete(self):
        """The user chooses the replacement rather than relying on ordering."""
        first = set_phone(self.user, FIRST, True)
        second = add_phone(self.user, SECOND)
        self.client.post(reverse("core_primary_phone", args=[second.pk]))
        self.assertTrue(self.user.phone_numbers.get(pk=first.pk).primary)
        confirm_phone(self.user, second.pk)
        self.client.post(reverse("core_remove_phone", args=[first.pk]))
        self.assertTrue(self.user.phone_numbers.filter(pk=first.pk).exists())
        self.client.post(reverse("core_primary_phone", args=[second.pk]))
        self.client.post(reverse("core_remove_phone", args=[first.pk]))
        self.assertFalse(self.user.phone_numbers.filter(pk=first.pk).exists())
        self.assertTrue(self.user.phone_numbers.get(pk=second.pk).primary)
        self.client.post(reverse("core_remove_phone", args=[second.pk]))
        self.assertFalse(self.user.phone_numbers.exists())

    def test_limit_includes_pending_contacts_and_lowering_it_does_not_delete(self):
        """Changing a limit blocks additions while leaving existing records usable."""
        for index in range(5):
            add_phone(self.user, f"+1202555020{index}")
        response, send = self.add()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Достигнут лимит")
        send.assert_not_called()
        with override_settings(AUTH_MAX_PHONE_NUMBERS=2):
            response = self.client.get(reverse("account_change_phone"))
            self.assertContains(response, "5 / 2")
            self.assertEqual(self.user.phone_numbers.count(), 5)
            self.add(SECOND)
        self.assertEqual(self.user.phone_numbers.count(), 5)

    def test_pending_contacts_do_not_reserve_a_number_and_verified_owner_is_unique(
        self,
    ):
        """Only a successful proof establishes exclusive cross-account ownership."""
        second_user = self.create_user("bob", "bob@example.com")
        one = add_phone(self.user, FIRST)
        two = add_phone(second_user, FIRST)
        confirm_phone(second_user, two.pk)
        with self.assertRaises(ValidationError):
            confirm_phone(self.user, one.pk)
        self.assertFalse(self.user.phone_numbers.get(pk=one.pk).verified)
        self.assertTrue(second_user.phone_numbers.get(pk=two.pk).verified)
        with override_settings(AUTH_PHONE_LOGIN_MODE="primary_only"):
            additional = set_phone(second_user, SECOND, True)
            self.assertFalse(additional.primary)
            self.assertEqual(
                AccountAdapter().get_user_by_phone(SECOND).pk, second_user.pk
            )

    def test_confirmation_race_never_overwrites_existing_contacts(self):
        """The database/service check still protects ownership if the form check races."""
        first = set_phone(self.user, FIRST, True)
        self.add(SECOND)
        winner = self.create_user("winner", "winner@example.com")
        set_phone(winner, SECOND, True)
        with patch(
            "accounts.adapters.AccountAdapter.get_user_by_phone", return_value=None
        ):
            response = self.verify()
        self.assertEqual(response.url, reverse("account_change_phone"))
        self.assertNotIn("account_phone_verification", self.client.session)
        self.assertTrue(self.user.phone_numbers.get(pk=first.pk).primary)
        self.assertFalse(self.user.phone_numbers.get(phone=SECOND).verified)
        self.assertTrue(winner.phone_numbers.get(phone=SECOND).verified)

    def test_duplicate_and_invalid_numbers_are_rejected_and_db_constraints_hold(self):
        """Domain validation and persisted invariants guard every write path."""
        first = set_phone(self.user, FIRST, True)
        for phone in (
            FIRST,
            "2025550123",
            "+02025550123",
            "+1 202 555 0123",
            "+123",
            "+" + "1" * 16,
        ):
            with self.subTest(phone=phone):
                response, send = self.add(phone)
                self.assertEqual(response.status_code, 200)
                send.assert_not_called()
        second = add_phone(self.user, SECOND)
        for changes in (
            {"primary": True},
            {"phone": ""},
            {"phone": FIRST},
            {"primary": True, "verified": True},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                PhoneNumber.objects.filter(pk=second.pk).update(**changes)
        other = self.create_user("other", "other@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            PhoneNumber.objects.create(user=other, phone=first.phone, verified=True)

    def test_delivery_failure_keeps_pending_contact_and_allows_retry(self):
        """Delivery outages do not remove contacts or falsely mark them verified."""
        with gateway_codes(failure=TelegramDeliveryError("transport_failure")):
            response = self.client.post(
                reverse("account_change_phone"), {"phone": FIRST}
            )
        self.assertEqual(response.url, reverse("account_change_phone"))
        contact = self.user.phone_numbers.get(phone=FIRST)
        self.assertFalse(contact.verified)
        with gateway_codes():
            cache.clear()
            response = self.client.post(reverse("core_verify_phone", args=[contact.pk]))
        self.assertEqual(response.url, reverse("account_verify_phone"))
        self.verify()
        self.assertTrue(self.user.phone_numbers.get(pk=contact.pk).verified)

    def test_resend_replaces_code_and_cancel_invalidates_process(self):
        """Native resend limits and ordinary server POSTs remain functional."""
        self.add()
        cache.clear()
        with gateway_codes("123456") as send:
            response = self.client.post(
                reverse("account_verify_phone"), {"action": "resend"}
            )
        self.assertEqual(response.status_code, 302)
        send.assert_called_once()
        self.verify(LOGIN_CODE)
        self.assertFalse(self.user.phone_numbers.get(phone=FIRST).verified)
        self.verify("123456")
        self.assertTrue(self.user.phone_numbers.get(phone=FIRST).verified)
        self.add(SECOND)
        self.client.post(reverse("account_verify_phone"), {"action": "cancel"})
        self.verify()
        self.assertFalse(self.user.phone_numbers.get(phone=SECOND).verified)

    def test_removed_readded_or_wrong_purpose_proof_cannot_confirm(self):
        """UUID and purpose binding reject reuse even when the number is identical."""
        self.add()
        old = self.user.phone_numbers.get(phone=FIRST)
        remove_phone(self.user, old.pk)
        new = add_phone(self.user, FIRST)
        self.verify()
        self.assertFalse(self.user.phone_numbers.get(pk=new.pk).verified)
        self.assertNotEqual(new.pk, old.pk)
        with gateway_codes():
            cache.clear()
            self.client.post(reverse("core_verify_phone", args=[new.pk]))
        session = self.client.session
        session["account_phone_verification"]["purpose"] = "phone_login"
        session.save()
        self.verify()
        self.assertFalse(self.user.phone_numbers.get(pk=new.pk).verified)

    def test_legacy_proof_and_verification_attempt_limits_fail_closed(self):
        """Old state and exhausted codes must require a new verification request."""
        self.add()
        session = self.client.session
        session["account_phone_verification"].pop("phone_id")
        session.save()
        self.assertRedirects(
            self.client.get(reverse("account_verify_phone")),
            reverse("account_change_phone"),
        )
        contact = self.user.phone_numbers.get(phone=FIRST)
        with gateway_codes():
            cache.clear()
            self.client.post(reverse("core_verify_phone", args=[contact.pk]))
        for _ in range(3):
            self.verify("000000")
        self.verify()
        self.assertFalse(self.user.phone_numbers.get(pk=contact.pk).verified)

    def test_gateway_disabled_retains_management_but_blocks_delivery(self):
        """Disabled delivery does not hide existing contacts or prevent safe removal."""
        first = set_phone(self.user, FIRST, True)
        second = set_phone(self.user, SECOND, True)
        pending = add_phone(self.user, "+12025550125")
        with override_settings(PHONE_LOGIN_ENABLED=False), gateway_codes() as send:
            response = self.client.get(reverse("account_change_phone"))
            self.assertContains(response, FIRST)
            self.assertNotContains(response, "Получить код в Telegram")
            self.assertEqual(
                self.client.post(
                    reverse("account_change_phone"), {"phone": "+12025550126"}
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.post(
                    reverse("core_verify_phone", args=[pending.pk])
                ).status_code,
                404,
            )
            self.client.post(reverse("core_primary_phone", args=[second.pk]))
            self.client.post(reverse("core_remove_phone", args=[first.pk]))
            self.assertFalse(self.user.phone_numbers.filter(pk=first.pk).exists())
            send.assert_not_called()

    def test_expiration_and_delivery_cooldown_preserve_pending_record(self):
        """Native timeout and rate limiting remain in effect for bound contacts."""
        self.add()
        contact = self.user.phone_numbers.get(phone=FIRST)
        with gateway_codes() as send:
            self.client.post(reverse("account_verify_phone"), {"action": "resend"})
        send.assert_not_called()
        session = self.client.session
        session["account_phone_verification"]["at"] = time.time() - 301
        session.save()
        self.verify()
        self.assertNotIn("account_phone_verification", self.client.session)
        self.assertFalse(self.user.phone_numbers.get(pk=contact.pk).verified)

    def test_owner_scope_uuid_routes_csrf_and_reauthentication(self):
        """UUID guessing, cross-account actions and stale sessions cannot change contacts."""
        contact = set_phone(self.user, FIRST, True)
        other = self.create_user("other", "other@example.com")
        foreign = add_phone(other, SECOND)
        for name in ("core_primary_phone", "core_remove_phone", "core_verify_phone"):
            for pk in (foreign.pk, uuid4()):
                cache.clear()
                self.assertEqual(
                    self.client.post(reverse(name, args=[pk])).status_code, 404
                )
            self.assertEqual(
                self.client.get(reverse(name, args=[contact.pk])).status_code, 405
            )
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        for name in ("core_primary_phone", "core_remove_phone", "core_verify_phone"):
            self.assertEqual(
                strict.post(reverse(name, args=[contact.pk])).status_code, 403
            )
        session = self.client.session
        session["account_authentication_methods"] = [
            {"method": "password", "at": time.time() - 1000}
        ]
        session.save()
        response = self.client.post(reverse("core_remove_phone", args=[contact.pk]))
        self.assertIn("reauthenticate", response.url)
        self.assertTrue(self.user.phone_numbers.filter(pk=contact.pk).exists())

    def test_pending_additional_phone_does_not_block_existing_email_login(self):
        """Incomplete enrollment is not a new mandatory step for established users."""
        add_phone(self.user, FIRST)
        self.client.logout()
        with (
            patch(
                "accounts.adapters.AccountAdapter.generate_login_code",
                return_value=LOGIN_CODE,
            ),
            gateway_codes() as send,
        ):
            self.client.post(
                reverse("account_request_login_code"), {"email": self.user.email}
            )
            self.client.post(
                reverse("account_confirm_login_code"), {"code": LOGIN_CODE}
            )
        send.assert_not_called()
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertFalse(self.user.phone_numbers.get(phone=FIRST).verified)

    def test_last_method_policy_uses_the_configured_primary_scope(self):
        """Only enabled primary login contacts count as alternatives to deletion."""
        primary = set_phone(self.user, FIRST, True)
        additional = set_phone(self.user, SECOND, True)
        with override_settings(
            AUTH_PASSWORD_MODE="passwordless", EMAIL_CODE_LOGIN_ENABLED=False
        ):
            self.assertTrue(has_primary_login(self.user, exclude_phone=primary.pk))
            with override_settings(AUTH_PHONE_LOGIN_MODE="primary_only"):
                self.assertFalse(has_primary_login(self.user, exclude_phone=primary.pk))
                self.assertTrue(
                    has_primary_login(self.user, exclude_phone=additional.pk)
                )
            remove_phone(self.user, additional.pk)
            with self.assertRaises(ValidationError):
                remove_phone(self.user, primary.pk)


class PhoneSignupTests(AccountTestCase):
    """Keep staged signup and contact correction compatible with multiple contacts."""

    @override_settings(ACCOUNT_PHONE_VERIFICATION_SUPPORTS_CHANGE=True)
    def test_signup_changed_phone_then_email_requires_each_own_code(self):
        """Changing the pending contact binds a new UUID and cannot reuse the old OTP."""
        with gateway_codes() as send:
            response = self.client.post(
                reverse("account_signup"),
                {
                    "first_name": "Анна",
                    "last_name": "Иванова",
                    "username": "phone-signup",
                    "email": "new-phone@example.invalid",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                    "phone": FIRST,
                    "next": "/app/?phone=signup",
                },
            )
        send.assert_called_once()
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="phone-signup")
        original = user.phone_numbers.get()
        self.assertIn(reverse("account_verify_phone"), response.url)
        self.assert_anonymous()
        with gateway_codes("519387") as send:
            cache.clear()
            response = self.client.post(
                reverse("account_verify_phone"),
                {
                    "action": "change",
                    "phone": SECOND,
                },
            )
        self.assertEqual(response.status_code, 302, response.content)
        self.assertIn(reverse("account_verify_phone"), response.url)
        send.assert_called_once()
        changed = user.phone_numbers.get(phone=SECOND)
        state = self.client.session["account_login"]["state"]["stages"]["verify_phone"][
            "data"
        ]
        self.assertEqual(state["phone_id"], str(changed.pk))
        self.assertNotEqual(changed.pk, original.pk)
        response = self.client.post(
            reverse("account_verify_phone"), {"code": LOGIN_CODE}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_anonymous()
        response = self.client.post(reverse("account_verify_phone"), {"code": "519387"})
        self.assert_anonymous()
        email_code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
        response = self.client.post(response.url, {"code": email_code})
        self.assertEqual(response.url, "/app/?phone=signup")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        changed.refresh_from_db()
        original.refresh_from_db()
        self.assertTrue(changed.verified and changed.primary)
        self.assertFalse(original.verified or original.primary)


class PhoneLoginPolicyTests(AccountTestCase):
    """Recheck phone policy through OTP, MFA and the final session creation gate."""

    def setUp(self):
        """Create two independently verified numbers with a stable primary."""
        super().setUp()
        self.first = set_phone(self.user, FIRST, True)
        self.second = set_phone(self.user, SECOND, True)

    def request_code(self, phone=SECOND):
        """Issue one isolated login proof for the selected contact."""
        with gateway_codes() as send:
            response = self.client.post(
                reverse("account_request_login_code"),
                {"phone": phone, "next": "/app/?phone=yes"},
            )
        return response, send

    def test_phone_password_post_cannot_bypass_the_bound_otp_flow(self):
        """The email/password form cannot authenticate through a phone ownership lookup."""
        for mode in ("any_verified", "primary_only"):
            with override_settings(AUTH_PHONE_LOGIN_MODE=mode), gateway_codes() as send:
                response = self.client.post(
                    reverse("account_login"),
                    {
                        "login": SECOND,
                        "password": PASSWORD,
                    },
                )
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response, "Для входа по телефону запросите код в Telegram."
            )
            self.assert_anonymous()
            send.assert_not_called()

    def confirm(self):
        """Submit the selected contact's login proof."""
        return self.client.post(
            reverse("account_confirm_login_code") + "?next=/app/?phone=yes",
            {"code": LOGIN_CODE},
        )

    def test_any_verified_accepts_secondary_and_keeps_primary_and_next(self):
        """Login never promotes the contact used for the proof."""
        self.request_code()
        self.assertEqual(self.confirm().url, "/app/?phone=yes")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertTrue(self.user.phone_numbers.get(pk=self.first.pk).primary)

    @override_settings(AUTH_PHONE_LOGIN_MODE="primary_only")
    def test_primary_only_never_sends_to_secondary(self):
        """Additional numbers cannot initiate a code in primary-only mode."""
        _, send = self.request_code()
        send.assert_not_called()
        self.confirm()
        self.assert_anonymous()
        cache.clear()
        self.client = Client()
        self.request_code(FIRST)
        self.confirm()
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_mode_change_blocks_pending_confirmation_and_resend(self):
        """Restarting with a stricter policy invalidates existing secondary proofs."""
        for action in ("verify", "resend"):
            cache.clear()
            self.client = Client()
            self.request_code()
            with (
                override_settings(AUTH_PHONE_LOGIN_MODE="primary_only"),
                gateway_codes() as send,
            ):
                self.client.post(
                    reverse("account_confirm_login_code"),
                    {"action": action, "code": LOGIN_CODE},
                )
                send.assert_not_called()
            self.assert_anonymous()

    @override_settings(AUTH_PHONE_LOGIN_MODE="primary_only")
    def test_primary_change_before_mfa_cannot_complete_login(self):
        """A valid first factor is rechecked after the user selects a different primary."""
        TOTP.activate(self.user, TOTP_SECRET)
        self.request_code(FIRST)
        self.assertEqual(self.confirm().url, reverse("mfa_authenticate"))
        set_primary_phone(self.user, self.second.pk)
        self.client.post(
            reverse("mfa_authenticate"),
            {
                "code": format_hotp_value(
                    hotp_value(TOTP_SECRET, int(time.time()) // 30)
                )
            },
        )
        self.assert_anonymous()

    def test_phone_mfa_completes_with_unchanged_owner_and_policy(self):
        """UUID proof metadata survives the native allauth MFA stage."""
        TOTP.activate(self.user, TOTP_SECRET)
        self.request_code()
        self.assertEqual(self.confirm().url, reverse("mfa_authenticate"))
        self.client.post(
            reverse("mfa_authenticate"),
            {
                "code": format_hotp_value(
                    hotp_value(TOTP_SECRET, int(time.time()) // 30)
                )
            },
        )
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_final_adapter_gate_rechecks_contact_after_mfa_validation(self):
        """An ownership change after middleware runs still prevents session creation."""
        TOTP.activate(self.user, TOTP_SECRET)
        self.request_code()
        self.confirm()
        original_login = AccountAdapter.login

        def remove_before_login(adapter, request, user):
            """Simulate a committed removal between middleware and final login."""
            remove_phone(user, self.second.pk)
            return original_login(adapter, request, user)

        with patch.object(AccountAdapter, "login", remove_before_login):
            self.client.post(
                reverse("mfa_authenticate"),
                {
                    "code": format_hotp_value(
                        hotp_value(TOTP_SECRET, int(time.time()) // 30)
                    )
                },
            )
        self.assert_anonymous()
