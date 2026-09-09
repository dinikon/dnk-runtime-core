"""Preserve contacts and grants while moving application-owned records to UUID."""

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def copy_memberships(
    apps, schema_editor, field_name, model_name, target_name, reverse=False
):
    """Copy relation endpoints; each target table generates its own primary keys."""
    user = apps.get_model("accounts", "User")
    legacy = user._meta.get_field(field_name).remote_field.through
    explicit = apps.get_model("accounts", model_name)
    source, target = (explicit, legacy) if reverse else (legacy, explicit)
    database = schema_editor.connection.alias
    batch = []
    for user_id, target_id in (
        source.objects.using(database)
        .values_list("user_id", target_name + "_id")
        .iterator()
    ):
        batch.append(target(user_id=user_id, **{target_name + "_id": target_id}))
        if len(batch) >= 1000:
            target.objects.using(database).bulk_create(batch)
            batch = []
    if batch:
        target.objects.using(database).bulk_create(batch)


def copy_groups(apps, schema_editor):
    """Preserve group memberships before removing the automatic through table."""
    copy_memberships(apps, schema_editor, "groups", "UserGroupMembership", "group")


def restore_groups(apps, schema_editor):
    """Restore relation endpoints to the recreated legacy through table."""
    copy_memberships(
        apps, schema_editor, "groups", "UserGroupMembership", "group", reverse=True
    )


def copy_permissions(apps, schema_editor):
    """Preserve individual permission grants before switching through models."""
    copy_memberships(
        apps,
        schema_editor,
        "user_permissions",
        "UserPermissionMembership",
        "permission",
    )


def restore_permissions(apps, schema_editor):
    """Restore individual grants when rolling back an unused schema upgrade."""
    copy_memberships(
        apps,
        schema_editor,
        "user_permissions",
        "UserPermissionMembership",
        "permission",
        reverse=True,
    )


def copy_phones(apps, schema_editor):
    """Preserve every existing number and its verification status."""
    user = apps.get_model("accounts", "User")
    phone = apps.get_model("accounts", "PhoneNumber")
    database = schema_editor.connection.alias
    batch = []
    for account in (
        user.objects.using(database)
        .exclude(phone__isnull=True)
        .exclude(phone="")
        .iterator()
    ):
        batch.append(
            phone(
                user_id=account.pk,
                phone=account.phone,
                verified=account.phone_verified,
                primary=account.phone_verified,
            )
        )
        if len(batch) >= 1000:
            phone.objects.using(database).bulk_create(batch)
            batch = []
    if batch:
        phone.objects.using(database).bulk_create(batch)


def restore_phones(apps, schema_editor):
    """Refuse a lossy rollback once users have added multiple phone numbers."""
    from django.db.migrations.exceptions import IrreversibleError

    user = apps.get_model("accounts", "User")
    phone = apps.get_model("accounts", "PhoneNumber")
    database = schema_editor.connection.alias
    if (
        phone.objects.using(database)
        .values("user_id")
        .annotate(total=models.Count("pk"))
        .filter(total__gt=1)
        .exists()
    ):
        raise IrreversibleError(
            "Multiple phones cannot be restored to a single User.phone field."
        )
    for contact in phone.objects.using(database).iterator():
        user.objects.using(database).filter(pk=contact.user_id).update(
            phone=contact.phone, phone_verified=contact.verified
        )


class Migration(migrations.Migration):
    """Use separate tables so relation changes never rely on unsupported AlterField."""

    dependencies = [
        ("accounts", "0002_user_middle_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhoneNumber",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        max_length=16,
                        validators=[
                            django.core.validators.RegexValidator(
                                code="invalid_phone",
                                message="Введите номер в международном формате, например +380501234567.",
                                regex="^\\+[1-9][0-9]{5,14}$",
                            )
                        ],
                        verbose_name="Телефон",
                    ),
                ),
                (
                    "verified",
                    models.BooleanField(default=False, verbose_name="Подтверждён"),
                ),
                (
                    "primary",
                    models.BooleanField(default=False, verbose_name="Основной"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Добавлен"),
                ),
            ],
            options={
                "verbose_name": "Телефон",
                "verbose_name_plural": "Телефоны",
                "ordering": ["-primary", "created_at", "pk"],
            },
        ),
        migrations.CreateModel(
            name="UserGroupMembership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserPermissionMembership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
        migrations.RemoveConstraint(
            model_name="user",
            name="accounts_verified_phone_present",
        ),
        migrations.RemoveConstraint(
            model_name="user",
            name="accounts_phone_not_empty",
        ),
        migrations.AddField(
            model_name="phonenumber",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="phone_numbers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="usergroupmembership",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="auth.group",
            ),
        ),
        migrations.AddField(
            model_name="usergroupmembership",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_groups, restore_groups),
        migrations.RemoveField(model_name="user", name="groups"),
        migrations.AddField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="user_set",
                related_query_name="user",
                through="accounts.UserGroupMembership",
                to="auth.group",
                verbose_name="groups",
            ),
        ),
        migrations.AddField(
            model_name="userpermissionmembership",
            name="permission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="auth.permission",
            ),
        ),
        migrations.AddField(
            model_name="userpermissionmembership",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_permissions, restore_permissions),
        migrations.RemoveField(model_name="user", name="user_permissions"),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                through="accounts.UserPermissionMembership",
                to="auth.permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.RunPython(copy_phones, restore_phones),
        migrations.RemoveField(
            model_name="user",
            name="phone",
        ),
        migrations.RemoveField(
            model_name="user",
            name="phone_verified",
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.UniqueConstraint(
                fields=("user", "phone"), name="accounts_user_phone_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.UniqueConstraint(
                condition=models.Q(("verified", True)),
                fields=("phone",),
                name="accounts_verified_phone_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.UniqueConstraint(
                condition=models.Q(("primary", True)),
                fields=("user",),
                name="accounts_primary_phone_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("primary", False), ("verified", True), _connector="OR"
                ),
                name="accounts_primary_phone_verified",
            ),
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.CheckConstraint(
                condition=models.Q(("phone", ""), _negated=True),
                name="accounts_phone_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="usergroupmembership",
            constraint=models.UniqueConstraint(
                fields=("user", "group"), name="accounts_user_group_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="userpermissionmembership",
            constraint=models.UniqueConstraint(
                fields=("user", "permission"), name="accounts_user_permission_unique"
            ),
        ),
    ]
