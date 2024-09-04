from rest_framework import permissions

class IsUser(permissions.BasePermission):
    """
    Permission for Users (Role 1)
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'user'


class IsOfficial(permissions.BasePermission):
    """
    Permission for Officials (Role 2)
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'official'


class IsAdmin(permissions.BasePermission):
    """
    Permission for Admins (Role 3)
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
