"""Small test fixtures shared by real browser authentication flows."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from allauth.account.models import EmailAddress

PASSWORD = "A-secure-test-password-123!"
LOGIN_CODE = "834719"
TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class AccountTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = self.create_user()

    def create_user(
        self, username="alice", email="alice@example.com", verified=True, **fields
    ):
        user = get_user_model().objects.create_user(
            username=username, email=email, password=PASSWORD, **fields
        )
        EmailAddress.objects.create(
            user=user, email=email, verified=verified, primary=True
        )
        return user

    def assert_anonymous(self, client=None):
        response = (client or self.client).get("/api/me/")
        self.assertEqual(response.status_code, 401, response.content)

    def password_login(self, client=None, **extra):
        return (client or self.client).post(
            "/accounts/login/",
            {"login": self.user.email, "password": PASSWORD, **extra},
        )
