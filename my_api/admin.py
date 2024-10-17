from django.contrib import admin
from .models import MyApiUser

class MyApiUserAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = ('username', 'email', 'is_active', "is_superuser", 'role', "email_verified")
    
    # Fields to search in the admin interface
    search_fields = ('username', 'email')
    
    # Filters to apply on the admin page
    list_filter = ('is_active', 'is_superuser', 'last_login', "email_verified")
    
    # Read-only fields (must be a list or tuple)
    readonly_fields = ('last_login',)
    
    # Fieldsets to control the layout of the admin form
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_superuser', "email_verified")}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    
    # This controls what fields are displayed when adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password'),
        }),
    )
    
    # This ensures the password is hashed correctly when saving a new user
    def save_model(self, request, obj, form, change):
        if not change:  # If the object is new
            obj.set_password(form.cleaned_data["password"])
        super().save_model(request, obj, form, change)

# Register the custom admin model
admin.site.register(MyApiUser, MyApiUserAdmin)
