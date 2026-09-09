"""Saved provider profiles remain identifiable and safely rendered in account UI."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from allauth.socialaccount.models import SocialAccount
from accounts.presentation.social_accounts import social_account_label
from tests.helpers import AccountTestCase


class SocialAccountLabelTests(SimpleTestCase):
    """Describe identities from a restricted set of provider display claims."""

    def test_provider_handles_and_email_take_precedence_over_generic_names(self):
        """Use actual provider profile identifiers instead of indistinguishable names."""
        cases = (
            (
                "telegram",
                {"username": "alice", "preferred_username": "old", "name": "Alice"},
                "Telegram · @alice",
            ),
            ("telegram", {"preferred_username": "alice"}, "Telegram · @alice"),
            ("telegram", {"username": "@alice"}, "Telegram · @alice"),
            ("github", {"login": "octocat", "name": "Alice"}, "GitHub · @octocat"),
            (
                "google",
                {"email": "alice@example.com", "name": "Alice"},
                "Google · alice@example.com",
            ),
        )
        for provider, data, expected in cases:
            with self.subTest(provider=provider, data=data):
                account = SocialAccount(provider=provider, uid="12345", extra_data=data)
                self.assertEqual(social_account_label(account), expected)

    def test_missing_handles_always_include_a_stable_profile_id(self):
        """A Telegram name alone cannot distinguish two profiles with the same name."""
        cases = (
            (
                "telegram",
                {"name": "Alice", "sub": "telegram-sub"},
                "Telegram · Alice · ID telegram-sub",
            ),
            ("telegram", {"name": "Alice"}, "Telegram · Alice · ID 12345"),
            ("telegram", {"sub": "telegram-sub"}, "Telegram · ID telegram-sub"),
            ("telegram", {}, "Telegram · ID 12345"),
            ("github", {"name": "Alice"}, "GitHub · ID 12345"),
            ("google", {"name": "Alice"}, "Google · ID 12345"),
        )
        for provider, data, expected in cases:
            with self.subTest(provider=provider, data=data):
                account = SocialAccount(provider=provider, uid="12345", extra_data=data)
                self.assertEqual(social_account_label(account), expected)

    def test_unexpected_metadata_is_not_stringified_or_used_as_a_label(self):
        """Only display strings are accepted, never nested data or private metadata."""
        for data in (
            None,
            [],
            {
                "username": {"password": "private"},
                "name": ["private"],
                "sub": False,
                "access_token": "private",
                "email": "private",
            },
        ):
            with self.subTest(data=data):
                account = SocialAccount(
                    provider="telegram", uid="12345", extra_data=data
                )
                self.assertEqual(social_account_label(account), "Telegram · ID 12345")

    def test_labels_do_not_initialize_or_contact_a_provider(self):
        """Saved identities stay readable even when credentials have been removed."""
        account = SocialAccount(
            provider="telegram", uid="12345", extra_data={"preferred_username": "alice"}
        )
        with patch.object(
            account,
            "get_provider",
            side_effect=AssertionError("No provider initialization needed"),
        ):
            self.assertEqual(social_account_label(account), "Telegram · @alice")


@override_settings(
    GOOGLE_LOGIN_ENABLED=False, GITHUB_LOGIN_ENABLED=False, TELEGRAM_LOGIN_ENABLED=False
)
class SocialAccountLabelRenderingTests(AccountTestCase):
    """Use identical escaped labels in account rows and disconnect form choices."""

    def test_disabled_saved_profiles_are_distinct_in_overview_and_connections(self):
        """Disabling a provider does not hide its stored handle or fallback identifier."""
        accounts = (
            SocialAccount.objects.create(
                user=self.user,
                provider="telegram",
                uid="111",
                extra_data={"preferred_username": "alice"},
            ),
            SocialAccount.objects.create(
                user=self.user,
                provider="telegram",
                uid="222",
                extra_data={"name": "Alice"},
            ),
            SocialAccount.objects.create(
                user=self.user,
                provider="github",
                uid="333",
                extra_data={"login": "alice-dev"},
            ),
            SocialAccount.objects.create(
                user=self.user,
                provider="google",
                uid="444",
                extra_data={"email": "work@example.com"},
            ),
        )
        self.password_login()
        overview = self.client.get(reverse("core_account_overview"))
        connections = self.client.get(reverse("socialaccount_connections"))
        for account in accounts:
            label = social_account_label(account)
            with self.subTest(label=label):
                self.assertContains(overview, label)
                self.assertContains(connections, label)
                self.assertEqual(
                    connections.context["form"]
                    .fields["account"]
                    .label_from_instance(account),
                    label,
                )

    def test_provider_markup_is_escaped_and_private_metadata_is_never_rendered(self):
        """Remote display data stays text in both native HTML and Vue field metadata."""
        SocialAccount.objects.create(
            user=self.user,
            provider="telegram",
            uid="111",
            extra_data={
                "name": "<img src=x onerror=alert(1)>",
                "access_token": "DO-NOT-RENDER-TOKEN",
                "password": "DO-NOT-RENDER-PASSWORD",
            },
        )
        self.password_login()
        for route in ("core_account_overview", "socialaccount_connections"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, "&lt;img src=x onerror=alert(1)&gt;")
                self.assertContains(response, "ID 111")
                self.assertNotContains(response, "<img src=x onerror=alert(1)>")
                self.assertNotContains(response, "DO-NOT-RENDER-TOKEN")
                self.assertNotContains(response, "DO-NOT-RENDER-PASSWORD")
