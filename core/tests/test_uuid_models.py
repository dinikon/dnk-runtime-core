"""UUID ownership boundaries, Django permissions and non-destructive migrations."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.admin.sites import AdminSite
from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, SimpleTestCase, TransactionTestCase
from django.test.utils import isolate_apps
from django.urls import reverse

from accounts.checks import check_core_primary_keys
from accounts.admin import PhoneNumberInline, UserGroupInline, UserPermissionInline
from accounts.models import User, UserGroupMembership, UserPermissionMembership
from tests.helpers import AccountTestCase


class UUIDPolicyTests(SimpleTestCase):
    """Fail checks for accidental integer identities in local application models."""

    def test_all_owned_models_have_uuid_keys_and_third_party_models_are_exempt(self):
        """The source-owned application set includes explicit membership tables."""
        self.assertEqual(check_core_primary_keys(), [])
        for model in apps.get_app_config("accounts").get_models(
            include_auto_created=True
        ):
            self.assertIsInstance(model._meta.pk, models.UUIDField)
        self.assertNotIsInstance(Group._meta.pk, models.UUIDField)
        self.assertIsInstance(
            UserGroupMembership._meta.get_field("user").target_field, models.UUIDField
        )
        self.assertEqual(
            UserGroupMembership._meta.get_field("group").target_field, Group._meta.pk
        )

    @isolate_apps("accounts")
    def test_check_rejects_integer_models_and_automatic_through_tables(self):
        """Future mistakes fail Django checks before deployment or migration."""

        class IntegerIdentity(models.Model):
            """A deliberately invalid future local model."""

            class Meta:
                """Register only in this test's isolated app registry."""

                app_label = "accounts"

        class AutomaticRelation(models.Model):
            """A UUID model whose implicit through table violates the policy."""

            id = models.UUIDField(primary_key=True)
            peers = models.ManyToManyField("self")

            class Meta:
                """Register only in this test's isolated app registry."""

                app_label = "accounts"

        probe = SimpleNamespace(
            path=str(Path(__file__).resolve().parents[1] / "src" / "accounts"),
            get_models=lambda **kwargs: [
                IntegerIdentity,
                AutomaticRelation,
                AutomaticRelation.peers.through,
            ],
        )
        errors = check_core_primary_keys([probe])
        self.assertEqual([error.id for error in errors], ["core.E001", "core.E001"])


class UUIDPermissionTests(AccountTestCase):
    """Explicit through models keep native relation managers and permission checks."""

    def test_group_and_individual_grants_keep_native_permission_behavior(self):
        """Add, remove and clear operations work with generated UUID memberships."""
        permission = Permission.objects.get(
            codename="view_user", content_type__app_label="accounts"
        )
        group = Group.objects.create(name="CORE reviewers")
        group.permissions.add(permission)
        self.user.groups.add(group)
        membership = UserGroupMembership.objects.get(user=self.user, group=group)
        self.assertIsInstance(membership.pk, UUID)
        self.assertTrue(
            User.objects.get(pk=self.user.pk).has_perm("accounts.view_user")
        )
        self.user.groups.remove(group)
        self.assertFalse(
            User.objects.get(pk=self.user.pk).has_perm("accounts.view_user")
        )
        self.user.user_permissions.add(permission)
        self.assertIsInstance(
            UserPermissionMembership.objects.get(user=self.user).pk, UUID
        )
        self.assertTrue(
            User.objects.get(pk=self.user.pk).has_perm("accounts.view_user")
        )
        self.user.user_permissions.clear()
        self.assertFalse(
            User.objects.get(pk=self.user.pk).has_perm("accounts.view_user")
        )

    def test_staff_admin_uses_group_grants_and_readonly_phones(self):
        """The native admin remains reachable with permissions inherited from a group."""
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        group = Group.objects.create(name="Staff reviewers")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="accounts",
                codename__in=["view_user", "view_phonenumber"],
            )
        )
        self.user.groups.add(group)
        self.password_login()
        self.assertEqual(
            self.client.get(reverse("admin:accounts_user_changelist")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:accounts_user_change", args=[self.user.pk])
            ).status_code,
            200,
        )

    def test_membership_editing_retains_parent_user_permissions(self):
        """Changing through models must not remove existing staff editing abilities."""
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts", codename="change_user"
            )
        )
        request = RequestFactory().get("/admin/")
        request.user = self.user
        phones = PhoneNumberInline(User, AdminSite())
        self.assertTrue(phones.has_view_permission(request, self.user))
        self.assertFalse(phones.has_add_permission(request, self.user))
        self.assertFalse(phones.has_change_permission(request, self.user))
        self.assertFalse(phones.can_delete)
        for inline_class in (UserGroupInline, UserPermissionInline):
            inline = inline_class(User, AdminSite())
            self.assertTrue(inline.has_view_permission(request, self.user))
            self.assertTrue(inline.has_add_permission(request, self.user))
            self.assertTrue(inline.has_change_permission(request, self.user))
            self.assertTrue(inline.has_delete_permission(request, self.user))


class PhoneUUIDMigrationTests(TransactionTestCase):
    """Exercise the real historical schema before and after contact migration."""

    def test_existing_contacts_and_permission_memberships_are_preserved(self):
        """Copy values and relation endpoints without changing user identities or hashes."""
        before = [("accounts", "0002_user_middle_name")]
        after = [("accounts", "0003_phone_contacts_uuid_memberships")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(after))
        old = executor.loader.project_state(before).apps
        old_user = old.get_model("accounts", "User")
        first = old_user.objects.create(
            username="migration-owner",
            email="migration@example.invalid",
            password="preserved-hash",
            phone="+12025550901",
            phone_verified=True,
            middle_name="Сохранено",
        )
        pending = old_user.objects.create(
            username="migration-pending", phone="+12025550902", phone_verified=False
        )
        group = old.get_model("auth", "Group").objects.create(name="Preserved group")
        permission = old.get_model("auth", "Permission").objects.first()
        self.assertIsNotNone(permission)
        first.groups.add(group)
        first.user_permissions.add(permission)
        executor = MigrationExecutor(connection)
        executor.migrate(after)
        migrated = User.objects.get(pk=first.pk)
        self.assertEqual(migrated.password, "preserved-hash")
        self.assertEqual(migrated.middle_name, "Сохранено")
        self.assertEqual(list(migrated.groups.values_list("pk", flat=True)), [group.pk])
        self.assertEqual(
            list(migrated.user_permissions.values_list("pk", flat=True)),
            [permission.pk],
        )
        contact = migrated.phone_numbers.get()
        self.assertEqual(contact.phone, "+12025550901")
        self.assertTrue(contact.primary and contact.verified)
        self.assertIsInstance(contact.pk, UUID)
        other = User.objects.get(pk=pending.pk).phone_numbers.get()
        self.assertFalse(other.primary or other.verified)
        self.assertIsInstance(UserGroupMembership.objects.get(user=migrated).pk, UUID)
        self.assertIsInstance(
            UserPermissionMembership.objects.get(user=migrated).pk, UUID
        )
        tables = connection.introspection.table_names()
        self.assertNotIn("accounts_user_groups", tables)
        self.assertNotIn("accounts_user_user_permissions", tables)
        MigrationExecutor(connection).migrate(after)
        self.assertEqual(migrated.phone_numbers.get().pk, contact.pk)
