"""Account administration with UUID memberships and read-only verified contacts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import PhoneNumber, User, UserGroupMembership, UserPermissionMembership


class PhoneNumberInline(admin.TabularInline):
    """Expose contact status without bypassing ownership verification services."""

    model = PhoneNumber
    fields = ("phone", "verified", "primary", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """Require phone enrollment through the verified account flow."""
        return False

    def has_view_permission(self, request, obj=None):
        """Keep contacts visible to staff authorized to inspect the parent account."""
        return request.user.has_perm("accounts.view_user") or request.user.has_perm(
            "accounts.change_user"
        )

    def has_change_permission(self, request, obj=None):
        """Never let the admin formset mutate contact verification or ownership."""
        return False


class UserMembershipInline(admin.TabularInline):
    """Retain the user editor's permission policy for explicit membership tables."""

    def has_view_permission(self, request, obj=None):
        """Allow membership inspection whenever the parent user may be viewed."""
        return request.user.has_perm(
            "accounts.view_user"
        ) or self.has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        """Keep grants editable by the same staff who could edit the old M2M fields."""
        return request.user.has_perm("accounts.change_user")

    def has_add_permission(self, request, obj=None):
        """Permit grants while creating or editing an authorized user account."""
        return self.has_change_permission(request, obj) or (
            obj is None and request.user.has_perm("accounts.add_user")
        )

    def has_delete_permission(self, request, obj=None):
        """Treat revocation as editing a user's permissions."""
        return self.has_change_permission(request, obj)


class UserGroupInline(UserMembershipInline):
    """Preserve staff group management with explicit UUID through records."""

    model = UserGroupMembership
    extra = 0


class UserPermissionInline(UserMembershipInline):
    """Preserve individual permission grants with explicit UUID through records."""

    model = UserPermissionMembership
    extra = 0
    raw_id_fields = ("permission",)


@admin.register(User)
class CoreUserAdmin(UserAdmin):
    """Expose CORE identities in the admin protected by allauth authentication."""

    fieldsets = tuple(
        (
            title,
            {
                **options,
                "fields": tuple(
                    field
                    for field in options["fields"]
                    if field not in {"groups", "user_permissions"}
                ),
            },
        )
        for title, options in UserAdmin.fieldsets
    ) + (("Дополнительные данные профиля", {"fields": ("middle_name",)}),)
    filter_horizontal = ()
    inlines = (PhoneNumberInline, UserGroupInline, UserPermissionInline)
    list_display = UserAdmin.list_display + ("primary_phone",)
    search_fields = UserAdmin.search_fields + ("phone_numbers__phone", "middle_name")

    def get_queryset(self, request):
        """Avoid a contact query per displayed account."""
        return super().get_queryset(request).prefetch_related("phone_numbers")

    @admin.display(description="Основной телефон")
    def primary_phone(self, obj):
        """Display only the confirmed primary contact."""
        return next(
            (contact.phone for contact in obj.phone_numbers.all() if contact.primary),
            "—",
        )
