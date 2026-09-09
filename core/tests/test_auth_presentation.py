"""Keep progressive authentication presentation faithful to native form contracts."""

from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.test import override_settings

from accounts.presentation.login import channel_url
from tests.helpers import AccountTestCase, PASSWORD


class FormMarkup(HTMLParser):
    """Collect native form controls and IDs to detect ambiguous submissions."""

    def __init__(self, content):
        """Parse a rendered page without executing its enhancement scripts."""
        super().__init__()
        self.forms = []
        self.ids = []
        self.current = None
        self.feed(content.decode())

    def handle_starttag(self, tag, attrs):
        """Retain each form's action, named inputs, and globally addressed IDs."""
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "form":
            self.current = {"action": attrs.get("action"), "fields": {}}
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            self.current["fields"][attrs.get("name")] = attrs

    def handle_endtag(self, tag):
        """End collection at the native form boundary."""
        if tag == "form":
            self.current = None


class AuthPresentationTests(AccountTestCase):
    """Exercise disabled channels, invalid POSTs and pre-JavaScript form topology."""

    def test_channel_forms_have_unique_ids_and_keep_native_actions(self):
        """Rendering alternatives cannot deliver a code or mix their POST contracts."""
        with patch("accounts.integrations.telegram_gateway.requests.post") as gateway:
            response = self.client.get("/accounts/login/?next=/app/?source=cards")
        gateway.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        markup = FormMarkup(response.content)
        self.assertEqual(len(markup.ids), len(set(markup.ids)))
        forms = {form["action"]: form["fields"] for form in markup.forms}
        for action in ("/accounts/login/", "/accounts/login/code/"):
            self.assertEqual(forms[action]["next"]["value"], "/app/?source=cards")
            self.assertIn("csrfmiddlewaretoken", forms[action])
        self.assertIn("login", forms["/accounts/login/"])
        self.assertNotIn("phone", forms["/accounts/login/"])
        self.assertEqual(forms["/accounts/login/code/"]["channel"]["value"], "telegram")

    @override_settings(
        PHONE_LOGIN_ENABLED=False,
        EMAIL_CODE_LOGIN_ENABLED=False,
        ACCOUNT_LOGIN_BY_CODE_ENABLED=False,
    )
    def test_password_only_form_needs_no_code_url_or_selector(self):
        """A valid password-only configuration renders without unavailable code links."""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-channel-selector")
        self.assertNotContains(response, 'name="channel"')
        self.assertContains(response, 'name="password"')

    def test_invalid_phone_post_keeps_channel_and_error(self):
        """An invalid Telegram contact stays bound to its own displayed form."""
        response = self.client.post(
            "/accounts/login/code/",
            {
                "channel": "telegram",
                "phone": "invalid",
                "next": "/app/?phone=yes",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["code_channel"], "telegram")
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, 'data-login-panel="telegram" >')
        self.assertContains(response, 'value="invalid"')
        self.assertEqual(len(mail.outbox), 0)

    def test_direct_email_code_page_uses_code_form_in_password_mode(self):
        """A direct email-code URL never switches back to password submission."""
        response = self.client.get("/accounts/login/code/?channel=email&next=/app/")
        self.assertEqual(list(response.context["form"].fields), ["email"])
        self.assertContains(response, 'name="channel" value="email"')
        self.assertContains(response, "Войти с паролем")
        markup = FormMarkup(response.content)
        self.assertEqual(len(markup.ids), len(set(markup.ids)))

    def test_channel_url_preserves_nested_return_query(self):
        """Channel changes must not corrupt escaped return addresses."""
        result = channel_url(
            "/accounts/login/code/?next=%2Fapp%2F%3Fa%3D1%26b%3D2&channel=email",
            "telegram",
        )
        self.assertEqual(
            parse_qs(urlsplit(result).query),
            {"next": ["/app/?a=1&b=2"], "channel": ["telegram"]},
        )

    @override_settings(ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_CHANGE=True)
    def test_code_card_retains_contact_change_and_stage_cancel(self):
        """Optional contact editing and cancellation remain ordinary protected POSTs."""
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "card_signup",
                "email": "card@example.invalid",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        confirm_url = response.url
        response = self.client.get(confirm_url)
        self.assertTrue(response.context["can_change"])
        self.assertContains(response, 'name="action" value="change"')
        response = self.client.post(
            confirm_url,
            {"action": "change", "email": "changed@example.invalid"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "changed@example.invalid")
        self.assertContains(response, 'id="logout-from-stage"')
        self.client.post("/accounts/logout/", {"next": "/accounts/login/"})
        self.assert_anonymous()
