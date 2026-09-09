"""Names are editable presentation data, independent of unique account identity."""

import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, override_settings
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.core import context
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount, SocialLogin
from accounts.forms import SocialSignupForm
from accounts.services.capabilities import has_primary_login
from dnk_core.config import load_config
from dnk_core.configuration.allauth import authentication_settings
from tests.helpers import AccountTestCase, PASSWORD
from tests import test_passkey_signup


def name_policy(mode="passwordless", username_mode="generated"):
    """Build actual Django policy projections without reading deployment files."""
    return authentication_settings(
        load_config(
            env_file=None,
            debug=True,
            auth_password_mode=mode,
            auth_username_mode=username_mode,
            telegram_gateway_enabled=False,
        )
    )


class ProfileTests(AccountTestCase):
    """Cover real signup, email proofs and owner-only profile POST requests."""

    def test_internal_username_is_not_a_fallback_for_last_email_removal(self):
        """A stored password needs a usable identifier when username login is disabled."""
        address = EmailAddress.objects.get(user=self.user)
        with override_settings(**name_policy("required")):
            self.assertTrue(has_primary_login(self.user))
            self.assertFalse(has_primary_login(self.user, exclude_email=address.pk))
            self.assertFalse(get_adapter().can_delete_email(address))

    def test_generated_signup_matrix_ignores_posted_username_and_verifies_email(self):
        """Every password mode registers by names and email with an opaque username."""
        for mode in ("required", "optional", "passwordless"):
            with self.subTest(mode=mode), override_settings(**name_policy(mode)):
                self.client.logout()
                response = self.client.get("/accounts/signup/")
                self.assertNotIn("username", response.context["form"].fields)
                data = {
                    "first_name": " Анна-Мария ",
                    "last_name": " О’Коннор ",
                    "middle_name": " Ивановна ",
                    "email": f"{mode}@example.com",
                    "username": self.user.username,
                    "next": "/app/?profile=created",
                }
                if mode == "required":
                    data.update(password1=PASSWORD, password2=PASSWORD)
                response = self.client.post("/accounts/signup/", data)
                self.assertEqual(response.status_code, 302, response.content)
                user = get_user_model().objects.get(email=data["email"])
                self.assertEqual(user.username, f"user_{user.pk.hex}")
                self.assertEqual(user.get_full_name(), "О’Коннор Анна-Мария Ивановна")
                self.assertEqual(user.has_usable_password(), mode == "required")
                self.assertFalse(EmailAddress.objects.get(user=user).verified)
                self.assert_anonymous()
                code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
                response = self.client.post(response.url, {"code": code})
                self.assertEqual(response.url, "/app/?profile=created")
                self.assertEqual(
                    self.client.get("/api/me/").json()["display_name"],
                    user.get_full_name(),
                )

    def test_signup_requires_names_and_accepts_nonunique_names_without_patronymic(self):
        """Missing names fail validation while equal names still identify different users."""
        with override_settings(**name_policy()):
            response = self.client.post(
                "/accounts/signup/", {"email": "names@example.com"}
            )
            self.assertEqual(
                set(response.context["form"].errors), {"first_name", "last_name"}
            )
            self.assertFalse(
                get_user_model().objects.filter(email="names@example.com").exists()
            )
            for number in range(2):
                self.client.logout()
                response = self.client.post(
                    "/accounts/signup/",
                    {
                        "first_name": "Анна",
                        "last_name": "Иванова",
                        "email": f"names{number}@example.com",
                    },
                )
                self.assertEqual(response.status_code, 302)
            users = get_user_model().objects.filter(
                first_name="Анна", last_name="Иванова"
            )
            self.assertEqual(users.count(), 2)
            self.assertEqual(len(set(users.values_list("username", flat=True))), 2)
            self.assertEqual(set(users.values_list("middle_name", flat=True)), {""})

    def test_generated_mode_uses_email_and_preserves_existing_username_and_password(
        self,
    ):
        """Switching policy cannot rewrite stored identifiers or invalidate email login."""
        original_password = self.user.password
        for mode in ("required", "optional"):
            with self.subTest(mode=mode), override_settings(**name_policy(mode)):
                self.client.logout()
                response = self.client.post(
                    "/accounts/login/",
                    {"login": self.user.username, "password": PASSWORD},
                )
                self.assertEqual(response.status_code, 200)
                self.assert_anonymous()
                self.assertEqual(self.password_login().status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "alice")
        self.assertEqual(self.user.password, original_password)

    def test_required_username_policy_remains_available(self):
        """An explicit legacy setting restores username selection and password login."""
        with override_settings(**name_policy("required", "required")):
            form = self.client.get("/accounts/signup/").context["form"]
            self.assertTrue(form.fields["username"].required)
            self.assertTrue(form.fields["first_name"].required)
            self.assertEqual(
                self.client.post(
                    "/accounts/login/",
                    {"login": self.user.username, "password": PASSWORD},
                ).status_code,
                302,
            )

    def test_profile_get_post_csrf_and_no_mass_assignment(self):
        """Only the authenticated owner's names can change through a CSRF-protected form."""
        self.assertEqual(self.client.get("/accounts/profile/").status_code, 302)
        other = self.create_user(
            username="other", email="other@example.com", first_name="Other"
        )
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        response = browser.get("/accounts/profile/")
        self.assertContains(response, 'autocomplete="family-name"')
        data = {
            "first_name": "Марія",
            "last_name": "Коваль",
            "middle_name": "Олексіївна",
            "id": str(other.pk),
            "username": "replace",
            "email": "replace@example.com",
            "password": "replace",
            "is_staff": "true",
            "is_superuser": "true",
        }
        self.assertEqual(browser.post("/accounts/profile/", data).status_code, 403)
        response = browser.post(
            "/accounts/profile/",
            data,
            HTTP_X_CSRFTOKEN=browser.get("/api/session/").json()["csrfToken"],
        )
        self.assertEqual(response.url, "/accounts/profile/")
        original_password = self.user.password
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Коваль Марія Олексіївна")
        self.assertEqual(self.user.initials, "КМ")
        self.assertEqual(other.first_name, "Other")
        self.assertEqual(
            (self.user.username, self.user.email, self.user.password),
            ("alice", "alice@example.com", original_password),
        )
        self.assertFalse(self.user.is_staff or self.user.is_superuser)
        data = browser.get("/api/me/").json()
        self.assertEqual(data["middle_name"], "Олексіївна")
        self.assertEqual(data["display_name"], self.user.get_full_name())

    def test_profile_errors_preserve_input_and_allow_clearing_patronymic(self):
        """Names retain validation errors and escaped input; the patronymic is optional."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/accounts/profile/",
            {"first_name": "<script>alert(1)</script>", "last_name": " "},
        )
        self.assertIn("last_name", response.context["form"].errors)
        self.assertEqual(
            response.context["form"]["first_name"].value(), "<script>alert(1)</script>"
        )
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")
        self.assertEqual(self.user.display_name, self.user.email)
        self.assertEqual(
            self.client.post(
                "/accounts/profile/", {"first_name": "李", "last_name": "王"}
            ).status_code,
            302,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.middle_name, "")
        self.assertEqual(self.user.get_full_name(), "王 李")

    def test_provider_prefill_and_missing_names_require_completion(self):
        """Provider data prefills the shared social form and missing names stop auto signup."""
        with override_settings(**name_policy()):
            request = self.client.get("/accounts/login/").wsgi_request
            with context.request_context(request):
                login = SocialLogin(
                    user=get_user_model()(
                        first_name="Ada",
                        last_name="Lovelace",
                        email="ada@example.com",
                        username="provider_name",
                    ),
                    account=SocialAccount(provider="google", uid="profile-qa"),
                )
                adapter = get_social_adapter(request)
                login.provider = adapter.get_provider(request, "google")
                form = SocialSignupForm(sociallogin=login)
                self.assertEqual(form["first_name"].value(), "Ada")
                self.assertEqual(form["last_name"].value(), "Lovelace")
                self.assertNotIn("username", form.fields)
                self.assertTrue(adapter.is_auto_signup_allowed(request, login))
                user = adapter.save_user(request, login)
                self.assertEqual(user.username, f"user_{user.pk.hex}")
                self.assertEqual(user.get_full_name(), "Lovelace Ada")
                self.assertFalse(user.has_usable_password())
                login.user.last_name = ""
                self.assertFalse(adapter.is_auto_signup_allowed(request, login))
                stored_username = user.username
                get_adapter(request).populate_username(request, user)
                self.assertEqual(user.username, stored_username)


@override_settings(
    AUTH_USERNAME_MODE="generated",
    ACCOUNT_SIGNUP_FIELDS=["email*"],
    ACCOUNT_LOGIN_METHODS={"email"},
)
class GeneratedPasskeySignupTests(test_passkey_signup.PasskeySignupTests):
    """Run the complete signed passkey, UV and recovery suite with generated usernames."""
