"""The server contract remains usable before or without the Vue bundle."""

from django.test import override_settings
from tests.helpers import AccountTestCase


class FormRenderingTests(AccountTestCase):
    def test_invalid_login_never_echoes_password_and_keeps_local_next(self):
        secret = "Do-not-serialize-this-password!"
        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.username,
                "password": secret,
                "next": "/app/?source=form",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, secret)
        self.assertContains(response, 'name="next" value="/app/?source=form"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, "data-field-fallback")
        self.assertContains(response, 'role="alert"')

    def test_json_metadata_escapes_markup_in_values(self):
        response = self.client.post(
            "/accounts/login/",
            {
                "login": '</script><script>alert("xss")</script>',
                "password": "invalid",
            },
        )
        self.assertNotContains(response, '<script>alert("xss")</script>')
        self.assertContains(response, "\\u003C/script\\u003E")

    def test_delivery_channels_render_only_selected_contact_and_keep_next(self):
        response = self.client.get("/accounts/login/code/?channel=email&next=/app/")
        self.assertEqual(list(response.context["form"].fields), ["email"])
        self.assertContains(response, 'name="channel" value="email"')
        response = self.client.get("/accounts/login/code/?channel=telegram")
        self.assertEqual(list(response.context["form"].fields), ["phone"])
        self.assertContains(response, "Код в Telegram")
        with override_settings(PHONE_LOGIN_ENABLED=False):
            response = self.client.get("/accounts/login/")
            self.assertNotContains(response, "Код в Telegram")

    def test_signup_passkey_and_sensitive_forms_keep_native_fields(self):
        response = self.client.get("/accounts/signup/passkey/")
        self.assertEqual(
            set(response.context["form"].fields),
            {"username", "email", "first_name", "last_name", "middle_name"},
        )
        self.password_login()
        for path in (
            "/accounts/email/",
            "/accounts/password/change/",
            "/accounts/2fa/totp/activate/",
            "/accounts/2fa/webauthn/add/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, "data-field-fallback")
