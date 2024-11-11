from django.contrib import admin
from django.contrib.auth import get_user_model

from unfold.admin import ModelAdmin
from unfold.sites import UnfoldAdminSite

from .models import Comment, Issue, Like, MyApiOfficial, MyApiUser


class MyApiUserAdmin(ModelAdmin):
    list_display = (
        "username",
        "email",
        "is_active",
        "is_superuser",
        "role",
        "verified",
    )
    search_fields = ("username", "email")
    list_filter = ("is_active", "is_superuser", "last_login", "verified")
    readonly_fields = ("last_login", "password", "created_at")
    fieldsets = (
        (None, {"fields": ("username", "email", "password", "role")}),
        ("Permissions", {"fields": ("is_active", "is_superuser", "verified")}),
        ("Important dates", {"fields": ("created_at", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "password"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(form.cleaned_data["password"])
        super().save_model(request, obj, form, change)


class IssueAdmin(ModelAdmin):
    list_display = ("title", "issue_status", "created_at", "user")
    list_filter = ("issue_status", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("title", "description", "user", "categories", "images")}),
        ("Status", {"fields": ("issue_status",)}),
        ("Location", {"fields": ("latitude", "longitude")}),
        (
            "Metadata",
            {
                "fields": (
                    "likes_count",
                    "comments_count",
                    "is_anonymous",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


class CommentAdmin(ModelAdmin):
    list_display = ("issue", "user", "content", "created_at", "likes_count")
    search_fields = ("content",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")


class LikeAdmin(ModelAdmin):
    list_display = ("issue", "user", "created_at")
    search_fields = ("issue__title",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)


class MyApiOfficialAdmin(ModelAdmin):
    list_display = ("user", "area_range", "country_code")
    search_fields = ("user__username", "country_code")
    list_filter = ("country_code",)
    fieldsets = (
        (None, {"fields": ("user", "assigned_issues", "area_range", "country_code")}),
    )


class CustomAdminSite(UnfoldAdminSite):
    site_header = "Masla Bolo Admin"
    site_title = "Masla Bolo Admin"
    index_title = "Welcome to Masla Bolo"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["custom_message"] = "Welcome to the custom dashboard!"
        return super().index(request, extra_context=extra_context)


custom_admin_site = CustomAdminSite(name="custom_admin")

custom_admin_site.register(MyApiUser, MyApiUserAdmin)
custom_admin_site.register(Issue, IssueAdmin)
custom_admin_site.register(Comment, CommentAdmin)
custom_admin_site.register(Like, LikeAdmin)
custom_admin_site.register(MyApiOfficial, MyApiOfficialAdmin)
