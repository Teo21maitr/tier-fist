"""Django Admin des comptes (spec §6.1, §6.3, §56).

L'administrateur doit pouvoir : voir les comptes PENDING, en accepter, en
refuser (= supprimer), réinitialiser un mot de passe, voir les comptes actifs.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, UserCreationForm
from django.utils.html import format_html

from accounts.models import User, UserStatus


class TierFistUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = TierFistUserCreationForm
    change_password_form = AdminPasswordChangeForm
    ordering = ["-created_at"]
    list_display = ["username", "status_badge", "avatar_preview", "created_at", "last_login"]
    list_filter = ["status", "is_staff", "is_superuser"]
    search_fields = ["username"]
    readonly_fields = ["created_at", "updated_at", "last_login"]
    actions = ["approve_accounts", "reject_accounts"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Compte", {"fields": ("status", "avatar")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "status")}),
    )

    @admin.display(description="statut", ordering="status")
    def status_badge(self, obj: User) -> str:
        color = "#f59e0b" if obj.status == UserStatus.PENDING else "#22c55e"
        return format_html(
            '<b style="color:{}">{}</b>', color, obj.get_status_display()
        )

    @admin.display(description="avatar")
    def avatar_preview(self, obj: User) -> str:
        if not obj.avatar:
            return "—"
        return format_html(
            '<img src="{}" style="height:32px;width:32px;border-radius:50%;'
            'object-fit:cover" />',
            obj.avatar.url,
        )

    @admin.action(description="Accepter les comptes sélectionnés")
    def approve_accounts(self, request, queryset):
        updated = queryset.filter(status=UserStatus.PENDING).update(status=UserStatus.ACTIVE)
        self.message_user(
            request, f"{updated} compte(s) accepté(s).", level=messages.SUCCESS
        )

    @admin.action(description="Refuser les comptes sélectionnés (suppression définitive)")
    def reject_accounts(self, request, queryset):
        # Un compte refusé est supprimé : il n'existe pas de statut REJECTED.
        queryset = queryset.filter(status=UserStatus.PENDING)
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request, f"{count} demande(s) de compte refusée(s) et supprimée(s).",
            level=messages.WARNING,
        )
