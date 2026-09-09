"""Social-only accounts must prove email ownership before security changes."""

import json
import time
from urllib.parse import urlparse
from unittest.mock import patch

from django.contrib.sessions.models import Session
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from accounts.reauthentication import STATE_KEY
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
from allauth.usersessions.models import UserSession

from tests.helpers import AccountTestCase, LOGIN_CODE


class SocialOnlyReauthenticationTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_login(self.user)
        self.other_browser = Client()
        self.other_browser.force_login(self.user)
        self.target = UserSession.objects.create(
            user=self.user,
            session_key=self.other_browser.session.session_key,
            ip="127.0.0.1",
            user_agent="other browser",
        )
        self.target_url = reverse("core_revoke_session", kwargs={"pk": self.target.pk})
        response = self.client.post(self.target_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            urlparse(response.url).path, reverse("core_email_reauthenticate")
        )
        self.reauth_url = response.url

    def send_code(self):
        with patch(
            "accounts.adapters.AccountAdapter.generate_login_code",
            return_value=LOGIN_CODE,
        ):
            response = self.client.post(self.reauth_url, {"action": "request"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["code_sent"])
        self.assertIn(LOGIN_CODE, mail.outbox[-1].body)
        return response

    def verify(self, code=LOGIN_CODE):
        return self.client.post(self.reauth_url, {"action": "verify", "code": code})

    def assert_target_preserved(self):
        self.assertTrue(
            Session.objects.filter(session_key=self.target.session_key).exists()
        )
        self.assertEqual(self.other_browser.get("/api/me/").status_code, 200)

    def test_code_is_hashed_and_success_resumes_exact_suspended_action(self):
        self.assert_target_preserved()
        self.send_code()
        self.assertNotIn(LOGIN_CODE, json.dumps(self.client.session[STATE_KEY]))
        self.assertEqual(
            self.client.post(self.reauth_url, {"action": "request"}).status_code, 429
        )
        response = self.verify()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Session.objects.filter(session_key=self.target.session_key).exists()
        )
        self.assertNotIn(STATE_KEY, self.client.session)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assert_anonymous(self.other_browser)

    def test_successful_code_cannot_be_replayed_for_another_security_action(self):
        self.send_code()
        self.verify()
        third_browser = Client()
        third_browser.force_login(self.user)
        third_session = UserSession.objects.create(
            user=self.user,
            session_key=third_browser.session.session_key,
            ip="127.0.0.1",
            user_agent="third browser",
        )
        session = self.client.session
        session[AUTHENTICATION_METHODS_SESSION_KEY][-1]["at"] = time.time() - 301
        session.save()
        response = self.client.post(
            reverse("core_revoke_session", kwargs={"pk": third_session.pk})
        )
        self.assertEqual(
            urlparse(response.url).path, reverse("core_email_reauthenticate")
        )
        replay = self.client.post(
            response.url, {"action": "verify", "code": LOGIN_CODE}
        )
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(
            Session.objects.filter(session_key=third_session.session_key).exists()
        )
        self.assertEqual(third_browser.get("/api/me/").status_code, 200)

    def test_empty_and_three_invalid_codes_do_not_resume_action(self):
        self.send_code()
        for code in ("", "000000", "111111"):
            self.assertEqual(self.verify(code).status_code, 200)
            self.assert_target_preserved()
        self.assertNotIn(STATE_KEY, self.client.session)
        self.verify()
        self.assert_target_preserved()

    def test_expired_code_is_removed_without_resuming_action(self):
        self.send_code()
        with patch(
            "accounts.services.reauthentication.time.time",
            return_value=time.time() + 301,
        ):
            response = self.verify()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(STATE_KEY, self.client.session)
        self.assert_target_preserved()

    def test_challenge_cannot_transfer_to_another_account(self):
        self.send_code()
        stranger = self.create_user(username="bob", email="bob@example.com")
        stranger.set_unusable_password()
        stranger.save(update_fields=["password"])
        browser = Client()
        browser.force_login(stranger)
        session = browser.session
        session[STATE_KEY] = self.client.session[STATE_KEY]
        session.save()
        response = browser.post(
            reverse("core_email_reauthenticate"),
            {"action": "verify", "code": LOGIN_CODE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(STATE_KEY, browser.session)
        self.assert_target_preserved()

    def test_removed_email_verification_invalidates_outstanding_challenge(self):
        self.send_code()
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.verify()
        self.assertNotIn(STATE_KEY, self.client.session)
        self.assert_target_preserved()
        cache.clear()
        self.assertEqual(
            self.client.post(self.reauth_url, {"action": "request"}).status_code, 403
        )

    def test_delivery_failure_and_csrf_failure_create_no_challenge(self):
        with patch(
            "accounts.adapters.AccountAdapter.send_mail",
            side_effect=OSError("mail delivery failed"),
        ):
            response = self.client.post(self.reauth_url, {"action": "request"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(STATE_KEY, self.client.session)
        self.assert_target_preserved()
        browser = Client(enforce_csrf_checks=True)
        browser.cookies = self.client.cookies.copy()
        self.assertEqual(
            browser.post(self.reauth_url, {"action": "request"}).status_code, 403
        )

    def test_enrollment_get_requires_reauthentication_but_logout_remains_available(
        self,
    ):
        for name in ("mfa_activate_totp", "mfa_add_webauthn"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                urlparse(response.url).path, reverse("core_email_reauthenticate")
            )
        self.client.post(reverse("account_logout"))
        self.assert_anonymous()
