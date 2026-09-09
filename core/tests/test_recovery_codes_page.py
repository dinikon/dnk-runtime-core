"""Recovery-code pages guide setup while preserving native generation and secrecy."""

import time

from django.test import Client, override_settings
from django.urls import reverse
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP

from tests.helpers import AccountTestCase, TOTP_SECRET


class RecoveryCodesPageTests(AccountTestCase):
    """Exercise the CORE empty page and the unchanged allauth recovery lifecycle."""

    def test_missing_codes_show_setup_without_creating_authenticators(self):
        """A signed-in account with no MFA receives useful guidance rather than 404."""
        self.password_login()
        response = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/recovery_codes_empty.html")
        self.assertFalse(response.context["can_generate_codes"])
        self.assertContains(response, "Настроить приложение-аутентификатор")
        self.assertContains(response, "Добавить ключ доступа")
        self.assertNotContains(response, "Создать резервные коды")
        self.assertFalse(Authenticator.objects.filter(user=self.user).exists())
        self.assertIn("no-store", response.headers["Cache-Control"])
        response = self.client.post(reverse("mfa_generate_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Authenticator.objects.filter(user=self.user).exists())

    @override_settings(
        MFA_TOTP_ENROLLMENT_ENABLED=False, MFA_PASSKEY_ENROLLMENT_ENABLED=False
    )
    def test_empty_page_respects_disabled_enrollment(self):
        """Do not send the user to setup actions disabled by deployment policy."""
        self.password_login()
        response = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Подключение новых способов защиты сейчас недоступно"
        )
        self.assertNotContains(response, "Настроить приложение-аутентификатор")
        self.assertNotContains(response, "Добавить ключ доступа")

    def test_existing_totp_without_codes_offers_explicit_native_generation(self):
        """GETs never generate codes; native POST creates them for an existing factor."""
        self.password_login()
        TOTP.activate(self.user, TOTP_SECRET)
        response = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_generate_codes"])
        self.assertContains(response, "Создать резервные коды")
        self.assertFalse(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.RECOVERY_CODES
            ).exists()
        )
        response = self.client.get(reverse("mfa_generate_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.RECOVERY_CODES
            ).exists()
        )
        response = self.client.post(reverse("mfa_generate_recovery_codes"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("mfa_view_recovery_codes"))
        self.assertTrue(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.RECOVERY_CODES
            ).exists()
        )

    def test_existing_codes_keep_native_one_time_display(self):
        """Display real codes only once and never pass them to subsequent templates."""
        self.password_login()
        TOTP.activate(self.user, TOTP_SECRET)
        RecoveryCodes.activate(self.user)
        first = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.context["can_view_codes"])
        code = first.context["unused_codes"][0]
        self.assertContains(first, code)
        second = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.context["can_view_codes"])
        self.assertTrue(
            all(value == "****" for value in second.context["unused_codes"])
        )
        self.assertNotContains(second, code)
        self.assertTrue(second.context["can_generate_codes"])

    def test_existing_codes_still_require_recent_authentication(self):
        """Stale sessions cannot reveal codes or consume their one-time display."""
        self.password_login()
        TOTP.activate(self.user, TOTP_SECRET)
        authenticator = RecoveryCodes.activate(self.user).instance
        session = self.client.session
        session["account_authentication_methods"][-1]["at"] = time.time() - 600
        session.save()
        response = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_reauthenticate"), response.url)
        authenticator.refresh_from_db()
        self.assertFalse(authenticator.wrap().did_view)

    def test_guest_access_and_generation_without_csrf_remain_rejected(self):
        """The empty-state override retains authentication and native CSRF boundaries."""
        response = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)
        self.password_login()
        TOTP.activate(self.user, TOTP_SECRET)
        protected = Client(enforce_csrf_checks=True)
        protected.cookies = self.client.cookies
        response = protected.post(reverse("mfa_generate_recovery_codes"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.RECOVERY_CODES
            ).exists()
        )
