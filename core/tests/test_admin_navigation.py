"""Expose admin navigation for privileged accounts without changing permissions."""

from tests.helpers import AccountTestCase


class AdminNavigationTests(AccountTestCase):
    """Verify the same role policy in session JSON and server-rendered navigation."""

    def test_guest_and_regular_user_do_not_see_admin_navigation(self):
        """Anonymous and ordinary accounts must not receive the admin entry point."""
        self.assertFalse(self.client.get("/api/session/").json()["showAdminLink"])
        self.assertNotContains(self.client.get("/accounts/login/"), 'href="/admin/"')
        self.client.force_login(self.user)
        self.assertFalse(self.client.get("/api/session/").json()["showAdminLink"])
        self.assertNotContains(self.client.get("/accounts/"), 'href="/admin/"')

    def test_staff_and_superusers_receive_admin_navigation(self):
        """Either supported privileged flag exposes a fixed, local admin URL."""
        for flags in (
            {"is_staff": True, "is_superuser": False},
            {"is_staff": False, "is_superuser": True},
            {"is_staff": True, "is_superuser": True},
        ):
            with self.subTest(**flags):
                for name, value in flags.items():
                    setattr(self.user, name, value)
                self.user.save(update_fields=list(flags))
                self.client.force_login(self.user)
                self.assertTrue(
                    self.client.get("/api/session/").json()["showAdminLink"]
                )
                self.assertContains(self.client.get("/accounts/"), 'href="/admin/"')
                self.assertNotIn("is_staff", self.client.get("/api/me/").json())

    def test_deactivated_staff_session_loses_admin_navigation(self):
        """Revoked activity cannot keep privileged navigation through an old session."""
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.get("/api/session/").json()
        self.assertFalse(response["authenticated"])
        self.assertFalse(response["showAdminLink"])
