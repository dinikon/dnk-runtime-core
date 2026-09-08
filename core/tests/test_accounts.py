"""Session authentication contracts exercised through Django's HTTP stack."""

import re
import time
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse

from allauth.account.models import EmailAddress
from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, hotp_value
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.usersessions.models import UserSession

from tests.helpers import AccountTestCase, LOGIN_CODE, PASSWORD, TOTP_SECRET


class SessionAPITests(AccountTestCase):
    def test_custom_user_has_uuid_and_abstract_user_behavior(self):
        self.assertIsInstance(self.user, AbstractUser)
        self.assertIsInstance(self.user.pk, UUID)
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_anonymous_bootstrap_has_csrf_token_and_no_cache(self):
        response = self.client.get("/api/session/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertGreaterEqual(len(response.json()["csrfToken"]), 32)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assert_anonymous()

    def test_csrf_is_required_for_login_even_with_a_session_cookie(self):
        browser = Client(enforce_csrf_checks=True)
        token = browser.get("/api/session/").json()["csrfToken"]
        payload = {"login": self.user.email, "password": PASSWORD}
        self.assertEqual(
            browser.post(reverse("account_login"), payload).status_code, 403
        )
        response = browser.post(
            reverse("account_login"), payload, HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(browser.get("/api/me/").status_code, 200)
        self.assertTrue(browser.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
        self.assertEqual(
            browser.cookies[settings.SESSION_COOKIE_NAME]["samesite"], "Lax"
        )

    def test_me_returns_current_user_without_password_or_staff_privileges(self):
        self.password_login()
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.user.pk))
        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["username"], self.user.username)
        self.assertNotIn("password", data)
        self.assertNotIn("is_superuser", data)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_api_wrong_methods_are_rejected(self):
        self.assertEqual(self.client.post("/api/session/").status_code, 405)
        self.assertEqual(self.client.post("/api/me/").status_code, 405)

    def test_logout_is_post_only_and_requires_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        token = browser.get("/api/session/").json()["csrfToken"]
        browser.get(reverse("account_logout"))
        self.assertEqual(browser.get("/api/me/").status_code, 200)
        self.assertEqual(browser.post(reverse("account_logout")).status_code, 403)
        browser.post(reverse("account_logout"), HTTP_X_CSRFTOKEN=token)
        self.assert_anonymous(browser)


class PasswordAndEmailTests(AccountTestCase):
    def test_email_and_username_password_login(self):
        for identifier in (self.user.email.upper(), self.user.username):
            with self.subTest(identifier=identifier):
                response = self.password_login(login=identifier, next="/app/")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(urlparse(response.url).path, "/app/")
                self.assertEqual(self.client.get("/api/me/").status_code, 200)
                self.client.logout()

    def test_login_rotates_session_and_refuses_external_next(self):
        self.client.get("/api/session/")
        old_session = self.client.session.session_key
        response = self.password_login(next="https://attacker.example/steal")
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(urlparse(response.url).netloc, "attacker.example")
        self.assertNotEqual(self.client.session.session_key, old_session)

    def test_wrong_password_inactive_and_unverified_email_cannot_enter(self):
        self.password_login(password="incorrect")
        self.assert_anonymous()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.password_login()
        self.assert_anonymous()
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.password_login()
        self.assert_anonymous()
        self.assertTrue(mail.outbox)

    def test_signup_requires_email_confirmation(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "new-member",
                "email": "new@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302, response.content)
        user = get_user_model().objects.get(username="new-member")
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assert_anonymous()
        confirmation = re.search(r"\b[0-9]{6}\b", mail.outbox[-1].body)
        self.assertIsNotNone(confirmation)
        url = reverse("account_email_verification_sent")
        self.client.get(url)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.client.post(url, {"code": confirmation.group()})
        self.assertTrue(EmailAddress.objects.get(user=user).verified)

    def test_password_reset_changes_password_and_consumes_link(self):
        self.client.post(reverse("account_reset_password"), {"email": self.user.email})
        reset = re.search(
            r"https?://[^\s<>]+/accounts/password/reset/key/[^\s<>]+",
            mail.outbox[-1].body,
        )
        self.assertIsNotNone(reset)
        url = urlparse(reset.group()).path
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        form_url = response.url
        replacement = "A-new-secure-test-password-456!"
        self.client.post(form_url, {"password1": replacement, "password2": replacement})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(replacement))
        self.assertFalse(self.user.check_password(PASSWORD))
        fresh_browser = Client()
        replay = fresh_browser.get(url, follow=True)
        self.assertNotContains(replay, 'name="password1"')

    def test_admin_login_uses_allauth_instead_of_password_bypass(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        response = self.client.post(
            "/admin/login/", {"username": self.user.username, "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("account_login"))
        self.assert_anonymous()


class CodeFlowMixin:
    def request_code(self, **payload):
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=LOGIN_CODE,
        ):
            response = self.client.post(
                reverse("account_request_login_code"),
                payload or {"email": self.user.email},
            )
        self.assertEqual(response.status_code, 302, response.content)
        return response

    def confirm_code(self, code=LOGIN_CODE):
        return self.client.post(reverse("account_confirm_login_code"), {"code": code})


class EmailCodeTests(CodeFlowMixin, AccountTestCase):
    def test_issued_email_code_cannot_login_after_address_moves_to_another_user(self):
        self.request_code()
        previous_email = self.user.email
        EmailAddress.objects.filter(user=self.user).delete()
        self.user.email = "replacement@example.com"
        self.user.save(update_fields=["email"])
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True
        )
        new_owner = self.create_user(username="new-owner", email=previous_email)
        self.confirm_code()
        self.assert_anonymous()
        self.assertFalse(
            EmailAddress.objects.filter(user=self.user, email=previous_email).exists()
        )
        self.assertTrue(
            EmailAddress.objects.filter(
                user=new_owner, email=previous_email, verified=True
            ).exists()
        )

    def test_removed_email_cannot_receive_a_resend_and_deleted_user_cannot_confirm(
        self,
    ):
        self.request_code()
        EmailAddress.objects.filter(user=self.user).delete()
        with patch("accounts.adapters.AccountAdapter.send_mail") as send:
            self.client.post(
                reverse("account_confirm_login_code"), {"action": "resend"}
            )
        send.assert_not_called()
        self.confirm_code()
        self.assert_anonymous()

        self.client = Client()
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True
        )
        self.request_code()
        self.user.delete()
        self.confirm_code()
        self.assert_anonymous()

    def test_resend_replaces_previous_code_and_requests_are_rate_limited(self):
        self.request_code()
        replacement = "729416"
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=replacement,
        ):
            response = self.client.post(
                reverse("account_confirm_login_code"), {"action": "resend"}
            )
        self.assertEqual(response.status_code, 302)
        self.confirm_code(LOGIN_CODE)
        self.assert_anonymous()
        self.confirm_code(replacement)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))

        from django.core.cache import cache

        cache.clear()
        with patch("accounts.adapters.AccountAdapter.send_mail") as send:
            for _ in range(4):
                response = Client().post(
                    reverse("account_request_login_code"), {"email": self.user.email}
                )
        self.assertEqual(send.call_count, 3)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_empty_and_two_channels_are_form_errors(self):
        for payload in ({}, {"email": self.user.email, "phone": "+12025550123"}):
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("account_request_login_code"), payload
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assert_anonymous()

    def test_valid_code_authenticates_and_cannot_be_replayed(self):
        self.request_code()
        self.assert_anonymous()
        self.confirm_code("")
        self.assert_anonymous()
        self.confirm_code()
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))
        self.confirm_code()
        self.assert_anonymous()

    def test_wrong_attempt_limit_invalidates_correct_code(self):
        self.request_code()
        for _ in range(settings.ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS):
            self.confirm_code("000000")
        self.confirm_code()
        self.assert_anonymous()

    def test_expired_code_cannot_authenticate(self):
        self.request_code()
        future = time.time() + settings.ACCOUNT_LOGIN_BY_CODE_TIMEOUT + 1
        with patch(
            "allauth.account.internal.flows.code_verification.time.time",
            return_value=future,
        ):
            self.confirm_code()
        self.assert_anonymous()

    def test_unknown_and_inactive_accounts_never_authenticate(self):
        self.request_code(email="absent@example.com")
        self.confirm_code()
        self.assert_anonymous()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.request_code()
        self.confirm_code()
        self.assert_anonymous()


class MFATests(CodeFlowMixin, AccountTestCase):
    secret = TOTP_SECRET

    def setUp(self):
        super().setUp()
        self.authenticator = TOTP.activate(self.user, self.secret)

    def test_valid_code_authenticates_and_cannot_be_replayed(self):
        self.request_code()
        response = self.confirm_code()
        self.assertEqual(urlparse(response.url).path, reverse("mfa_authenticate"))
        self.assert_anonymous()

    def test_password_requires_second_factor_and_real_totp_completes_it(self):
        response = self.password_login()
        self.assertEqual(urlparse(response.url).path, reverse("mfa_authenticate"))
        self.assert_anonymous()
        self.client.post(reverse("mfa_authenticate"), {"code": "000000"})
        self.assert_anonymous()
        code = format_hotp_value(hotp_value(self.secret, int(time.time()) // 30))
        self.client.post(reverse("mfa_authenticate"), {"code": code})
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))
        self.password_login()
        self.client.post(reverse("mfa_authenticate"), {"code": code})
        self.assert_anonymous()

    def test_totp_and_recovery_seed_are_encrypted_and_recovery_is_single_use(self):
        from accounts.adapters import MFAAdapter

        adapter = MFAAdapter()
        ciphertext = self.authenticator.instance.data["secret"]
        self.assertNotEqual(ciphertext, self.secret)
        self.assertEqual(adapter.decrypt(ciphertext), self.secret)
        recovery = RecoveryCodes.activate(self.user)
        seed = recovery.instance.data["seed"]
        self.assertNotEqual(seed, adapter.decrypt(seed))
        code = recovery.get_unused_codes()[0]
        self.password_login()
        self.client.post(reverse("mfa_authenticate"), {"code": code})
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.client.post(reverse("account_logout"))
        self.password_login()
        self.client.post(reverse("mfa_authenticate"), {"code": code})
        self.assert_anonymous()


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            "APP": {"client_id": "test-google-id", "secret": "test-google-secret"}
        },
        "github": {
            "APP": {"client_id": "test-github-id", "secret": "test-github-secret"}
        },
    }
)
class SocialLoginTests(AccountTestCase):
    def callback(
        self, provider="google", linked=True, process="login", before_callback=None
    ):
        if linked:
            SocialAccount.objects.create(
                user=self.user, provider=provider, uid="provider-123"
            )
        response = self.client.post(reverse(f"{provider}_login"), {"process": process})
        self.assertEqual(response.status_code, 302, response.content)
        state = parse_qs(urlparse(response.url).query)["state"][0]
        login = SocialLogin(
            user=get_user_model()(email=self.user.email, username="provider-user"),
            account=SocialAccount(provider=provider, uid="provider-123"),
            email_addresses=[
                EmailAddress(email=self.user.email, verified=True, primary=True)
            ],
        )
        adapter = {"google": "GoogleOAuth2Adapter", "github": "GitHubOAuth2Adapter"}[
            provider
        ]

        def complete_login(request, app, token, **kwargs):
            login.provider = get_social_adapter(request).get_provider(
                request, provider=provider
            )
            return login

        if before_callback:
            before_callback()

        with (
            patch(
                "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                return_value={"access_token": "test-token"},
            ),
            patch(
                f"allauth.socialaccount.providers.{provider}.views.{adapter}.complete_login",
                side_effect=complete_login,
            ),
        ):
            return self.client.get(
                reverse(f"{provider}_callback"), {"code": "test-code", "state": state}
            )

    def test_disabled_stored_providers_can_be_displayed_and_removed_but_not_used(self):
        self.password_login()
        accounts = [
            SocialAccount.objects.create(
                user=self.user, provider=provider, uid="saved-connection"
            )
            for provider in ("google", "github")
        ]
        with override_settings(
            GOOGLE_LOGIN_ENABLED=False,
            GITHUB_LOGIN_ENABLED=False,
            SOCIALACCOUNT_PROVIDERS={},
        ):
            for name in ("core_account_overview", "socialaccount_connections"):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Google")
                self.assertContains(response, "GitHub")
            login = Client().get(reverse("account_login"))
            for provider in ("google", "github"):
                self.assertNotContains(login, f"/accounts/{provider}/login/")
                self.assertEqual(
                    self.client.post(reverse(f"{provider}_login")).status_code, 404
                )
                self.assertEqual(
                    self.client.get(
                        reverse(f"{provider}_callback"),
                        {"code": "ignored", "state": "ignored"},
                    ).status_code,
                    404,
                )
            for account in accounts:
                response = self.client.post(
                    reverse("socialaccount_connections"), {"account": account.pk}
                )
                self.assertEqual(response.status_code, 302)
                self.assertFalse(SocialAccount.objects.filter(pk=account.pk).exists())
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_delayed_social_only_connect_requires_email_code_before_creating_link(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.callback("google")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

        def age_authentication():
            session = self.client.session
            session[AUTHENTICATION_METHODS_SESSION_KEY][-1]["at"] = time.time() - 301
            session.save()

        response = self.callback(
            "github",
            linked=False,
            process="connect",
            before_callback=age_authentication,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            urlparse(response.url).path, reverse("core_email_reauthenticate")
        )
        self.assertFalse(
            SocialAccount.objects.filter(user=self.user, provider="github").exists()
        )
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=LOGIN_CODE,
        ):
            self.client.post(response.url, {"action": "request"})
        self.client.post(response.url, {"action": "verify", "code": "000000"})
        self.assertFalse(
            SocialAccount.objects.filter(user=self.user, provider="github").exists()
        )
        result = self.client.post(
            response.url, {"action": "verify", "code": LOGIN_CODE}
        )
        self.assertEqual(result.status_code, 302)
        self.assertTrue(
            SocialAccount.objects.filter(
                user=self.user, provider="github", uid="provider-123"
            ).exists()
        )
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_google_and_github_linked_accounts_use_server_session(self):
        for provider in ("google", "github"):
            with self.subTest(provider=provider):
                response = self.callback(provider)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.client.get("/api/me/").status_code, 200)
                self.client.post(reverse("account_logout"))

    def test_social_login_requires_enrolled_mfa(self):
        TOTP.activate(self.user, TOTP_SECRET)
        response = self.callback()
        self.assertEqual(urlparse(response.url).path, reverse("mfa_authenticate"))
        self.assert_anonymous()

    def test_inactive_linked_social_account_cannot_enter(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.callback()
        self.assert_anonymous()

    def test_equal_verified_email_does_not_silently_link_provider(self):
        self.callback(linked=False)
        self.assert_anonymous()
        self.assertFalse(SocialAccount.objects.filter(user=self.user).exists())

    def test_forged_oauth_state_is_rejected_before_token_exchange(self):
        with patch(
            "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token"
        ) as exchange:
            self.client.get(
                reverse("google_callback"),
                {"code": "test-code", "state": "forged-state"},
            )
        exchange.assert_not_called()
        self.assert_anonymous()


class UserSessionTests(AccountTestCase):
    def test_revocation_requires_csrf_and_recent_reauthentication(self):
        self.password_login()
        other_browser = Client()
        self.password_login(client=other_browser)
        target = UserSession.objects.get(session_key=other_browser.session.session_key)
        url = reverse("core_revoke_session", kwargs={"pk": target.pk})
        browser = Client(enforce_csrf_checks=True)
        browser.cookies = self.client.cookies.copy()
        self.assertEqual(browser.post(url).status_code, 403)
        self.assertTrue(Session.objects.filter(session_key=target.session_key).exists())
        future = time.time() + settings.ACCOUNT_REAUTHENTICATION_TIMEOUT + 1
        with patch(
            "allauth.account.internal.flows.reauthentication.time.time",
            return_value=future,
        ):
            response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("account_reauthenticate"))
        self.assertTrue(Session.objects.filter(session_key=target.session_key).exists())
        self.assertEqual(other_browser.get("/api/me/").status_code, 200)

    def test_revoking_current_session_logs_out_only_that_browser(self):
        self.password_login()
        other_browser = Client()
        self.password_login(client=other_browser)
        current = UserSession.objects.get(session_key=self.client.session.session_key)
        response = self.client.post(
            reverse("core_revoke_session", kwargs={"pk": current.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assert_anonymous()
        self.assertEqual(other_browser.get("/api/me/").status_code, 200)

    def test_owner_can_revoke_another_session_and_cannot_revoke_someone_elses(self):
        self.password_login()
        other_browser = Client()
        self.password_login(client=other_browser)
        second = UserSession.objects.get(session_key=other_browser.session.session_key)
        url = reverse("core_revoke_session", kwargs={"pk": second.pk})
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Session.objects.filter(session_key=second.session_key).exists()
        )
        self.assert_anonymous(other_browser)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        stranger = self.create_user(username="bob", email="bob@example.com")
        stranger_browser = Client()
        stranger_browser.force_login(stranger)
        stranger_session = UserSession.objects.create(
            user=stranger,
            session_key=stranger_browser.session.session_key,
            ip="127.0.0.1",
            user_agent="test",
        )
        response = self.client.post(
            reverse("core_revoke_session", kwargs={"pk": stranger_session.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Session.objects.filter(session_key=stranger_session.session_key).exists()
        )

    def test_account_pages_require_login(self):
        for name in (
            "core_account_overview",
            "account_email",
            "mfa_index",
            "usersessions_list",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 302)
