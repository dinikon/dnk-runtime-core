from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CoreUserAdmin(UserAdmin):
    """Expose CORE identities in the admin protected by allauth authentication."""

    fieldsets = UserAdmin.fieldsets + (
        ("Телефон", {"fields": ("phone", "phone_verified")}),
    )
    readonly_fields = ("phone_verified",)
    list_display = UserAdmin.list_display + ("phone", "phone_verified")
    search_fields = UserAdmin.search_fields + ("phone",)

    def save_model(self, request, obj, form, change):
        """Normalize an empty optional phone before storing the admin edit."""
        if "phone" in form.changed_data:
            obj.phone = obj.phone or None
            obj.phone_verified = False
        super().save_model(request, obj, form, change)
